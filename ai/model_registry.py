from typing import Any

from ai.providers.base import BaseLLMProvider
from ai.providers.factory import ProviderFactory
from exceptions import ConfigurationError


class ModelRegistry:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config


    def _get_profile(self, profile_name: str) -> dict[str, Any]:
        profile = self.config.get("profiles", {}).get(profile_name)
        if profile is None:
            raise ConfigurationError(f"Unknown model profile: {profile_name}")
        return profile


    def _get_provider(self, provider_name: str) -> dict[str, Any]:
        provider = self.config.get("providers", {}).get(provider_name)
        if provider is None:
            raise ConfigurationError(f"Unknown provider: {provider_name}")
        return provider
    

    def _get_agent(self, agent_name: str) -> dict[str, Any]:
        agent = self.config.get("agents", {}).get(agent_name)
        if agent is None:
            raise ConfigurationError(f"Unknown agent: {agent_name}")
        return agent


    def _get_task(self, task_name: str) -> dict[str, Any]:
        task = self.config.get("tasks", {}).get(task_name)
        if task is None:
            raise ConfigurationError(f"Unknown task: {task_name}")
        return task


    def _get_fallback_profile(self) -> str:
        fallback = self.config.get("defaults", {}).get("fallback_profile")
        if not fallback:
            raise ConfigurationError(
                "Missing defaults.fallback_profile in model configuration"
            )
        return fallback


    def _resolve_profile_name(self, override: str | None, default: str | None, owner: str) -> str:
        profile_name = override or default or self._get_fallback_profile()
        if not profile_name:
            raise ConfigurationError(f"No profile configured for {owner}")
        return profile_name



    def create_client_from_profile(self, profile_name: str) -> BaseLLMProvider:
        profile = self._get_profile(profile_name)
        provider_name = profile.get("provider")

        if not provider_name:
            raise ConfigurationError(f"Model profile '{profile_name}' does not define a provider")

        provider = self._get_provider(provider_name)
        return ProviderFactory.create(provider_config=provider, profile_config=profile,)


    def create_agent_client(self, agent_name: str, profile_override: str | None = None) -> BaseLLMProvider:
        agent = self._get_agent(agent_name)
        profile_name = self._resolve_profile_name(
            override=profile_override,
            default=agent.get("default_profile"),
            owner=f"agent '{agent_name}'",
        )
        return self.create_client_from_profile(profile_name)


    def create_task_client(self, task_name: str, profile_override: str | None = None) -> BaseLLMProvider:
        task = self._get_task(task_name)
        profile_name = self._resolve_profile_name(
            override=profile_override,
            default=task.get("default_profile"),
            owner=f"task '{task_name}'",
        )
        return self.create_client_from_profile(profile_name)




