from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from models.enums.LLMEnums import EmbeddingBackendEnum, GenerationBackendEnum
from models.enums.VectorDBEnum import VectorDBBackendEnum


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    EMBEDDING_BACKEND: EmbeddingBackendEnum
    GOOGLE_API_KEYS: str
    GOOGLE_EMBEDDING_MODEL: str
    GOOGLE_GENERATION_MODEL: str
    EMBEDDING_DIM: int
    EMBEDDING_SLEEP_SECONDS: float

    GENERATION_BACKEND: GenerationBackendEnum = GenerationBackendEnum.GOOGLE
    GROQ_API_KEY: str = ""
    GROQ_GENERATION_MODEL: str = "llama-3.3-70b-versatile"

    VECTORDB_BACKEND: VectorDBBackendEnum
    VECTOR_MAX_DISTANCE: float

    # JWT / Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 30

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def check_jwt_secret_strength(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY en az 32 karakter olmalı (örn. `openssl rand -hex 32` ile üretin)."
            )
        return v

    model_config = SettingsConfigDict(env_file=".env")


def get_settings():
    return Settings()