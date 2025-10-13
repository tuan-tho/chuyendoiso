# backend/ai/train_phobert.py
from __future__ import annotations

import os
import json
import random
from typing import Dict, Any

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
    preds = np.asarray(preds); refs = np.asarray(refs)
    return float((preds == refs).mean())

def _f1_macro(preds, refs, num_labels: int):
    preds = np.asarray(preds); refs = np.asarray(refs)
    f1s = []
    for c in range(num_labels):
        tp = np.sum((preds == c) & (refs == c))
        fp = np.sum((preds == c) & (refs != c))
        fn = np.sum((preds != c) & (refs == c))
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1   = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        f1s.append(f1)
    return float(np.mean(f1s))


# ================= CẤU HÌNH =================
MODEL_NAME = "vinai/phobert-base"
DATA_PATH  = os.path.join(os.path.dirname(__file__), "Datakssv.csv")  # cần: text, label
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "models", "phobert_kssv")
MAX_LEN    = 256
SEED       = 42

# 6 nhãn loại sự cố
LABELS = ["điện", "nước", "internet", "thiết bị", "vệ sinh", "khác"]
label2id = {lbl: i for i, lbl in enumerate(LABELS)}
id2label = {i: lbl for i, lbl in enumerate(LABELS)}

def _set_seed(s=SEED):
    random.seed(s)
    np.random.seed(s)
    try:
        import torch  # type: ignore
        torch.manual_seed(s)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(s)
    except Exception:
        pass

def _require_file(path: str):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"❌ Không tìm thấy file dữ liệu: {path}")


# ================= LOAD DATA (6 NHÃN) =================
def load_dataset(csv_path: str) -> DatasetDict:
    _require_file(csv_path)
    df = pd.read_csv(csv_path)

    # Cần có 2 cột: text, label
    need_cols = {"text", "label"}
    if not need_cols.issubset(df.columns):
        raise ValueError("❌ CSV phải có cột: 'text' và 'label'.")

    # Chuẩn hoá
    df["text"] = df["text"].astype(str).fillna("").str.strip()
    df["label"] = df["label"].astype(str).fillna("").str.strip()

    # Bỏ dòng text rỗng (nếu có)
    df = df[df["text"] != ""].copy()

    # Lọc label hợp lệ
    df = df[df["label"].isin(LABELS)].copy()
    if df.empty:
        raise ValueError("❌ Không còn dòng nào sau khi lọc theo LABELS.")

    # Thống kê nhanh
    print("🔎 Label distribution (after filtering):")
    print(df["label"].value_counts().to_string())

    # Map sang id
    df["labels"] = df["label"].map(label2id).astype("int64")

    # Chia tập stratify theo labels
    train_df, test_df = train_test_split(
        df[["text", "labels"]],
        test_size=0.15,
        random_state=SEED,
        stratify=df["labels"],
    )
    val_df, test_df = train_test_split(
        test_df,
        test_size=0.5,
        random_state=SEED,
        stratify=test_df["labels"],
    )

    ds_train = Dataset.from_pandas(train_df, preserve_index=False)
    ds_val   = Dataset.from_pandas(val_df,   preserve_index=False)
    ds_test  = Dataset.from_pandas(test_df,  preserve_index=False)

    dsdict = DatasetDict(train=ds_train, validation=ds_val, test=ds_test)
    dsdict = dsdict.cast_column("labels", Value("int64"))
    return dsdict


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
        "f1": _f1_macro(preds, labels, num_labels=len(LABELS)),
    }


# ================= MAIN =================
def main():
    _set_seed(SEED)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("🔹 Loading dataset from:", DATA_PATH)
    dsdict = load_dataset(DATA_PATH)

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
        num_labels=len(LABELS),
        id2label=id2label,
        label2id=label2id,
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
        load_best_model_at_end=True,
        metric_for_best_model="eval_f1",
        greater_is_better=True,
        logging_steps=50,
        report_to="none",
        no_cuda=True,         # dùng CPU để tránh lỗi CUDA
        fp16=False,
        remove_unused_columns=False,
        seed=SEED,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        tokenizer=tokenizer,
        data_collator=collator,
        compute_metrics=compute_metrics,
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
    with open(os.path.join(OUTPUT_DIR, "label_map.json"), "w", encoding="utf-8") as f:
        json.dump({"label2id": label2id, "id2label": id2label}, f, ensure_ascii=False, indent=2)

    print("✅ Done. Model saved at:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
