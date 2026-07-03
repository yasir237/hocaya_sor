from dotenv import load_dotenv
load_dotenv()



import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from helpers.config import get_settings
from routes.fatwa_routes import fatwa_router
from routes.auth_routes import auth_router
from helpers.rate_limiter import limiter
from models.enums.ResponseEnums import ResponseSignal


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Yakalanmayan tüm hatalar buradan geçer. İç detaylar (stack trace, hata
    mesajı) client'a asla dönmez, sadece sunucu loglarına yazılır.
    """
    logger.exception("Beklenmeyen hata: %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": ResponseSignal.SERVER_ERROR.value},
    )


app.include_router(fatwa_router)
app.include_router(auth_router)


@app.get("/")
async def welcome():
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
    }