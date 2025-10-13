# app/routers/files_router.py
from __future__ import annotations
import os
from uuid import uuid4
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends  # type: ignore
from fastapi.responses import JSONResponse                 # type: ignore

from ..deps import get_current_user
from ..models import User

router = APIRouter(prefix="/files", tags=["Files"])

# Thư mục uploads: <project>/app/uploads  (được mount ở main.py → /uploads)
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),   # bắt buộc đã đăng nhập
):
    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return JSONResponse({"detail": "Chỉ hỗ trợ JPG/PNG/WebP/GIF"}, status_code=400)

    fname = f"{uuid4().hex}{ext}"
    fpath = UPLOAD_DIR / fname

    data = await file.read()
    fpath.write_bytes(data)

    # Trả về URL tĩnh (đã mount ở /uploads)
    return {"url": f"/uploads/{fname}"}
