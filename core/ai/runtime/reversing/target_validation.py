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


class TargetValidationStatus(str, Enum):
    VALID = "VALID"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"


class TargetType(str, Enum):
    ADDRESS = "address"
    FUNCTION = "function"
    SECTION = "section"
    IMPORT_FUNCTION = "import_function"
    IMPORT_DLL = "import_dll"
    STRING = "string"


COMPATIBLE_TOOLS_BY_TARGET_TYPE = {
    TargetType.ADDRESS: CODE_ADDRESS_TOOLS,
    TargetType.FUNCTION: {"disassembly"},
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
    canonical_target: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "status": self.status.value,
            "original_tool": self.original_tool,
            "original_parameters": self.original_parameters,
            "target_type": self.target_type.value if self.target_type else None,
            "message": self.message,
        }

        if self.canonical_target is not None:
            data["canonical_target"] = self.canonical_target

        if self.status == TargetValidationStatus.CORRECTED:
            data["corrected_tool"] = self.tool
            data["corrected_parameters"] = self.parameters

        return data


class ReversingTargetValidator:
    def __init__(
        self,
        functions: list[dict[str, Any]] | None = None,
        section_names: list[str] | None = None,
    ) -> None:
        self.functions = _function_inventory(functions)
        self.section_names = _string_inventory(section_names)

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

        if tool_name == "disassembly":
            return self._validate_disassembly(tool_name, original_parameters)

        value = target_text(tool_name, parameters)
        if value is None:
            return _rejected(
                tool_name,
                original_parameters,
                None,
                "No usable target argument was provided.",
            )

        target_type, target_value, canonical_target = self._resolve_for_tool(
            tool_name,
            value,
        )
        if tool_name in _compatible_tools(target_type):
            return _accepted(
                tool_name,
                original_parameters,
                target_type,
                target_value,
                canonical_target,
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
            canonical_target,
        )

    def _validate_disassembly(
        self,
        tool_name: str,
        original_parameters: dict[str, Any],
    ) -> TargetValidationResult:
        address = _non_empty_string(original_parameters.get("address"))
        function = _non_empty_string(original_parameters.get("function"))

        if bool(address) == bool(function):
            return _rejected(
                tool_name,
                original_parameters,
                None,
                "disassembly requires exactly one of address or function.",
            )

        if address is not None:
            parsed_address = parse_address(address)
            if parsed_address is None:
                return _rejected(
                    tool_name,
                    original_parameters,
                    None,
                    f"Invalid internal code address: {address}",
                )

            value = hex(parsed_address)
            canonical_target = self._canonical_code_address(parsed_address)
            return _accepted(
                tool_name,
                original_parameters,
                TargetType.ADDRESS,
                value,
                canonical_target,
            )

        resolved = self._resolve_function_name(function or "")
        if resolved is None:
            return _rejected(
                tool_name,
                original_parameters,
                TargetType.FUNCTION,
                f"Internal function not found: {function}",
            )

        name, address_value, corrected = resolved
        status = TargetValidationStatus.CORRECTED if corrected else TargetValidationStatus.VALID
        message = (
            "Function name was adjusted by unambiguous normalization."
            if corrected
            else "Tool is compatible with target type."
        )
        return TargetValidationResult(
            status=status,
            original_tool=tool_name,
            original_parameters=original_parameters,
            target_type=TargetType.FUNCTION,
            tool=tool_name,
            parameters={"function": name},
            message=message,
            canonical_target=address_value,
        )

    def _resolve_for_tool(
        self,
        tool_name: str,
        value: str,
    ) -> tuple[TargetType, str, str]:
        if tool_name == "import_xrefs":
            return _resolve_import_target(value)

        return self._resolve_target(value)

    def _resolve_target(self, value: str) -> tuple[TargetType, str, str]:
        address = parse_address(value)
        if address is not None:
            resolved = hex(address)
            return TargetType.ADDRESS, resolved, resolved

        section = self._resolve_section_name(value)
        if section is not None:
            return TargetType.SECTION, section, _canonical_text(section)

        lowered = value.lower()
        if lowered.endswith(".dll"):
            return TargetType.IMPORT_DLL, value, lowered

        if _looks_like_import_function(value):
            return TargetType.IMPORT_FUNCTION, value, value.lower()

        return TargetType.STRING, value, _canonical_string(value)

    def _resolve_section_name(self, value: str) -> str | None:
        return _resolve_name(value, self.section_names)

    def _resolve_function_name(self, value: str) -> tuple[str, str, bool] | None:
        requested = value.strip()
        if not requested:
            return None

        exact_matches = [
            item
            for item in self.functions
            if item["name"] == requested
        ]
        if len(exact_matches) == 1:
            item = exact_matches[0]
            return item["name"], item["address"], False
        if len(exact_matches) > 1:
            return None

        normalized = _normalize_name(requested)
        normalized_matches = [
            item
            for item in self.functions
            if _normalize_name(item["name"]) == normalized
        ]
        if len(normalized_matches) == 1:
            item = normalized_matches[0]
            return item["name"], item["address"], True

        return None

    def _canonical_code_address(self, address: int) -> str:
        for item in self.functions:
            start = item.get("address_value")
            size = item.get("size")
            if not isinstance(start, int) or not isinstance(size, int):
                continue

            if start <= address < start + max(size, 1):
                return item["address"]

        return hex(address)


def _accepted(
    tool_name: str,
    original_parameters: dict[str, Any],
    target_type: TargetType,
    value: str,
    canonical_target: str,
) -> TargetValidationResult:
    accepted_parameters = _parameters_for_validated_target(
        tool_name,
        target_type,
        value,
    )
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
        canonical_target=canonical_target,
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
        canonical_target=tool_name,
    )


def _corrected(
    original_tool: str,
    original_parameters: dict[str, Any],
    target_type: TargetType,
    corrected_tool: str,
    value: str,
    canonical_target: str,
) -> TargetValidationResult:
    return TargetValidationResult(
        status=TargetValidationStatus.CORRECTED,
        original_tool=original_tool,
        original_parameters=original_parameters,
        target_type=target_type,
        tool=corrected_tool,
        parameters=_parameters_for_validated_target(
            corrected_tool,
            target_type,
            value,
        ),
        message=f"{target_type.value} target uses {corrected_tool}.",
        canonical_target=canonical_target,
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


def _resolve_import_target(value: str) -> tuple[TargetType, str, str]:
    if value.lower().endswith(".dll"):
        return TargetType.IMPORT_DLL, value, value.lower()

    return TargetType.IMPORT_FUNCTION, value, value.lower()


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


def _parameters_for_validated_target(
    tool_name: str,
    target_type: TargetType,
    value: str,
) -> dict[str, Any]:
    return prepare_reversing_tool_parameters(
        tool_name,
        _parameters_for(tool_name, target_type, value),
    )


def _parameters_for(
    tool_name: str,
    target_type: TargetType,
    value: str,
) -> dict[str, Any]:
    if tool_name == "disassembly" and target_type == TargetType.FUNCTION:
        return {
            "function": value,
        }

    if tool_name in CODE_ADDRESS_TOOLS or tool_name in {
        "inspect_section",
        "import_xrefs",
        "string_xrefs",
    }:
        return {
            target_parameter_key(tool_name): value,
        }

    return {}


def _function_inventory(functions: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    inventory = []
    if not isinstance(functions, list):
        return inventory

    for item in functions:
        if not isinstance(item, dict):
            continue

        name = item.get("name")
        address = parse_address(item.get("address"))
        if not isinstance(name, str) or not name.strip() or address is None:
            continue

        size = item.get("size")
        if not isinstance(size, int) or size <= 0:
            size = 1

        inventory.append(
            {
                "name": name.strip(),
                "address": hex(address),
                "address_value": address,
                "size": size,
            }
        )

    return inventory


def _string_inventory(values: list[str] | None) -> list[str]:
    if not isinstance(values, list):
        return []

    return [
        value.strip()
        for value in values
        if isinstance(value, str) and value.strip()
    ]


def _resolve_name(value: str, candidates: list[str]) -> str | None:
    requested = value.strip()
    if not requested:
        return None

    exact_matches = [
        candidate
        for candidate in candidates
        if candidate == requested
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        return None

    normalized = _normalize_name(requested)
    normalized_matches = [
        candidate
        for candidate in candidates
        if _normalize_name(candidate) == normalized
    ]
    if len(normalized_matches) == 1:
        return normalized_matches[0]

    return None


def _non_empty_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


def _normalize_name(value: str) -> str:
    return value.strip().casefold()


def _canonical_text(value: str) -> str:
    return _normalize_name(value)


def _canonical_string(value: str) -> str:
    normalized = _strip_outer_quotes(value.strip())
    windows_candidate = _normalize_backslashes(normalized)

    if _is_windows_or_registry_target(windows_candidate):
        return windows_candidate.lower()

    return normalized


def _strip_outer_quotes(value: str) -> str:
    if len(value) < 2:
        return value

    first = value[0]
    last = value[-1]
    if first == last and first in {"'", '"'}:
        return value[1:-1].strip()

    return value


def _normalize_backslashes(value: str) -> str:
    while "\\\\" in value:
        value = value.replace("\\\\", "\\")

    return value


def _is_windows_or_registry_target(value: str) -> bool:
    if len(value) >= 3 and value[1] == ":" and value[2] == "\\":
        return value[0].isalpha()

    return _looks_like_registry_path(value)


def _looks_like_registry_path(value: str) -> bool:
    if value.startswith("\\"):
        return False

    parts = [
        part
        for part in value.split("\\")
        if part
    ]
    if len(parts) < 3:
        return False

    root = parts[0]
    if len(root) == 2 and root[1] == ":":
        return False

    return root.isidentifier()
