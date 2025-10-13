# app/auth_utils.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status  # type: ignore
from fastapi.security import OAuth2PasswordBearer  # type: ignore
from jose import JWTError, jwt  # type: ignore
from passlib.context import CryptContext  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from .config import settings
from .database import get_db
from .models import User

# ===================== Password hashing =====================
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain_password: str) -> str:
    return pwd_ctx.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_ctx.verify(plain_password, hashed_password)

# ===================== JWT config =====================
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 ngày, tuỳ chỉnh .env nếu muốn

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def create_access_token(
    data: Dict[str, Any],
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
) -> str:
    """Ký JWT: payload nên có 'sub' (username) và 'user_id' nếu muốn."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

# ===================== Current user dependency =====================
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Lấy JWT từ header Authorization -> giải mã -> tìm User trong DB.
    Hỗ trợ cả 'sub' (username) và 'user_id' trong payload.
    """
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không xác thực được người dùng",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub") or payload.get("username")
    user_id = payload.get("user_id")

    user: Optional[User] = None
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
    elif username:
        user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản không tồn tại hoặc token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
