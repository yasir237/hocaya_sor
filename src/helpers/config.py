from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    EMBEDDING_BACKEND: str 
    GOOGLE_API_KEYS: str 
    GOOGLE_EMBEDDING_MODEL: str 
    GOOGLE_GENERATION_MODEL: str 
    EMBEDDING_DIM: int 
    VECTORDB_BACKEND: str 
    EMBEDDING_SLEEP_SECONDS: float 

    VECTOR_MAX_DISTANCE:float

    model_config = SettingsConfigDict(env_file=".env")


def get_settings():
    return Settings()