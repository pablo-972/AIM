from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

Message = dict[str, str]
JsonSchema = dict[str, Any]
ToolDefinition = dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMResponse:
    content: str
    tool_calls: tuple[ToolCall, ...] = ()


class BaseLLMProvider(ABC):
    @abstractmethod
    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: JsonSchema,
    ) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    def chat_with_assistant(
        self,
        system_prompt: str,
        assistant_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    def chat_json_with_assistant(
        self,
        system_prompt: str,
        assistant_prompt: str,
        user_prompt: str,
        schema: JsonSchema,
    ) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    def chat_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition],
    ) -> LLMResponse:
        raise NotImplementedError
