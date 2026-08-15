from typing import Any

from core.utils.logger import Logger
from core.utils.postprocessing.reversing import ReversingPostprocessor
from core.utils.preprocessing.reversing.reversing import chunk_reversing_evidence
from core.ai.agents.reversing import ReversingAgent
from core.ai.runtime.memory import TraceMemory
from core.ai.runtime.reversing.targets import ReversingTargetQueue
from core.utils.reversing.address import parse_address


FOLLOW_UP_PRIORITY_BOOST = 5
EXTERNAL_CODE_PREFIXES = ("sym.imp.", "imp.", "reloc.", "fcn.imp.")


class ReversingEvidenceEvaluator:
    def __init__(
        self,
        agent: ReversingAgent,
        enrichment: str,
        available_tools: dict[str, Any],
        postprocessor: ReversingPostprocessor,
        memory: "TraceMemory",
        targets: "ReversingTargetQueue",
    ) -> None:
        self.agent = agent
        self.enrichment = enrichment
        self.available_tools = available_tools
        self.postprocessor = postprocessor
        self.memory = memory
        self.targets = targets

    def evaluate(
        self,
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
        self._enqueue_deterministic_follow_ups(target, tool_output)

        for chunk_index, chunk in enumerate(chunks, start=1):
            analysis, error = self._analyze_chunk(
                target,
                observation,
                chunk,
                chunk_index,
                len(chunks),
            )
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

    def _enqueue_deterministic_follow_ups(
        self,
        target: dict[str, Any],
        tool_output: dict[str, Any],
    ) -> None:
        follow_ups = self._deterministic_follow_ups(target, tool_output)
        if not follow_ups:
            return

        added = self.targets.enqueue(follow_ups, source="follow_up")
        tool_name = target.get("tool")
        Logger.info(
            f"Queued {added}/{len(follow_ups)} deterministic reversing follow-ups "
            f"from {tool_name}"
        )

    def _deterministic_follow_ups(
        self,
        target: dict[str, Any],
        tool_output: dict[str, Any],
    ) -> list[dict[str, Any]]:
        tool_name = target.get("tool")
        data = tool_output.get("data")
        if not isinstance(tool_name, str) or not isinstance(data, dict):
            return []

        if tool_name in {"import_xrefs", "string_xrefs"}:
            return self._xref_follow_ups(target, data)
        if tool_name == "disassembly":
            return self._disassembly_follow_ups(target, data)

        return []

    def _xref_follow_ups(
        self,
        target: dict[str, Any],
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        follow_ups = []

        for match in self._dict_items(data.get("matches")):
            for xref in self._dict_items(match.get("xrefs")):
                address = self._xref_address(xref)
                if address is None:
                    continue

                follow_ups.append(
                    self._follow_up_target(
                        target,
                        address,
                        str(xref.get("type") or "xref"),
                        "Code reference discovered by xref search.",
                    )
                )

        return follow_ups

    def _xref_address(self, xref: dict[str, Any]) -> str | None:
        for key in ("function", "from", "address"):
            address = self._format_address(xref.get(key))
            if address is not None:
                return address

        return None

    def _disassembly_follow_ups(
        self,
        target: dict[str, Any],
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        follow_ups = []
        current_start = parse_address(data.get("start_address"))
        current_end = parse_address(data.get("end_address"))

        for line in self._instruction_lines(data.get("instructions")):
            relation, raw_target = self._direct_code_reference(line)
            if relation is None or raw_target is None:
                continue
            if self._is_external_code_target(raw_target):
                continue

            address = self._format_address(raw_target)
            if address is None:
                continue
            if self._inside_current_function(address, current_start, current_end):
                continue

            follow_ups.append(
                self._follow_up_target(
                    target,
                    address,
                    relation,
                    "Direct internal code reference discovered in disassembly.",
                )
            )

        return follow_ups

    def _follow_up_target(
        self,
        origin: dict[str, Any],
        address: str,
        relation: str,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "tool": "disassembly",
            "parameters": {
                "address": address,
            },
            "priority": self._follow_up_priority(origin),
            "reason": reason,
            "origin_tool": origin.get("tool"),
            "origin_target": self._origin_target(origin),
            "discovered_target": address,
            "relation": relation,
        }

    def _follow_up_priority(self, origin: dict[str, Any]) -> int:
        try:
            priority = int(origin.get("priority", 50))
        except (TypeError, ValueError):
            priority = 50

        return min(100, priority + FOLLOW_UP_PRIORITY_BOOST)

    def _origin_target(self, target: dict[str, Any]) -> str | None:
        parameters = target.get("parameters")
        if not isinstance(parameters, dict):
            return None

        for key in ("address", "import_name", "value", "section"):
            value = parameters.get(key)
            if isinstance(value, str) and value:
                return value

        return None

    def _direct_code_reference(self, line: str) -> tuple[str | None, str | None]:
        _, separator, instruction = line.partition(":")
        if not separator:
            return None, None

        parts = instruction.strip().split()
        if len(parts) < 2:
            return None, None

        mnemonic = parts[0].lower()
        if mnemonic == "call":
            return "call", parts[1].rstrip(",")
        if mnemonic.startswith("j"):
            return "jump", parts[1].rstrip(",")

        return None, None

    def _inside_current_function(
        self,
        address: str,
        current_start: int | None,
        current_end: int | None,
    ) -> bool:
        parsed_address = parse_address(address)
        return (
            parsed_address is not None
            and current_start is not None
            and current_end is not None
            and current_start <= parsed_address < current_end
        )

    def _is_external_code_target(self, value: str) -> bool:
        normalized = value.strip().lower()
        return (
            normalized.startswith(EXTERNAL_CODE_PREFIXES)
            or ".dll" in normalized
        )

    def _format_address(self, value: Any) -> str | None:
        address = parse_address(value)
        if address is None:
            return None

        return hex(address)

    def _instruction_lines(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []

        return [
            item
            for item in value
            if isinstance(item, str) and item.strip()
        ]

    def _dict_items(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []

        return [
            item
            for item in value
            if isinstance(item, dict)
        ]

    def _analyze_chunk(
        self,
        target: dict[str, Any],
        observation: dict[str, Any],
        chunk: Any,
        chunk_index: int,
        total_chunks: int,
    ) -> tuple[dict[str, Any], str | None]:
        try:
            return self._request_analysis(
                self.enrichment,
                target,
                observation,
                chunk,
                chunk_index,
                total_chunks,
            ), None
        except Exception as first_exc:
            return self._retry_without_enrichment(
                first_exc,
                target,
                observation,
                chunk,
                chunk_index,
                total_chunks,
            )

    def _retry_without_enrichment(
        self,
        first_exc: Exception,
        target: dict[str, Any],
        observation: dict[str, Any],
        chunk: Any,
        chunk_index: int,
        total_chunks: int,
    ) -> tuple[dict[str, Any], str | None]:
        try:
            Logger.warning(
                f"Retrying {target['tool']} chunk {chunk_index} "
                "without enrichment context"
            )
            analysis = self._request_analysis(
                "",
                target,
                observation,
                chunk,
                chunk_index,
                total_chunks,
            )
            return analysis, None
        except Exception as retry_exc:
            error = (
                f"Initial LLM error: {first_exc}; "
                f"compact retry error: {retry_exc}"
            )
            Logger.error(
                f"Reversing agent failed for {target['tool']} "
                f"chunk {chunk_index}: {error}"
            )
            return {
                "thought": "LLM decision failed.",
                "confidence": "low",
                "action": "none",
                "parameters": {},
                "finding": None,
            }, error

    def _request_analysis(
        self,
        enrichment: str,
        target: dict[str, Any],
        observation: dict[str, Any],
        chunk: Any,
        chunk_index: int,
        total_chunks: int,
    ) -> dict[str, Any]:
        return self.agent.analyze_evidence(
            enrichment=enrichment,
            target=target,
            observation=observation,
            chunk=chunk,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            available_tools=self.available_tools,
        )
