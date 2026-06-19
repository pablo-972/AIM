from typing import Any

from ai.providers.base import BaseLLMProvider
from ai.providers.factory import ProviderFactory
from exceptions import ConfigurationError


class ModelRegistry:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config: dict[str, Any] = config


    def _get_config_entry(
        self,
        section_name: str,
        entry_name: str,
        entry_label: str,
    ) -> dict[str, Any]:
        section = self.config.get(section_name)
        if not isinstance(section, dict):
            raise ConfigurationError(
                f"Missing or invalid model configuration section: {section_name}"
            )

        entry = section.get(entry_name)
        if entry is None:
            raise ConfigurationError(f"Unknown {entry_label}: {entry_name}")
        if not isinstance(entry, dict):
            raise ConfigurationError(f"Invalid {entry_label}: {entry_name}")

        return entry


    def _get_profile(self, profile_name: str) -> dict[str, Any]:
        return self._get_config_entry("profiles", profile_name, "model profile")


    def _get_provider(self, provider_name: str) -> dict[str, Any]:
        return self._get_config_entry("providers", provider_name, "provider")
    

    def _get_agent(self, agent_name: str) -> dict[str, Any]:
        return self._get_config_entry("agents", agent_name, "agent")


    def _get_task(self, task_name: str) -> dict[str, Any]:
        return self._get_config_entry("tasks", task_name, "task")


    def _get_fallback_profile(self) -> str:
        defaults = self.config.get("defaults")
        fallback = (
            defaults.get("fallback_profile")
            if isinstance(defaults, dict)
            else None
        )
        if not isinstance(fallback, str) or not fallback:
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

        if not isinstance(provider_name, str) or not provider_name:
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




