import requests

from ai.providers.base import BaseLLMProvider, LLMResponse


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str, model: str, temperature: float = 0.2, response_format: str = "text"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.response_format = response_format


    def chat(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }
        if self.response_format == "json":
            payload["format"] = "json"

        response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()

        return LLMResponse(content=data["message"]["content"])
    

    def chat_with_assistant(self, system_prompt: str, assistant_prompt: str, user_prompt: str) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": assistant_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        response = requests.post(f"{self.base_url}/api/chat", json=payload,timeout=120)
        response.raise_for_status()
        data = response.json()

        return LLMResponse(content=data["message"]["content"])