# app/schemas.py
from pydantic import BaseModel, ConfigDict # type: ignore
from typing import Optional
from datetime import datetime, date

# -------- Users --------
class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "student"
    model_config = ConfigDict(extra="ignore")


class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    role: str
    model_config = ConfigDict(from_attributes=True)


# Dùng cho lồng trong ReportOut (đủ để hiển thị người gửi)
class UserShort(BaseModel):
    id: int
    username: str
    model_config = ConfigDict(from_attributes=True)


# -------- Auth --------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# -------- Reports --------
class ReportCreate(BaseModel):
    """
    Dùng cho tạo báo cáo từ phía SV.
    - 'title' là bắt buộc.
    - description/category/priority optional -> backend có thể tự suy luận.
    - image_url: link ảnh đã upload (nếu có).
    - Các trường AI là optional (backend sẽ tự gán).
    - building/room thêm để lưu vị trí nếu người dùng nhập.
    """
    title: str
    description: Optional[str] = None
    category: Optional[str] = None            # backend có thể tự map từ AI
    priority: Optional[str] = None            # normal/high/urgent (nếu có)
    building: Optional[str] = None            # ✅ khớp models.Report
    room: Optional[str] = None                # ✅ khớp models.Report
    image_url: Optional[str] = None           # ✅ khớp models.Report

    # ---- Enrichment từ AI (server sẽ tự gán) ----
    ai_label: Optional[str] = None            # điện | nước | internet | thiết bị | vệ sinh | khác
    ai_confidence: Optional[float] = None     # 0..1
    ai_room: Optional[str] = None             # "214", "B203", ...
    ai_floor: Optional[int] = None            # 1..15
    ai_time_text: Optional[str] = None        # "tối qua", "2 ngày trước", ...

    model_config = ConfigDict(extra="ignore")


class ReportUpdate(BaseModel):
    """
    Dùng cho admin cập nhật trạng thái/ghi chú.
    Có thể mở rộng cho phép cập nhật priority, image_url nếu cần.
    """
    status: Optional[str] = None              # open | in_progress | resolved
    admin_reply: Optional[str] = None
    priority: Optional[str] = None            # (tuỳ chọn) cho phép admin chỉnh mức độ
    building: Optional[str] = None            # (tuỳ chọn) nếu muốn sửa
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

    # ✅ Bổ sung cho khớp models.Report
    building: Optional[str]
    room: Optional[str]
    image_url: Optional[str]

    created_at: datetime
    updated_at: datetime
    reporter_id: int

    # 👇 Trả kèm user rút gọn để FE hiển thị người gửi
    reporter: Optional[UserShort] = None

    # ---- Trường AI trả về cho client xem ----
    ai_label: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_room: Optional[str] = None
    ai_floor: Optional[int] = None
    ai_time_text: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# -------- Checkins --------
class CheckinCreate(BaseModel):
    type: str                                 # checkin | checkout
    date: str                                 # YYYY-MM-DD
    time: Optional[str] = None                # HH:MM
    note: Optional[str] = None
    model_config = ConfigDict(extra="ignore")


class CheckinUpdate(BaseModel):
    status: Optional[str] = None              # pending | approved | rejected
    admin_reply: Optional[str] = None
    model_config = ConfigDict(extra="ignore")


class CheckinOut(BaseModel):
    id: int
    type: str
    date: str
    time: Optional[str]
    note: Optional[str]
    status: str
    admin_reply: Optional[str]
    created_at: datetime
    updated_at: datetime
    student_id: int
    model_config = ConfigDict(from_attributes=True)


# -------- Student Profile --------
class StudentProfileBase(BaseModel):
    student_code: Optional[str] = None
    faculty: Optional[str] = None
    major: Optional[str] = None
    address: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    hometown: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    building: Optional[str] = None
    room: Optional[str] = None
    bed: Optional[str] = None
    checkin_date: Optional[date] = None
    model_config = ConfigDict(extra="ignore")


class StudentProfileUpdate(StudentProfileBase):
    # Cho phép cập nhật full_name (nằm ở bảng users) nếu backend của bạn handle:
    full_name: Optional[str] = None
    model_config = ConfigDict(extra="ignore")


class StudentProfileOut(BaseModel):
    id: int
    user_id: int
    full_name: Optional[str]   # nếu backend gộp từ bảng users, để None nếu không map
    student_code: Optional[str] = None
    faculty: Optional[str] = None
    major: Optional[str] = None
    address: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    hometown: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    building: Optional[str] = None
    room: Optional[str] = None
    bed: Optional[str] = None
    checkin_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


# -------- Password Change --------
class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str
    model_config = ConfigDict(extra="ignore")


class ChangePasswordOut(BaseModel):
    message: str
