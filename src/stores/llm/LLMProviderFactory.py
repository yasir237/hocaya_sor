"""
.env dosyasındaki EMBEDDING_BACKEND / GENERATION_BACKEND değerlerine bakarak
doğru provider'ı döner.

Embedding ve generation ARTIK AYRI provider'lar olabilir:
  - Embedding her zaman Google üzerinden yürütülür (Groq embedding sunmuyor).
  - Generation Google veya Groq olabilir (.env -> GENERATION_BACKEND).

Provider değiştirmek istediğinde sadece .env'deki ilgili backend değerini
değiştirmen yeterli, kodda hiçbir yer değişmiyor.
"""
import os

from stores.llm.LLMInterface import LLMInterface
from stores.llm.providers.GoogleProvider import GoogleProvider
from stores.llm.providers.GroqProvider import GroqProvider


class LLMProviderFactory:

    @staticmethod
    def _create_google(embedding_dim: int | None = None) -> GoogleProvider:
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
            embedding_model=os.getenv("GOOGLE_EMBEDDING_MODEL", "gemini-embedding-001"),
            generation_model=os.getenv("GOOGLE_GENERATION_MODEL", "gemini-2.5-flash"),
            embedding_dim=embedding_dim or int(os.getenv("EMBEDDING_DIM", "768")),
        )

    @staticmethod
    def _create_groq() -> GroqProvider:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY .env içinde tanımlı değil. Örn: GROQ_API_KEY=gsk_..."
            )
        return GroqProvider(
            api_key=api_key,
            generation_model=os.getenv("GROQ_GENERATION_MODEL", "llama-3.3-70b-versatile"),
        )

    @staticmethod
    def create_embedding_provider(backend: str | None = None) -> LLMInterface:
        """Embedding için provider döner. Şu an sadece Google destekleniyor."""
        backend = (backend or os.getenv("EMBEDDING_BACKEND", "google")).lower()

        if backend == "google":
            return LLMProviderFactory._create_google()

        raise ValueError(f"Bilinmeyen EMBEDDING_BACKEND: '{backend}'")

    @staticmethod
    def create_generation_provider(backend: str | None = None) -> LLMInterface:
        """Metin üretimi (RAG cevabı) için provider döner. Google veya Groq olabilir."""
        backend = (backend or os.getenv("GENERATION_BACKEND", "google")).lower()

        if backend == "google":
            return LLMProviderFactory._create_google()
        if backend == "groq":
            return LLMProviderFactory._create_groq()

        raise ValueError(f"Bilinmeyen GENERATION_BACKEND: '{backend}'")

    @staticmethod
    def create(backend: str | None = None) -> LLMInterface:
        """
        GERİYE DÖNÜK UYUMLULUK için bırakıldı (örn. fill_embeddings.py,
        test_rag.py gibi eski script'ler hâlâ bunu çağırıyor olabilir).
        Yeni kodda create_embedding_provider / create_generation_provider kullan.
        """
        return LLMProviderFactory.create_embedding_provider(backend)