from enum import Enum


class VectorDBBackendEnum(str, Enum):
    PGVECTOR = "pgvector"
    # QDRANT = "qdrant"  # ileride eklenirse aç