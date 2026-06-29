import os
from typing import Any

from ai.providers.base import BaseLLMProvider
from ai.providers.cloud import OpenAICompatibleProvider
from ai.providers.ollama import OllamaProvider
from exceptions import ConfigurationError

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
    @staticmethod
    def create(provider_config: dict[str, Any], profile_config: dict[str, Any]) -> BaseLLMProvider:
        provider_type = provider_config.get("type")
        
        if (
            not isinstance(provider_type, str)
            or provider_type not in SUPPORTED_PROVIDER_TYPES
        ):
            raise ConfigurationError(f"Unsupported provider type: {provider_type}")

        model = resolve_value(profile_config.get("model"))
        temperature = profile_config.get("temperature", 0.2)
        response_format = profile_config.get("response_format", "text")

        if not isinstance(model, str) or not model:
            raise ConfigurationError("Model is empty for selected profile")
        if not isinstance(temperature, int | float):
            raise ConfigurationError("Profile temperature must be numeric")
        if not isinstance(response_format, str):
            raise ConfigurationError("Profile response_format must be a string")

        if provider_type == "ollama":
            base_url = resolve_value(provider_config.get("base_url"))

            if not isinstance(base_url, str) or not base_url:
                raise ConfigurationError("Missing base_url for Ollama provider")

            return OllamaProvider(
                base_url=base_url,
                model=model,
                temperature=temperature,
                response_format=response_format,
            )

        base_url = resolve_value(provider_config.get("base_url"))
        api_key = resolve_value(provider_config.get("api_key"))

        if not isinstance(base_url, str) or not base_url:
            raise ConfigurationError(f"Missing base_url for provider: {provider_type}")

        if not isinstance(api_key, str) or not api_key:
            raise ConfigurationError(f"Missing API key for provider: {provider_type}")

        return OpenAICompatibleProvider(
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=temperature,
            response_format=response_format,
            provider_type=provider_type,
        )
