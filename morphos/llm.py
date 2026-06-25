"""Local LLM interface via Ollama."""

import ollama


class LLMClient:
    def __init__(self, model: str = "gemma4:12b"):
        self.model = model

    def chat(self, messages: list[dict]) -> str:
        resp = ollama.chat(model=self.model, messages=messages)
        return resp["message"]["content"]
