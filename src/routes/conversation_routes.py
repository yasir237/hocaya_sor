"""
Sohbet listeleme ve geçmiş mesajları getirme endpoint'leri.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session

from controllers.conversation_controller import list_conversations, get_messages_page
from models.db_connection import get_db
from models.schemas.conversation_schemas import ConversationResponse, ConversationMessagesPage
from models.db_schemes.hocaya_sor.schemes.user import User
from helpers.security import get_current_user
from helpers.rate_limiter import limiter


conversation_router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])


@conversation_router.get("", response_model=list[ConversationResponse], summary="Sohbetlerimi listele")
@limiter.limit("30/minute")
async def get_conversations(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await list_conversations(user.id, db)


@conversation_router.get(
    "/{conversation_id}/messages",
    response_model=ConversationMessagesPage,
    summary="Bir sohbetin mesaj geçmişini sayfalı getir",
)
@limiter.limit("30/minute")
async def get_conversation_messages(
    request: Request,
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    before: Optional[str] = Query(
        None,
        description="'{created_at_iso}|{log_id}' formatında cursor. Verilmezse en yeni sayfadan başlar.",
    ),
):
    return await get_messages_page(
        db=db,
        conversation_id=conversation_id,
        user_id=user.id,
        limit=limit,
        before=before,
    )