import random
import time
from typing import Any

import requests

from ai.providers.base import BaseLLMProvider, LLMResponse
from exceptions import ProviderError


REQUEST_TIMEOUT = 120
DEFAULT_MAX_RETRIES = 4
DEFAULT_MIN_REQUEST_INTERVAL = 5.0


class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_format: str = "text",
        provider_type: str = "openai",
        max_retries: int = DEFAULT_MAX_RETRIES,
        min_request_interval: float = DEFAULT_MIN_REQUEST_INTERVAL,
    ) -> None:
        
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.response_format = response_format
        self.provider_type = provider_type
        self.max_retries = max_retries
        self.min_request_interval = min_request_interval
        self._last_request_at = 0.0

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }


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


    def _chat(self, messages: list[dict[str, str]]) -> LLMResponse:
        payload = self._build_payload(messages)
        data = self._post_with_retries(payload)
        content = self._extract_content(data)

        return LLMResponse(content=content)


    def _build_payload(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if self.response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        return payload


    def _post_with_retries(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._wait_for_rate_limit()
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                )

                if response.status_code == 429:
                    self._sleep_before_retry(response, attempt)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                self._sleep_before_retry(None, attempt)

            except ValueError as exc:
                raise ProviderError(f"Invalid JSON response from {self.provider_type}") from exc

        raise ProviderError(f"{self.provider_type} request failed after retries: {last_error}")


    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.min_request_interval - elapsed

        if remaining > 0:
            time.sleep(remaining)

        self._last_request_at = time.monotonic()


    def _sleep_before_retry(self, response: requests.Response | None, attempt: int) -> None:
        retry_after = None
        if response is not None:
            retry_after_header = response.headers.get("Retry-After")
            if retry_after_header:
                try:
                    retry_after = float(retry_after_header)
                except ValueError:
                    retry_after = None

        delay = retry_after or min(60.0, (2 ** attempt) + random.uniform(0, 1))
        time.sleep(delay)


    def _extract_content(self, data: dict[str, Any]) -> str:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.provider_type} response does not contain choices[0].message.content") from exc

        if not isinstance(content, str) or not content.strip():
            raise ProviderError(f"{self.provider_type} response content is empty")

        return content