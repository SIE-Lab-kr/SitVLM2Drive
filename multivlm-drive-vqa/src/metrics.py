from typing import List, Dict, Tuple

from rouge_score import rouge_scorer
from pycocoevalcap.bleu.bleu import Bleu
from pycocoevalcap.cider.cider import Cider
from bert_score import score as bertscore_score
from sklearn.metrics import accuracy_score, precision_recall_fscore_support


def compute_metrics(predictions: List[str], references: List[str]) -> Dict[str, float]:
    """
    BLEU, ROUGE, CIDEr, BERTScore, Accuracy, Precision, Recall, F1.
    """
    bleu_scorer = Bleu(4)
    cider_scorer = Cider()

    gts = {i: [ref] for i, ref in enumerate(references)}
    res = {i: [pred] for i, pred in enumerate(predictions)}

    try:
        bleu_scores, _ = bleu_scorer.compute_score(gts, res)
    except Exception:
        bleu_scores = [0, 0, 0, 0]

    try:
        cider_score, _ = cider_scorer.compute_score(gts, res)
    except Exception:
        cider_score = 0.0

    try:
        scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
        rouge_agg = {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}
        for pred, ref in zip(predictions, references):
            scores = scorer.score(ref, pred)
            rouge_agg["rouge1"] += scores["rouge1"].fmeasure
            rouge_agg["rouge2"] += scores["rouge2"].fmeasure
            rouge_agg["rougeL"] += scores["rougeL"].fmeasure
        n = max(len(predictions), 1)
        for k in rouge_agg:
            rouge_agg[k] /= n
    except Exception:
        rouge_agg = {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}

    try:
        P, R, F1 = bertscore_score(predictions, references, lang="en", rescale_with_baseline=True)
        bert_p = P.mean().item() * 100.0
        bert_r = R.mean().item() * 100.0
        bert_f1 = F1.mean().item() * 100.0
    except Exception:
        bert_p = bert_r = bert_f1 = 0.0

    try:
        accuracy = accuracy_score(references, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            references, predictions, average="weighted", zero_division=0
        )
    except Exception:
        accuracy = precision = recall = f1 = 0.0

    return {
        "BLEU-1": float(bleu_scores[0]),
        "BLEU-2": float(bleu_scores[1]),
        "BLEU-3": float(bleu_scores[2]),
        "BLEU-4": float(bleu_scores[3]),
        "ROUGE-1": rouge_agg["rouge1"] * 100.0,
        "ROUGE-2": rouge_agg["rouge2"] * 100.0,
        "ROUGE-L": rouge_agg["rougeL"] * 100.0,
        "CIDEr": float(cider_score),
        "BERTScore_P": bert_p,
        "BERTScore_R": bert_r,
        "BERTScore_F1": bert_f1,
        "Accuracy": float(accuracy),
        "Precision": float(precision),
        "Recall": float(recall),
        "F1-Score": float(f1),
    }


def evaluate_by_type(
    sample_records: List[Tuple[str, str, str, str, str]]
) -> Dict[str, Dict[str, float]]:
    """
    sample_records: list of (img_path, question, ref, pred, q_type)
    """
    type_groups = {}
    for img_path, question, ref, pred, q_type in sample_records:
        if q_type not in type_groups:
            type_groups[q_type] = {"predictions": [], "references": []}
        type_groups[q_type]["predictions"].append(pred.strip() if pred else "")
        type_groups[q_type]["references"].append(ref.strip() if ref else "")

    out = {}
    for q_type, group in type_groups.items():
        out[q_type] = compute_metrics(group["predictions"], group["references"])
    return out
