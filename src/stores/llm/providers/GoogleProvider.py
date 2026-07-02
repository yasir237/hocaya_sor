"""
Google Gemini tabanlı LLM/Embedding provider.
Yeni 'google.genai' SDK kullanıyor (google.generativeai deprecated).

Birden fazla API key destekler (round-robin) -- ücretsiz tier rate limit'ine
takılmamak için. Bir key 429 (rate limit) hatası verirse otomatik olarak
sıradaki key'e geçer.
"""

import time
import itertools

from google import genai
from google.genai import types

from stores.llm.LLMInterface import LLMInterface


class GoogleProvider(LLMInterface):

    def __init__(
        self,
        api_keys: list[str],
        embedding_model: str = "text-embedding-004",
        generation_model: str = "gemini-1.5-flash",
        embedding_dim: int = 768,
        max_retries_per_call: int = 3,
    ):
        if not api_keys:
            raise ValueError("GoogleProvider için en az bir API key gerekli.")

        self.api_keys = api_keys
        self.embedding_model = embedding_model
        self.generation_model = generation_model
        self.embedding_dim = embedding_dim
        self.max_retries_per_call = max_retries_per_call

        # round-robin için sonsuz döngüsel iterator
        self._key_cycle = itertools.cycle(self.api_keys)
        self._current_key = next(self._key_cycle)
        self._client = genai.Client(api_key=self._current_key)

    def _rotate_key(self):
        self._current_key = next(self._key_cycle)
        self._client = genai.Client(api_key=self._current_key)

    def _is_rate_limit_error(self, error: Exception) -> bool:
        msg = str(error).lower()
        return "429" in msg or "quota" in msg or "rate limit" in msg or "resource exhausted" in msg

    def embed_text(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Boş metin embed edilemez.")

        last_error = None
        attempts = max(self.max_retries_per_call, len(self.api_keys))

        for attempt in range(attempts):
            try:
                result = self._client.models.embed_content(
                    model=self.embedding_model,
                    contents=text,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
                )
                return result.embeddings[0].values
            except Exception as e:
                last_error = e
                if self._is_rate_limit_error(e):
                    self._rotate_key()
                    continue
                else:
                    time.sleep(2)
                    continue

        raise RuntimeError(f"Embedding alınamadı, son hata: {last_error}")

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]

    def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        last_error = None
        attempts = max(self.max_retries_per_call, len(self.api_keys))

        for attempt in range(attempts):
            try:
                response = self._client.models.generate_content(
                    model=self.generation_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                    ) if system_prompt else None,
                )
                return response.text
            except Exception as e:
                last_error = e
                if self._is_rate_limit_error(e):
                    self._rotate_key()
                    continue
                else:
                    time.sleep(2)
                    continue

        raise RuntimeError(f"Metin üretilemedi, son hata: {last_error}")