# backend/ai/predictor.py
from __future__ import annotations

import os
import json
from typing import Dict, Any, Tuple, Optional, List

import torch  # type: ignore
import torch.nn.functional as F  # type: ignore
from transformers import AutoTokenizer, AutoModelForSequenceClassification  # type: ignore

# ---------------------------------------------------------
# Import tương thích:
# - Gọi qua FastAPI: from .xxx import ...
# - Chạy tay:        python -m ai.predictor "..."
# ---------------------------------------------------------
try:
    from .text_preprocess_kssv import normalize_text  # type: ignore
    from .ner_vn import extract_info  # type: ignore
    from .logging_utils import log_prediction  # type: ignore
except ImportError:
    from text_preprocess_kssv import normalize_text  # type: ignore
    from ner_vn import extract_info  # type: ignore

    try:
        from logging_utils import log_prediction  # type: ignore
    except Exception:
        def log_prediction(*args, **kwargs):  # fallback an toàn
            return

# ================== CẤU HÌNH ĐƯỜNG DẪN ==================
_THIS_DIR = os.path.dirname(__file__)

# Mô hình 6 nhãn sự cố
LABEL_MODEL_DIR = os.path.join(_THIS_DIR, "models", "phobert_kssv")
LABEL_MAP_PATH  = os.path.join(LABEL_MODEL_DIR, "label_map.json")

# Mô hình 3 mức độ ưu tiên
PRIO_MODEL_DIR  = os.path.join(_THIS_DIR, "models", "phobert_priority")
PRIO_MAP_PATH   = os.path.join(PRIO_MODEL_DIR,  "label_map.json")

# Tập tin nhận dạng nếu dùng model GỘP 18 lớp (giữ để backward-compatible)
TASK_TYPE_PATH        = os.path.join(LABEL_MODEL_DIR, "task_type.json")        # {"type": "combined_label_priority"}
MULTITASK_MAPS_PATH   = os.path.join(LABEL_MODEL_DIR, "multitask_maps.json")   # {"id2comb": {...}, ...}
COMBINED_MAP_OLD_PATH = os.path.join(LABEL_MODEL_DIR, "combined_map.json")     # fallback cũ

# Dùng CPU mặc định. Bật CUDA qua USE_CUDA=1 nếu có.
_USE_CUDA = (os.environ.get("USE_CUDA", "0") in ("1", "true", "True")) and torch.cuda.is_available()
_DEVICE   = torch.device("cuda" if _USE_CUDA else "cpu")

# ================== BỘ NHỚ CACHE ==================
_PIPE: Dict[str, Any] = {
    # label model (6 nhãn)
    "label_tokenizer": None,
    "label_model": None,
    "id2label_6": None,     # {int: "điện"...}
    "label2id_6": None,     # {"điện": 0, ...}

    # priority model (3 mức)
    "prio_tokenizer": None,
    "prio_model": None,
    "id2prio_3": None,      # {int: "normal/high/urgent"}
    "prio2id_3": None,      # {"normal": 0, ...}

    # nếu phát hiện model gộp (18 lớp) trong phobert_kssv
    "is_combined": False,
    "id2comb": None,        # {0: "điện|normal", ...}
    "comb2id": None,        # {"điện|normal": 0, ...}
    "LABELS": None,         # ["điện", ...]
    "PRIORITIES": None,     # ["normal","high","urgent"]
}

# ================== HELPERS ==================
def _softmax_np(logits: torch.Tensor) -> Tuple[int, float, List[float]]:
    probs = F.softmax(logits, dim=-1).detach().cpu().numpy()[0]
    pred_id = int(probs.argmax())
    return pred_id, float(probs[pred_id]), list(map(float, probs))

def _read_json(path: str) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

# ----- load maps cho 6 nhãn
def _load_label_maps() -> Tuple[Optional[Dict[int, str]], Optional[Dict[str, int]]]:
    id2label, label2id = None, None
    mp = _read_json(LABEL_MAP_PATH)
    if mp:
        id2label = mp.get("id2label")
        label2id = mp.get("label2id")
    if isinstance(id2label, dict):
        id2label = {int(k): v for k, v in id2label.items()}
    if isinstance(label2id, dict):
        label2id = {str(k): int(v) for k, v in label2id.items()}
    return id2label, label2id

# ----- load maps cho 3 priority
def _load_prio_maps() -> Tuple[Optional[Dict[int, str]], Optional[Dict[str, int]]]:
    id2prio, prio2id = None, None
    mp = _read_json(PRIO_MAP_PATH)
    if mp:
        id2prio = mp.get("id2label") or mp.get("id2prio")
        prio2id = mp.get("label2id") or mp.get("prio2id")
    if isinstance(id2prio, dict):
        id2prio = {int(k): v for k, v in id2prio.items()}
    if isinstance(prio2id, dict):
        prio2id = {str(k): int(v) for k, v in prio2id.items()}
    return id2prio, prio2id

# ----- phát hiện & nạp map cho model gộp 18 lớp (nếu có)
def _maybe_load_combined_into_pipe() -> bool:
    # cách mới: task_type + multitask_maps
    if os.path.exists(TASK_TYPE_PATH) and os.path.exists(MULTITASK_MAPS_PATH):
        tt = _read_json(TASK_TYPE_PATH)
        mp = _read_json(MULTITASK_MAPS_PATH)
        if tt and tt.get("type") == "combined_label_priority" and mp:
            id2comb = mp.get("id2comb") or mp.get("id2combo")
            comb2id = mp.get("comb2id") or mp.get("combo2id")
            labels  = mp.get("LABELS")
            prios   = mp.get("PRIORITIES")
            if isinstance(id2comb, dict):
                id2comb = {int(k): v for k, v in id2comb.items()}
            if isinstance(id2comb, dict) and isinstance(comb2id, dict):
                _PIPE["id2comb"] = id2comb
                _PIPE["comb2id"] = comb2id
                _PIPE["LABELS"]  = labels
                _PIPE["PRIORITIES"] = prios
                _PIPE["is_combined"] = True
                return True
    # fallback cũ
    mp_old = _read_json(COMBINED_MAP_OLD_PATH)
    if mp_old:
        id2comb = mp_old.get("id2comb") or mp_old.get("id2combo")
        comb2id = mp_old.get("comb2id") or mp_old.get("combo2id")
        labels  = mp_old.get("LABELS")
        prios   = mp_old.get("PRIORITIES")
        if isinstance(id2comb, dict):
            id2comb = {int(k): v for k, v in id2comb.items()}
        if isinstance(id2comb, dict) and isinstance(comb2id, dict):
            _PIPE["id2comb"] = id2comb
            _PIPE["comb2id"] = comb2id
            _PIPE["LABELS"]  = labels
            _PIPE["PRIORITIES"] = prios
            _PIPE["is_combined"] = True
            return True
    return False

def _aggregate_label_probs_from_combined(probs: List[float], id2comb: Dict[int, str]) -> Dict[str, float]:
    """Khi model gộp 18 lớp: gom xác suất theo 'label' (bỏ priority)."""
    agg: Dict[str, float] = {}
    for i, p in enumerate(probs):
        comb = id2comb.get(i, "")
        label = comb.split("|", 1)[0] if "|" in comb else comb
        if label:
            agg[label] = agg.get(label, 0.0) + float(p)
    return agg

# --------- CHỌN PRIORITY BẰNG NGƯỠNG + DEFAULT AN TOÀN ---------
def _choose_priority_with_thresholds(
    probs: Dict[str, float],
    text_norm: str
) -> Tuple[str, float, Dict[str, float]]:
    """
    Chọn priority theo ngưỡng thay vì argmax thuần:
      - urgent nếu >= 0.55
      - high   nếu >= 0.35
      - còn lại: default=high (tránh thiên vị 'normal' khi mơ hồ)
    Trả về (priority, confidence, probs_điều_chỉnh)
    """
    p_urgent = float(probs.get("urgent", 0.0))
    p_high   = float(probs.get("high",   0.0))
    p_normal = float(probs.get("normal", 0.0))

    if p_urgent >= 0.55:
        return "urgent", p_urgent, {"normal": p_normal, "high": p_high, "urgent": p_urgent}
    if p_high >= 0.35:
        return "high", p_high, {"normal": p_normal, "high": p_high, "urgent": p_urgent}

    # Mơ hồ: mặc định high để an toàn vận hành
    return "high", max(p_high, 0.60), {"normal": p_normal, "high": max(p_high, 0.60), "urgent": p_urgent}

# ================== LOAD MODELS (LAZY) ==================
def _lazy_load_label_model():
    if _PIPE["label_model"] is not None and _PIPE["label_tokenizer"] is not None:
        return
    if not os.path.isdir(LABEL_MODEL_DIR):
        raise FileNotFoundError(f"Không tìm thấy thư mục model nhãn: {LABEL_MODEL_DIR}. Hãy train lại.")

    tok = AutoTokenizer.from_pretrained(LABEL_MODEL_DIR, use_fast=False)
    mdl = AutoModelForSequenceClassification.from_pretrained(LABEL_MODEL_DIR).to(_DEVICE).eval()

    # model 6 nhãn hay model gộp?
    id2label, label2id = _load_label_maps()
    if not id2label or not label2id:
        try:
            id2label = {int(k): v for k, v in mdl.config.id2label.items()}
            label2id = {str(k): int(v) for k, v in mdl.config.label2id.items()}
        except Exception:
            pass

    # nếu vẫn không ra map 6 nhãn, thử nhận dạng model gộp
    if not id2label or not label2id:
        _maybe_load_combined_into_pipe()

    _PIPE["label_tokenizer"] = tok
    _PIPE["label_model"]     = mdl
    _PIPE["id2label_6"]      = id2label
    _PIPE["label2id_6"]      = label2id

def _lazy_load_priority_model():
    if _PIPE["prio_model"] is not None and _PIPE["prio_tokenizer"] is not None:
        return
    if not os.path.isdir(PRIO_MODEL_DIR):
        # không có model ưu tiên => để None, predictor vẫn hoạt động cho phần nhãn
        return
    tok = AutoTokenizer.from_pretrained(PRIO_MODEL_DIR, use_fast=False)
    mdl = AutoModelForSequenceClassification.from_pretrained(PRIO_MODEL_DIR).to(_DEVICE).eval()

    id2prio, prio2id = _load_prio_maps()
    if not id2prio or not prio2id:
        try:
            id2prio = {int(k): v for k, v in mdl.config.id2label.items()}
            prio2id = {str(k): int(v) for k, v in mdl.config.label2id.items()}
        except Exception:
            pass

    _PIPE["prio_tokenizer"] = tok
    _PIPE["prio_model"]     = mdl
    _PIPE["id2prio_3"]      = id2prio
    _PIPE["prio2id_3"]      = prio2id

# ================== SUY LUẬN ==================
@torch.inference_mode()
def classify_one_full(text: str) -> Dict[str, Any]:
    """
    Trả về:
      - Nếu model nhãn là 6 lớp: label + probs_label (và meta)
      - Nếu model nhãn là gộp 18 lớp: label/priority suy thẳng từ phobert_kssv
      - Nếu có model priority riêng: suy thêm priority + probs_priority và GHÉP vào kết quả
    """
    # nạp models
    _lazy_load_label_model()
    _lazy_load_priority_model()

    label_tok = _PIPE["label_tokenizer"]
    label_mdl = _PIPE["label_model"]
    id2label6 = _PIPE["id2label_6"]
    is_comb   = _PIPE["is_combined"]
    id2comb   = _PIPE["id2comb"]

    # chuẩn hoá text + meta
    text_norm = normalize_text(text)
    meta = extract_info(text_norm)

    # ===== 1) Dự đoán NHÃN
    inputs_label = label_tok(
        text_norm, truncation=True, max_length=256,
        return_tensors="pt", return_token_type_ids=False
    ).to(_DEVICE)
    logits_label = label_mdl(**inputs_label).logits
    pred_label_id, pred_label_conf, label_probs = _softmax_np(logits_label)

    result: Dict[str, Any] = {"meta": meta}

    if is_comb and id2comb:
        # model gộp 18 lớp: id2comb -> "label|priority"
        comb = id2comb.get(pred_label_id, "")
        label, prio = (comb.split("|", 1) + [None])[:2] if "|" in comb else (comb, None)
        result["label"] = label or None
        result["label_confidence"] = round(pred_label_conf, 4)
        result["probs_combined"] = {id2comb[i]: float(p) for i, p in enumerate(label_probs)}
        result["probs_label"] = _aggregate_label_probs_from_combined(label_probs, id2comb)
        if prio:  # nếu combined đã dự đoán luôn priority
            result["priority"] = prio
            try:
                prio_scores = []
                for k, v in result["probs_combined"].items():
                    if k.startswith(label + "|"):
                        prio_scores.append(v)
                result["priority_confidence"] = round(float(max(prio_scores)), 4) if prio_scores else None
            except Exception:
                result["priority_confidence"] = None
    else:
        # model 6 lớp
        if not id2label6:
            raise RuntimeError("Không có id2label cho model 6 nhãn.")
        label_name = id2label6[pred_label_id]
        result["label"] = label_name
        result["label_confidence"] = round(pred_label_conf, 4)
        result["probs_label"] = {id2label6[i]: float(p) for i, p in enumerate(label_probs)}

    # ===== 2) Dự đoán PRIORITY bằng model riêng (nếu có)
    prio_tok = _PIPE["prio_tokenizer"]
    prio_mdl = _PIPE["prio_model"]
    id2prio3 = _PIPE["id2prio_3"]

    if prio_tok is not None and prio_mdl is not None and id2prio3:
        inputs_prio = prio_tok(
            text_norm, truncation=True, max_length=256,
            return_tensors="pt", return_token_type_ids=False
        ).to(_DEVICE)
        logits_prio = prio_mdl(**inputs_prio).logits
        pred_prio_id, pred_prio_conf, prio_probs = _softmax_np(logits_prio)

        probs_dict = {id2prio3[i]: float(p) for i, p in enumerate(prio_probs)}

        # Chọn theo NGƯỠNG thay vì argmax
        priority, pr_conf, probs_adj = _choose_priority_with_thresholds(probs_dict, text_norm)
        result["priority"] = priority
        result["priority_confidence"] = round(float(pr_conf), 4)
        result["probs_priority"] = probs_adj
    else:
        if "priority" not in result:
            result["priority"] = None
            result["priority_confidence"] = None

    # ===== 3) Heuristics nâng tính thực dụng (nâng cấp theo từ khóa)
    lower_txt = text_norm.lower()

    INTERNET_TOKENS = {"wifi", "wi-fi", "mạng", "internet"}
    lb_conf = float(result.get("label_confidence") or 0.0)
    if lb_conf < 0.60 and any(tok in lower_txt for tok in INTERNET_TOKENS):
        result["label"] = "internet"
        result["label_confidence"] = max(lb_conf, 0.70)

    CRITICAL_PRIORITY = {
        "cháy", "chập điện mạnh", "tia lửa", "tóe lửa", "bốc khói", "khét", "mùi khét",
        "nổ", "rò rỉ gas", "gas rò", "vỡ ống", "vỡ đường ống", "tràn nước", "ngập",
        "rò rỉ nhiều", "rò rỉ mạnh", "điện giật", "sự cố nguy hiểm"
    }
    HIGH_PRIORITY     = {
        "rò rỉ", "chập", "tắc nghẽn", "tắc cống", "tắc bồn", "nghẹt", "mùi khó chịu",
        "mùi nặng", "nhấp nháy", "sụt áp", "mất nước cục bộ", "mất điện cục bộ", "rò nước"
    }

    pr = (result.get("priority") or "").lower()
    pr_conf = float(result.get("priority_confidence") or 0.0)

    # chỉ can thiệp khi model chưa quá chắc
    if pr_conf < 0.85:
        if any(k in lower_txt for k in CRITICAL_PRIORITY):
            result["priority"] = "urgent"
            result["priority_confidence"] = max(pr_conf, 0.90)
            if "probs_priority" in result and isinstance(result["probs_priority"], dict):
                pp = result["probs_priority"]
                pp["urgent"] = max(pp.get("urgent", 0.0), 0.90)
                s = sum(pp.values())
                if s > 0:
                    for k in list(pp.keys()):
                        pp[k] = float(pp[k] / s)
        elif any(k in lower_txt for k in HIGH_PRIORITY) and pr != "urgent":
            result["priority"] = "high"
            result["priority_confidence"] = max(pr_conf, 0.75)
            if "probs_priority" in result and isinstance(result["probs_priority"], dict):
                pp = result["probs_priority"]
                pp["high"] = max(pp.get("high", 0.0), 0.75)
                s = sum(pp.values())
                if s > 0:
                    for k in list(pp.keys()):
                        pp[k] = float(pp[k] / s)

    # 4) Log nhẹ
    try:
        log_prediction(text=text, normalized=text_norm, result=result)
    except Exception:
        pass

    return result


def classify_one(text: str) -> Tuple[Optional[str], float, Dict[str, Any]]:
    """
    Wrapper tương thích ngược:
      -> luôn trả (label, label_confidence, meta)
    """
    r = classify_one_full(text)
    return r.get("label"), float(r.get("label_confidence", 0.0)), dict(r.get("meta") or {})


# ================== TEST NHANH ==================
if __name__ == "__main__":
    # ví dụ:
    #   python -m ai.predictor "phòng B2-305 chập điện, có tia lửa"
    import sys
    sample = sys.argv[1] if len(sys.argv) > 1 else "phòng 302 bóng đèn nhấp nháy 2 ngày"
    out = classify_one_full(sample)
    print(json.dumps(out, ensure_ascii=False, indent=2))
