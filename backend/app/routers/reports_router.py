# app/routers/reports_router.py
from __future__ import annotations

import os
from uuid import uuid4
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from ..database import get_db
from ..schemas import ReportCreate, ReportOut, ReportUpdate
from ..models import User
from ..deps import get_current_user, require_role
from ..crud import reports as crud_reports

# Router chính cho Reports
router = APIRouter(tags=["Reports"])

# --------------------------
# 📁 Upload ảnh minh hoạ
# --------------------------
# Thư mục lưu ảnh: <app>/uploads  (được serve tĩnh qua /uploads trong main.py)
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),   # yêu cầu đăng nhập khi upload
):
    """
    Upload ảnh minh hoạ cho báo cáo.
    Trả về JSON: {"url": "/uploads/<filename>"} để front-end gắn vào `image_url`.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ JPG/PNG/WebP/GIF")

    fname = f"{uuid4().hex}{ext}"
    fpath = os.path.join(UPLOAD_DIR, fname)

    # Ghi file
    content = await file.read()
    with open(fpath, "wb") as f:
        f.write(content)

    return {"url": f"/uploads/{fname}"}

# ==========================
# 🟢 Student + Admin: Tạo phản ánh
# ==========================
@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    data: ReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Tạo phản ánh mới. AI/priority/image_url đã được xử lý ở CRUD hoặc từ client.
    """
    return crud_reports.create_report(db, reporter_id=user.id, data=data)

# ==========================
# 🟢 Student: Xem phản ánh của mình
# ==========================
@router.get("/mine", response_model=List[ReportOut])
def my_reports(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud_reports.list_reports_by_user(db, user.id)

# ==========================
# 🔵 Admin: Xem tất cả phản ánh
# ==========================
@router.get("", response_model=List[ReportOut])
def list_reports(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    return crud_reports.list_reports(db)

# ==========================
# 🔵 Admin: Xem chi tiết phản ánh
# ==========================
@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    rpt = crud_reports.get_report(db, report_id)
    if not rpt:
        raise HTTPException(status_code=404, detail="Report not found")
    return rpt

# ==========================
# 🔵 Admin: Cập nhật trạng thái / phản hồi
# ==========================
@router.patch("/{report_id}", response_model=ReportOut)
def update_report(
    report_id: int,
    data: ReportUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    rpt = crud_reports.update_report(db, report_id, data)
    if not rpt:
        raise HTTPException(status_code=404, detail="Report not found")
    return rpt

# ==========================
# 🔵 Admin: Xoá phản ánh
# ==========================
@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    ok = crud_reports.delete_report(db, report_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Report not found")
    return None
