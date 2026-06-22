from typing import Any

from config import (
    ENRICHMENT_FILENAME,
    REVERSING_AGENT_RESULT_FILENAME,
    REVERSING_AGENT_TOOLS_PATH,
)
from ai.agents.reversing import ReversingAgent
from ai.model_registry import ModelRegistry
from ai.runner.base import BaseAIRunner
from ai.runtime.memory import AgentMemory
from ai.runtime.priority_queue import TargetPriorityQueue
from ai.runtime.validators import validate_tool_parameters
from orchestrator.context import AnalysisContext
from tools.reversing.analyzers.reconnaissance import collect_reconnaissance
from tools.runner.reversing import ReversingAgentToolRunner
from utils.artifacts.documents import EMPTY_DOCUMENT_BODY, ENRICHMENT_TITLE, MarkdownDocument
from utils.io.files import load_json
from utils.io.text import read_text
from utils.logger import Logger
from utils.preprocessing.chunks import chunk_large_value


DEFAULT_REVERSING_BUDGET = 12
DEFAULT_TARGET_PRIORITY = 50


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
        self.targets = TargetPriorityQueue()
        self.memory = AgentMemory(
            output_dir=self.context.output,
            filename=REVERSING_AGENT_RESULT_FILENAME,
            agent_name="reverse_agent",
        )


    def _load_enrichment(self) -> str:
        path = self.context.output / ENRICHMENT_FILENAME
        document = MarkdownDocument(path, ENRICHMENT_TITLE)
        content = document.sanitize(read_text(path))
        if not content:
            return ""

        body = document.extract_body(content)
        return "" if body == EMPTY_DOCUMENT_BODY else body


    def _normalize_target(self, target: Any) -> dict[str, Any] | None:
        if not isinstance(target, dict):
            return None

        tool_name = target.get("tool")
        parameters = target.get("parameters")
        if not isinstance(tool_name, str) or not isinstance(parameters, dict):
            return None

        tool_spec = self.available_tools.get(tool_name)
        if not isinstance(tool_spec, dict):
            return None
        if not validate_tool_parameters(parameters, tool_spec):
            return None

        try:
            priority = int(target.get("priority", DEFAULT_TARGET_PRIORITY))
        except (TypeError, ValueError):
            priority = DEFAULT_TARGET_PRIORITY

        return {
            "tool": tool_name,
            "parameters": parameters,
            "priority": max(1, min(priority, 100)),
            "reason": str(target.get("reason") or "").strip(),
        }


    def _enqueue_targets(
        self,
        targets: Any,
        source: str,
    ) -> None:
        if not isinstance(targets, list):
            return

        for target in targets:
            normalized = self._normalize_target(target)
            if normalized is not None and self.targets.push(normalized):
                self.memory.record_queue_event(
                    action="added",
                    target=normalized,
                    queue_size=self.targets.size(),
                    source=source,
                )


    def _fallback_targets(
        self,
        reconnaissance: dict[str, Any],
    ) -> list[dict[str, Any]]:
        targets = [
            {
                "tool": "import_xrefs",
                "parameters": {"import_name": item["name"]},
                "priority": 90,
                "reason": "Suspicious import discovered during reconnaissance.",
            }
            for item in reconnaissance["suspicious_imports"][:5]
            if item.get("name")
        ]
        targets.extend(
            {
                "tool": "disassembly",
                "parameters": {
                    "function": item["name"],
                    "max_instructions": 200,
                },
                "priority": 80,
                "reason": "Large function discovered during reconnaissance.",
            }
            for item in reconnaissance["large_functions"][:3]
            if item.get("name")
        )
        targets.extend(
            {
                "tool": "string_xrefs",
                "parameters": {"value": item["value"]},
                "priority": 70,
                "reason": "Interesting string discovered during reconnaissance.",
            }
            for item in reconnaissance["interesting_strings"][:3]
            if item.get("value")
        )
        return targets


    def _input_ref(
        self,
        target: dict[str, Any],
        chunk_index: int | None = None,
    ) -> dict[str, Any]:
        tool_name = target["tool"]
        parameters = target["parameters"]

        if tool_name in {"function", "disassembly", "callers", "callees"}:
            input_type = "function"
            value = parameters.get("function")
        elif tool_name == "string_xrefs":
            input_type = "string_xref"
            value = parameters.get("value")
        elif tool_name == "import_xrefs":
            input_type = "import_xref"
            value = parameters.get("import_name")
        else:
            input_type = tool_name
            value = None

        result = {
            "type": input_type,
            "value": value,
        }
        if chunk_index is not None:
            result["index"] = chunk_index
        return result


    def _step_decision(
        self,
        analysis: dict[str, Any],
    ) -> dict[str, Any]:
        next_targets = analysis.get("next_targets")
        first_target = (
            next_targets[0]
            if isinstance(next_targets, list)
            and next_targets
            and isinstance(next_targets[0], dict)
            else None
        )

        if first_target is not None:
            action = first_target.get("tool", "none")
            parameters = first_target.get("parameters", {})
        elif analysis.get("finish") is True:
            action = "finish"
            parameters = {}
        else:
            action = "none"
            parameters = {}

        return {
            "thought": analysis.get("thought", ""),
            "confidence": analysis.get("confidence", "low"),
            "action": action,
            "parameters": parameters if isinstance(parameters, dict) else {},
        }


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
            "action": first_target.get("tool", "finish") if first_target else "finish",
            "parameters": (
                first_target.get("parameters", {})
                if first_target
                else {}
            ),
        }


    def _analyze_target(
        self,
        agent: ReversingAgent,
        enrichment: str,
        target: dict[str, Any],
        tool_output: dict[str, Any],
    ) -> None:
        chunks = chunk_large_value(target["tool"], tool_output.get("data"))
        for chunk_index, chunk in enumerate(chunks, start=1):
            error = None
            try:
                analysis = agent.analyze_evidence(
                    enrichment=enrichment,
                    target=target,
                    chunk=chunk,
                    chunk_index=chunk_index,
                    total_chunks=len(chunks),
                    available_tools=self.available_tools,
                )
            except Exception as exc:
                error = str(exc)
                Logger.error(
                    f"Reversing agent failed for {target['tool']} "
                    f"chunk {chunk_index}: {exc}"
                )
                analysis = {
                    "relevant": False,
                    "thought": "The evidence chunk could not be analyzed.",
                    "confidence": "low",
                    "finding": None,
                    "next_targets": [],
                    "finish": False,
                }

            finding = analysis.get("finding")
            if analysis.get("relevant") is not True or not isinstance(finding, dict):
                finding = None

            self.memory.record(
                decision=self._step_decision(analysis),
                tool_name=target["tool"],
                tool_output=tool_output,
                input_ref=self._input_ref(target, chunk_index),
                finding=finding,
                error=error,
            )
            self._enqueue_targets(
                analysis.get("next_targets"),
                source="follow_up",
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

            seed = agent.create_initial_targets(
                enrichment=enrichment,
                reconnaissance=reconnaissance,
                available_tools=self.available_tools,
            )
            targets = seed.get("targets")
            missing_targets = not isinstance(targets, list) or not targets
            fallback_used = missing_targets and not enrichment
            if fallback_used:
                targets = self._fallback_targets(reconnaissance)
                seed = {
                    "reasoning": "Using deterministic reconnaissance fallback.",
                    "targets": targets,
                }
            elif missing_targets:
                targets = []

            self.memory.record(
                decision=self._seed_decision(seed),
                input_ref={
                    "type": "initialization",
                    "value": "enrichment" if enrichment else "reconnaissance",
                },
            )
            self._enqueue_targets(
                targets,
                source="fallback" if fallback_used else "seed",
            )

            while (
                self.targets.has_items()
                and self.targets.visited_count() < self.budget
            ):
                target = self.targets.pop()
                self.memory.record_queue_event(
                    action="removed",
                    target=target,
                    queue_size=self.targets.size(),
                    source="execution",
                )
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
                else:
                    self.memory.record(
                        decision={
                            "thought": target["reason"],
                            "confidence": "low",
                            "action": target["tool"],
                            "parameters": target["parameters"],
                        },
                        tool_name=target["tool"],
                        tool_output=tool_output,
                        input_ref=self._input_ref(target),
                    )
        except KeyboardInterrupt:
            self.memory.close(status="interrupted")
            raise
        except Exception as exc:
            self.memory.fail(str(exc))
            raise
        else:
            self.memory.close()

        Logger.success("Reversing agent finished")
