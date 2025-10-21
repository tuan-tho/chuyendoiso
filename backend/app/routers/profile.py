# app/routers/profile.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore
from sqlalchemy.orm import Session  # type: ignore
from passlib.context import CryptContext  # type: ignore

from ..database import get_db
from .. import models, schemas
from ..auth_utils import get_current_user  # middleware xác thực JWT

router = APIRouter(prefix="/profile", tags=["Profile"])

# ===== Password helpers =====
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# ===== Helper: build output dict phù hợp StudentProfileOut =====
def _profile_out(
    profile: models.StudentProfile,
    full_name: str | None,
    fallback_student_code: str,
) -> dict:
    """
    Chuẩn hóa dữ liệu trả về theo schemas.StudentProfileOut.
    - student_code: ưu tiên profile.student_id (nếu có), fallback = username.
    - Chỉ trả những field tồn tại trong StudentProfileOut.
    """
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "full_name": full_name,

        # thông tin hồ sơ
        "major": getattr(profile, "major", None),
        "address": getattr(profile, "address", None),
        "dob": getattr(profile, "dob", None),
        "gender": getattr(profile, "gender", None),
        "hometown": getattr(profile, "hometown", None),
        "guardian_name": getattr(profile, "guardian_name", None),
        "guardian_phone": getattr(profile, "guardian_phone", None),

        # cư trú
        "building": getattr(profile, "building", None),
        "bed": getattr(profile, "bed", None),
        "checkin_date": getattr(profile, "checkin_date", None),

        # tương thích: schema đang có student_code
        "student_code": getattr(profile, "student_id", None) or fallback_student_code,
    }

# ===== Me: Get profile =====
@router.get("/me", response_model=schemas.StudentProfileOut)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ sinh viên mới có hồ sơ cá nhân",
        )

    profile = (
        db.query(models.StudentProfile)
        .filter(models.StudentProfile.user_id == current_user.id)
        .first()
    )
    # Tự tạo profile rỗng nếu chưa có
    if not profile:
        profile = models.StudentProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    # fallback_student_code = username (mã SV)
    return _profile_out(profile, current_user.full_name, current_user.username)

# ===== Me: Update profile (WHITELIST) =====
@router.put("/me", response_model=schemas.StudentProfileOut)
def update_my_profile(
    payload: schemas.StudentProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ sinh viên mới có quyền cập nhật hồ sơ",
        )

    profile = (
        db.query(models.StudentProfile)
        .filter(models.StudentProfile.user_id == current_user.id)
        .first()
    )
    if not profile:
        # Nếu chưa có thì khởi tạo rỗng
        profile = models.StudentProfile(user_id=current_user.id)
        db.add(profile)
        db.flush()

    data = payload.model_dump(exclude_unset=True)

    # ---- WHITELIST bảng users
    # full_name
    if "full_name" in data and data["full_name"] is not None:
        current_user.full_name = data["full_name"]
    # email
    if "email" in data and data["email"] is not None:
        current_user.email = data["email"]
    # phone
    if "phone" in data and data["phone"] is not None:
        current_user.phone = data["phone"]

    # ---- WHITELIST bảng student_profiles
    # address
    if "address" in data and data["address"] is not None:
        profile.address = data["address"]

    # ⚠️ Không cho SV tự sửa: faculty/room/bed/building/checkin_date...

    db.add_all([current_user, profile])
    db.commit()
    db.refresh(profile)
    db.refresh(current_user)

    return _profile_out(profile, current_user.full_name, current_user.username)

# ===== Admin: Get profile by user_id =====
@router.get("/{user_id}", response_model=schemas.StudentProfileOut)
def get_profile_by_user_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin có quyền truy cập",
        )

    profile = (
        db.query(models.StudentProfile)
        .filter(models.StudentProfile.user_id == user_id)
        .first()
    )
    if not profile:
        # Cho trải nghiệm mượt mà hơn: tự tạo rỗng thay vì 404
        profile = models.StudentProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    user_obj = db.query(models.User).filter(models.User.id == user_id).first()
    full_name = user_obj.full_name if user_obj else None
    fallback_student_code = user_obj.username if user_obj else ""

    return _profile_out(profile, full_name, fallback_student_code)

# ===== Me: Change password =====
@router.post("/change-password", response_model=schemas.ChangePasswordOut)
def change_password(
    payload: schemas.ChangePasswordIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng")

    current_user.hashed_password = get_password_hash(payload.new_password)
    db.add(current_user)
    db.commit()
    return schemas.ChangePasswordOut(message="Đổi mật khẩu thành công")
