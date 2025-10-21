# app/models.py
from sqlalchemy import (  # type: ignore
    Column, Integer, DateTime, ForeignKey, Date, Float,
    UniqueConstraint, CheckConstraint, Index
)  # type: ignore
from sqlalchemy.orm import relationship  # type: ignore
from sqlalchemy.sql import func  # type: ignore
from sqlalchemy.types import Unicode, UnicodeText  # type: ignore

from .database import Base


# ==============================
# 🧍 USERS
# ==============================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Mã SV dùng để đăng nhập
    username = Column(Unicode(50), unique=True, index=True, nullable=False)

    full_name = Column(Unicode(100), nullable=True)
    hashed_password = Column(Unicode(255), nullable=False)
    role = Column(Unicode(20), nullable=False, default="student")  # student | admin

    # Thông tin gốc nằm ở users
    email = Column(Unicode(100), nullable=True, index=True)
    phone = Column(Unicode(20), nullable=True)
    faculty = Column(Unicode(100), nullable=True, index=True)
    room = Column(Unicode(20), nullable=True, index=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Quan hệ
    reports = relationship(
        "Report", back_populates="reporter",
        cascade="all, delete-orphan", passive_deletes=True
    )
    checkins = relationship(
        "CheckinRequest", back_populates="student",
        cascade="all, delete-orphan", passive_deletes=True
    )
    profile = relationship(
        "StudentProfile", back_populates="user",
        uselist=False, cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index("ix_users_faculty_room", "faculty", "room"),
    )


# ==============================
# 🧾 REPORTS
# ==============================
class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Unicode(150), nullable=False)
    description = Column(UnicodeText, nullable=True)
    category = Column(Unicode(50), nullable=True)
    priority = Column(Unicode(20), default="normal")  # normal | high | urgent ...
    status = Column(Unicode(20), default="open")      # open | in_progress | resolved
    admin_reply = Column(UnicodeText, nullable=True)
    admin_reply_source = Column(Unicode(20), nullable=True)

    # Thông tin bổ sung
    building = Column(Unicode(20), nullable=True)
    room = Column(Unicode(20), nullable=True)
    image_url = Column(UnicodeText, nullable=True)

    # AI enrichment
    ai_label = Column(Unicode(20), nullable=True)
    ai_confidence = Column(Float, nullable=True)
    ai_room = Column(Unicode(16), nullable=True)
    ai_floor = Column(Integer, nullable=True)
    ai_time_text = Column(Unicode(64), nullable=True)
    ai_meta = Column(UnicodeText, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reporter = relationship("User", back_populates="reports")

    __table_args__ = (
        CheckConstraint("status in ('open','in_progress','resolved')", name="ck_reports_status"),
        CheckConstraint("priority in ('normal','high','urgent')", name="ck_reports_priority"),
    )


# ==============================
# 🧾 CHECKINS
# ==============================
class CheckinRequest(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Unicode(20), nullable=False)   # checkin | checkout
    date = Column(Unicode(10), nullable=False)   # YYYY-MM-DD
    time = Column(Unicode(5), nullable=True)     # HH:MM
    note = Column(UnicodeText, nullable=True)
    status = Column(Unicode(20), default="pending")  # pending | approved | rejected
    admin_reply = Column(UnicodeText, nullable=True)

    # 🔹 Ảnh minh hoạ kèm yêu cầu
    image_url = Column(UnicodeText, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    student = relationship("User", back_populates="checkins")

    __table_args__ = (
        CheckConstraint("type in ('checkin','checkout')", name="ck_checkins_type"),
        CheckConstraint("status in ('pending','approved','rejected')", name="ck_checkins_status"),
    )


# ==============================
# 🧍‍♂️ STUDENT PROFILES
# ==============================
class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Không lặp lại email/phone/faculty/room — đã nằm ở bảng users
    major          = Column(Unicode(150), nullable=True)
    address        = Column(Unicode(255), nullable=True)
    gender         = Column(Unicode(10), nullable=True)
    dob            = Column(Date, nullable=True)
    hometown       = Column(Unicode(255), nullable=True)
    guardian_name  = Column(Unicode(100), nullable=True)
    guardian_phone = Column(Unicode(20), nullable=True)

    # Cư trú chi tiết
    building       = Column(Unicode(20), nullable=True)
    bed            = Column(Unicode(20), nullable=True)
    checkin_date   = Column(Date, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Quan hệ
    user = relationship("User", back_populates="profile")

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_student_profiles_user_id"),
        Index("ix_profiles_building_room_bed", "building", "bed"),
    )
