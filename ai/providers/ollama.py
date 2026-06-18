import requests

from ai.providers.base import BaseLLMProvider, LLMResponse
from exceptions import ProviderError


REQUEST_TIMEOUT = 120


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str, model: str, temperature: float = 0.2, response_format: str = "text") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.response_format = response_format


    def chat(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        return self._chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )


    def chat_with_assistant(self, system_prompt: str, assistant_prompt: str, user_prompt: str) -> LLMResponse:
        return self._chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": assistant_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )


    def _chat(self, messages: list[dict]) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        if self.response_format == "json":
            payload["format"] = "json"

        try:
            response = requests.post( f"{self.base_url}/api/chat", json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            content = data.get("message", {}).get("content")
            if not content:
                raise ProviderError("Ollama response does not contain message.content")

            return LLMResponse(content=content)

        except requests.RequestException as exc:
            raise ProviderError(f"Ollama request failed: {exc}") from exc

        except ValueError as exc:
            raise ProviderError("Invalid JSON response from Ollama") from exc