from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI

from helpers.config import get_settings
from routes.fatwa_routes import fatwa_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Uygulama başlarken provider'ları ısıt (ilk isteği yavaşlatmaması için)
    from controllers.fatwa_controller import get_embedding_llm, get_generation_llm, get_vdb
    get_embedding_llm()
    get_generation_llm()
    get_vdb()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.include_router(fatwa_router)


@app.get("/")
async def welcome():
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
    }