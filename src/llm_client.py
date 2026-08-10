
from __future__ import annotations
import os
import json
from typing import Type, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel
from google import genai
from google.genai import types

load_dotenv()

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

_client: genai.Client | None = None


def get_llm_client() -> genai.Client:

    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY not found in environment. "
            "Add it to your .env file at the project root."
        )

    _client = genai.Client(api_key=api_key)
    return _client


def call_structured(
    prompt: str,
    output_schema: Type[T],
    client: genai.Client | None = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.4,
) -> T:

    client = client or get_llm_client()

    config = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type="application/json",
        response_schema=output_schema,
    )

    last_error: Exception | None = None
    for attempt in range(2):  
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
        raw_text = response.text

        try:
            data = json.loads(raw_text)
            return output_schema.model_validate(data)
        except Exception as e: 
            last_error = e
            continue

    raise ValueError(
        f"Failed to parse Gemini response into {output_schema.__name__} "
        f"after retry. Last error: {last_error}\nRaw response: {raw_text!r}"
    )
