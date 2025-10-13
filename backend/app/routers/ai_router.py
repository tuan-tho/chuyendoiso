# app/routers/ai_router.py
from fastapi import APIRouter, HTTPException # type: ignore
from pydantic import BaseModel, Field # type: ignore
from typing import Any, Dict, Tuple

from ai.predictor import classify_one  # type: ignore

router = APIRouter()

class PredictIn(BaseModel):
    text: str = Field(..., description="Câu phản ánh/sự cố tiếng Việt")

class PredictOut(BaseModel):
    label: str
    confidence: float
    meta: Dict[str, Any]

def _normalize_result(res: Any) -> Tuple[str, float, Dict[str, Any]]:
    """Chấp nhận (label, prob, meta), (label, prob, meta, ...), hoặc dict."""
    if isinstance(res, dict):
        label = res.get("label") or res.get("pred_label")
        conf = res.get("confidence") or res.get("prob") or res.get("score")
        meta = res.get("meta") or {}
        if label is None or conf is None:
            raise ValueError("Result dict missing 'label' or 'confidence/prob'")
        return str(label), float(conf), dict(meta)
    # tuple / list
    try:
        label, conf, meta = res  # 3 phần tử
        return str(label), float(conf), dict(meta)
    except ValueError:
        # có thể là 4+ phần tử -> lấy 3 cái đầu
        label, conf, meta, *_ = res
        return str(label), float(conf), dict(meta)

@router.post("/predict", response_model=PredictOut, summary="Predict Endpoint")
def predict(payload: PredictIn) -> PredictOut:
    try:
        res = classify_one(payload.text)
        label, prob, meta = _normalize_result(res)
        return PredictOut(label=label, confidence=prob, meta=meta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/classify", response_model=PredictOut, summary="Classify (alias of /predict)")
def classify(payload: PredictIn) -> PredictOut:
    return predict(payload)
