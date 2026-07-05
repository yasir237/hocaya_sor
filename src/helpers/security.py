"""
Şifre hashleme (bcrypt), JWT access token ve opaque token (refresh/verification) yönetimi.
"""
import datetime
import hashlib
import secrets
import uuid
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from helpers.config import get_settings
from models.db_connection import get_db
from models.db_schemes.hocaya_sor.schemes.user import User
from models.enums.ResponseEnums import ResponseSignal

settings = get_settings()
bearer_scheme = HTTPBearer()


# ---------- Şifre hashleme ----------
def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


# ---------- Access token (JWT, kısa ömürlü) ----------
def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ResponseSignal.INVALID_TOKEN_TYPE.value,
            )
        return uuid.UUID(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ResponseSignal.TOKEN_EXPIRED.value,
        )
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ResponseSignal.INVALID_TOKEN.value,
        )


# ---------- Opaque token (refresh / e-posta doğrulama, DB'de hash tutulur) ----------
def generate_opaque_token() -> str:
    """Rastgele, tahmin edilemez bir token üretir (ham hali sadece client'a/e-postaya gider)."""
    return secrets.token_urlsafe(48)


def hash_opaque_token(token: str) -> str:
    """DB'de tutulacak sha256 hash. Ham token asla veritabanına yazılmaz."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        days=settings.JWT_REFRESH_EXPIRE_DAYS
    )

def generate_verification_code() -> str:
    """6 haneli, tahmin edilemez rastgele bir doğrulama kodu üretir."""
    return f"{secrets.randbelow(1_000_000):06d}"


def verification_token_expiry() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES
    )



# ---------- Dependency: mevcut kullanıcıyı çöz ----------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_access_token(credentials.credentials)
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ResponseSignal.USER_NOT_FOUND.value,
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ResponseSignal.ACCOUNT_DISABLED.value,
        )
    return user
