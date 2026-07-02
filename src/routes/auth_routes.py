"""
Kullanıcı kayıt ve giriş endpoint'leri.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from controllers.auth_controller import register_user, login_user
from models.db_connection import get_db
from models.schemas.auth_schemas import RegisterRequest, LoginRequest, TokenResponse

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@auth_router.post("/register", response_model=TokenResponse, summary="Kayıt ol")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Yeni kullanıcı kaydı oluşturur ve giriş yapılmış olarak bir token döner.
    - **email**: Geçerli bir e-posta adresi
    - **password**: En az 8 karakter
    """
    return await register_user(request, db)


@auth_router.post("/login", response_model=TokenResponse, summary="Giriş yap")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    E-posta ve şifre ile giriş yapar, geçerliyse bir JWT token döner.
    """
    return await login_user(request, db)