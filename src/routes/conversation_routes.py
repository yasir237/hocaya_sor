"""
Sohbet listeleme ve geçmiş mesajları getirme endpoint'leri.
"""
import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from controllers.conversation_controller import list_conversations, get_conversation_messages
from models.db_connection import get_db
from models.schemas.conversation_schemas import ConversationResponse, ConversationMessageResponse
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
    response_model=list[ConversationMessageResponse],
    summary="Bir sohbetin mesaj geçmişini getir",
)
@limiter.limit("30/minute")
async def get_messages(
    request: Request,
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await get_conversation_messages(conversation_id, user.id, db)