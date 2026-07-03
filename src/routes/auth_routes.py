"""
Kullanıcı kayıt, giriş, token yenileme ve çıkış endpoint'leri.
"""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from controllers.auth_controller import (
    register_user, login_user, refresh_access_token, logout_user,
)
from models.db_connection import get_db
from models.schemas.auth_schemas import (
    RegisterRequest, LoginRequest, TokenResponse,
    RefreshRequest, AccessTokenResponse, LogoutRequest,
)
from helpers.rate_limiter import limiter

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@auth_router.post("/register", response_model=TokenResponse, summary="Kayıt ol")
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    """
    Yeni kullanıcı kaydı oluşturur; bir access token (30 dk) ve bir refresh
    token (30 gün) döner. Dakikada en fazla 5 istek.
    """
    return await register_user(body, db)


@auth_router.post("/login", response_model=TokenResponse, summary="Giriş yap")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    """
    E-posta ve şifre ile giriş yapar; bir access token (30 dk) ve bir refresh
    token (30 gün) döner. Dakikada en fazla 5 istek.
    """
    return await login_user(body, db)


@auth_router.post("/refresh", response_model=AccessTokenResponse, summary="Access token yenile")
@limiter.limit("20/minute")
async def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
    """
    Geçerli bir refresh token karşılığında yeni bir access token üretir.
    Refresh token'ın kendisi değişmez (rotasyon yapılmıyor).
    """
    return await refresh_access_token(body, db)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Çıkış yap")
@limiter.limit("10/minute")
async def logout(request: Request, body: LogoutRequest, db: Session = Depends(get_db)):
    """
    Verilen refresh token'ı iptal eder. Bundan sonra bu refresh token ile
    yeni access token alınamaz. Mevcut access token, doğal süresi
    (en fazla 30 dk) dolana kadar geçerliliğini korur.
    """
    await logout_user(body, db)
    return None