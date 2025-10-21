# app/routers/users_router.py
from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore
from sqlalchemy.orm import Session  # type: ignore
from typing import List

from .. import crud, schemas
from ..database import get_db
from ..auth_utils import get_current_user


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

# =========================================================
# 🧩 ADMIN - Quản lý tài khoản
# =========================================================
@router.get("/", response_model=List[schemas.AdminUserRow])
def list_users_admin_rows(
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user)
):
    """
    Danh sách cho bảng Admin (JOIN users + student_profiles)
    -> có đủ faculty, room (users) + bed, address (student_profiles).
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Chỉ quản trị viên được truy cập.")
    return crud.users.get_users_admin_rows(db)


# (Tuỳ chọn) Giữ endpoint raw cũ nếu chỗ khác đang dùng UserOut
@router.get("/raw", response_model=List[schemas.UserOut])
def list_users_raw(
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Chỉ quản trị viên được truy cập.")
    return crud.users.get_users(db)


@router.post("/", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: schemas.AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền tạo tài khoản.")
    try:
        return crud.users.create_user(db, user_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{user_id}", response_model=schemas.UserOut)
def update_user_admin(
    user_id: int,
    user_in: schemas.UserUpdateAdmin,
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền cập nhật.")
    u = crud.users.update_user_admin(db, user_id, user_in)
    if not u:
        raise HTTPException(status_code=404, detail="Không tìm thấy user.")
    return u


@router.delete("/{user_id}", response_model=dict)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền xóa.")
    ok = crud.users.delete_user(db, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy user.")
    return {"message": "Đã xóa tài khoản."}


# =========================================================
# 👤 SINH VIÊN - Hồ sơ cá nhân
# =========================================================
@router.get("/me", response_model=schemas.UserOut)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user)
):
    u = crud.users.get_user_by_id(db, current_user.id)
    if not u:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    return u


@router.patch("/me", response_model=schemas.UserOut)
def update_my_profile(
    user_in: schemas.ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.UserOut = Depends(get_current_user)
):
    u = crud.users.update_profile_self(db, current_user.id, user_in)
    if not u:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    return u
