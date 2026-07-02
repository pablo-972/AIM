from typing import Any

import requests

from ai.providers.base import BaseLLMProvider, JsonSchema, LLMResponse, Message
from exceptions import ProviderError

REQUEST_TIMEOUT = 120
MAX_ERROR_BODY_LENGTH = 2000


class OllamaProvider(BaseLLMProvider):
    def __init__(
        self, 
        base_url: str, 
        model: str, 
        temperature: float = 0.2, 
        response_format: str = "text"
        ) -> None:
        self.base_url: str = base_url.rstrip("/")
        self.model: str = model
        self.temperature: float = temperature
        self.response_format: str = response_format

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

    def _chat(
        self,
        messages: list[Message],
        schema: JsonSchema | None = None,
    ) -> LLMResponse:
        payload = self._build_payload(messages, schema)

        try:
            response = requests.post( 
                f"{self.base_url}/api/chat", 
                json=payload, 
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise ProviderError(
                f"Ollama connection failed for {self.base_url}/api/chat: {exc}"
            ) from exc

        if not response.ok:
            error_message = self._http_error_message(response)
            raise ProviderError(error_message)

        try:
            data = response.json()
        except ValueError as exc:
                raise ProviderError("Invalid JSON response from Ollama") from exc

        content = self._extract_content(data)

        return LLMResponse(content=content)
    

    def _build_payload(
        self,
        messages: list[Message],
        schema: JsonSchema | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }
    
        if schema is not None:
            payload["format"] = schema
        elif self.response_format == "json":
            payload["format"] = "json"

        return payload

    def _http_error_message(self, response: requests.Response) -> str:
        error_body = response.text.strip()

        if len(error_body) > MAX_ERROR_BODY_LENGTH:
            error_body = f"{error_body[:MAX_ERROR_BODY_LENGTH]}..."

        details = error_body or "<empty response body>"

        return (
            f"Ollama request failed with HTTP {response.status_code}: "
            f"{details}"
        )
    
    def _extract_content(self, data: Any) -> str:
        if not isinstance(data, dict):
            raise ProviderError("Ollama response must be a JSON object")

        message = data.get("message")

        content = None
        if isinstance(message, dict):
            content = message.get("content")

        if isinstance(content, str) and content.strip():
            return content
        
        diagnostics = self._response_diagnostics(data, message)
        raise ProviderError(
            "Ollama response does not contain message.content. "
            f"Diagnostics: {diagnostics}"
        )
    
    def _response_diagnostics(
        self,
        data: dict[str, Any],
        message: Any,
    ) -> dict[str, Any]:
        return {
            "done": data.get("done"),
            "done_reason": data.get("done_reason"),
            "prompt_eval_count": data.get("prompt_eval_count"),
            "eval_count": data.get("eval_count"),
            "message_keys": sorted(message) if isinstance(message, dict) else [],
        }