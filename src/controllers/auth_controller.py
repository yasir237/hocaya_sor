"""
Kullanıcı kayıt ve giriş iş mantığı.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from helpers.security import hash_password, verify_password, create_access_token
from models.db_schemes.hocaya_sor.schemes.user import User
from models.schemas.auth_schemas import RegisterRequest, LoginRequest, TokenResponse


async def register_user(request: RegisterRequest, db: Session) -> TokenResponse:
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu e-posta ile zaten bir hesap var.",
        )

    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


async def login_user(request: LoginRequest, db: Session) -> TokenResponse:
    user = db.query(User).filter(User.email == request.email).first()
    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesap devre dışı bırakılmış.",
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)