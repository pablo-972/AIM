import random
import time
from typing import Any

import requests

from core.ai.providers.base import (
    BaseLLMProvider,
    JsonSchema,
    LLMResponse,
    Message,
)
from core.exceptions import ProviderError


REQUEST_TIMEOUT = 120
DEFAULT_MAX_RETRIES = 4
DEFAULT_MIN_REQUEST_INTERVAL = 5.0
PROVIDER_TYPE = "gemini"


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
        self.max_retries: int = max_retries
        self.min_request_interval: float = min_request_interval
        self._last_request_at: float = 0.0
        self.headers: dict[str, str] = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

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

    def _chat(
        self,
        messages: list[Message],
        schema: JsonSchema | None = None,
    ) -> LLMResponse:
        payload = self._build_payload(messages, schema)
        data = self._post_with_retries(payload)
        content = self._extract_content(data)

        return LLMResponse(content=content)

    def _build_payload(
        self,
        messages: list[Message],
        schema: JsonSchema | None = None,
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

        response_format = self._response_format_payload(schema)
        if response_format is not None:
            payload["response_format"] = response_format

        return payload

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

    def _post_with_retries(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            self._wait_for_rate_limit()

            try:
                response = requests.post(
                    f"{self.base_url}/interactions",
                    headers=self.headers,
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.RequestException as exc:
                last_error = exc
                if self._is_last_attempt(attempt):
                    break

                self._sleep_before_retry(None, attempt)
                continue

            if response.status_code == 429:
                if self._is_last_attempt(attempt):
                    last_error = ProviderError("Rate limit exceeded")
                    break

                self._sleep_before_retry(response, attempt)
                continue

            try:
                if not response.ok:
                    raise ProviderError(self._http_error_message(response))

                return self._parse_response(response)
            except requests.RequestException as exc:
                last_error = exc
                if self._is_last_attempt(attempt):
                    break

                self._sleep_before_retry(response, attempt)
            except ProviderError as exc:
                last_error = exc
                if self._is_last_attempt(attempt):
                    break

                self._sleep_before_retry(response, attempt)
            except ValueError as exc:
                raise ProviderError(
                    f"Invalid JSON response from {PROVIDER_TYPE}"
                ) from exc

        raise ProviderError(
            f"{PROVIDER_TYPE} request failed after retries: {last_error}"
        )

    def _extract_content(self, data: dict[str, Any]) -> str:
        content = data.get("output_text")

        if not isinstance(content, str) or not content.strip():
            content = self._extract_content_from_steps(data)

        if not isinstance(content, str) or not content.strip():
            raise ProviderError(
                f"{PROVIDER_TYPE} response does not contain output text"
            )

        return content

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

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.min_request_interval - elapsed

        if remaining > 0:
            time.sleep(remaining)

        self._last_request_at = time.monotonic()

    def _sleep_before_retry(
        self,
        response: requests.Response | None,
        attempt: int,
    ) -> None:
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

    def _parse_response(self, response: requests.Response) -> dict[str, Any]:
        data = response.json()

        if not isinstance(data, dict):
            raise ProviderError(f"{PROVIDER_TYPE} response must be a JSON object")

        return data

    def _http_error_message(self, response: requests.Response) -> str:
        body = response.text.strip()
        if len(body) > 1000:
            body = f"{body[:1000]}..."

        message = (
            f"{response.status_code} {response.reason} for "
            f"{response.request.method} {response.url}"
        )
        if body:
            message = f"{message}: {body}"

        return message

    def _is_last_attempt(self, attempt: int) -> bool:
        return attempt >= self.max_retries
