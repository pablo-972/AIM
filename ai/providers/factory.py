import os
from typing import Any
from ai.providers.base import BaseLLMProvider
from ai.providers.ollama import OllamaProvider
from ai.providers.cloud import OpenAICompatibleProvider
from exceptions import ConfigurationError


def resolve_value(value: Any) -> Any:
    if isinstance(value, dict):
        env_name = value.get("env")
        default = value.get("default")

        if env_name:
            return os.getenv(env_name, default)

        return default
    return value


class ProviderFactory:
    @staticmethod
    def create(provider_config: dict[str, Any], profile_config: dict[str, Any]) -> BaseLLMProvider:
        provider_type = provider_config["type"]

        model = resolve_value(profile_config.get("model"))
        temperature = profile_config.get("temperature", 0.2)
        max_tokens = profile_config.get("max_tokens", 4096)
        response_format = profile_config.get("response_format", "text")

        if not model:
            raise ConfigurationError("Model is empty for selected profile")

        if provider_type == "ollama":
            base_url = resolve_value(provider_config["base_url"])
            return OllamaProvider(base_url=base_url, model=model, temperature=temperature, response_format=response_format)

        if provider_type in {"openai", "gemini"}:
            base_url = resolve_value(provider_config["base_url"])
            api_key = resolve_value(provider_config["api_key"])

            if not api_key:
                raise ConfigurationError(f"Missing API key for provider: {provider_type}")

            return OpenAICompatibleProvider(
                base_url=base_url,
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        raise ConfigurationError(f"Unsupported provider type: {provider_type}")