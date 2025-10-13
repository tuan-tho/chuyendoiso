# app/deps.py
from fastapi import Depends, HTTPException, status  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from .database import get_db
from .auth_utils import decode_token, oauth2_scheme  # ✅ dùng chung oauth2_scheme
from .models import User
from .crud.users import get_user_by_username


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload["sub"]
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(required: str):
    """Giới hạn quyền truy cập theo vai trò (vd: 'admin')."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role != required:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return user
    return checker
