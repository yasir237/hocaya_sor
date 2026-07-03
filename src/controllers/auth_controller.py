"""
Kullanıcı kayıt, giriş, token yenileme ve çıkış iş mantığı.
"""
import datetime
import logging
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from models.enums.ResponseEnums import ResponseSignal

from helpers.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)
from models.db_schemes.hocaya_sor.schemes.user import User
from models.db_schemes.hocaya_sor.schemes.refresh_token import RefreshToken
from models.schemas.auth_schemas import (
    RegisterRequest, LoginRequest, TokenResponse,
    RefreshRequest, AccessTokenResponse, LogoutRequest,
)

logger = logging.getLogger(__name__)


def _issue_tokens(user_id, db: Session) -> TokenResponse:
    access_token = create_access_token(user_id)
    raw_refresh = generate_refresh_token()

    try:
        record = RefreshToken(
            user_id=user_id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=refresh_token_expiry(),
        )
        db.add(record)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Refresh token kaydetme hatası (user_id=%s)", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ResponseSignal.SERVER_ERROR.value,
        )

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


async def register_user(request: RegisterRequest, db: Session) -> TokenResponse:
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu e-posta ile zaten bir hesap var.",
        )

    try:
        user = User(
            email=request.email,
            hashed_password=hash_password(request.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        logger.exception("Kullanıcı kayıt hatası (email=%s)", request.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ResponseSignal.SERVER_ERROR.value,
        )

    return _issue_tokens(user.id, db)


async def login_user(request: LoginRequest, db: Session) -> TokenResponse:
    user = db.query(User).filter(User.email == request.email).first()
    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ResponseSignal.INVALID_CREDENTIALS.value,
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ResponseSignal.ACCOUNT_DISABLED.value,
        )
    return _issue_tokens(user.id, db)


async def refresh_access_token(request: RefreshRequest, db: Session) -> AccessTokenResponse:
    token_hash = hash_refresh_token(request.refresh_token)

    try:
        record = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    except Exception:
        logger.exception("Refresh token sorgulama hatası")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ResponseSignal.SERVER_ERROR.value,
        )

    now = datetime.datetime.now(datetime.timezone.utc)
    invalid = (
        record is None
        or record.revoked_at is not None
        or record.expires_at < now
    )
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ResponseSignal.INVALID_REFRESH_TOKEN.value,
        )

    access_token = create_access_token(record.user_id)
    return AccessTokenResponse(access_token=access_token)


async def logout_user(request: LogoutRequest, db: Session) -> None:
    token_hash = hash_refresh_token(request.refresh_token)

    try:
        record = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if record is not None and record.revoked_at is None:
            record.revoked_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
    except Exception:
        db.rollback()
        logger.exception("Logout / refresh token iptal hatası")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ResponseSignal.SERVER_ERROR.value,
        )
    # Token bulunamasa/geçersiz olsa bile aynı (içerik açığa vermeyen) yanıt döneriz.