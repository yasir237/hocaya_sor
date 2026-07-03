"""
.env dosyasındaki EMBEDDING_BACKEND / GENERATION_BACKEND değerlerine bakarak
doğru provider'ı döner.

Embedding ve generation ARTIK AYRI provider'lar olabilir:
  - Embedding her zaman Google üzerinden yürütülür (Groq embedding sunmuyor).
  - Generation Google veya Groq olabilir (.env -> GENERATION_BACKEND).

Provider değiştirmek istediğinde sadece .env'deki ilgili backend değerini
değiştirmen yeterli, kodda hiçbir yer değişmiyor.
"""
from helpers.config import get_settings
from models.enums.LLMEnums import EmbeddingBackendEnum, GenerationBackendEnum
from stores.llm.LLMInterface import LLMInterface
from stores.llm.providers.GoogleProvider import GoogleProvider
from stores.llm.providers.GroqProvider import GroqProvider

settings = get_settings()


class LLMProviderFactory:

    @staticmethod
    def _create_google(embedding_dim: int | None = None) -> GoogleProvider:
        raw_keys = settings.GOOGLE_API_KEYS
        api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        if not api_keys:
            raise ValueError(
                "GOOGLE_API_KEYS .env içinde tanımlı değil. "
                "Virgülle ayrılmış key listesi bekleniyor, örn: "
                "GOOGLE_API_KEYS=key1,key2,key3"
            )
        return GoogleProvider(
            api_keys=api_keys,
            embedding_model=settings.GOOGLE_EMBEDDING_MODEL,
            generation_model=settings.GOOGLE_GENERATION_MODEL,
            embedding_dim=embedding_dim or settings.EMBEDDING_DIM,
        )

    @staticmethod
    def _create_groq() -> GroqProvider:
        api_key = settings.GROQ_API_KEY.strip()
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY .env içinde tanımlı değil. Örn: GROQ_API_KEY=gsk_..."
            )
        return GroqProvider(
            api_key=api_key,
            generation_model=settings.GROQ_GENERATION_MODEL,
        )

    @staticmethod
    def create_embedding_provider(
        backend: EmbeddingBackendEnum | None = None,
    ) -> LLMInterface:
        """Embedding için provider döner. Şu an sadece Google destekleniyor."""
        backend = backend or settings.EMBEDDING_BACKEND

        if backend == EmbeddingBackendEnum.GOOGLE:
            return LLMProviderFactory._create_google()

        raise ValueError(f"Bilinmeyen EMBEDDING_BACKEND: '{backend}'")

    @staticmethod
    def create_generation_provider(
        backend: GenerationBackendEnum | None = None,
    ) -> LLMInterface:
        """Metin üretimi (RAG cevabı) için provider döner. Google veya Groq olabilir."""
        backend = backend or settings.GENERATION_BACKEND

        if backend == GenerationBackendEnum.GOOGLE:
            return LLMProviderFactory._create_google()
        if backend == GenerationBackendEnum.GROQ:
            return LLMProviderFactory._create_groq()

        raise ValueError(f"Bilinmeyen GENERATION_BACKEND: '{backend}'")

    @staticmethod
    def create(backend: EmbeddingBackendEnum | None = None) -> LLMInterface:
        """
        GERİYE DÖNÜK UYUMLULUK için bırakıldı (örn. fill_embeddings.py,
        test_rag.py gibi eski script'ler hâlâ bunu çağırıyor olabilir).
        Yeni kodda create_embedding_provider / create_generation_provider kullan.
        """
        return LLMProviderFactory.create_embedding_provider(backend)