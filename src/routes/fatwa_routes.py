"""
Fetva API endpoint'leri.
"""
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from controllers.fatwa_controller import ask_question, submit_feedback
from models.schemas.fatwa_schemas import (
    AskRequest, AskResponse, FeedbackRequest, FeedbackResponse,
)
from helpers.security import get_current_user
from models.db_schemes.hocaya_sor.schemes.user import User
from models.db_connection import get_db

fatwa_router = APIRouter(prefix="/api/v1/fatwa", tags=["Fetva"])


@fatwa_router.post("/ask", response_model=AskResponse, summary="Fetva sor")
async def ask(
    request: AskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Kullanıcının sorusunu alır, ilgili fetvaları vektör aramasıyla bulur
    ve LLM aracılığıyla Türkçe bir cevap üretir.

    JWT ile korumalıdır. Soru/cevap otomatik loglanır; dönen `log_id`
    feedback endpoint'inde kullanılır.
    """
    return await ask_question(request, current_user.id, db)


@fatwa_router.post(
    "/feedback/{log_id}", response_model=FeedbackResponse, summary="Cevaba geri bildirim ver"
)
async def feedback(
    log_id: uuid.UUID,
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Bir soru-cevap logu için like/dislike geri bildirimi kaydeder.
    Sadece kendi sorduğunuz sorulara geri bildirim verebilirsiniz.
    Tekrar çağrılırsa mevcut feedback güncellenir.
    """
    return await submit_feedback(log_id, request, current_user.id, db)