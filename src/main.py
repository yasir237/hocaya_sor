from fastapi import FastAPI
from helpers.config import get_settings

app = FastAPI()


@app.get("/")
async def welcome():
    settings = get_settings()
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
    }