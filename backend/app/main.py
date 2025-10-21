# app/main.py
from __future__ import annotations

import os
from pathlib import Path
from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.staticfiles import StaticFiles  # type: ignore

from .config import settings
from .database import Base, engine
from . import models  # noqa: F401  # đảm bảo load models để tạo bảng

# 1) Khởi tạo app
app = FastAPI(
    title=settings.PROJECT_NAME or "KSSV Backend",
    docs_url="/docs",
    redoc_url="/redoc",
    version="1.0.0",
)

# 2) CORS
allow_origins = settings.CORS_ORIGINS or [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3) Static uploads
# Gốc lưu upload: app/uploads
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
(UPLOAD_DIR / "reports").mkdir(parents=True, exist_ok=True)
(UPLOAD_DIR / "checkins").mkdir(parents=True, exist_ok=True)

# a) /uploads -> duyệt toàn bộ cây uploads (giữ lại cho tương thích)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# b) /static/reports và /static/checkins -> đường dẫn ngắn gọn cho FE
app.mount(
    "/static/reports",
    StaticFiles(directory=str(UPLOAD_DIR / "reports")),
    name="reports-static",
)
app.mount(
    "/static/checkins",
    StaticFiles(directory=str(UPLOAD_DIR / "checkins")),
    name="checkins-static",
)

# 4) Import routers
from .routers.auth_router import router as auth_router          # noqa: E402
from .routers.reports_router import router as reports_router    # noqa: E402
from .routers.checkins_router import router as checkins_router  # noqa: E402
from .routers.profile import router as profile_router           # noqa: E402
from .routers.ai_router import router as ai_router              # noqa: E402
from .routers.files_router import router as files_router        # noqa: E402
from .routers.users_router import router as users_router        # noqa: E402

# 5) Gắn routers
app.include_router(auth_router,     prefix="/auth",     tags=["Auth"])
app.include_router(reports_router,  prefix="/reports",  tags=["Reports"])
app.include_router(checkins_router, prefix="/checkins", tags=["Checkins"])
app.include_router(profile_router)  # file profile đã tự đặt prefix="/profile"
app.include_router(ai_router,       prefix="/ai",       tags=["AI"])
app.include_router(files_router)    # -> /files/upload
app.include_router(users_router)    # -> /users

# 6) Tạo bảng khi khởi động
@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)

# 7) Health & root
@app.get("/")
def root():
    return {"message": "✅ KSSV backend is connected and running!"}

@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True}
