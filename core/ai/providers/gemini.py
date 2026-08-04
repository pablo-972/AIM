from typing import Any

from core.ai.providers.base import (
    BaseLLMProvider,
    JsonSchema,
    LLMResponse,
    Message,
    ToolCall,
    ToolDefinition,
)
from core.ai.providers.transport import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_MIN_REQUEST_INTERVAL,
    JsonTransport,
)
from core.exceptions import ProviderError


class GeminiProvider(BaseLLMProvider):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        response_format: str = "text",
        max_retries: int = DEFAULT_MAX_RETRIES,
        min_request_interval: float = DEFAULT_MIN_REQUEST_INTERVAL,
    ) -> None:
        self.base_url: str = base_url.rstrip("/")
        self.api_key: str = api_key
        self.model: str = model
        self.temperature: float = temperature
        self.response_format: str = response_format
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        self.transport = JsonTransport(
            provider_name="Gemini",
            headers=headers,
            max_retries=max_retries,
            min_request_interval=min_request_interval,
        )

    def chat(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        return self._chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: JsonSchema,
    ) -> LLMResponse:
        return self._chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            schema=schema,
        )

    def chat_with_assistant(
        self,
        system_prompt: str,
        assistant_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        return self._chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": assistant_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

    def chat_json_with_assistant(
        self,
        system_prompt: str,
        assistant_prompt: str,
        user_prompt: str,
        schema: JsonSchema,
    ) -> LLMResponse:
        return self._chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": assistant_prompt},
                {"role": "user", "content": user_prompt},
            ],
            schema=schema,
        )

    def chat_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition],
    ) -> LLMResponse:
        return self._chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=tools,
            allow_empty_content=True,
        )

    def _chat(
        self,
        messages: list[Message],
        schema: JsonSchema | None = None,
        tools: list[ToolDefinition] | None = None,
        allow_empty_content: bool = False,
    ) -> LLMResponse:
        payload = self._build_payload(messages, schema, tools)
        data = self.transport.post(f"{self.base_url}/interactions", payload)
        content, tool_calls = self._extract_response(data, allow_empty_content)

        return LLMResponse(content=content, tool_calls=tool_calls)

    def _build_payload(
        self,
        messages: list[Message],
        schema: JsonSchema | None = None,
        tools: list[ToolDefinition] | None = None,
    ) -> dict[str, Any]:
        system_instruction = self._system_instruction(messages)

        payload: dict[str, Any] = {
            "model": self.model,
            "input": self._input_text(messages),
            "stream": False,
            "store": False,
            "generation_config": {
                "temperature": self.temperature,
            },
        }

        if system_instruction:
            payload["system_instruction"] = system_instruction

        if tools:
            payload["tools"] = self._tool_payload(tools)
        else:
            response_format = self._response_format_payload(schema)
            if response_format is not None:
                payload["response_format"] = response_format

        return payload

    def _tool_payload(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        tool_payload = []
        for tool in tools:
            tool_payload.append(
                {
                    "type": "function",
                    **tool,
                }
            )

        return tool_payload

    def _system_instruction(self, messages: list[Message]) -> str:
        parts: list[str] = []
        for message in messages:
            content = message.get("content", "").strip()

            if message.get("role") == "system" and content:
                parts.append(content)

        return "\n\n".join(parts)

    def _input_text(self, messages: list[Message]) -> str:
        parts: list[str] = []

        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "").strip()

            if role == "system" or not content:
                continue

            label = self._message_label(role)
            parts.append(f"{label}:\n{content}")

        return "\n\n".join(parts)

    def _message_label(self, role: str) -> str:
        if role == "assistant":
            return "Assistant"

        return "User"

    def _response_format_payload(
        self,
        schema: JsonSchema | None,
    ) -> dict[str, Any] | None:
        if schema is None:
            if self.response_format == "json":
                return {
                    "type": "text",
                    "mime_type": "application/json",
                }

            return None

        return {
            "type": "text",
            "mime_type": "application/json",
            "schema": schema,
        }


    def _extract_response(
        self,
        data: dict[str, Any],
        allow_empty_content: bool,
    ) -> tuple[str, tuple[ToolCall, ...]]:
        content = self._extract_optional_content(data)
        tool_calls = self._extract_tool_calls(data)

        if content or (allow_empty_content and tool_calls):
            return content, tool_calls

        raise ProviderError(
            f"Gemini response does not contain output text"
        )

    def _extract_optional_content(self, data: dict[str, Any]) -> str:
        content = data.get("output_text")
        if not isinstance(content, str) or not content.strip():
            content = self._extract_content_from_steps(data)

        result = ""
        if isinstance(content, str):
            result = content.strip()

        return result

    def _extract_tool_calls(self, data: dict[str, Any]) -> tuple[ToolCall, ...]:
        steps = data.get("steps")
        if not isinstance(steps, list):
            return ()

        calls = []
        for step in steps:
            if not isinstance(step, dict) or step.get("type") != "function_call":
                continue

            name = step.get("name")
            arguments = step.get("arguments")
            if isinstance(name, str) and name and isinstance(arguments, dict):
                calls.append(ToolCall(name=name, arguments=arguments))

        return tuple(calls)

    def _extract_content_from_steps(self, data: dict[str, Any]) -> str | None:
        steps = data.get("steps")
        if not isinstance(steps, list):
            return None

        for step in reversed(steps):
            if not isinstance(step, dict):
                continue

            content = step.get("content")
            if not isinstance(content, list):
                continue

            text = self._extract_text_part(content)
            if text:
                return text

        return None

    def _extract_text_part(self, content: list[Any]) -> str | None:
        for part in content:
            if not isinstance(part, dict):
                continue

            text = part.get("text")
            if isinstance(text, str) and text.strip():
                return text

        return None
