"""
Kullanıcı kayıt, e-posta doğrulama, giriş, token yenileme ve çıkış iş mantığı.
"""
import datetime
import logging
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from helpers.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    refresh_token_expiry,
    verification_token_expiry,
)
from helpers.email import send_verification_email
from models.db_schemes.hocaya_sor.schemes.user import User
from models.db_schemes.hocaya_sor.schemes.refresh_token import RefreshToken
from models.db_schemes.hocaya_sor.schemes.email_verification_token import EmailVerificationToken
from models.enums.ResponseEnums import ResponseSignal
from models.schemas.auth_schemas import (
    RegisterRequest, LoginRequest, TokenResponse, MessageResponse,
    RefreshRequest, AccessTokenResponse, LogoutRequest,
    VerifyEmailRequest, ResendVerificationRequest, UserResponse,
    UpdateProfileRequest
)
from helpers.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    refresh_token_expiry,
    verification_token_expiry,
    generate_verification_code,
)

from helpers.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

_GENERIC_REGISTER_MESSAGE = (
    "Kayıt isteğiniz alındı. E-posta adresinize gönderilen talimatları takip edin."
)
_GENERIC_RESEND_MESSAGE = (
    "Eğer bu e-posta adresi kayıtlıysa ve doğrulanmamışsa, "
    "yeni bir doğrulama e-postası gönderildi."
)


def _issue_tokens(user_id, db: Session) -> TokenResponse:
    access_token = create_access_token(user_id)
    raw_refresh = generate_opaque_token()

    try:
        record = RefreshToken(
            user_id=user_id,
            token_hash=hash_opaque_token(raw_refresh),
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

MAX_VERIFICATION_ATTEMPTS = 5

def _create_and_send_verification(user_id, email: str, db: Session) -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    cooldown_start = now - datetime.timedelta(
        minutes=settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_MINUTES
    )

    last = (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.user_id == user_id)
        .order_by(EmailVerificationToken.created_at.desc())
        .first()
    )
    if last is not None and last.created_at > cooldown_start:
        # Cooldown aktif — sessizce çık, yeni kod üretme/gönderme (spam önleme).
        # Çağıran taraf (register/resend_verification) yine de aynı generic
        # mesajı döner, kullanıcıya cooldown olduğu belli edilmez.
        logger.info("Doğrulama kodu cooldown içinde, gönderim atlandı (user_id=%s)", user_id)
        return

    code = generate_verification_code()
    try:
        db.query(EmailVerificationToken).filter(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.used_at.is_(None),
        ).update({"used_at": now})

        record = EmailVerificationToken(
            user_id=user_id,
            code_hash=hash_opaque_token(code),
            expires_at=verification_token_expiry(),
        )
        db.add(record)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Doğrulama kodu kaydetme hatası (user_id=%s)", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ResponseSignal.SERVER_ERROR.value,
        )
    send_verification_email(email, code)

async def verify_email(request: VerifyEmailRequest, db: Session) -> MessageResponse:
    user = db.query(User).filter(User.email == request.email).first()
    if user is None or user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ResponseSignal.INVALID_VERIFICATION_TOKEN.value,
        )

    record = (
        db.query(EmailVerificationToken)
        .filter(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.used_at.is_(None),
        )
        .order_by(EmailVerificationToken.created_at.desc())
        .first()
    )

    now = datetime.datetime.now(datetime.timezone.utc)
    if record is None or record.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ResponseSignal.INVALID_VERIFICATION_TOKEN.value,
        )

    if record.attempts >= MAX_VERIFICATION_ATTEMPTS:
        record.used_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ResponseSignal.TOO_MANY_VERIFICATION_ATTEMPTS.value,
        )

    if hash_opaque_token(request.code) != record.code_hash:
        record.attempts += 1
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ResponseSignal.INVALID_VERIFICATION_TOKEN.value,
        )

    try:
        user.is_verified = True
        record.used_at = now
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("E-posta doğrulama hatası (user_id=%s)", user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ResponseSignal.SERVER_ERROR.value,
        )

    return MessageResponse(message="E-posta adresiniz doğrulandı. Artık giriş yapabilirsiniz.")

async def register_user(request: RegisterRequest, db: Session) -> MessageResponse:
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        # Enumeration'ı önlemek için var olan hesapta da AYNI genel mesajı dönüyoruz.
        return MessageResponse(message=_GENERIC_REGISTER_MESSAGE)

    try:
        user = User(
            name=request.name,
            email=request.email,
            hashed_password=hash_password(request.password),
            is_verified=False,
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

    _create_and_send_verification(user.id, user.email, db)
    return MessageResponse(message=_GENERIC_REGISTER_MESSAGE)

async def get_profile(user: User) -> UserResponse:
    """"Giriş yapmış kullanıcılarının profil bilgisini döner"""
    return UserResponse.model_validate(user)

async def update_profile(request: UpdateProfileRequest, user:User, db: Session) -> UserResponse:
    """Giriş yapmış kullanıcının adını günceller"""
    try:
        user.name = request.name
        db.commit()
        db.refresh(user)
    except:
        db.rollback()
        logger.exception("Profil güncelleme hatası (user_id=%s)",user.id)
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ResponseSignal.SERVER_ERROR.value,
        )
    
    return UserResponse.model_validate(user)

async def resend_verification(request: ResendVerificationRequest, db: Session) -> MessageResponse:
    user = db.query(User).filter(User.email == request.email).first()
    if user is None or user.is_verified:
        return MessageResponse(message=_GENERIC_RESEND_MESSAGE)  # enumeration'ı önle

    _create_and_send_verification(user.id, user.email, db)
    return MessageResponse(message=_GENERIC_RESEND_MESSAGE)

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
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ResponseSignal.EMAIL_NOT_VERIFIED.value,
        )
    return _issue_tokens(user.id, db)


async def refresh_access_token(request: RefreshRequest, db: Session) -> AccessTokenResponse:
    token_hash = hash_opaque_token(request.refresh_token)

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
    token_hash = hash_opaque_token(request.refresh_token)

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


