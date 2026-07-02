from typing import Any

from utils.postprocessing.reversing.contracts import CODE_FOLLOW_UP_TOOLS


class ReversingObservationBuilder:
    SCALAR_FIELDS = (
        "query",
        "function",
        "resolved_function",
        "start_address",
        "end_address",
        "instructions_count",
        "returned_instructions",
        "truncated",
        "count",
    )

    def input_ref(
        self,
        target: dict[str, Any],
        chunk_index: int | None = None,
    ) -> dict[str, Any]:
        tool_name = target.get("tool")
        parameters = target.get("parameters")

        if not isinstance(tool_name, str):
            tool_name = "unknown"
        if not isinstance(parameters, dict):
            parameters = {}

        if tool_name in CODE_FOLLOW_UP_TOOLS:
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

        result = {"type": input_type, "value": value}
        
        if chunk_index is not None:
            result["index"] = chunk_index

        return result

    def build_summary(
        self,
        target: dict[str, Any],
        tool_output: dict[str, Any],
    ) -> dict[str, Any]:
        tool_name = target.get("tool")
        data = tool_output.get("data")
        summary: dict[str, Any] = {
            "success": tool_output.get("success") is True,
            "tool": tool_name,
        }
        code_targets: list[str] = []

        if not isinstance(data, dict):
            summary["result_type"] = type(data).__name__
            return summary

        self._copy_scalar_fields(data, summary)
        code_targets.extend(self._summarize_matches(data, summary))

        self._summarize_instructions(data, summary)
        code_targets.extend(self._summarize_callers(data, summary))
        code_targets.extend(self._summarize_callees(data, summary))

        if tool_name in {"function", "disassembly"}:
            function = data.get("resolved_function") or data.get("function")
            candidate = self._format_address(function)

            if candidate:
                code_targets.append(candidate)

        summary["code_targets"] = self._unique(code_targets)[:12]
        return summary


    def _copy_scalar_fields(self, data: dict[str, Any], summary: dict[str, Any]) -> None:
        for key in self.SCALAR_FIELDS:
            value = data.get(key)

            if value is not None and not isinstance(value, (dict, list)):
                summary[key] = value

    def _summarize_matches(self, data: dict[str, Any], summary: dict[str, Any]) -> list[str]:
        matches = data.get("matches")
        if not isinstance(matches, list):
            return []

        summary["matches_count"] = len(matches)
        xrefs_count = 0
        code_targets: list[str] = []

        for match in matches:
            if not isinstance(match, dict):
                continue

            match_xrefs = match.get("xrefs")
            if isinstance(match_xrefs, list):
                xrefs_count += len(match_xrefs)

            code_targets.extend(self._code_targets_from_xrefs(match_xrefs))

        summary["xrefs_count"] = xrefs_count

        return code_targets

    def _summarize_instructions(self, data: dict[str, Any], summary: dict[str, Any]) -> None:
        instructions = data.get("instructions")
        if not isinstance(instructions, list):
            return

        summary.setdefault("instructions_count", len(instructions))

        addresses = []
        for instruction in instructions:
            if isinstance(instruction, dict):
                address = instruction.get("address")

                if isinstance(address, int):
                    addresses.append(address)

        if addresses:
            summary["start_address"] = hex(min(addresses))
            summary["end_address"] = hex(max(addresses))

    def _summarize_callers(self, data: dict[str, Any], summary: dict[str, Any]) -> list[str]:
        callers = data.get("callers")
        if not isinstance(callers, list):
            return []

        summary["callers_count"] = len(callers)
        
        return self._code_targets_from_xrefs(callers)

    def _summarize_callees(self, data: dict[str, Any], summary: dict[str, Any]) -> list[str]:
        callees = data.get("callees")
        if not isinstance(callees, list):
            return []

        summary["callees_count"] = len(callees)
        targets: list[str] = []

        for callee in callees:
            if not isinstance(callee, dict):
                continue
            
            address = callee.get("target_address") or callee.get("callee")
            candidate = self._format_address(address)

            if candidate:
                targets.append(candidate)

        return targets

    def _code_targets_from_xrefs(self, values: Any) -> list[str]:
        if not isinstance(values, list):
            return []

        targets: list[str] = []

        for value in values:
            if not isinstance(value, dict):
                continue

            function = value.get("fcn_name") or value.get("function")
            address = value.get("from") or value.get("address")
            target = self._format_address(function) or self._format_address(address)

            if target and target not in targets:
                targets.append(target)

        return targets

    def _format_address(self, value: Any) -> str | None:
        if isinstance(value, int):
            return hex(value)
        
        if isinstance(value, str) and value:
            return value
        
        return None

    def _unique(values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))