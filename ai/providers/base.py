from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    content: str


class BaseLLMProvider(ABC):
    @abstractmethod
    def chat(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        pass

    @abstractmethod
    def chat_with_assistant(self, system_prompt: str, assitant_prompt: str, user_prompt: str) -> LLMResponse:
        pass