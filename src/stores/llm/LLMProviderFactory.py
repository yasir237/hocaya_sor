"""
.env dosyasındaki EMBEDDING_BACKEND değerine bakarak doğru LLM/Embedding
provider'ını döner. Provider değiştirmek istediğinde (örn. google -> ollama)
sadece .env'deki EMBEDDING_BACKEND değerini değiştirmen yeterli, kodda
hiçbir yer değişmiyor.
"""

import os

from stores.llm.LLMInterface import LLMInterface
from stores.llm.providers.GoogleProvider import GoogleProvider


class LLMProviderFactory:

    @staticmethod
    def create(backend: str | None = None) -> LLMInterface:
        backend = (backend or os.getenv("EMBEDDING_BACKEND", "google")).lower()

        if backend == "google":
            raw_keys = os.getenv("GOOGLE_API_KEYS", "")
            api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
            if not api_keys:
                raise ValueError(
                    "GOOGLE_API_KEYS .env içinde tanımlı değil. "
                    "Virgülle ayrılmış key listesi bekleniyor, örn: "
                    "GOOGLE_API_KEYS=key1,key2,key3"
                )
            return GoogleProvider(
                api_keys=api_keys,
                embedding_model=os.getenv("GOOGLE_EMBEDDING_MODEL", "models/text-embedding-004"),
                generation_model=os.getenv("GOOGLE_GENERATION_MODEL", "gemini-1.5-flash"),
                embedding_dim=int(os.getenv("EMBEDDING_DIM", "768")),
            )

        # ileride buraya elif backend == "ollama": ... eklenecek

        raise ValueError(f"Bilinmeyen EMBEDDING_BACKEND: '{backend}'")