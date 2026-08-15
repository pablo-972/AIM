from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.ai.runtime.reversing.parameters import (
    CODE_ADDRESS_TOOLS,
    DISCOVERY_TOOLS,
    normalize_reversing_tool_parameters,
)
from core.utils.reversing.address import parse_address


KNOWN_SECTION_NAMES = {
    ".text",
    ".data",
    ".rdata",
    ".rsrc",
    ".reloc",
    ".idata",
    ".edata",
    ".pdata",
    ".bss",
    ".tls",
}


class TargetValidationStatus(str, Enum):
    VALID = "VALID"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"


class TargetType(str, Enum):
    ADDRESS = "address"
    SECTION = "section"
    IMPORT_FUNCTION = "import_function"
    IMPORT_DLL = "import_dll"
    STRING = "string"


@dataclass(frozen=True)
class TargetValidationResult:
    status: TargetValidationStatus
    original_tool: str
    original_parameters: dict[str, Any]
    target_type: TargetType | None
    tool: str | None
    parameters: dict[str, Any]
    reason: str

    def debug(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "status": self.status.value,
            "original_tool": self.original_tool,
            "original_parameters": self.original_parameters,
            "target_type": self.target_type.value if self.target_type else None,
            "reason": self.reason,
        }

        if self.status == TargetValidationStatus.CORRECTED:
            data["corrected_tool"] = self.tool
            data["corrected_parameters"] = self.parameters

        return data


class ReversingTargetValidator:
    def validate(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        available_tools: dict[str, Any],
    ) -> TargetValidationResult:
        original_parameters = dict(parameters)

        if tool_name not in available_tools:
            return _rejected(
                tool_name,
                original_parameters,
                None,
                f"Unknown tool: {tool_name}",
            )

        if tool_name in DISCOVERY_TOOLS:
            return _accepted_discovery(tool_name, original_parameters)

        value = _target_value(tool_name, parameters)
        if value is None:
            return _rejected(
                tool_name,
                original_parameters,
                None,
                "No usable target argument was provided.",
            )

        target_type, normalized_value = _resolve_for_tool(tool_name, value)
        if tool_name in _compatible_tools(target_type):
            return _accepted(
                tool_name,
                original_parameters,
                target_type,
                normalized_value,
            )

        corrected_tool = _correction_tool(target_type)
        if corrected_tool is None:
            return _rejected(
                tool_name,
                original_parameters,
                target_type,
                "No unambiguous correction exists for target type.",
            )

        if corrected_tool not in available_tools:
            return _rejected(
                tool_name,
                original_parameters,
                target_type,
                f"Corrected tool is not available: {corrected_tool}",
            )

        return _corrected(
            tool_name,
            original_parameters,
            target_type,
            corrected_tool,
            normalized_value,
        )


def _accepted(
    tool_name: str,
    original_parameters: dict[str, Any],
    target_type: TargetType,
    value: str,
) -> TargetValidationResult:
    normalized_parameters = _normalized_parameters(tool_name, value)
    status = TargetValidationStatus.VALID
    reason = "Tool is compatible with target type."

    if normalized_parameters != original_parameters:
        status = TargetValidationStatus.CORRECTED
        reason = "Tool parameters were normalized."

    return TargetValidationResult(
        status=status,
        original_tool=tool_name,
        original_parameters=original_parameters,
        target_type=target_type,
        tool=tool_name,
        parameters=normalized_parameters,
        reason=reason,
    )


def _accepted_discovery(
    tool_name: str,
    original_parameters: dict[str, Any],
) -> TargetValidationResult:
    normalized_parameters = normalize_reversing_tool_parameters(
        tool_name,
        original_parameters,
    )
    status = TargetValidationStatus.VALID
    reason = "Discovery tool is compatible without a target argument."

    if normalized_parameters != original_parameters:
        status = TargetValidationStatus.CORRECTED
        reason = "Tool parameters were normalized."

    return TargetValidationResult(
        status=status,
        original_tool=tool_name,
        original_parameters=original_parameters,
        target_type=None,
        tool=tool_name,
        parameters=normalized_parameters,
        reason=reason,
    )


def _corrected(
    original_tool: str,
    original_parameters: dict[str, Any],
    target_type: TargetType,
    corrected_tool: str,
    value: str,
) -> TargetValidationResult:
    return TargetValidationResult(
        status=TargetValidationStatus.CORRECTED,
        original_tool=original_tool,
        original_parameters=original_parameters,
        target_type=target_type,
        tool=corrected_tool,
        parameters=_normalized_parameters(corrected_tool, value),
        reason=f"{target_type.value} target uses {corrected_tool}.",
    )


def _rejected(
    tool_name: str,
    original_parameters: dict[str, Any],
    target_type: TargetType | None,
    reason: str,
) -> TargetValidationResult:
    return TargetValidationResult(
        status=TargetValidationStatus.REJECTED,
        original_tool=tool_name,
        original_parameters=original_parameters,
        target_type=target_type,
        tool=None,
        parameters={},
        reason=reason,
    )


def _target_value(tool_name: str, parameters: dict[str, Any]) -> str | None:
    value = parameters.get(_tool_parameter_key(tool_name))
    if isinstance(value, str) and value.strip():
        return value.strip()

    string_values = [
        value.strip()
        for value in parameters.values()
        if isinstance(value, str) and value.strip()
    ]
    if len(string_values) == 1:
        return string_values[0]

    return None


def _resolve_for_tool(tool_name: str, value: str) -> tuple[TargetType, str]:
    if tool_name == "import_xrefs":
        return _resolve_import_target(value)

    return _resolve_target(value)


def _resolve_target(value: str) -> tuple[TargetType, str]:
    address = parse_address(value)
    if address is not None:
        return TargetType.ADDRESS, hex(address)

    lowered = value.lower()
    if lowered in KNOWN_SECTION_NAMES:
        return TargetType.SECTION, value

    if lowered.endswith(".dll"):
        return TargetType.IMPORT_DLL, value

    if _looks_like_import_function(value):
        return TargetType.IMPORT_FUNCTION, value

    return TargetType.STRING, value


def _resolve_import_target(value: str) -> tuple[TargetType, str]:
    if value.lower().endswith(".dll"):
        return TargetType.IMPORT_DLL, value

    return TargetType.IMPORT_FUNCTION, value


def _looks_like_import_function(value: str) -> bool:
    normalized = value.strip()
    if len(normalized) < 4 or not normalized.isidentifier():
        return False

    has_lower = any(character.islower() for character in normalized)
    has_upper = any(character.isupper() for character in normalized)
    if has_lower and has_upper and normalized[0].isupper():
        return True

    return normalized.endswith(("A", "W", "Ex"))


def _compatible_tools(target_type: TargetType) -> set[str]:
    if target_type == TargetType.ADDRESS:
        return CODE_ADDRESS_TOOLS
    if target_type == TargetType.SECTION:
        return {"inspect_section"}
    if target_type in {TargetType.IMPORT_FUNCTION, TargetType.IMPORT_DLL}:
        return {"import_xrefs"}
    if target_type == TargetType.STRING:
        return {"string_xrefs"}

    return set()


def _correction_tool(target_type: TargetType) -> str | None:
    if target_type == TargetType.SECTION:
        return "inspect_section"
    if target_type in {TargetType.IMPORT_FUNCTION, TargetType.IMPORT_DLL}:
        return "import_xrefs"

    return None


def _normalized_parameters(tool_name: str, value: str) -> dict[str, Any]:
    return normalize_reversing_tool_parameters(
        tool_name,
        _parameters_for(tool_name, value),
    )


def _parameters_for(tool_name: str, value: str) -> dict[str, Any]:
    if tool_name in CODE_ADDRESS_TOOLS:
        return {"address": value}
    if tool_name == "inspect_section":
        return {"section": value}
    if tool_name == "import_xrefs":
        return {"import_name": value}
    if tool_name == "string_xrefs":
        return {"value": value}

    return {}


def _tool_parameter_key(tool_name: str) -> str:
    if tool_name in CODE_ADDRESS_TOOLS:
        return "address"
    if tool_name == "inspect_section":
        return "section"
    if tool_name == "import_xrefs":
        return "import_name"
    if tool_name == "string_xrefs":
        return "value"

    return "value"
