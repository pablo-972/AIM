import json
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


DEFAULT_SCHEMA_NAME = "aim_schema"


class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        response_format: str = "text",
        provider_type: str = "OpenAI",
        max_retries: int = DEFAULT_MAX_RETRIES,
        min_request_interval: float = DEFAULT_MIN_REQUEST_INTERVAL,
    ) -> None:
        self.base_url: str = base_url.rstrip("/")
        self.api_key: str = api_key
        self.model: str = model
        self.temperature: float = temperature
        self.response_format: str = response_format
        self.provider_type: str = provider_type
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self.transport = JsonTransport(
            provider_name=self.provider_type,
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
        data = self.transport.post(f"{self.base_url}/chat/completions", payload)
        content, tool_calls = self._extract_response(data, allow_empty_content)

        return LLMResponse(content=content, tool_calls=tool_calls)

    def _build_payload(
        self,
        messages: list[Message],
        schema: JsonSchema | None = None,
        tools: list[ToolDefinition] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": self.temperature,
        }

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
                    "function": tool,
                }
            )

        return tool_payload

    def _response_format_payload(
        self,
        schema: JsonSchema | None,
    ) -> dict[str, Any] | None:
        if schema is None:
            if self.response_format == "json":
                return {
                    "type": "json_object",
                }

            return None

        return {
            "type": "json_schema",
            "json_schema": {
                "name": DEFAULT_SCHEMA_NAME,
                "strict": True,
                "schema": schema,
            },
        }

    def _extract_response(
        self,
        data: dict[str, Any],
        allow_empty_content: bool,
    ) -> tuple[str, tuple[ToolCall, ...]]:
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                f"{self.provider_type} response does not contain choices[0].message"
            ) from exc

        if not isinstance(message, dict):
            raise ProviderError(
                f"{self.provider_type} response message must be an object"
            )

        content = message.get("content")
        if not isinstance(content, str):
            content = ""

        tool_calls = self._extract_tool_calls(message)
        if content.strip() or (allow_empty_content and tool_calls):
            return content, tool_calls

        raise ProviderError(f"{self.provider_type} response content is empty")

    def _extract_tool_calls(self, message: dict[str, Any]) -> tuple[ToolCall, ...]:
        raw_calls = message.get("tool_calls")
        if not isinstance(raw_calls, list):
            return ()

        calls = []
        for raw_call in raw_calls:
            if not isinstance(raw_call, dict):
                continue

            function = raw_call.get("function")
            if not isinstance(function, dict):
                continue

            name = function.get("name")
            arguments = self._tool_arguments(function.get("arguments"))
            if isinstance(name, str) and name:
                calls.append(ToolCall(name=name, arguments=arguments))

        return tuple(calls)

    def _tool_arguments(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if not isinstance(value, str):
            return {}

        try:
            arguments = json.loads(value)
        except ValueError:
            return {}

        return arguments if isinstance(arguments, dict) else {}
