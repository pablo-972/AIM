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


    def _chat(
        self,
        messages: list[Message],
        schema: JsonSchema | None = None,
    ) -> LLMResponse:
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

        try:
            response = requests.post( 
                f"{self.base_url}/api/chat", 
                json=payload, 
                timeout=REQUEST_TIMEOUT
            )

            if not response.ok:
                error_body = response.text.strip()
                if len(error_body) > MAX_ERROR_BODY_LENGTH:
                    error_body = f"{error_body[:MAX_ERROR_BODY_LENGTH]}..."

                details = error_body or "<empty response body>"
                raise ProviderError(
                    f"Ollama request failed with HTTP {response.status_code}: "
                    f"{details}"
                )

            data = response.json()
            if not isinstance(data, dict):
                raise ProviderError("Ollama response must be a JSON object")

            message = data.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, str) or not content.strip():
                diagnostics = {
                    "done": data.get("done"),
                    "done_reason": data.get("done_reason"),
                    "prompt_eval_count": data.get("prompt_eval_count"),
                    "eval_count": data.get("eval_count"),
                    "message_keys": (
                        sorted(message)
                        if isinstance(message, dict)
                        else []
                    ),
                }
                raise ProviderError(
                    "Ollama response does not contain message.content. "
                    f"Diagnostics: {diagnostics}"
                )

            return LLMResponse(content=content)

        except requests.RequestException as exc:
            raise ProviderError(
                f"Ollama connection failed for {self.base_url}/api/chat: {exc}"
            ) from exc

        except ValueError as exc:
            raise ProviderError("Invalid JSON response from Ollama") from exc



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
