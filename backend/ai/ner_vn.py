# backend/ai/ner_vn.py
from __future__ import annotations

import re
from typing import Dict, Optional

# ======= Số đếm tiếng Việt cơ bản -> số =======
VI_NUM = {
    "một": 1, "hai": 2, "ba": 3, "bốn": 4, "năm": 5,
    "sáu": 6, "bảy": 7, "tám": 8, "chín": 9, "mười": 10
}

def _word_to_num(w: str) -> Optional[int]:
    w = w.lower().strip()
    return VI_NUM.get(w)

# ======= Helpers =======
def _clean_room_token(s: str) -> str:
    """Loại bỏ khoảng trắng / '-' trong chuỗi phòng, chuẩn hoá chữ hoa."""
    return s.replace(" ", "").replace("-", "").upper()

def _floor_from_digits(digits: str) -> Optional[str]:
    """
    Suy tầng từ CHUỖI SỐ phòng:
      - 402  -> 4
      - 1205 -> 12
      - 333  -> 3
      - 1001 -> 10
    Chỉ nhận 1..15.
    """
    if not digits:
        return None
    try:
        if len(digits) >= 4:
            f = int(digits[:2])
        else:
            f = int(digits[0])
        return str(f) if 1 <= f <= 15 else None
    except ValueError:
        return None

def _infer_floor_from_room(room: str) -> Optional[str]:
    """
    Suy tầng an toàn từ chuỗi phòng có thể kèm toà và dấu '-':
      - 'B3-402'  -> lấy '402' rồi suy -> 4
      - 'P.1205'  -> 12
      - '203'     -> 2
      - 'KSSV214' -> 2
    """
    s = str(room).strip()
    # Ưu tiên phần sau dấu '-'
    if "-" in s:
        tail = s.split("-")[-1]
        digits = "".join(ch for ch in tail if ch.isdigit())
    else:
        # Lấy 3–4 chữ số cuối nếu có
        m = re.search(r'(\d{3,4})$', s)
        if m:
            digits = m.group(1)
        else:
            # Fallback: lấy toàn bộ số tìm thấy
            digits = "".join(ch for ch in s if ch.isdigit())
    return _floor_from_digits(digits)

# ======= Main extractor =======
def extract_info(text: str) -> Dict[str, Optional[str]]:
    """
    Trích xuất:
      - toanha: B3, C2, ...
      - phong : 203, 402, 1205, ...
      - tang  : 2, 4, 12 (nếu không có 'tầng X' thì suy từ 'phong')
      - thoigian: 'từ sáng', 'tối qua', 'ngày 10/10', ...
    """
    info: Dict[str, Optional[str]] = {"toanha": None, "phong": None, "tang": None, "thoigian": None}
    txt = text.strip()

    # --------- PHÒNG (ưu tiên toà + phòng: B3-402 / b3 402 / B3.402) ----------
    m_build = re.search(r'\b([A-Za-z]\d)[\-\s\.]?(\d{3,4})\b', txt, flags=re.IGNORECASE)
    if m_build:
        info["toanha"] = m_build.group(1).upper()      # B3
        room_digits = m_build.group(2)                  # 402 / 1001
        info["phong"] = room_digits
    else:
        # Các biến thể thường gặp
        room_patterns = [
            r"(?:phòng|phong|p\.?)\s*(?:khách\s*sạn\s*sinh\s*viên|kssv)?\s*[-:\s]?([A-Za-z]?\d{2,4}[A-Za-z]?)",
            r"\bKSSV\s*[-:\s]?(\d{2,4})\b",
            r"\bP\s*\.?\s*([A-Za-z]?\d{2,4}[A-Za-z]?)\b",
        ]
        for pat in room_patterns:
            m = re.search(pat, txt, flags=re.IGNORECASE)
            if m:
                info["phong"] = _clean_room_token(m.group(1))
                break

    # --------- TẦNG ----------
    # Ưu tiên 'tầng X', nếu không thì suy từ 'phong'
    m_tang = re.search(r"tầng\s*(\d{1,2})\b", txt, flags=re.IGNORECASE)
    if m_tang:
        info["tang"] = m_tang.group(1)
    elif info["phong"]:
        info["tang"] = _infer_floor_from_room(info["phong"])

    # --------- THỜI GIAN ----------
    fixed_time_patterns = [
        r"(từ\s*tối\s*qua)", r"(tối\s*qua)", r"(đêm\s*qua)", r"(chiều\s*hôm\s*qua)", r"(hôm\s*qua)",
        r"(hôm\s*kia)", r"(sáng\s*nay)", r"(trưa\s*nay)", r"(chiều\s*nay)", r"(tối\s*nay)", r"(hôm\s*nay)",
        r"(từ\s*sáng)",  # thêm 'từ sáng'
    ]
    for ptn in fixed_time_patterns:
        m = re.search(ptn, txt, flags=re.IGNORECASE)
        if m:
            info["thoigian"] = m.group(1).lower().strip()
            return info

    m_date = re.search(r"(ngày\s*\d{1,2}/\d{1,2}(?:/\d{2,4})?)", txt, flags=re.IGNORECASE)
    if m_date:
        info["thoigian"] = m_date.group(1).lower().strip()
        return info

    m_cachd = re.search(r"cách\s*đây\s*(\d{1,2})\s*(ngày|hôm)\b", txt, flags=re.IGNORECASE)
    if m_cachd:
        num = int(m_cachd.group(1))
        info["thoigian"] = f"{num} ngày trước"
        return info

    m_num_truoc = re.search(r"\b(\d{1,2})\s*(ngày|hôm)\s*trước\b", txt, flags=re.IGNORECASE)
    if m_num_truoc:
        num = int(m_num_truoc.group(1))
        info["thoigian"] = f"{num} ngày trước"
        return info

    m_num_nay = re.search(r"\b(\d{1,2})\s*(ngày|hôm)\s*nay\b", txt, flags=re.IGNORECASE)
    if m_num_nay:
        num = int(m_num_nay.group(1))
        info["thoigian"] = f"{num} ngày gần đây"
        return info

    m_num_plain = re.search(r"\b(\d{1,2})\s*(ngày|hôm)\b", txt, flags=re.IGNORECASE)
    if m_num_plain:
        num = int(m_num_plain.group(1))
        info["thoigian"] = f"{num} ngày gần đây"
        return info

    m_word_truoc = re.search(r"\b(một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười)\s*(ngày|hôm)\s*trước\b", txt, flags=re.IGNORECASE)
    if m_word_truoc:
        num = _word_to_num(m_word_truoc.group(1))
        if num:
            info["thoigian"] = f"{num} ngày trước"
            return info

    m_word_nay = re.search(r"\b(một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười)\s*(ngày|hôm)\s*nay\b", txt, flags=re.IGNORECASE)
    if m_word_nay:
        num = _word_to_num(m_word_nay.group(1))
        if num:
            info["thoigian"] = f"{num} ngày gần đây"
            return info

    m_word_plain = re.search(r"\b(một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười)\s*(ngày|hôm)\b", txt, flags=re.IGNORECASE)
    if m_word_plain:
        num = _word_to_num(m_word_plain.group(1))
        if num:
            info["thoigian"] = f"{num} ngày gần đây"
            return info

    if re.search(r"\b(mấy|vài)\s*hôm\s*nay\b", txt, flags=re.IGNORECASE):
        info["thoigian"] = "gần đây"
        return info

    return info

# ============ Test nhanh ============
if __name__ == "__main__":
    tests = [
        "phòng 203 đèn bị hỏng từ hôm qua",
        "phong B203 mất điện 2 ngày rồi",
        "phòng KSSV-214 tối không sáng",
        "P.305 bị mất nước 1 ngày trước",
        "B3-402 mất nước từ sáng",
        "P 12A2 bóng đèn cháy tối qua",
        "phòng 1205 hư internet từ sáng nay",
        "phòng tầng 5 bị hư wifi",
        "Cách đây 3 ngày phòng 203 mất điện",
        "vài hôm nay phòng 203 chập chờn",
        "2 ngày nay wifi yếu phòng 203",
    ]
    for t in tests:
        print(f"\n🟩 {t}")
        print(extract_info(t))
