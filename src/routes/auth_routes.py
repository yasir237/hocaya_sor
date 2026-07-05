"""
Kullanıcı kayıt, e-posta doğrulama, giriş, token yenileme ve çıkış endpoint'leri.
"""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from controllers.auth_controller import (
    register_user, verify_email, resend_verification,
    login_user, refresh_access_token, logout_user, 
    get_profile, update_profile,
)
from models.db_connection import get_db
from models.schemas.auth_schemas import (
    RegisterRequest, LoginRequest, TokenResponse, MessageResponse,
    RefreshRequest, AccessTokenResponse, LogoutRequest,
    VerifyEmailRequest, ResendVerificationRequest, UserResponse,
    UpdateProfileRequest,
)
from models.db_schemes.hocaya_sor.schemes.user import User

from helpers.security import get_current_user
from helpers.rate_limiter import limiter

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@auth_router.post(
    "/register", response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED, summary="Kayıt ol",
)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    """
    Yeni kullanıcı kaydı oluşturur. Hesap doğrudan aktif olmaz; e-posta adresine
    bir doğrulama bağlantısı gönderilir. Doğrulanana kadar giriş yapılamaz.
    """
    return await register_user(body, db)


@auth_router.post("/verify-email", response_model=MessageResponse, summary="E-posta doğrula")
@limiter.limit("10/minute")
async def verify_email_endpoint(request: Request, body: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    E-postayla gönderilen doğrulama token'ını kullanarak hesabı aktifleştirir.
    """
    return await verify_email(body, db)


@auth_router.post(
    "/resend-verification", response_model=MessageResponse,
    summary="Doğrulama e-postasını tekrar gönder",
)
@limiter.limit("3/minute")
async def resend_verification_endpoint(
    request: Request, body: ResendVerificationRequest, db: Session = Depends(get_db)
):
    """
    Doğrulanmamış bir hesap için yeni bir doğrulama e-postası gönderir.
    E-posta kayıtlı olsun olmasın aynı genel yanıt döner (enumeration önleme).
    """
    return await resend_verification(body, db)


@auth_router.post("/login", response_model=TokenResponse, summary="Giriş yap")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    """
    E-posta ve şifre ile giriş yapar; bir access token ve bir refresh token döner.
    E-posta doğrulanmamışsa 403 döner.
    """
    return await login_user(body, db)


@auth_router.post("/refresh", response_model=AccessTokenResponse, summary="Access token yenile")
@limiter.limit("20/minute")
async def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
    """Geçerli bir refresh token karşılığında yeni bir access token üretir."""
    return await refresh_access_token(body, db)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Çıkış yap")
@limiter.limit("10/minute")
async def logout(request: Request, body: LogoutRequest, db: Session = Depends(get_db)):
    """Verilen refresh token'ı iptal eder."""
    await logout_user(body, db)
    return None

@auth_router.get("/me", response_model=UserResponse, summary="Profil Bilgisi")
@limiter.limit("30/minute")
async def me(request: Request, user: User = Depends(get_current_user), db:Session = Depends(get_db)):
    return await get_profile(user)

@auth_router.patch("/me", response_model=UserResponse, summary="isim güncelle")
@limiter.limit("3/minute")
async def update_me(request: Request, body: UpdateProfileRequest, user: User = Depends(get_current_user), db:Session = Depends(get_db)):
    return await update_profile(body, user, db)