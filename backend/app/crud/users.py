# app/crud/users.py
from sqlalchemy.orm import Session  # type: ignore
from sqlalchemy import select  # type: ignore
from typing import Optional, List

from ..models import User, StudentProfile
from ..schemas import (
    AdminUserCreate,
    UserUpdateAdmin,
    ProfileUpdate,
    UserCreate,
)
from ..auth_utils import hash_password, verify_password


# =========================================================
# 🔍 Lấy thông tin User
# =========================================================
def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_users(db: Session) -> List[User]:
    """Lấy danh sách users (raw User objects). 
    ⚠️ Không JOIN profile, không có bed/address."""
    return db.query(User).all()


# ===== NEW =====
def get_users_admin_rows(db: Session) -> List[dict]:
    """
    Danh sách cho bảng Admin (JOIN users + student_profiles)
    -> có đủ: faculty, room (từ users) + bed, address (từ student_profiles).
    """
    stmt = (
        select(
            User.id,
            User.username,
            User.full_name,
            User.email,
            User.role,
            User.faculty,
            User.room,
            StudentProfile.bed,
            StudentProfile.address,
        )
        .select_from(User)
        .join(StudentProfile, StudentProfile.user_id == User.id, isouter=True)
        .order_by(User.id.asc())
    )
    rows = db.execute(stmt).all()
    return [
        {
            "id": r.id,
            "username": r.username,
            "full_name": r.full_name,
            "email": r.email,
            "role": r.role,
            "faculty": r.faculty,
            "room": r.room,
            "bed": r.bed,
            "address": r.address,
        }
        for r in rows
    ]


# =========================================================
# 🧩 Tạo tài khoản mới
# =========================================================
def create_user(db: Session, user_in: AdminUserCreate | UserCreate) -> User:
    """
    Admin hoặc hệ thống tạo tài khoản mới.
    - username chính là MÃ SINH VIÊN.
    - Các cột email/phone/faculty/room lưu ở bảng users.
    - Các thông tin chi tiết khác (address, major, ...) ở student_profiles.
    """
    # Chống trùng mã SV/username
    if get_user_by_username(db, user_in.username):
        raise ValueError("Username already exists")

    u = User(
        username=user_in.username,  # 👈 mã sinh viên
        full_name=getattr(user_in, "full_name", None),
        hashed_password=hash_password(user_in.password),
        role=(user_in.role or "student"),
        # các cột thuộc users
        email=getattr(user_in, "email", None),
        phone=getattr(user_in, "phone", None),
        faculty=getattr(user_in, "faculty", None),
        room=getattr(user_in, "room", None),
    )
    db.add(u)
    db.commit()
    db.refresh(u)

    # Nếu là sinh viên -> tạo hồ sơ kèm theo (nếu được truyền)
    if u.role == "student":
        p = StudentProfile(
            user_id=u.id,
            # các cột thuộc student_profiles
            address=getattr(user_in, "address", None),
            major=getattr(user_in, "major", None),
            gender=getattr(user_in, "gender", None),
            dob=getattr(user_in, "dob", None),
            hometown=getattr(user_in, "hometown", None),
            guardian_name=getattr(user_in, "guardian_name", None),
            guardian_phone=getattr(user_in, "guardian_phone", None),
            building=getattr(user_in, "building", None),
            bed=getattr(user_in, "bed", None),  # 👈 có thể set giường khi tạo
            checkin_date=getattr(user_in, "checkin_date", None),
        )
        db.add(p)
        db.commit()

    db.refresh(u)
    return u


# =========================================================
# ✏️ Admin cập nhật tài khoản
# =========================================================
def update_user_admin(db: Session, user_id: int, data: UserUpdateAdmin) -> Optional[User]:
    """
    Admin được sửa mọi thứ:
      - Bảng users: username (nếu không trùng), full_name, role, password,
                    email, phone, faculty, room
      - Bảng student_profiles: address, major, gender, dob, hometown,
                    guardian_name, guardian_phone, building, bed, checkin_date
    """
    u = get_user_by_id(db, user_id)
    if not u:
        return None

    # Đổi username (mã SV) nếu được truyền và chưa trùng
    if getattr(data, "username", None):
        new_username = data.username.strip()
        if new_username != u.username and get_user_by_username(db, new_username):
            raise ValueError("Username already exists")
        u.username = new_username

    if getattr(data, "full_name", None):
        u.full_name = data.full_name

    if getattr(data, "role", None):
        u.role = data.role

    if getattr(data, "password", None):
        u.hashed_password = hash_password(data.password)

    # Các cột thuộc bảng users
    for field in ["email", "phone", "faculty", "room"]:
        if hasattr(data, field):
            val = getattr(data, field)
            if val is not None:
                setattr(u, field, val)

    # Đảm bảo có profile
    if not u.profile:
        p = StudentProfile(user_id=u.id)
        db.add(p)
        db.flush()
    else:
        p = u.profile

    # Cập nhật các field trong StudentProfile
    profile_fields = [
        "address", "major", "gender", "dob", "hometown",
        "guardian_name", "guardian_phone", "building", "bed", "checkin_date",
    ]
    for field in profile_fields:
        if hasattr(data, field):
            val = getattr(data, field)
            if val is not None:
                setattr(p, field, val)

    db.commit()
    db.refresh(u)
    return u


# =========================================================
# ❌ Xóa tài khoản
# =========================================================
def delete_user(db: Session, user_id: int) -> bool:
    u = get_user_by_id(db, user_id)
    if not u:
        return False
    db.delete(u)
    db.commit()
    return True


# =========================================================
# 👤 Sinh viên tự cập nhật hồ sơ
# =========================================================
def update_profile_self(db: Session, user_id: int, data: ProfileUpdate) -> Optional[User]:
    """
    Sinh viên chỉ được sửa: full_name, password (bảng users),
    email, phone (bảng users) và address (bảng student_profiles).
    """
    u = get_user_by_id(db, user_id)
    if not u:
        return None

    # Cập nhật full_name
    if getattr(data, "full_name", None):
        u.full_name = data.full_name

    # Cập nhật mật khẩu
    if getattr(data, "password", None):
        u.hashed_password = hash_password(data.password)

    # email/phone là cột ở users
    for field in ["email", "phone"]:
        if hasattr(data, field):
            val = getattr(data, field)
            if val is not None:
                setattr(u, field, val)

    # Đảm bảo có profile
    if not u.profile:
        p = StudentProfile(user_id=u.id)
        db.add(p)
        db.flush()
    else:
        p = u.profile

    # address nằm ở profile
    if hasattr(data, "address") and data.address is not None:
        p.address = data.address

    db.commit()
    db.refresh(u)
    return u


# =========================================================
# 🔐 Xác thực (login)
# =========================================================
def authenticate(db: Session, username: str, password: str) -> Optional[User]:
    u = get_user_by_username(db, username)
    if not u:
        return None
    if not verify_password(password, u.hashed_password):
        return None
    return u
