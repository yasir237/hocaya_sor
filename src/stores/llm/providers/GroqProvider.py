"""
Groq tabanlı LLM provider — YALNIZCA metin üretimi (generate_text) için.

Groq embedding API'si sunmuyor (sadece hızlı LLM inference yapıyor),
bu yüzden embed_text / embed_batch çağrılırsa NotImplementedError fırlatır.
Embedding tarafı hâlâ GoogleProvider üzerinden yürütülmelidir.

Rate limit (429) durumunda otomatik retry yapar; Groq'un ücretsiz tier'ı
tek key ile de Google'a göre çok daha cömert olduğu için key rotasyonuna
şimdilik gerek yok.
"""

import time

from groq import Groq

from stores.llm.LLMInterface import LLMInterface


class GroqProvider(LLMInterface):

    def __init__(
        self,
        api_key: str,
        generation_model: str = "llama-3.3-70b-versatile",
        max_retries_per_call: int = 3,
    ):
        if not api_key:
            raise ValueError("GroqProvider için GROQ_API_KEY gerekli.")

        self.generation_model = generation_model
        self.max_retries_per_call = max_retries_per_call
        self._client = Groq(api_key=api_key)

    def _is_rate_limit_error(self, error: Exception) -> bool:
        msg = str(error).lower()
        return "429" in msg or "rate limit" in msg or "quota" in msg

    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError(
            "GroqProvider embedding desteklemiyor. Embedding için "
            "EMBEDDING_BACKEND=google kullanılmalı (GENERATION_BACKEND ayrı tutulur)."
        )

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "GroqProvider embedding desteklemiyor. Embedding için "
            "EMBEDDING_BACKEND=google kullanılmalı (GENERATION_BACKEND ayrı tutulur)."
        )

    def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error = None

        for attempt in range(self.max_retries_per_call):
            try:
                response = self._client.chat.completions.create(
                    model=self.generation_model,
                    messages=messages,
                )
                return response.choices[0].message.content
            except Exception as e:
                last_error = e
                if self._is_rate_limit_error(e):
                    time.sleep(3)
                    continue
                else:
                    time.sleep(1)
                    continue

        raise RuntimeError(f"Metin üretilemedi (Groq), son hata: {last_error}")