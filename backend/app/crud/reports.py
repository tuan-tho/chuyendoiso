# app/crud/reports.py
from __future__ import annotations

import json
import logging
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session, selectinload  # type: ignore
from sqlalchemy.exc import SQLAlchemyError  # type: ignore

from .. import models, schemas

# ✅ PhoBERT / bộ phân loại
try:
    from ai.predictor import classify_one_full  # type: ignore
except Exception:
    classify_one_full = None  # fallback nếu môi trường chưa có AI

# ✅ Gemini auto-reply
try:
    from ai.auto_reply_gemini import generate_auto_reply  # type: ignore
except Exception:
    generate_auto_reply = None

logger = logging.getLogger(__name__)

ALLOWED_PRIORITIES = {"normal", "high", "urgent"}


# --------- Helpers ----------
def _infer_floor_from_room(room: Optional[str]) -> Optional[int]:
    """Suy tầng từ số phòng khi NER không bắt được."""
    if not room:
        return None
    digits = "".join(ch for ch in str(room) if ch.isdigit())
    if not digits:
        return None

    # Phòng 1001 -> tầng 10; 1205 -> tầng 12
    if len(digits) >= 4:
        try:
            floor = int(digits[:2])
            if 1 <= floor <= 15:
                return floor
        except ValueError:
            pass

    # Phòng 214 -> tầng 2
    try:
        floor = int(digits[0])
        if 1 <= floor <= 15:
            return floor
    except ValueError:
        return None

    return None


def _auto_priority_backup(title: str, desc: Optional[str], ai_label: Optional[str]) -> str:
    """
    Fallback ưu tiên an toàn khi chưa có AI.
    """
    text = f"{title} {desc or ''}".lower()

    urgent_kw = [
        "khẩn cấp", "khẩn", "nguy hiểm", "cháy", "chập điện",
        "tia lửa", "bốc khói", "vỡ ống", "ngập nặng", "rò rỉ mạnh",
        "mất hoàn toàn", "toàn dãy", "toàn khu",
    ]
    if any(k in text for k in urgent_kw):
        return "urgent"

    if ai_label in {"điện", "nước"}:
        if any(k in text for k in ["không có nước", "không có điện", "mất hoàn toàn", "toàn dãy", "toàn khu"]):
            return "urgent"
        if any(k in text for k in ["rò rỉ", "rò nước", "nhấp nháy", "chập chờn"]):
            return "high"

    if ai_label == "vệ sinh" and any(k in text for k in ["hôi thối", "rất bẩn", "đầy rác", "tràn rác"]):
        return "high"

    # Mặc định HIGH để đảm bảo xử lý kịp thời
    return "high"


def _normalize_priority(p: Optional[str]) -> str:
    """Đưa priority về 1 trong ALLOWED_PRIORITIES, mặc định 'high'."""
    if not p:
        return "high"
    p2 = str(p).strip().lower()
    return p2 if p2 in ALLOWED_PRIORITIES else "high"


# --------- CRUD ----------
def create_report(db: Session, reporter_id: int, data: schemas.ReportCreate) -> models.Report:
    # Làm sạch input
    title = (data.title or "").strip() or "(không có tiêu đề)"
    description = (data.description or None)
    category = (data.category or None)
    client_priority = (data.priority or None)

    image_url = (getattr(data, "image_url", None) or None)
    if isinstance(image_url, str):
        image_url = image_url.strip() or None

    building = (getattr(data, "building", None) or None)
    if isinstance(building, str):
        building = building.strip() or None

    room = (getattr(data, "room", None) or None)
    if isinstance(room, str):
        room = room.strip() or None

    rpt = models.Report(
        title=title,
        description=description,
        category=category,        # có thể None, sẽ map từ AI nếu có
        priority=None,            # set ở dưới
        reporter_id=reporter_id,
        status="open",
        image_url=image_url,
        building=building,
        room=room,
    )

    db.add(rpt)
    db.flush()  # có id tạm cho log

    ai_label: Optional[str] = None
    pred: dict = {}

    # ✅ Gọi AI phân loại (nếu có)
    if classify_one_full:
        try:
            text = f"{title}. {description or ''}"
            pred = classify_one_full(text) or {}
            ai_label = pred.get("label")
            rpt.ai_label = ai_label
            rpt.ai_confidence = float(pred.get("label_confidence") or 0.0) or None
            meta = pred.get("meta") or {}
            rpt.ai_room = meta.get("phong")

            # Tầng: ưu tiên NER, nếu thiếu thì suy từ số phòng
            floor_val = meta.get("tang")
            if floor_val is None:
                floor_val = _infer_floor_from_room(rpt.ai_room)
            try:
                rpt.ai_floor = int(floor_val) if floor_val is not None else None
            except Exception:
                rpt.ai_floor = None

            # Thời gian: nếu NER không có, set theo thời điểm gửi
            rpt.ai_time_text = meta.get("thoigian") or datetime.now().strftime("%H:%M:%S %d/%m/%Y")

            # Map category theo nhãn (nếu thiếu)
            if not rpt.category and ai_label:
                mapping = {
                    "điện": "Điện",
                    "nước": "Nước",
                    "internet": "Internet",
                    "thiết bị": "Cơ sở vật chất",
                    "vệ sinh": "Vệ sinh",
                    "khác": "Khác",
                }
                rpt.category = mapping.get(ai_label, "Khác")

        except Exception as e:
            logger.warning(f"[AI enrich failed][report_id={rpt.id}] {e}")

    # ✅ Chốt priority
    ai_priority = (pred.get("priority") if pred else None)
    chosen_priority = client_priority or ai_priority or _auto_priority_backup(title, description, ai_label)
    rpt.priority = _normalize_priority(chosen_priority)

    # ✅ Gọi Gemini để sinh phản hồi tự động
    if generate_auto_reply:
        try:
            auto_reply = generate_auto_reply(description or title, ai_label or "khác", rpt.priority)
            if auto_reply and len(auto_reply) > 500:
                auto_reply = auto_reply[:500].rstrip() + "…"
            rpt.admin_reply = auto_reply
            rpt.admin_reply_source = "ai"  # 👈 Đánh dấu nguồn phản hồi là AI
        except Exception as e:
            logger.warning(f"[Gemini auto-reply failed][report_id={rpt.id}] {e}")
            # Không gán source để biết đây không phải AI
            rpt.admin_reply = "Hệ thống đã ghi nhận sự cố, bộ phận kỹ thuật sẽ xử lý trong thời gian sớm nhất."

    # ✅ Lưu meta AI (nếu có)
    if pred:
        try:
            rpt.ai_meta = json.dumps(pred, ensure_ascii=False)
        except Exception:
            pass

    # Nếu vẫn chưa có ai_time_text (trường hợp không có AI), đặt theo giờ thực
    if not getattr(rpt, "ai_time_text", None):
        rpt.ai_time_text = datetime.now().strftime("%H:%M:%S %d/%m/%Y")

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception(f"[DB COMMIT FAILED][report_id={getattr(rpt,'id',None)}]")
        raise
    db.refresh(rpt)
    return rpt


def list_reports(db: Session, skip: int = 0, limit: int = 200) -> List[models.Report]:
    return (
        db.query(models.Report)
        .options(selectinload(models.Report.reporter))
        .order_by(models.Report.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def list_reports_by_user(db: Session, user_id: int) -> List[models.Report]:
    return (
        db.query(models.Report)
        .options(selectinload(models.Report.reporter))
        .filter(models.Report.reporter_id == user_id)
        .order_by(models.Report.created_at.desc())
        .all()
    )


def get_report(db: Session, report_id: int) -> Optional[models.Report]:
    return (
        db.query(models.Report)
        .options(selectinload(models.Report.reporter))
        .filter(models.Report.id == report_id)
        .first()
    )


def update_report(db: Session, report_id: int, upd: schemas.ReportUpdate) -> Optional[models.Report]:
    rpt = get_report(db, report_id)
    if not rpt:
        return None

    # cập nhật các trường cho phép
    if hasattr(upd, "title") and upd.title is not None:
        rpt.title = upd.title
    if hasattr(upd, "description") and upd.description is not None:
        rpt.description = upd.description
    if hasattr(upd, "category") and upd.category is not None:
        rpt.category = upd.category
    if hasattr(upd, "status") and upd.status is not None:
        rpt.status = upd.status
    if hasattr(upd, "admin_reply") and upd.admin_reply is not None:
        rpt.admin_reply = upd.admin_reply
        # nếu admin tự sửa, đánh dấu nguồn thủ công
        if (rpt.admin_reply or "").strip():
            rpt.admin_reply_source = "manual"
    if hasattr(upd, "priority") and upd.priority is not None:
        rpt.priority = _normalize_priority(upd.priority)
    if hasattr(upd, "building") and upd.building is not None:
        rpt.building = (upd.building or "").strip() or None
    if hasattr(upd, "room") and upd.room is not None:
        rpt.room = (upd.room or "").strip() or None
    if hasattr(upd, "image_url") and upd.image_url is not None:
        img = (upd.image_url or "").strip()
        rpt.image_url = img or None

    # Tùy chọn: phân loại lại nếu admin yêu cầu
    reclass = getattr(upd, "reclassify", False)
    if reclass and classify_one_full:
        try:
            text = f"{rpt.title}. {rpt.description or ''}"
            pred = classify_one_full(text) or {}
            if pred:
                rpt.ai_label = pred.get("label") or rpt.ai_label
                rpt.ai_confidence = float(pred.get("label_confidence") or 0.0) or rpt.ai_confidence
                new_priority = _normalize_priority(pred.get("priority"))
                rpt.priority = new_priority
                try:
                    rpt.ai_meta = json.dumps(pred, ensure_ascii=False)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"[AI reclassify failed][report_id={rpt.id}] {e}")

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(rpt)
    return rpt


def delete_report(db: Session, report_id: int) -> bool:
    """Xoá report (dùng cho router Admin)."""
    rpt = get_report(db, report_id)
    if not rpt:
        return False
    db.delete(rpt)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return True
