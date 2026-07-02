"""
Fetva API endpoint'leri.
"""

from fastapi import APIRouter

from controllers.fatwa_controller import ask_question
from models.schemas.fatwa_schemas import AskRequest, AskResponse


fatwa_router = APIRouter(prefix="/api/v1/fatwa", tags=["Fetva"])


@fatwa_router.post("/ask", response_model=AskResponse, summary="Fetva sor")
async def ask(request: AskRequest):
    """
    Kullanıcının sorusunu alır, ilgili fetvaları vektör aramasıyla bulur
    ve LLM aracılığıyla Türkçe bir cevap üretir.

    - **question**: Sorunuz (3-1000 karakter)
    - **top_k**: Kaç fetva baz alınsın (varsayılan: 5, maks: 10)
    """
    return await ask_question(request)