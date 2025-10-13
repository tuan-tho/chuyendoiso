# app/routers/checkins_router.py
from fastapi import APIRouter, Depends, HTTPException  # type: ignore
from sqlalchemy.orm import Session  # type: ignore
from typing import List

from ..database import get_db
from ..schemas import CheckinCreate, CheckinOut, CheckinUpdate
from ..models import User
from ..deps import get_current_user, require_role
from ..crud import checkins as crud_ck

router = APIRouter(tags=["Checkins"])  # ❌ bỏ prefix ở đây

# Student: create
@router.post("", response_model=CheckinOut, status_code=201)
def create_checkin(
    data: CheckinCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.type not in ("checkin", "checkout"):
        raise HTTPException(400, "type must be 'checkin' or 'checkout'")
    return crud_ck.create_checkin(db, student_id=user.id, data=data)

# Student: mine
@router.get("/mine", response_model=List[CheckinOut])
def my_checkins(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud_ck.list_checkins_by_user(db, user.id)

# Admin: list all
@router.get("", response_model=List[CheckinOut])
def list_checkins(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    return crud_ck.list_checkins(db)

# Admin: update
@router.patch("/{ck_id}", response_model=CheckinOut)
def update_checkin(
    ck_id: int,
    data: CheckinUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    ck = crud_ck.update_checkin(db, ck_id, data)
    if not ck:
        raise HTTPException(404, "Checkin request not found")
    return ck
