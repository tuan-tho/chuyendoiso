from sqlalchemy.orm import Session # type: ignore
from typing import List, Optional
from ..models import CheckinRequest
from ..schemas import CheckinCreate, CheckinUpdate

def create_checkin(db: Session, student_id: int, data: CheckinCreate) -> CheckinRequest:
    ck = CheckinRequest(
        type=data.type,
        date=data.date,
        time=data.time,
        note=data.note,
        student_id=student_id,
    )
    db.add(ck)
    db.commit()
    db.refresh(ck)
    return ck

def list_checkins(db: Session, skip: int = 0, limit: int = 200) -> List[CheckinRequest]:
    return db.query(CheckinRequest).order_by(CheckinRequest.created_at.desc()).offset(skip).limit(limit).all()

def list_checkins_by_user(db: Session, user_id: int) -> List[CheckinRequest]:
    return db.query(CheckinRequest).filter(CheckinRequest.student_id == user_id).order_by(CheckinRequest.created_at.desc()).all()

def get_checkin(db: Session, ck_id: int) -> Optional[CheckinRequest]:
    return db.query(CheckinRequest).filter(CheckinRequest.id == ck_id).first()

def update_checkin(db: Session, ck_id: int, upd: CheckinUpdate) -> Optional[CheckinRequest]:
    ck = get_checkin(db, ck_id)
    if not ck:
        return None
    if upd.status is not None:
        ck.status = upd.status
    if upd.admin_reply is not None:
        ck.admin_reply = upd.admin_reply
    db.commit()
    db.refresh(ck)
    return ck
