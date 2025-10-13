# app/routers/profile.py
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

# Helper: build output dict “sạch” cho StudentProfileOut
def _profile_out(profile: models.StudentProfile, full_name: str | None) -> dict:
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "student_code": profile.student_code,
        "faculty": profile.faculty,
        "major": profile.major,
        "address": profile.address,
        "dob": profile.dob,
        "gender": profile.gender,
        "phone": profile.phone,
        "email": profile.email,
        "hometown": profile.hometown,
        "guardian_name": profile.guardian_name,
        "guardian_phone": profile.guardian_phone,
        "building": profile.building,
        "room": profile.room,
        "bed": profile.bed,
        "checkin_date": profile.checkin_date,
        "full_name": full_name,
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

    return _profile_out(profile, current_user.full_name)

# ===== Me: Update profile =====
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
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ")

    # Cập nhật các trường hồ sơ
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "full_name":
            # cập nhật họ tên sang bảng users
            if value is not None:
                current_user.full_name = value
                db.add(current_user)
            continue
        if hasattr(profile, field):
            setattr(profile, field, value)

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return _profile_out(profile, current_user.full_name)

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
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ sinh viên")

    user_obj = db.query(models.User).filter(models.User.id == user_id).first()
    full_name = user_obj.full_name if user_obj else None

    return _profile_out(profile, full_name)

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
