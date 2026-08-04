from typing import Any

from core.ai.providers.base import (
    BaseLLMProvider, 
    JsonSchema, 
    LLMResponse, 
    Message,
    ToolCall,
    ToolDefinition,
)
from core.ai.providers.transport import JsonTransport
from core.exceptions import ProviderError


class OllamaProvider(BaseLLMProvider):
    def __init__(
        self, 
        base_url: str, 
        model: str, 
        temperature: float = 0.2, 
        response_format: str = "text",
        num_ctx: int | None = None,
        ) -> None:
        self.base_url: str = base_url.rstrip("/")
        self.model: str = model
        self.temperature: float = temperature
        self.response_format: str = response_format
        self.num_ctx: int | None = num_ctx
        self.transport = JsonTransport(
            provider_name="Ollama",
            headers={},
            min_request_interval=0,
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
        user_prompt: str
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
        schema: JsonSchema
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
        data = self.transport.post(f"{self.base_url}/api/chat", payload)
        content, tool_calls = self._extract_response(data, allow_empty_content)

        return LLMResponse(content=content, tool_calls=tool_calls)
    

    def _build_payload(
        self,
        messages: list[Message],
        schema: JsonSchema | None,
        tools: list[ToolDefinition] | None,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            "temperature": self.temperature,
        }

        if self.num_ctx is not None:
            options["num_ctx"] = self.num_ctx

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": options,
        }
    
        if schema is not None:
            payload["format"] = schema
        elif tools is None and self.response_format == "json":
            payload["format"] = "json"

        if tools:
            payload["tools"] = self._tool_payload(tools)

        return payload

    def _tool_payload(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": tool,
            }
            for tool in tools
        ]

    def _extract_response(
        self,
        data: Any,
        allow_empty_content: bool,
    ) -> tuple[str, tuple[ToolCall, ...]]:
        if not isinstance(data, dict):
            raise ProviderError("Ollama response must be a JSON object")

        message = data.get("message")

        content = ""
        if isinstance(message, dict):
            value = message.get("content")
            if isinstance(value, str):
                content = value

        tool_calls = self._extract_tool_calls(message)

        if content.strip() or (allow_empty_content and tool_calls):
            return content, tool_calls
        
        diagnostics = self._response_diagnostics(data, message)
        raise ProviderError(
            "Ollama response does not contain message.content. "
            f"Diagnostics: {diagnostics}"
        )

    def _extract_tool_calls(self, message: Any) -> tuple[ToolCall, ...]:
        if not isinstance(message, dict):
            return ()

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
            arguments = function.get("arguments")
            if not isinstance(name, str) or not name:
                continue
            if not isinstance(arguments, dict):
                arguments = {}

            calls.append(ToolCall(name=name, arguments=arguments))

        return tuple(calls)
    
    def _response_diagnostics(
        self,
        data: dict[str, Any],
        message: Any,
    ) -> dict[str, Any]:
        done = data.get("done")
        done_reason = data.get("done_reason")
        prompt_eval_count = data.get("prompt_eval_count")
        eval_count = data.get("eval_count")
        message_keys = sorted(message) if isinstance(message, dict) else []

        return {
            "done": done,
            "done_reason": done_reason,
            "prompt_eval_count": prompt_eval_count,
            "eval_count": eval_count,
            "message_keys": message_keys,
        }
