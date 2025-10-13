# backend/ai/text_preprocess_kssv.py
import re
import unicodedata

# ==============================
# Tiền xử lý văn bản KSSV
# ==============================

def normalize_text(text: str) -> str:
    """
    Chuẩn hoá văn bản phản ánh:
    - Chuyển về chữ thường
    - Bỏ dấu câu / ký tự đặc biệt
    - Chuẩn hoá cách viết phòng, tầng, KSSV
    - Loại bỏ từ thừa (vd: "phản ánh", "báo cáo")
    - Chuẩn hoá khoảng trắng
    """

    if not isinstance(text, str):
        return ""

    # --- B1: chuẩn hoá unicode ---
    text = unicodedata.normalize("NFC", text)

    # --- B2: chuyển về chữ thường ---
    text = text.lower()

    # --- B3: thay thế các biến thể thường gặp ---
    replacements = {
        "ký túc": "kssv",
        "ktx": "kssv",
        "phòng ": "phong ",
        "tầng ": "tang ",
        "khu ": "khu ",
        "khu vực ": "khu ",
        "wifi": "wi-fi",
        "mạng ": "internet ",
        "mất mạng": "mất internet",
        "đèn điện": "điện",
        "bị hỏng": "hỏng",
        "rò nước": "rò rỉ nước",
        "vòi bị rỉ": "rò rỉ nước",
        "rò rỉ": "rò rỉ nước",
        "thiết bị điện": "thiết bị",
        "wc": "vệ sinh",
        "toilet": "vệ sinh",
        "nhà tắm": "vệ sinh",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    # --- B4: xoá ký tự không cần thiết ---
    text = re.sub(r"[^\w\s]", " ", text)       # chỉ giữ lại chữ/số/khoảng trắng
    text = re.sub(r"\s+", " ", text).strip()   # bỏ khoảng trắng thừa

    # --- B5: bỏ các từ vô nghĩa thường gặp ---
    stopwords = [
        "phản ánh", "báo cáo", "bị", "tình trạng", "trong", "ở", "tại",
        "đã", "vẫn", "rất", "có", "này", "kia", "đó", "rồi", "luôn", "luôn luôn",
        "đang", "vừa", "cũng", "chưa", "nữa"
    ]
    pattern = r"\b(" + "|".join(stopwords) + r")\b"
    text = re.sub(pattern, "", text).strip()

    # --- B6: chuẩn hoá khoảng trắng lần cuối ---
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ==============================
# Test nhanh khi chạy độc lập
# ==============================
if __name__ == "__main__":
    samples = [
        "Phòng KSSV-214 mất điện từ tối qua tầng 2 khu B",
        "Vòi nước tầng 5 bị rò rỉ",
        "Wi-Fi tầng 3 không kết nối được",
        "Nhà vệ sinh khu C bị tắc nước",
    ]

    for s in samples:
        print(f"\n🧩 Gốc: {s}")
        print(f"👉 Chuẩn hoá: {normalize_text(s)}")
