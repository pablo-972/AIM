import random
import time
from typing import Any

import requests

from core.exceptions import ProviderError


DEFAULT_TIMEOUT = 120
DEFAULT_MAX_RETRIES = 4
DEFAULT_MIN_REQUEST_INTERVAL = 5.0
MAX_RETRY_DELAY = 60.0
MAX_ERROR_BODY_LENGTH = 2000


class JsonTransport:
    def __init__(
        self,
        provider_name: str,
        headers: dict[str, str],
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        min_request_interval: float = DEFAULT_MIN_REQUEST_INTERVAL,
    ) -> None:
        self.provider_name = provider_name
        self.headers = headers
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_request_interval = min_request_interval
        self._last_request_at = 0.0

    def post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            self._wait_for_rate_limit()
            response = self._request(url, payload)

            if isinstance(response, Exception):
                last_error = response
                if self._is_last_attempt(attempt):
                    break

                self._sleep_before_retry(None, attempt)
                continue

            if response.ok:
                return self._json_object(response)

            error = ProviderError(self._http_error_message(response))
            if not self._should_retry(response) or self._is_last_attempt(attempt):
                raise error

            last_error = error
            self._sleep_before_retry(response, attempt)

        raise ProviderError(
            f"{self.provider_name} request failed after retries: {last_error}"
        )

    def _request(
        self,
        url: str,
        payload: dict[str, Any],
    ) -> requests.Response | requests.RequestException:
        try:
            return requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            return exc

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.min_request_interval - elapsed

        if remaining > 0:
            time.sleep(remaining)

        self._last_request_at = time.monotonic()

    def _should_retry(self, response: requests.Response) -> bool:
        return response.status_code == 429 or response.status_code >= 500

    def _sleep_before_retry(
        self,
        response: requests.Response | None,
        attempt: int,
    ) -> None:
        delay = self._retry_after(response)
        if delay is None:
            delay = min(MAX_RETRY_DELAY, 2 ** attempt + random.uniform(0, 1))

        time.sleep(delay)

    def _retry_after(self, response: requests.Response | None) -> float | None:
        if response is None:
            return None

        value = response.headers.get("Retry-After")
        if not value:
            return None

        try:
            return float(value)
        except ValueError:
            return None

    def _json_object(self, response: requests.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError(
                f"Invalid JSON response from {self.provider_name}"
            ) from exc

        if not isinstance(data, dict):
            raise ProviderError(
                f"{self.provider_name} response must be a JSON object"
            )

        return data

    def _http_error_message(self, response: requests.Response) -> str:
        body = response.text.strip()
        if len(body) > MAX_ERROR_BODY_LENGTH:
            body = f"{body[:MAX_ERROR_BODY_LENGTH]}..."

        details = body or "<empty response body>"
        return (
            f"{self.provider_name} request failed with HTTP "
            f"{response.status_code}: {details}"
        )

    def _is_last_attempt(self, attempt: int) -> bool:
        return attempt >= self.max_retries
