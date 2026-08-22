from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.ai.runtime.reversing.parameters import (
    CODE_ADDRESS_TOOLS,
    DISCOVERY_TOOLS,
    prepare_reversing_tool_parameters,
    target_parameter_key,
    target_text,
)
from core.utils.address import parse_address


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


COMPATIBLE_TOOLS_BY_TARGET_TYPE = {
    TargetType.ADDRESS: CODE_ADDRESS_TOOLS,
    TargetType.SECTION: {"inspect_section"},
    TargetType.IMPORT_FUNCTION: {"import_xrefs"},
    TargetType.IMPORT_DLL: {"import_xrefs"},
    TargetType.STRING: {"string_xrefs"},
}
CORRECTION_TOOL_BY_TARGET_TYPE = {
    TargetType.SECTION: "inspect_section",
    TargetType.IMPORT_FUNCTION: "import_xrefs",
    TargetType.IMPORT_DLL: "import_xrefs",
}


@dataclass(frozen=True)
class TargetValidationResult:
    status: TargetValidationStatus
    original_tool: str
    original_parameters: dict[str, Any]
    target_type: TargetType | None
    tool: str | None
    parameters: dict[str, Any]
    message: str

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "status": self.status.value,
            "original_tool": self.original_tool,
            "original_parameters": self.original_parameters,
            "target_type": self.target_type.value if self.target_type else None,
            "message": self.message,
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

        value = target_text(tool_name, parameters)
        if value is None:
            return _rejected(
                tool_name,
                original_parameters,
                None,
                "No usable target argument was provided.",
            )

        target_type, target_value = _resolve_for_tool(tool_name, value)
        if tool_name in _compatible_tools(target_type):
            return _accepted(
                tool_name,
                original_parameters,
                target_type,
                target_value,
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
            target_value,
        )


def _accepted(
    tool_name: str,
    original_parameters: dict[str, Any],
    target_type: TargetType,
    value: str,
) -> TargetValidationResult:
    accepted_parameters = _parameters_for_validated_target(tool_name, value)
    status = TargetValidationStatus.VALID
    message = "Tool is compatible with target type."

    if accepted_parameters != original_parameters:
        status = TargetValidationStatus.CORRECTED
        message = "Tool parameters were adjusted."

    return TargetValidationResult(
        status=status,
        original_tool=tool_name,
        original_parameters=original_parameters,
        target_type=target_type,
        tool=tool_name,
        parameters=accepted_parameters,
        message=message,
    )


def _accepted_discovery(
    tool_name: str,
    original_parameters: dict[str, Any],
) -> TargetValidationResult:
    accepted_parameters = prepare_reversing_tool_parameters(
        tool_name,
        original_parameters,
    )
    status = TargetValidationStatus.VALID
    message = "Discovery tool is compatible without a target argument."

    if accepted_parameters != original_parameters:
        status = TargetValidationStatus.CORRECTED
        message = "Tool parameters were adjusted."

    return TargetValidationResult(
        status=status,
        original_tool=tool_name,
        original_parameters=original_parameters,
        target_type=None,
        tool=tool_name,
        parameters=accepted_parameters,
        message=message,
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
        parameters=_parameters_for_validated_target(corrected_tool, value),
        message=f"{target_type.value} target uses {corrected_tool}.",
    )


def _rejected(
    tool_name: str,
    original_parameters: dict[str, Any],
    target_type: TargetType | None,
    message: str,
) -> TargetValidationResult:
    return TargetValidationResult(
        status=TargetValidationStatus.REJECTED,
        original_tool=tool_name,
        original_parameters=original_parameters,
        target_type=target_type,
        tool=None,
        parameters={},
        message=message,
    )


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
    name = value.strip()
    if len(name) < 4 or not name.isidentifier():
        return False

    has_lower = any(character.islower() for character in name)
    has_upper = any(character.isupper() for character in name)
    if has_lower and has_upper and name[0].isupper():
        return True

    return name.endswith(("A", "W", "Ex"))


def _compatible_tools(target_type: TargetType) -> set[str]:
    return COMPATIBLE_TOOLS_BY_TARGET_TYPE.get(target_type, set())


def _correction_tool(target_type: TargetType) -> str | None:
    return CORRECTION_TOOL_BY_TARGET_TYPE.get(target_type)


def _parameters_for_validated_target(tool_name: str, value: str) -> dict[str, Any]:
    return prepare_reversing_tool_parameters(
        tool_name,
        _parameters_for(tool_name, value),
    )


def _parameters_for(tool_name: str, value: str) -> dict[str, Any]:
    if tool_name in CODE_ADDRESS_TOOLS or tool_name in {
        "inspect_section",
        "import_xrefs",
        "string_xrefs",
    }:
        return {
            target_parameter_key(tool_name): value,
        }

    return {}
