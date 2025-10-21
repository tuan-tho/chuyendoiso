# app/deps.py
from fastapi import Depends, HTTPException, status  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from .database import get_db
from .auth_utils import decode_token, oauth2_scheme  # ✅ dùng chung oauth2_scheme
from .models import User
from .crud.users import get_user_by_username


# =========================================================
# 🔑 Lấy user từ JWT token
# =========================================================
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Giải mã token, trả về User tương ứng."""
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


# =========================================================
# 🧩 Hạn chế quyền theo vai trò
# =========================================================
def require_role(required: str):
    """Decorator tạo dependency giới hạn quyền (ví dụ: require_role('admin'))."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role != required:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Yêu cầu quyền '{required}' để truy cập.",
            )
        return user
    return checker


# =========================================================
# 🧠 Shortcut tiện dụng
# =========================================================
def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """Chỉ cho phép admin truy cập."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ quản trị viên được phép truy cập.",
        )
    return user


def get_current_student(user: User = Depends(get_current_user)) -> User:
    """Chỉ cho phép sinh viên truy cập."""
    if user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ sinh viên được phép truy cập.",
        )
    return user
