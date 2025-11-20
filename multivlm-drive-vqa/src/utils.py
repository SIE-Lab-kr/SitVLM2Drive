import os
import csv
from typing import List, Tuple

import matplotlib.pyplot as plt
import torch


def save_predictions_csv(sample_records: List[Tuple], path: str):
    """
    sample_records: iterable of (image_path, question, actual_answer, predicted_answer, q_type)
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["image_path", "question", "actual_answer", "predicted_answer", "q_type"])
        for rec in sample_records:
            writer.writerow(rec)


def plot_loss_curves(epochs_list, train_losses, val_losses, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.figure()
    plt.plot(epochs_list, train_losses, label="Train Loss")
    plt.plot(epochs_list, val_losses, label="Val Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("Training & Validation Loss")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def plot_metric_curve(epochs_list, metric_values, metric_name, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.figure()
    plt.plot(epochs_list, metric_values, marker="o")
    plt.xlabel("Epoch")
    plt.ylabel(metric_name)
    plt.title(f"{metric_name} over epochs")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def save_checkpoint(model, processor, out_dir, epoch: int):
    os.makedirs(out_dir, exist_ok=True)
    real_model = model.module if hasattr(model, "module") else model
    ckpt_path = os.path.join(out_dir, f"checkpoint_epoch_{epoch}")
    real_model.save_pretrained(
        ckpt_path,
        safe_serialization=True,
        max_shard_size="24GB",
    )
    processor.save_pretrained(ckpt_path)
