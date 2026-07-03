from enum import Enum


class EmbeddingBackendEnum(str, Enum):
    GOOGLE = "google"
    # OLLAMA = "ollama"  # ileride eklenirse aç


class GenerationBackendEnum(str, Enum):
    GOOGLE = "google"
    GROQ = "groq"