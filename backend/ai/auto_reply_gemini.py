from __future__ import annotations
import os
from dotenv import load_dotenv # type: ignore
import google.generativeai as genai  # type: ignore

# ==============================
# 🔧 1) Load biến môi trường
# ==============================
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("❌ GEMINI_API_KEY is missing in .env")

# ==============================
# 🤖 2) Cấu hình Gemini API
# ==============================
genai.configure(api_key=API_KEY)

# ✅ Dùng model ổn định đã test OK
MODEL_NAME = "models/gemini-2.5-flash-preview-05-20"

try:
    MODEL = genai.GenerativeModel(MODEL_NAME)
    print(f"[Gemini] ✅ Model loaded successfully: {MODEL_NAME}")
except Exception as e:
    print(f"[Gemini] ⚠️ Failed to load model {MODEL_NAME}: {e}")
    MODEL = None


# ==============================
# 💬 3) Hàm sinh phản hồi tự động
# ==============================
def generate_auto_reply(description: str, label: str, priority: str) -> str:
    """
    Sinh phản hồi ngắn gọn, lịch sự cho phản ánh ký túc xá.
    - description: nội dung mô tả sự cố
    - label: loại sự cố (điện / nước / internet / ...)
    - priority: mức độ ưu tiên (normal / high / urgent)
    """
    prompt = f"""
    Bạn là nhân viên quản lý ký túc xá Đại Nam.
    Viết phản hồi ngắn gọn (1–2 câu) cho phản ánh dưới đây:

    Nội dung: {description}
    Loại sự cố: {label}
    Mức độ ưu tiên: {priority}

    Yêu cầu:
    - Giọng điệu thân thiện, lịch sự, có trách nhiệm.
    - Không dùng emoji hoặc ký tên.
    """

    if MODEL is None:
        return "Hệ thống đã ghi nhận sự cố, bộ phận kỹ thuật sẽ xử lý trong thời gian sớm nhất."

    try:
        resp = MODEL.generate_content(prompt)
        if not resp or not getattr(resp, "text", "").strip():
            raise ValueError("Empty response")
        return resp.text.strip()
    except Exception as e:
        print("[Gemini Reply Error]", e)
        return "Hệ thống đã ghi nhận sự cố, bộ phận kỹ thuật sẽ xử lý trong thời gian sớm nhất."


# ==============================
# 🧪 4) Test nhanh
# ==============================
if __name__ == "__main__":
    print(f"GEMINI_API_KEY: {'OK' if API_KEY else 'MISSING'}")
    print(f"Model in use: {MODEL_NAME}")
    print("---- Test output ----")
    reply = generate_auto_reply(
        "Phòng 302 bị rò rỉ nước mạnh ở vòi lavabo", "nước", "urgent"
    )
    print("Phản hồi Gemini:", reply)
