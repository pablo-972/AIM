from typing import Any

from core.ai.runtime.reversing.parameters import display_target_value

REVERSING_INVESTIGATION_TOOL_NAMES = {
    "disassembly",
    "callers",
    "callees",
    "inspect_section",
    "string_xrefs",
    "import_xrefs",
    "list_imports",
    "list_functions",
    "list_sections",
    "list_entrypoints",
}


class ReversingTraceFormatter:
    def step(
        self,
        step_number: int,
        decision: dict[str, Any],
        tool_name: str | None = None,
        tool_parameters: dict[str, Any] | None = None,
        tool_output: dict[str, Any] | None = None,
        input_ref: dict[str, Any] | None = None,
        finding: dict[str, Any] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        return {
            "step": step_number,
            "input": self.input(
                input_ref,
                tool_name,
                tool_parameters,
                tool_output,
            ),
            "decision": self.decision(decision),
            "finding": self.finding(finding),
            "tool_calls": self.tool_calls(tool_calls),
            "error": error or self.tool_error(tool_output),
        }

    def queue_event(
        self,
        event_number: int,
        action: str,
        target: dict[str, Any],
        queue_size: int,
        source: str,
    ) -> dict[str, Any]:
        event: dict[str, Any] = {
            "event": event_number,
            "action": action,
            "source": source,
            "queue_size": queue_size,
        }

        tool = target.get("tool")
        parameters = target.get("parameters")
        if isinstance(tool, str):
            event["tool"] = tool
        if isinstance(parameters, dict):
            target_value = display_target_value(tool, parameters)
            if target_value is not None:
                event["target"] = target_value

        priority = target.get("priority")
        if isinstance(priority, int):
            event["priority"] = priority

        validation = self._compact_validation(target.get("validation"))
        if validation is not None:
            event["validation"] = validation
            self._fill_event_target_from_validation(event, validation)

        origin = self._compact_origin(target)
        if origin:
            event["origin"] = origin

        return event

    def input(
        self,
        input_ref: dict[str, Any] | None,
        tool_name: str | None,
        tool_parameters: dict[str, Any] | None,
        tool_output: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not isinstance(input_ref, dict):
            input_ref = {}

        input_type = input_ref.get("type")
        if input_type == "initialization":
            return {
                "type": "initialization",
                "source": input_ref.get("value"),
            }

        parameters = self._parameters(tool_parameters)
        target = display_target_value(tool_name, parameters)
        compact: dict[str, Any] = {}

        if isinstance(tool_name, str):
            compact["tool"] = tool_name
        else:
            compact["type"] = self._input_type(tool_name, input_type)

        if target is not None:
            compact["target"] = target
        elif input_ref.get("value") is not None:
            compact["target"] = input_ref.get("value")

        index = input_ref.get("index")
        total_chunks = input_ref.get("total_chunks")

        if index is not None:
            compact["chunk"] = index
        if total_chunks is not None:
            compact["total_chunks"] = total_chunks
        if tool_name == "disassembly":
            total_instructions = self._total_instructions(tool_output)
            if total_instructions is not None:
                compact["total_instructions"] = total_instructions
        status = self._tool_status(tool_output)
        if status is not None:
            compact["status"] = status

        return compact

    def decision(self, decision: dict[str, Any]) -> dict[str, Any]:
        confidence = decision.get("confidence")
        if confidence not in {"low", "medium", "high"}:
            confidence = "unknown"

        summary = decision.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            summary = "No decision summary was recorded."
        else:
            summary = summary.strip()

        thinking = decision.get("thinking")
        if not isinstance(thinking, list):
            thinking = []

        clean_thinking = [
            line.strip()
            for line in thinking
            if isinstance(line, str) and line.strip()
        ]
        return {
            "thinking": clean_thinking,
            "summary": summary,
            "confidence": confidence,
        }

    def _total_instructions(
        self,
        tool_output: dict[str, Any] | None,
    ) -> int | None:
        if not isinstance(tool_output, dict):
            return None

        data = tool_output.get("data")
        if not isinstance(data, dict):
            return None

        for key in ("instructions_count", "returned_instructions"):
            value = data.get(key)
            if isinstance(value, int):
                return value

        instructions = data.get("instructions")
        if isinstance(instructions, list):
            return len(instructions)
        if isinstance(instructions, str):
            return len([
                line
                for line in instructions.splitlines()
                if line.strip()
            ])

        return None

    def _tool_status(self, tool_output: dict[str, Any] | None) -> str | None:
        if not isinstance(tool_output, dict):
            return None

        success = tool_output.get("success")
        if success is True:
            return "ok"
        if success is False:
            return "error"

        return None

    def finding(self, finding: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(finding, dict):
            return None

        evidence = finding.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            return None

        clean_evidence = [
            item.strip()
            for item in evidence
            if isinstance(item, str) and item.strip()
        ]
        if not clean_evidence:
            return None

        return {
            "type": self._string_or_default(
                finding.get("type"),
                "reverse_engineering",
            ),
            "category": self._string_or_default(
                finding.get("category"),
                "unknown",
            ),
            "confidence": self._confidence(finding.get("confidence")),
            "summary": self._string_or_default(
                finding.get("summary"),
                "Reversing evidence identified a relevant code region.",
            ),
            "evidence": list(dict.fromkeys(clean_evidence)),
        }

    def tool_calls(
        self,
        tool_calls: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        if not isinstance(tool_calls, list):
            return []

        compact = []
        for tool_call in tool_calls:
            item = self._compact_target(tool_call)
            if item is not None:
                compact.append(item)

        return compact

    def tool_error(self, tool_output: dict[str, Any] | None) -> str | None:
        if not isinstance(tool_output, dict):
            return None
        if tool_output.get("success") is not False:
            return None

        error = tool_output.get("error") or tool_output.get("message")
        return str(error) if error else "Tool execution failed."

    def _input_type(self, tool_name: str | None, input_type: Any) -> str:
        if tool_name in {"disassembly", "callers", "callees"}:
            return "code"
        if tool_name == "import_xrefs":
            return "import"
        if tool_name == "string_xrefs":
            return "string"
        if tool_name == "inspect_section":
            return "section"
        if isinstance(tool_name, str) and tool_name.startswith("list_"):
            return "discovery"
        if isinstance(input_type, str) and input_type:
            return input_type

        return "unknown"

    def _compact_target(self, target: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(target, dict):
            return None

        tool = target.get("tool")
        parameters = target.get("parameters")
        if tool not in REVERSING_INVESTIGATION_TOOL_NAMES:
            return None
        if not isinstance(parameters, dict):
            parameters = {}

        compact: dict[str, Any] = {
            "tool": tool,
        }
        target_value = display_target_value(tool, parameters)
        if target_value is not None:
            compact["target"] = target_value

        priority = target.get("priority")
        if isinstance(priority, int):
            compact["priority"] = priority

        return compact

    def _compact_validation(self, validation: Any) -> str | dict[str, Any] | None:
        if not isinstance(validation, dict):
            return None

        status = validation.get("status")
        if status == "VALID":
            return "VALID"

        if status == "CORRECTED":
            return {
                "status": "CORRECTED",
                "original": self._compact_validation_target(
                    validation.get("original_tool"),
                    validation.get("original_parameters"),
                ),
                "corrected": self._compact_validation_target(
                    validation.get("corrected_tool"),
                    validation.get("corrected_parameters"),
                ),
            }

        if status == "REJECTED":
            return {
                "status": "REJECTED",
                "original": self._compact_validation_target(
                    validation.get("original_tool"),
                    validation.get("original_parameters"),
                ),
                "message": validation.get("message"),
            }

        return None

    def _compact_validation_target(
        self,
        tool: Any,
        parameters: Any,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if isinstance(tool, str):
            result["tool"] = tool
        if isinstance(parameters, dict):
            target = display_target_value(tool, parameters)
            if target is not None:
                result["target"] = target

        return result

    def _fill_event_target_from_validation(
        self,
        event: dict[str, Any],
        validation: str | dict[str, Any],
    ) -> None:
        if not isinstance(validation, dict):
            return
        if "tool" in event and "target" in event:
            return

        original = validation.get("original")
        if not isinstance(original, dict):
            return

        tool = original.get("tool")
        target = original.get("target")
        if "tool" not in event and isinstance(tool, str):
            event["tool"] = tool
        if "target" not in event and target is not None:
            event["target"] = target

    def _compact_origin(self, target: dict[str, Any]) -> dict[str, Any]:
        origin: dict[str, Any] = {}

        origin_tool = target.get("origin_tool")
        origin_target = target.get("origin_target")
        relation = target.get("relation")
        if isinstance(origin_tool, str) and origin_tool:
            origin["tool"] = origin_tool
        if isinstance(origin_target, str) and origin_target:
            origin["target"] = origin_target
        if isinstance(relation, str) and relation:
            origin["relation"] = relation

        return origin

    def _parameters(self, parameters: dict[str, Any] | None) -> dict[str, Any]:
        return parameters if isinstance(parameters, dict) else {}

    def _string_or_default(self, value: Any, default: str) -> str:
        return value.strip() if isinstance(value, str) and value.strip() else default

    def _confidence(self, value: Any) -> str:
        return value if value in {"low", "medium", "high"} else "unknown"
