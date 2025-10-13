# backend/ai/classifier.py
import os
import argparse
import json
import torch # pyright: ignore[reportMissingImports]
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification # type: ignore

from text_preprocess import normalize_text # type: ignore
from ner_vn import extract_info # type: ignore
from logging_utils import log_prediction # type: ignore

LABELS = ["điện", "nước", "internet", "thiết bị", "vệ sinh", "khác"]
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models", "phobert_kssv")

class PhoBERTClassifier:
    def __init__(self, model_dir: str = MODEL_DIR):
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir, use_fast=False)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        self.model.eval()

    def predict(self, text: str, max_len: int = 256):
        text_norm = normalize_text(text)
        inputs = self.tokenizer(
            text_norm,
            return_tensors="pt",
            truncation=True,
            max_length=max_len,
            padding=True,
        )
        with torch.no_grad():
            logits = self.model(**inputs).logits
            probs = torch.softmax(logits, dim=-1).numpy()[0]
        idx = int(np.argmax(probs))
        return {
            "label": LABELS[idx],
            "confidence": float(probs[idx]),
            "probs": {LABELS[i]: float(p) for i, p in enumerate(probs)},
            "text_norm": text_norm,
        }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("text", type=str, help="Câu phản ánh cần phân loại")
    parser.add_argument("--threshold", type=float, default=0.65, help="Ngưỡng tin cậy")
    parser.add_argument("--log", action="store_true", help="Ghi log dự đoán vào ai/logs/predictions.csv")
    args = parser.parse_args()

    clf = PhoBERTClassifier(MODEL_DIR)
    out = clf.predict(args.text)

    # NER (trích xuất meta)
    meta = extract_info(out["text_norm"])

    # Đánh giá theo threshold
    low_conf = out["confidence"] < args.threshold

    # In kết quả gọn giống trước
    print(f"Label: {out['label']} (Confidence: {out['confidence']:.4f})")
    if low_conf:
        print(f"⚠️ Thấp hơn ngưỡng {args.threshold:.2f} → nên gắn cờ duyệt thủ công hoặc map tạm 'khác'.")

    # In meta (gợi ý)
    if meta:
        print("Meta:", json.dumps(meta, ensure_ascii=False))

    # Ghi log nếu cần
    if args.log:
        payload = {
            "threshold": args.threshold,
            "low_confidence": low_conf,
            "meta": meta,
        }
        log_prediction(args.text, out["label"], out["confidence"], payload)

if __name__ == "__main__":
    main()
