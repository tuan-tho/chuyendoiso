# Export tất cả routers để main.py import gọn
from .auth_router import router as auth_router
from .reports_router import router as reports_router
from .checkins_router import router as checkins_router
from .profile import router as router  # file này tự có prefix="/profile"
from .ai_router import router as ai_router
from .files_router import router as files_router  # ✅ thêm dòng này
