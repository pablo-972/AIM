from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


Message = dict[str, str]
JsonSchema = dict[str, Any]


@dataclass(frozen=True)
class LLMResponse:
    content: str


class BaseLLMProvider(ABC):
    @abstractmethod
    def chat(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: JsonSchema,
    ) -> LLMResponse:
        return self.chat(system_prompt, user_prompt)


    @abstractmethod
    def chat_with_assistant(
            self, 
            system_prompt: str, 
            assistant_prompt: str, 
            user_prompt: str
        ) -> LLMResponse:
        raise NotImplementedError


    @abstractmethod
    def chat_json_with_assistant(
            self, 
            system_prompt: str, 
            assistant_prompt: str, 
            user_prompt: str, 
            schema: JsonSchema
        ) -> LLMResponse:
        return self.chat_with_assistant(system_prompt, assistant_prompt, user_prompt)
