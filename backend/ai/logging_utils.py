# backend/ai/logging_utils.py
import os
import csv
from datetime import datetime

LOG_PATH = os.path.join(os.path.dirname(__file__), "prediction_logs.csv")

def log_prediction(text: str, label: str, confidence: float, info: dict):
    """
    Ghi lại log dự đoán vào file CSV.
    Mỗi dòng gồm: thời gian, phản ánh, nhãn dự đoán, độ tin cậy, thông tin trích xuất.
    (Đã bỏ cột 'khu' theo yêu cầu)
    """
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    file_exists = os.path.exists(LOG_PATH)

    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Nếu file mới → ghi header
        if not file_exists:
            writer.writerow(["timestamp", "text", "label", "confidence", "phong", "tang", "thoigian"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            text,
            label,
            f"{confidence:.4f}",
            info.get("phong", ""),
            info.get("tang", ""),
            info.get("thoigian", "")
        ])
