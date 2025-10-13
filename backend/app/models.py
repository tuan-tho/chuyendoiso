# app/models.py
from sqlalchemy import (
    Column, Integer, DateTime, ForeignKey, Date, Float
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import Unicode, UnicodeText

from .database import Base


# ==============================
# 🧍 BẢNG NGƯỜI DÙNG (USERS)
# ==============================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(Unicode(50), unique=True, index=True, nullable=False)
    full_name = Column(Unicode(100), nullable=True)
    hashed_password = Column(Unicode(255), nullable=False)
    role = Column(Unicode(20), default="student")  # student | admin
    created_at = Column(DateTime, server_default=func.now())

    # Quan hệ
    reports = relationship("Report", back_populates="reporter", cascade="all, delete-orphan")
    checkins = relationship("CheckinRequest", back_populates="student", cascade="all, delete-orphan")
    profile = relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


# ==============================
# 🧾 BẢNG PHẢN ÁNH SỰ CỐ (REPORTS)
# ==============================
class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Unicode(150), nullable=False)
    description = Column(UnicodeText, nullable=True)
    category = Column(Unicode(50), nullable=True)
    priority = Column(Unicode(20), default="normal")
    status = Column(Unicode(20), default="open")  # open | in_progress | resolved
    admin_reply = Column(UnicodeText, nullable=True)

    # ✅ Thông tin thêm từ người gửi
    building = Column(Unicode(20), nullable=True)   # tòa nhà (nếu có)
    room = Column(Unicode(20), nullable=True)       # phòng (nếu có)
    image_url = Column(UnicodeText, nullable=True)  # link ảnh duy nhất được upload

    # ====== AI enrichment (tự động gán khi tạo phản ánh) ======
    ai_label = Column(Unicode(20), nullable=True)        # ví dụ: "điện", "nước"
    ai_confidence = Column(Float, nullable=True)         # độ tin cậy
    ai_room = Column(Unicode(16), nullable=True)
    ai_floor = Column(Integer, nullable=True)
    ai_time_text = Column(Unicode(64), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Quan hệ với bảng User
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reporter = relationship("User", back_populates="reports")


# ==============================
# 🧾 BẢNG CHECKIN / CHECKOUT
# ==============================
class CheckinRequest(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Unicode(20), nullable=False)  # checkin | checkout
    date = Column(Unicode(10), nullable=False)  # YYYY-MM-DD
    time = Column(Unicode(5), nullable=True)    # HH:MM
    note = Column(UnicodeText, nullable=True)
    status = Column(Unicode(20), default="pending")  # pending | approved | rejected
    admin_reply = Column(UnicodeText, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    student = relationship("User", back_populates="checkins")


# ==============================
# 🧍‍♂️ BẢNG THÔNG TIN SINH VIÊN
# ==============================
class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # ===== Thông tin sinh viên =====
    student_code   = Column(Unicode(50), nullable=True)
    faculty        = Column(Unicode(100), nullable=True)
    major          = Column(Unicode(150), nullable=True)
    address        = Column(Unicode(255), nullable=True)
    gender         = Column(Unicode(10), nullable=True)
    dob            = Column(Date, nullable=True)
    phone          = Column(Unicode(20), nullable=True)
    email          = Column(Unicode(100), nullable=True)
    hometown       = Column(Unicode(255), nullable=True)
    guardian_name  = Column(Unicode(100), nullable=True)
    guardian_phone = Column(Unicode(20), nullable=True)

    # ===== Cư trú =====
    building       = Column(Unicode(20), nullable=True)
    room           = Column(Unicode(20), nullable=True)
    bed            = Column(Unicode(20), nullable=True)
    checkin_date   = Column(Date, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")
