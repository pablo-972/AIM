import os
from typing import Any

from core.ai.providers.base import BaseLLMProvider
from core.ai.providers.cloud import OpenAICompatibleProvider
from core.ai.providers.ollama import OllamaProvider
from core.exceptions import ConfigurationError

SUPPORTED_PROVIDER_TYPES = {
    "ollama",
    "openai",
    "gemini",
}


def resolve_value(value: Any) -> Any:
    if isinstance(value, dict):
        env_name = value.get("env")
        default = value.get("default")
        
        if isinstance(env_name, str) and env_name:
            return os.getenv(env_name, default)
        
        return default
    
    return value


class ProviderFactory:
    def __init__(
        self,
        provider_config: dict[str, Any],
        profile_config: dict[str, Any],
    ) -> None:
        self.provider_config = provider_config
        self.profile_config = profile_config

    def create(self) -> BaseLLMProvider:
        provider_type = self._provider_type()

        model = self._model()
        temperature = self._temperature()
        response_format = self._response_format()

        if provider_type == "ollama":
            return self._create_ollama(
                model,
                temperature,
                response_format,
            )

        return self._create_openai_compatible(
            provider_type,
            model,
            temperature,
            response_format,
        )

    def _provider_type(self) -> str:
        provider_type = self.provider_config.get("type")

        if (
            not isinstance(provider_type, str)
            or provider_type not in SUPPORTED_PROVIDER_TYPES
        ):
            raise ConfigurationError(f"Unsupported provider type: {provider_type}")

        return provider_type

    def _model(self) -> str:
        model = resolve_value(self.profile_config.get("model"))

        if not isinstance(model, str) or not model:
            raise ConfigurationError("Model is empty for selected profile")

        return model

    def _temperature(self) -> float:
        temperature = self.profile_config.get("temperature", 0.2)

        if not isinstance(temperature, int | float):
            raise ConfigurationError("Profile temperature must be numeric")

        return float(temperature)

    def _response_format(self) -> str:
        response_format = self.profile_config.get("response_format", "text")

        if not isinstance(response_format, str):
            raise ConfigurationError("Profile response_format must be a string")

        return response_format

    def _base_url(self) -> str:
        base_url = resolve_value(self.provider_config.get("base_url"))

        if not isinstance(base_url, str) or not base_url:
            raise ConfigurationError(f"Missing base_url for provider: {self.provider_type}")

        return base_url

    def _api_key(self) -> str:
        api_key = resolve_value(self.provider_config.get("api_key"))

        if not isinstance(api_key, str) or not api_key:
            raise ConfigurationError(f"Missing API key for provider: {self.provider_type}")

        return api_key

    def _create_ollama(
        self,
        model: str,
        temperature: float,
        response_format: str,
    ) -> OllamaProvider:
        return OllamaProvider(
            base_url=self._base_url(),
            model=model,
            temperature=temperature,
            response_format=response_format,
        )

    def _create_openai_compatible(
        self,
        provider_type: str,
        model: str,
        temperature: float,
        response_format: str,
    ) -> OpenAICompatibleProvider:
        return OpenAICompatibleProvider(
            base_url=self._base_url(),
            api_key=self._api_key(),
            model=model,
            temperature=temperature,
            response_format=response_format,
            provider_type=provider_type,
        )