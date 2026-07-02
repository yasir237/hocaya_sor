import os

from stores.vectordb.VectorDBInterface import VectorDBInterface
from stores.vectordb.providers.PGVectorProvider import PGVectorProvider


class VectorDBProviderFactory:

    @staticmethod
    def create(backend: str | None = None) -> VectorDBInterface:
        backend = (backend or os.getenv("VECTORDB_BACKEND", "pgvector")).lower()

        if backend == "pgvector":
            return PGVectorProvider(
                max_distance=float(os.getenv("VECTOR_MAX_DISTANCE", "0.20"))
            )

        raise ValueError(f"Bilinmeyen VECTORDB_BACKEND: '{backend}'")