from typing import Any

from ai.runtime.validators import validate_tool_parameters


NO_TOOL_ACTIONS = {"none", "finish"}
CODE_FOLLOW_UP_TOOLS = {"function", "disassembly", "callers", "callees"}


class ReversingPostprocessor:
    def __init__(self, available_tools: dict[str, Any]) -> None:
        self.available_tools = available_tools


    def input_ref(
        self,
        target: dict[str, Any],
        chunk_index: int | None = None,
    ) -> dict[str, Any]:
        tool_name = target["tool"]
        parameters = target["parameters"]

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


    def observation_summary(
        self,
        target: dict[str, Any],
        tool_output: dict[str, Any],
    ) -> dict[str, Any]:
        tool_name = target["tool"]
        data = tool_output.get("data")
        summary: dict[str, Any] = {
            "success": tool_output.get("success") is True,
            "tool": tool_name,
        }
        code_targets: list[str] = []

        if not isinstance(data, dict):
            summary["result_type"] = type(data).__name__
            return summary

        for key in (
            "query",
            "function",
            "resolved_function",
            "instructions_count",
            "returned_instructions",
            "truncated",
            "count",
        ):
            value = data.get(key)
            if value is not None and not isinstance(value, (dict, list)):
                summary[key] = value

        matches = data.get("matches")
        if isinstance(matches, list):
            summary["matches_count"] = len(matches)
            xrefs_count = 0
            for match in matches:
                if not isinstance(match, dict):
                    continue
                match_xrefs = match.get("xrefs")
                if isinstance(match_xrefs, list):
                    xrefs_count += len(match_xrefs)
                code_targets.extend(self._code_targets_from_xrefs(match_xrefs))
            summary["xrefs_count"] = xrefs_count

        instructions = data.get("instructions")
        if isinstance(instructions, list):
            summary.setdefault("instructions_count", len(instructions))

        callers = data.get("callers")
        if isinstance(callers, list):
            summary["callers_count"] = len(callers)
            code_targets.extend(self._code_targets_from_xrefs(callers))

        callees = data.get("callees")
        if isinstance(callees, list):
            summary["callees_count"] = len(callees)
            for callee in callees:
                if not isinstance(callee, dict):
                    continue
                candidate = self._format_address(
                    callee.get("target_address") or callee.get("callee")
                )
                if candidate:
                    code_targets.append(candidate)

        if tool_name in {"function", "disassembly"}:
            candidate = self._format_address(
                data.get("resolved_function") or data.get("function")
            )
            if candidate:
                code_targets.append(candidate)

        summary["code_targets"] = list(dict.fromkeys(code_targets))[:12]
        return summary


    def finding(
        self,
        finding: Any,
        target: dict[str, Any],
        observation: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not isinstance(finding, dict):
            return None

        finding_type = finding.get("type")
        code_targets = observation.get("code_targets")
        has_code_evidence = (
            target["tool"] in CODE_FOLLOW_UP_TOOLS
            or isinstance(code_targets, list) and bool(code_targets)
        )

        if self._is_empty_code_observation(observation):
            return None

        if finding_type == "critical_code_region" and not has_code_evidence:
            return None

        if (
            target["tool"] == "string_xrefs"
            and finding_type == "configuration_loading"
        ):
            query = str(observation.get("query") or "").lower()
            finding["type"] = (
                "ransom_payment_artifact"
                if "btc" in query or query.startswith(("bc1", "1", "3"))
                else "ransom_contact_artifact"
            )
            finding["category"] = "unknown"
            finding["function"] = None
            finding["address_range"] = None
            finding["reason"] = (
                "The evidence is a string artifact, not "
                "configuration-loading code."
            )

        if finding.get("type") == "critical_code_region":
            function = finding.get("function")
            if not function and isinstance(code_targets, list) and code_targets:
                finding["function"] = code_targets[0]

        evidence = finding.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            return None

        return finding


    def trace_decision(
        self,
        analysis: dict[str, Any],
        target: dict[str, Any],
        observation: dict[str, Any],
    ) -> dict[str, Any]:
        next_action, _ = self.next_action(analysis, target, observation)
        trace_action = (
            next_action if next_action in NO_TOOL_ACTIONS else target["tool"]
        )

        return {
            "thought": self._thought(analysis.get("thought"), observation),
            "confidence": analysis.get("confidence", "low"),
            "action": trace_action,
            "parameters": (
                {} if trace_action in NO_TOOL_ACTIONS else target["parameters"]
            ),
        }


    def follow_up_target(
        self,
        analysis: dict[str, Any],
        target: dict[str, Any],
        observation: dict[str, Any],
    ) -> dict[str, Any] | None:
        action, parameters = self.next_action(analysis, target, observation)
        if action in NO_TOOL_ACTIONS:
            return None

        return {
            "tool": action,
            "parameters": parameters,
            "priority": min(100, target["priority"] + 5),
            "reason": self._thought(
                analysis.get("thought"),
                observation,
            ) or f"Follow code evidence from {target['tool']}.",
        }


    def next_action(
        self,
        analysis: dict[str, Any],
        target: dict[str, Any],
        observation: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        action = analysis.get("action")
        parameters = analysis.get("parameters")
        if not isinstance(action, str):
            return "none", {}
        if not isinstance(parameters, dict):
            parameters = {}

        raw_code_targets = observation.get("code_targets")
        code_targets = (
            [value for value in raw_code_targets if isinstance(value, str)]
            if isinstance(raw_code_targets, list)
            else []
        )
        has_code_target = bool(code_targets)

        if target["tool"] in {"string_xrefs", "import_xrefs"} and has_code_target:
            return "function", {"function": code_targets[0]}

        if target["tool"] == "function" and action == "disassembly":
            confidence = analysis.get("confidence")
            instructions_count = observation.get("instructions_count")
            if (
                confidence not in {"medium", "high"}
                or not isinstance(instructions_count, int)
                or instructions_count < 3
            ):
                return "none", {}

        if action in CODE_FOLLOW_UP_TOOLS and has_code_target:
            requested_function = parameters.get("function")
            if requested_function not in code_targets:
                normalized_parameters = {"function": code_targets[0]}
                if action == "disassembly" and isinstance(
                    parameters.get("max_instructions"),
                    int,
                ):
                    normalized_parameters["max_instructions"] = parameters[
                        "max_instructions"
                    ]
                return action, normalized_parameters

        if (
            target["tool"] in {"string_xrefs", "import_xrefs"}
            and not has_code_target
            and action in CODE_FOLLOW_UP_TOOLS
        ):
            return "none", {}

        if action in NO_TOOL_ACTIONS:
            return action, {}

        tool_spec = self.available_tools.get(action)
        if (
            not isinstance(tool_spec, dict)
            or not validate_tool_parameters(parameters, tool_spec)
        ):
            return "none", {}

        return action, parameters


    def _thought(
        self,
        thought: Any,
        observation: dict[str, Any],
    ) -> str:
        normalized = str(thought or "").strip()
        lower = normalized.lower()
        matches_count = observation.get("matches_count")
        xrefs_count = observation.get("xrefs_count")

        if (
            isinstance(matches_count, int)
            and matches_count > 0
            and any(phrase in lower for phrase in ("no match", "none were found"))
        ):
            return (
                f"The tool returned {matches_count} matches; "
                "follow the reported code references."
            )

        if (
            isinstance(xrefs_count, int)
            and xrefs_count > 0
            and any(
                phrase in lower
                for phrase in ("no cross-reference", "no xref")
            )
        ):
            return (
                f"The tool returned {xrefs_count} code references; "
                "follow the reported functions or addresses."
            )

        if self._is_empty_code_observation(observation):
            return "No instructions were returned; no code conclusion was made."

        return normalized


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


    def _is_empty_code_observation(
        self,
        observation: dict[str, Any],
    ) -> bool:
        return (
            observation.get("returned_instructions") == 0
            or observation.get("instructions_count") == 0
        )
