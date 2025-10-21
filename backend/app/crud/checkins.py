from sqlalchemy.orm import Session, selectinload  # type: ignore
from typing import List, Optional

from ..models import CheckinRequest
from ..schemas import CheckinCreate, CheckinUpdate


def create_checkin(db: Session, student_id: int, data: CheckinCreate) -> CheckinRequest:
    """
    Tạo yêu cầu check-in/out (có thể kèm image_url).
    """
    ck = CheckinRequest(
        type=(data.type or "").strip().lower(),  # 'checkin' | 'checkout'
        date=data.date,                           # YYYY-MM-DD
        time=data.time,                           # HH:MM | None
        note=data.note,
        image_url=getattr(data, "image_url", None),
        student_id=student_id,
    )
    db.add(ck)
    db.commit()

    # Trả về bản ghi kèm thông tin sinh viên
    return (
        db.query(CheckinRequest)
        .options(selectinload(CheckinRequest.student))
        .get(ck.id)
    )


def list_checkins(db: Session, skip: int = 0, limit: int = 200) -> List[CheckinRequest]:
    """
    Lấy toàn bộ yêu cầu check-in/out (cho Admin), có kèm thông tin sinh viên.
    """
    return (
        db.query(CheckinRequest)
        .options(selectinload(CheckinRequest.student))  # Load luôn dữ liệu user liên kết
        .order_by(CheckinRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def list_checkins_by_user(db: Session, user_id: int) -> List[CheckinRequest]:
    """
    Lấy danh sách yêu cầu check-in/out của sinh viên hiện tại.
    """
    return (
        db.query(CheckinRequest)
        .options(selectinload(CheckinRequest.student))
        .filter(CheckinRequest.student_id == user_id)
        .order_by(CheckinRequest.created_at.desc())
        .all()
    )


def get_checkin(db: Session, ck_id: int) -> Optional[CheckinRequest]:
    """
    Lấy chi tiết 1 yêu cầu (kèm thông tin sinh viên).
    """
    return (
        db.query(CheckinRequest)
        .options(selectinload(CheckinRequest.student))
        .filter(CheckinRequest.id == ck_id)
        .first()
    )


def update_checkin(db: Session, ck_id: int, upd: CheckinUpdate) -> Optional[CheckinRequest]:
    """
    Admin có thể đổi status/admin_reply; cho phép cập nhật lại image_url nếu cần.
    """
    ck = get_checkin(db, ck_id)
    if not ck:
        return None

    if upd.status is not None:
        ck.status = upd.status
    if upd.admin_reply is not None:
        ck.admin_reply = upd.admin_reply
    if hasattr(upd, "image_url") and upd.image_url is not None:
        ck.image_url = upd.image_url

    db.commit()

    # Trả về bản ghi sau cập nhật, có kèm student
    return get_checkin(db, ck_id)
