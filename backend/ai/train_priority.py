# backend/ai/train_priority.py
from __future__ import annotations

import os
import json
import random
from typing import Dict, Any, Tuple

import numpy as np  # type: ignore
import pandas as pd  # type: ignore
from sklearn.model_selection import train_test_split  # type: ignore
from datasets import Dataset, DatasetDict, Value  # type: ignore
from transformers import (  # type: ignore
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
)
import torch  # type: ignore
import torch.nn as nn  # type: ignore

# ===== metrics: dùng evaluate nếu có, nếu không thì tự tính =====
try:
    import evaluate  # type: ignore
    _USE_EVALUATE = True
    metric_accuracy = evaluate.load("accuracy")
    metric_f1 = evaluate.load("f1")
except Exception:
    _USE_EVALUATE = False
    metric_accuracy = None
    metric_f1 = None

def _acc(preds, refs):
    preds = np.asarray(preds)
    refs = np.asarray(refs)
    return float((preds == refs).mean())

def _f1_macro(preds, refs, num_labels: int):
    preds = np.asarray(preds)
    refs = np.asarray(refs)
    f1s = []
    for c in range(num_labels):
        tp = np.sum((preds == c) & (refs == c))
        fp = np.sum((preds == c) & (refs != c))
        fn = np.sum((preds != c) & (refs == c))
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1   = (2*prec*rec)/(prec+rec) if (prec+rec) > 0 else 0.0
        f1s.append(f1)
    return float(np.mean(f1s))


# ================= CẤU HÌNH =================
MODEL_NAME = "vinai/phobert-base"
DATA_PATH  = os.path.join(os.path.dirname(__file__), "Datakssv.csv")  # cần cột: text, priority
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "models", "phobert_priority")
MAX_LEN    = 256
SEED       = 42

PRIORITIES = ["normal", "high", "urgent"]
pri2id = {p: i for i, p in enumerate(PRIORITIES)}
id2pri = {i: p for i, p in enumerate(PRIORITIES)}


def _set_seed(s=SEED):
    random.seed(s)
    np.random.seed(s)
    torch.manual_seed(s)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(s)


def _require_file(path: str):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"❌ Không tìm thấy file dữ liệu: {path}")


# ================= LOAD DATA =================
def load_dataset(csv_path: str) -> Tuple[DatasetDict, np.ndarray]:
    _require_file(csv_path)
    df = pd.read_csv(csv_path)

    need_cols = {"text", "priority"}
    if not need_cols.issubset(df.columns):
        raise ValueError("❌ CSV phải có đủ cột: text, priority.")

    # Chuẩn hoá
    df["text"] = df["text"].astype(str).fillna("").str.strip()
    df["priority"] = df["priority"].astype(str).fillna("").str.lower().str.strip()

    # Bỏ text rỗng & lọc nhãn hợp lệ
    df = df[(df["text"] != "") & (df["priority"].isin(PRIORITIES))].copy()
    if df.empty:
        raise ValueError("❌ Không còn dòng nào sau khi lọc priority hợp lệ & text khác rỗng.")

    # Map id
    df["labels"] = df["priority"].map(pri2id).astype("int64")

    # Thống kê
    print("🔎 Priority distribution (after filtering):")
    print(df["priority"].value_counts().to_string())

    # Tính class weights (ngược tần suất): weight_k = N / (C * n_k)
    counts = df["labels"].value_counts().sort_index()
    N = float(len(df))
    C = float(len(PRIORITIES))
    weights = np.array([N / (C * (counts.get(i, 1))) for i in range(len(PRIORITIES))], dtype=np.float32)

    # Chia data (cố gắng stratify; nếu lớp quá hiếm <2 ở tập con thì fallback)
    can_stratify = counts.min() >= 2
    if can_stratify:
        train_df, temp_df = train_test_split(
            df[["text", "labels"]],
            test_size=0.15,
            random_state=SEED,
            stratify=df["labels"],
        )
        temp_counts = temp_df["labels"].value_counts()
        can_valtest_stratify = temp_counts.min() >= 2
        if can_valtest_stratify:
            val_df, test_df = train_test_split(
                temp_df, test_size=0.5, random_state=SEED, stratify=temp_df["labels"]
            )
        else:
            val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=SEED, shuffle=True)
    else:
        train_df, temp_df = train_test_split(
            df[["text", "labels"]],
            test_size=0.15,
            random_state=SEED,
            shuffle=True,
        )
        val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=SEED, shuffle=True)

    ds_train = Dataset.from_pandas(train_df, preserve_index=False)
    ds_val   = Dataset.from_pandas(val_df,   preserve_index=False)
    ds_test  = Dataset.from_pandas(test_df,  preserve_index=False)

    dsdict = DatasetDict(train=ds_train, validation=ds_val, test=ds_test)
    dsdict = dsdict.cast_column("labels", Value("int64"))

    return dsdict, weights


# ================= TOKENIZE =================
def tokenize_function(examples, tokenizer):
    return tokenizer(
        examples["text"],
        truncation=True,
        max_length=MAX_LEN,
        padding=False,                 # collator sẽ padding
        return_token_type_ids=False,   # PhoBERT/Roberta không dùng
    )


# ================= METRICS =================
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    if _USE_EVALUATE:
        return {
            **metric_accuracy.compute(predictions=preds, references=labels),
            **metric_f1.compute(predictions=preds, references=labels, average="macro"),
        }
    return {
        "accuracy": _acc(preds, labels),
        "f1": _f1_macro(preds, labels, num_labels=len(PRIORITIES)),
    }


# ====== Custom Trainer để nhúng class weights vào loss ======
class WeightedTrainer(Trainer):
    def __init__(self, class_weights: np.ndarray | None = None, **kwargs):
        super().__init__(**kwargs)
        self.class_weights = None
        if class_weights is not None:
            # đảm bảo tensor đúng device
            self.class_weights = torch.tensor(class_weights, dtype=torch.float32)

    def compute_loss(self, model, inputs, return_outputs=False):
        labels = inputs.get("labels")
        outputs = model(**{k: v for k, v in inputs.items() if k != "labels"})
        logits = outputs.get("logits")

        # Label smoothing đã có trong TrainingArguments, nhưng khi tự tính loss
        # ta sẽ dùng CrossEntropyLoss với weights; smoothing được đặt ở args.
        # Ở đây CE không có smoothing, nhưng ta ưu tiên trọng số lớp.
        if self.class_weights is not None:
            if self.class_weights.device != logits.device:
                self.class_weights = self.class_weights.to(logits.device)
            loss_fct = nn.CrossEntropyLoss(weight=self.class_weights)
        else:
            loss_fct = nn.CrossEntropyLoss()

        loss = loss_fct(logits.view(-1, logits.size(-1)), labels.view(-1))
        return (loss, outputs) if return_outputs else loss


# ================= MAIN =================
def main():
    _set_seed(SEED)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("🔹 Loading dataset from:", DATA_PATH)
    dsdict, class_weights = load_dataset(DATA_PATH)

    print("🔹 Loading tokenizer:", MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=False)

    tokenized = dsdict.map(
        lambda ex: tokenize_function(ex, tokenizer),
        batched=True,
        remove_columns=["text"],
    )
    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    for split in ["train", "validation", "test"]:
        print(f"✅ [{split}] columns:", tokenized[split].column_names)

    print("🔹 Loading model:", MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=len(PRIORITIES),
        id2label=id2pri,
        label2id=pri2id,
    )

    args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        num_train_epochs=5,
        weight_decay=0.01,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_f1",
        greater_is_better=True,
        logging_steps=50,
        report_to="none",
        no_cuda=True,            # dùng CPU (tránh lỗi GPU driver)
        fp16=False,
        remove_unused_columns=False,
        seed=SEED,
        label_smoothing_factor=0.05,  # nhẹ để giảm overfit lớp lớn
    )

    trainer = WeightedTrainer(
        model=model,
        args=args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        tokenizer=tokenizer,
        data_collator=collator,
        compute_metrics=compute_metrics,
        class_weights=class_weights,   # <— trọng số lớp
    )

    print("🔹 Start training...")
    trainer.train()

    print("🔹 Evaluate on validation:")
    print(json.dumps(trainer.evaluate(tokenized["validation"]), indent=2, ensure_ascii=False))

    print("🔹 Evaluate on test:")
    print(json.dumps(trainer.evaluate(tokenized["test"]), indent=2, ensure_ascii=False))

    print("🔹 Saving model to:", OUTPUT_DIR)
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    # Lưu label map & tem loại tác vụ (để predictor nhận diện đúng)
    with open(os.path.join(OUTPUT_DIR, "label_map.json"), "w", encoding="utf-8") as f:
        json.dump({"label2id": pri2id, "id2label": id2pri}, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUTPUT_DIR, "task_type.json"), "w", encoding="utf-8") as f:
        json.dump({"type": "priority_only"}, f, ensure_ascii=False, indent=2)

    print("✅ Done. Model saved at:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
