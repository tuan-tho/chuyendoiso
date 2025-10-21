# app/schemas.py
from pydantic import BaseModel, ConfigDict, EmailStr  # type: ignore
from typing import Optional
from datetime import datetime, date

# =========================================================
# USERS
# =========================================================

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "student"
    model_config = ConfigDict(extra="ignore")


class AdminUserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "student"

    # users table
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    faculty: Optional[str] = None
    room: Optional[str] = None

    # student_profiles table
    address: Optional[str] = None
    bed: Optional[str] = None

    # compatibility
    student_code: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class UserUpdateAdmin(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

    # users table
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    faculty: Optional[str] = None
    room: Optional[str] = None

    # profile table
    address: Optional[str] = None
    bed: Optional[str] = None

    # compatibility
    student_code: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


# Sinh viên tự cập nhật qua /users/me (nếu dùng)
class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    password: Optional[str] = None
    model_config = ConfigDict(extra="ignore")


class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    role: str

    email: Optional[str] = None
    phone: Optional[str] = None
    faculty: Optional[str] = None
    room: Optional[str] = None

    address: Optional[str] = None
    student_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserShort(BaseModel):
    id: int
    username: str
    model_config = ConfigDict(from_attributes=True)


# Hàng hiển thị cho bảng Admin (JOIN users + student_profiles)
class AdminUserRow(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: str

    faculty: Optional[str] = None
    room: Optional[str] = None

    bed: Optional[str] = None
    address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# AUTH
# =========================================================
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# =========================================================
# REPORTS
# =========================================================
class ReportCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    building: Optional[str] = None
    room: Optional[str] = None
    image_url: Optional[str] = None

    # AI enrichment (server tự gán nếu có)
    ai_label: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_room: Optional[str] = None
    ai_floor: Optional[int] = None
    ai_time_text: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class ReportUpdate(BaseModel):
    status: Optional[str] = None
    admin_reply: Optional[str] = None
    priority: Optional[str] = None
    building: Optional[str] = None
    room: Optional[str] = None
    image_url: Optional[str] = None
    model_config = ConfigDict(extra="ignore")


class ReportOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    category: Optional[str]
    priority: Optional[str]
    status: str
    admin_reply: Optional[str]
    admin_reply_source: Optional[str] = None
    building: Optional[str]
    room: Optional[str]
    image_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    reporter_id: int
    reporter: Optional[UserShort] = None

    ai_label: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_room: Optional[str] = None
    ai_floor: Optional[int] = None
    ai_time_text: Optional[str] = None
    ai_meta: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# CHECKINS (✅ đầy đủ, có image_url và thông tin sinh viên)
# =========================================================
class UserLite(BaseModel):
    """Thông tin rút gọn của sinh viên để nhúng trong CheckinOut"""
    id: int
    username: str
    full_name: Optional[str] = None
    student_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CheckinCreate(BaseModel):
    type: str                  # checkin | checkout
    date: str                  # YYYY-MM-DD
    time: Optional[str] = None # HH:MM
    note: Optional[str] = None
    image_url: Optional[str] = None
    model_config = ConfigDict(extra="ignore")


class CheckinUpdate(BaseModel):
    status: Optional[str] = None          # pending | approved | rejected
    admin_reply: Optional[str] = None
    image_url: Optional[str] = None
    model_config = ConfigDict(extra="ignore")


class CheckinOut(BaseModel):
    id: int
    type: str
    date: str
    time: Optional[str]
    note: Optional[str]
    status: str
    admin_reply: Optional[str]
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    student_id: int

    # ✅ Thêm thông tin sinh viên để frontend hiển thị username / mã SV
    student: Optional[UserLite] = None

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# STUDENT PROFILE
# =========================================================
class StudentProfileBase(BaseModel):
    major: Optional[str] = None
    address: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    hometown: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None

    building: Optional[str] = None
    bed: Optional[str] = None
    checkin_date: Optional[date] = None

    student_code: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


# 👉 SV chỉ được sửa các trường cho phép
class StudentProfileUpdate(BaseModel):
    # cập nhật sang bảng users
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    # cập nhật sang student_profiles
    address: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class StudentProfileOut(BaseModel):
    id: int
    user_id: int
    full_name: Optional[str] = None

    major: Optional[str] = None
    address: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    hometown: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None

    building: Optional[str] = None
    bed: Optional[str] = None
    checkin_date: Optional[date] = None

    student_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# PASSWORD
# =========================================================
class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str
    model_config = ConfigDict(extra="ignore")


class ChangePasswordOut(BaseModel):
    message: str
