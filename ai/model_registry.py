from typing import Any

from exceptions import ConfigurationError

from ai.providers.base import BaseLLMProvider
from ai.providers.factory import ProviderFactory



class ModelRegistry:
    def __init__(self, config: dict[str, Any]):
        self.config = config


    def create_client_from_profile(self, profile_name: str) -> BaseLLMProvider:
        profiles = self.config.get("profiles", {})
        providers = self.config.get("providers", {})

        profile = profiles.get(profile_name)
        if profile is None:
            raise ConfigurationError(f"Unknown model profile: {profile_name}")

        provider_name = profile.get("provider")
        provider = providers.get(provider_name)
        if provider is None:
            raise ConfigurationError(f"Unknown provider: {provider_name}")

        return ProviderFactory.create(provider_config=provider, profile_config=profile)


    def create_agent_client(self, agent_name: str, profile_override: str | None = None) -> BaseLLMProvider:
        agent = self.config.get("agents", {}).get(agent_name)
        if agent is None:
            raise ConfigurationError(f"Unknown agent: {agent_name}")

        profile_name = (
            profile_override 
            or agent.get("default_profile") 
            or self.config["defaults"]["fallback_profile"]
        )
        
        return self.create_client_from_profile(profile_name)


    def create_task_client(self, task_name: str, profile_override: str | None = None) -> BaseLLMProvider:
        task = self.config.get("tasks", {}).get(task_name)
        if task is None:
            raise ConfigurationError(f"Unknown task: {task_name}")

        profile_name = (
            profile_override
            or task.get("default_profile")
            or self.config["defaults"]["fallback_profile"]
        )

        return self.create_client_from_profile(profile_name)