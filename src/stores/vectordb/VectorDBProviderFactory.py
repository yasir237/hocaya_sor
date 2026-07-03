from helpers.config import get_settings
from models.enums.VectorDBEnum import VectorDBBackendEnum
from stores.vectordb.VectorDBInterface import VectorDBInterface
from stores.vectordb.providers.PGVectorProvider import PGVectorProvider

settings = get_settings()


class VectorDBProviderFactory:

    @staticmethod
    def create(backend: VectorDBBackendEnum | None = None) -> VectorDBInterface:
        backend = backend or settings.VECTORDB_BACKEND

        if backend == VectorDBBackendEnum.PGVECTOR:
            return PGVectorProvider(max_distance=settings.VECTOR_MAX_DISTANCE)

        raise ValueError(f"Bilinmeyen VECTORDB_BACKEND: '{backend}'")