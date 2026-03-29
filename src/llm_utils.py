from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
import yaml


load_dotenv()


def strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json|yaml|yml|text)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


class LLMClient:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-5.4")

        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_text(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )
        return response.output_text.strip()

    def generate_json(self, prompt: str) -> dict[str, Any]:
        text = self.generate_text(prompt)
        text = strip_code_fences(text)
        return json.loads(text)

    def generate_yaml(self, prompt: str) -> dict[str, Any]:
        text = self.generate_text(prompt)
        text = strip_code_fences(text)
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            raise ValueError("YAML response is not a dictionary")
        return data
