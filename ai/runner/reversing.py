from typing import Any

from ai.agents.reversing import ReversingAgent
from ai.model_registry import ModelRegistry
from ai.runner.base import BaseAIRunner
from ai.runtime.memory import AgentMemory
from ai.runtime.reversing_targets import ReversingTargetQueue
from config import (
    ENRICHMENT_FILENAME,
    REVERSING_AGENT_RESULT_FILENAME,
    REVERSING_AGENT_TOOLS_PATH,
)
from orchestrator.context import AnalysisContext
from tools.reversing.analyzers.reconnaissance import collect_reconnaissance
from tools.runner.reversing import ReversingAgentToolRunner
from utils.artifacts.documents import (
    EMPTY_DOCUMENT_BODY,
    ENRICHMENT_TITLE,
    MarkdownDocument,
)
from utils.io.files import load_json
from utils.io.text import read_text
from utils.logger import Logger
from utils.postprocessing.reversing import ReversingPostprocessor
from utils.preprocessing.reversing import chunk_reversing_evidence


class ReversingAgentRunner(BaseAIRunner):
    def __init__(
        self,
        context: AnalysisContext,
        model_registry: ModelRegistry,
    ) -> None:
        super().__init__(context)
        self.model_registry = model_registry
        self.budget = context.reversing_budget
        self.available_tools = load_json(
            REVERSING_AGENT_TOOLS_PATH.parent,
            REVERSING_AGENT_TOOLS_PATH.name,
        ) or {}
        self.tool_runner = ReversingAgentToolRunner(context)
        self.memory = AgentMemory(
            output_dir=self.context.output,
            filename=REVERSING_AGENT_RESULT_FILENAME,
            agent_name="reverse_agent",
        )
        self.targets = ReversingTargetQueue(
            available_tools=self.available_tools,
            memory=self.memory,
        )
        self.postprocessor = ReversingPostprocessor(self.available_tools)


    def _load_enrichment(self) -> str:
        path = self.context.output / ENRICHMENT_FILENAME
        document = MarkdownDocument(path, ENRICHMENT_TITLE)
        content = document.sanitize(read_text(path))
        if not content:
            return ""

        body = document.extract_body(content)
        return "" if body == EMPTY_DOCUMENT_BODY else body


    def _seed_decision(
        self,
        seed: dict[str, Any],
    ) -> dict[str, Any]:
        targets = seed.get("targets")
        first_target = (
            targets[0]
            if isinstance(targets, list)
            and targets
            and isinstance(targets[0], dict)
            else None
        )
        return {
            "thought": str(seed.get("reasoning") or ""),
            "confidence": "medium" if first_target else "low",
            "action": "seed_queue",
            "parameters": {},
        }


    def _analyze_target(
        self,
        agent: ReversingAgent,
        enrichment: str,
        target: dict[str, Any],
        tool_output: dict[str, Any],
    ) -> None:
        chunks = chunk_reversing_evidence(
            target["tool"],
            tool_output.get("data"),
        )
        observation = self.postprocessor.observation_summary(
            target,
            tool_output,
        )

        for chunk_index, chunk in enumerate(chunks, start=1):
            error = None
            try:
                analysis = agent.analyze_evidence(
                    enrichment=enrichment,
                    target=target,
                    observation=observation,
                    chunk=chunk,
                    chunk_index=chunk_index,
                    total_chunks=len(chunks),
                    available_tools=self.available_tools,
                )
            except Exception as first_exc:
                try:
                    Logger.warning(
                        f"Retrying {target['tool']} chunk {chunk_index} "
                        "without enrichment context"
                    )
                    analysis = agent.analyze_evidence(
                        enrichment="",
                        target=target,
                        observation=observation,
                        chunk=chunk,
                        chunk_index=chunk_index,
                        total_chunks=len(chunks),
                        available_tools=self.available_tools,
                    )
                except Exception as retry_exc:
                    error = (
                        f"Initial LLM error: {first_exc}; "
                        f"compact retry error: {retry_exc}"
                    )
                    Logger.error(
                        f"Reversing agent failed for {target['tool']} "
                        f"chunk {chunk_index}: {error}"
                    )
                    analysis = {
                        "thought": "LLM decision failed.",
                        "confidence": "low",
                        "action": "none",
                        "parameters": {},
                        "finding": None,
                    }

            finding = self.postprocessor.finding(
                analysis.get("finding"),
                target,
                observation,
            )
            follow_up = self.postprocessor.follow_up_target(
                analysis,
                target,
                observation,
            )
            self.memory.record(
                decision=self.postprocessor.trace_decision(
                    analysis,
                    target,
                    observation,
                ),
                tool_name=target["tool"],
                tool_output=tool_output,
                input_ref=self.postprocessor.input_ref(target, chunk_index),
                finding=finding,
                error=error,
            )
            if follow_up is not None:
                self.targets.enqueue([follow_up], source="follow_up")


    def _initial_targets(
        self,
        agent: ReversingAgent,
        enrichment: str,
        reconnaissance: dict[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]], str, str | None]:
        seed_error = None
        try:
            seed = agent.create_initial_targets(
                enrichment=enrichment,
                reconnaissance=reconnaissance,
                available_tools=self.available_tools,
            )
        except Exception as exc:
            seed_error = str(exc)
            Logger.error(f"Reversing seed decision failed: {exc}")
            seed = {
                "reasoning": "LLM decision failed.",
                "targets": [],
            }

        raw_targets = seed.get("targets")
        targets = (
            raw_targets[:6]
            if isinstance(raw_targets, list) and raw_targets
            else []
        )
        source = "seed"
        if not targets and not enrichment:
            targets = self.targets.fallback_targets(reconnaissance)
            seed = {
                "reasoning": "Using deterministic reconnaissance fallback.",
                "targets": targets,
            }
            source = "fallback"

        return seed, targets, source, seed_error


    def _execute_queue(
        self,
        agent: ReversingAgent,
        enrichment: str,
    ) -> None:
        while (
            self.targets.has_items()
            and self.targets.visited_count() < self.budget
        ):
            target = self.targets.pop()
            Logger.info(
                f"Reversing agent target: {target['tool']} "
                f"({self.targets.visited_count()}/{self.budget})"
            )
            tool_output = self.tool_runner.execute(
                target["tool"],
                target["parameters"],
            )

            if tool_output.get("success") is True:
                self._analyze_target(
                    agent=agent,
                    enrichment=enrichment,
                    target=target,
                    tool_output=tool_output,
                )
                continue

            self.memory.record(
                decision={
                    "thought": target["reason"],
                    "confidence": "low",
                    "action": target["tool"],
                    "parameters": target["parameters"],
                },
                tool_name=target["tool"],
                tool_output=tool_output,
                input_ref=self.postprocessor.input_ref(target),
            )


    def run(self) -> None:
        Logger.info("Running AI reversing agent")

        try:
            enrichment = self._load_enrichment()
            reconnaissance = (
                {}
                if enrichment
                else collect_reconnaissance(str(self.context.sample))
            )
            llm = self.model_registry.create_agent_client(
                "reversing",
                profile_override=self.context.profile,
            )
            agent = ReversingAgent(llm)
            seed, targets, source, seed_error = self._initial_targets(
                agent,
                enrichment,
                reconnaissance,
            )

            self.memory.record(
                decision=self._seed_decision(seed),
                input_ref={
                    "type": "initialization",
                    "value": "enrichment" if enrichment else "reconnaissance",
                },
                error=seed_error,
            )
            self.targets.enqueue(targets, source=source)
            self._execute_queue(agent, enrichment)
        except KeyboardInterrupt:
            self.memory.close(status="interrupted")
            raise
        except Exception as exc:
            self.memory.fail(str(exc))
            raise
        else:
            self.memory.close()

        Logger.success("Reversing agent finished")
