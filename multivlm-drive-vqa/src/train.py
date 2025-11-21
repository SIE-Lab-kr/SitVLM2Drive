import os
import argparse
import csv

import torch
from torch.utils.data import DataLoader, random_split
from torch.optim import AdamW
from tqdm import tqdm

from src.data import DrivingVideoDataset
from src.metrics import compute_metrics, evaluate_by_type
from src.utils import (
    save_predictions_csv,
    plot_loss_curves,
    plot_metric_curve,
)

from src.models.llama_vl import build_llama_vl
from src.models.qwen_vl import build_qwen_vl
from src.models.internvl_vl import build_internvl_vl


def parse_args():
    parser = argparse.ArgumentParser(description="Multi-VLM Drive VQA training")

    parser.add_argument("--data-root", type=str, required=True,
                        help="Root folder with frames/ and json/")
    parser.add_argument("--output-dir", type=str, default="result",
                        help="Output directory for logs, checkpoints, plots")

    parser.add_argument("--model-type", type=str, required=True,
                        choices=["llama", "qwen", "internvl"],
                        help="Which VLM backend to use")
    parser.add_argument("--model-id", type=str, default=None,
                        help="HF model id. If None, use backend default.")

    parser.add_argument("--q-type-filter", type=str, default=None,
                        help="Optional question type to filter (e.g. CCot)")
    parser.add_argument("--train-split", type=float, default=0.8,
                        help="Train split ratio (0-1)")

    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--eval-epochs", type=int, nargs="+", default=[1, 5, 10],
                        help="Epochs to run full evaluation on (metrics, preds)")

    return parser.parse_args()


def move_batch_to_device(batch, device):
    return {k: v.to(device) for k, v in batch.items()}


def train_one_epoch(model, train_loader, optimizer, epoch, device):
    model.train()
    total_loss = 0.0
    pbar = tqdm(train_loader, desc=f"Epoch {epoch} - Training")
    for batch in pbar:
        batch = move_batch_to_device(batch, device)
        with torch.autocast(
            device_type=device.type,
            dtype=torch.bfloat16 if device.type == "cuda" else torch.float32,
        ):
            outputs = model(**batch)
            loss = outputs.loss

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        pbar.set_postfix({"loss": loss.item()})

    return total_loss / max(len(train_loader), 1)


def evaluate_loss(model, val_loader, epoch, device):
    model.eval()
    total_loss = 0.0
    with torch.no_grad():
        pbar = tqdm(val_loader, desc=f"Epoch {epoch} - ValLoss")
        for batch in pbar:
            batch = move_batch_to_device(batch, device)
            with torch.autocast(
                device_type=device.type,
                dtype=torch.bfloat16 if device.type == "cuda" else torch.float32,
            ):
                outputs = model(**batch)
                loss = outputs.loss
            total_loss += loss.item()
    return total_loss / max(len(val_loader), 1)


def evaluate_and_predict(model, val_eval_loader, processor, epoch, device, max_new_tokens=256):
    model.eval()
    predictions = []
    references = []
    sample_records = []  # (img_path, question, ref, pred, q_type)

    with torch.no_grad():
        pbar = tqdm(val_eval_loader, desc=f"Epoch {epoch} - Evaluation")
        for batch in pbar:
            enc = batch["encoding"]
            enc = move_batch_to_device(enc, device)

            answers_gt = batch["answers"]
            paths = batch["paths"]
            questions = batch["questions"]
            q_types = batch["q_types"]

            with torch.autocast(
                device_type=device.type,
                dtype=torch.bfloat16 if device.type == "cuda" else torch.float32,
            ):
                output_ids = model.generate(
                    **enc,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                )

            decoded = processor.batch_decode(
                output_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )

            for img_path, question, ref, raw_pred, q_type in zip(
                paths, questions, answers_gt, decoded, q_types
            ):
                pred = (raw_pred or "").strip()
                ref = (ref or "").strip()

                predictions.append(pred)
                references.append(ref)
                sample_records.append((img_path, question, ref, pred, q_type))

    metrics = compute_metrics(predictions, references)
    return metrics, sample_records


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Using device:", device)

    # ---------------- model & collators ----------------
    if args.model_type == "llama":
        model, processor, collate_train, collate_eval = build_llama_vl(
            model_id=args.model_id
        )
    elif args.model_type == "qwen":
        model, processor, collate_train, collate_eval = build_qwen_vl(
            model_id=args.model_id
        )
    else:  # internvl
        model, processor, collate_train, collate_eval = build_internvl_vl(
            model_id=args.model_id
        )

    model.to(device)

    # --------------- dataset -----------------
    if args.q_type_filter is not None:
        q_type_filter = [args.q_type_filter]
    else:
        q_type_filter = None

    dataset = DrivingVideoDataset(args.data_root, q_type_filter=q_type_filter)
    print("Total samples:", len(dataset))
    if len(dataset) == 0:
        print("No data found. Check dataset paths.")
        return

    train_size = max(1, int(args.train_split * len(dataset)))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    print(f"Train samples: {len(train_dataset)}, Val samples: {len(val_dataset)}")

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=collate_train,
    )
    val_loader_for_loss = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=collate_train,
    )
    val_loader_for_eval = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=collate_eval,
    )

    # --------------- optimizer -----------------
    optimizer = AdamW(model.parameters(), lr=args.lr)

    # --------------- logging CSV -----------------
    log_csv_path = os.path.join(args.output_dir, "training_eval_log.csv")
    with open(log_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Epoch",
            "Train_Loss",
            "Val_Loss",
            "BLEU-1", "BLEU-2", "BLEU-3", "BLEU-4",
            "ROUGE-1", "ROUGE-2", "ROUGE-L",
            "BERTScore_P", "BERTScore_R", "BERTScore_F1",
            "Accuracy", "Precision", "Recall", "F1-Score", "CIDEr",
        ])

    best_val_loss = float("inf")
    final_sample_records = None

    epoch_indices = []
    train_losses_hist = []
    val_losses_hist = []
    eval_epoch_indices = []
    f1_scores_hist = []

    eval_epochs_set = set(args.eval_epochs)

    for epoch in range(1, args.epochs + 1):
        train_loss = train_one_epoch(model, train_loader, optimizer, epoch, device)
        val_loss = evaluate_loss(model, val_loader_for_loss, epoch, device)

        epoch_indices.append(epoch)
        train_losses_hist.append(train_loss)
        val_losses_hist.append(val_loss)

        if epoch in eval_epochs_set:
            overall_metrics, sample_records = evaluate_and_predict(
                model, val_loader_for_eval, processor, epoch, device
            )
            per_type_metrics = evaluate_by_type(sample_records)

            eval_epoch_indices.append(epoch)
            f1_scores_hist.append(overall_metrics["F1-Score"])

            # Save epoch predictions
            pred_csv = os.path.join(args.output_dir, f"predictions_epoch_{epoch}.csv")
            save_predictions_csv(sample_records, pred_csv)

            # log metrics
            with open(log_csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                row = [
                    epoch,
                    f"{train_loss:.4f}",
                    f"{val_loss:.4f}",
                    f"{overall_metrics['BLEU-1']:.2f}",
                    f"{overall_metrics['BLEU-2']:.2f}",
                    f"{overall_metrics['BLEU-3']:.2f}",
                    f"{overall_metrics['BLEU-4']:.2f}",
                    f"{overall_metrics['ROUGE-1']:.2f}",
                    f"{overall_metrics['ROUGE-2']:.2f}",
                    f"{overall_metrics['ROUGE-L']:.2f}",
                    f"{overall_metrics['BERTScore_P']:.2f}",
                    f"{overall_metrics['BERTScore_R']:.2f}",
                    f"{overall_metrics['BERTScore_F1']:.2f}",
                    f"{overall_metrics['Accuracy']:.2f}",
                    f"{overall_metrics['Precision']:.2f}",
                    f"{overall_metrics['Recall']:.2f}",
                    f"{overall_metrics['F1-Score']:.2f}",
                    f"{overall_metrics['CIDEr']:.2f}",
                ]
                writer.writerow(row)

            print(f"[Epoch {epoch}] Train: {train_loss:.4f}, Val: {val_loss:.4f}")
            print("Overall metrics:", overall_metrics)
            for q_type, metrics in per_type_metrics.items():
                print(f"  Type '{q_type}': {metrics}")

            final_sample_records = sample_records
        else:
            # log only losses
            with open(log_csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                row = [
                    epoch,
                    f"{train_loss:.4f}",
                    f"{val_loss:.4f}",
                    "", "", "", "",
                    "", "", "",
                    "", "", "",
                    "", "", "", "", "",
                ]
                writer.writerow(row)
            print(f"[Epoch {epoch}] Train: {train_loss:.4f}, Val: {val_loss:.4f} (no heavy eval)")

        # save best checkpoint
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            ckpt_dir = os.path.join(args.output_dir, "best_model")
            os.makedirs(ckpt_dir, exist_ok=True)
            from src.utils import save_checkpoint
            save_checkpoint(model, processor, ckpt_dir, epoch)

    # final predictions
    if final_sample_records is not None:
        save_predictions_csv(
            final_sample_records,
            os.path.join(args.output_dir, "final_predictions.csv")
        )

    # plots
    plot_loss_curves(
        epoch_indices,
        train_losses_hist,
        val_losses_hist,
        os.path.join(args.output_dir, "loss_curve.png"),
    )
    if len(eval_epoch_indices) > 0:
        plot_metric_curve(
            eval_epoch_indices,
            f1_scores_hist,
            "F1-Score",
            os.path.join(args.output_dir, "metric_curve_F1.png"),
        )

    print("Done. Outputs in", args.output_dir)


if __name__ == "__main__":
    main()
