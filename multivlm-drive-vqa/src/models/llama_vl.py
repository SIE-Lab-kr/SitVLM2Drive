import torch
from transformers import MllamaForConditionalGeneration, AutoProcessor


def build_llama_vl(model_id=None):
    """
    Returns:
      model, processor, collate_fn_training, collate_fn_evaluation
    """
    if model_id is None:
        model_id = "meta-llama/Llama-3.2-11B-Vision"

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = MllamaForConditionalGeneration.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16 if device.type == "cuda" else torch.float32,
        device_map=None,   # simple .to(device) later
    )
    processor = AutoProcessor.from_pretrained(model_id)

    def collate_fn_training(batch):
        images = [b["image"] for b in batch]
        questions = [b["question"] for b in batch]
        answers = [b["answer"] for b in batch]

        texts_full = [
            f"<|image|><|begin_of_text|>Question: {q}\nAnswer: {a}"
            for q, a in zip(questions, answers)
        ]
        texts_prompt = [
            f"<|image|><|begin_of_text|>Question: {q}\nAnswer:"
            for q in questions
        ]

        enc_full = processor(
            images=images,
            text=texts_full,
            padding=True,
            truncation=True,
            max_length=4096,
            return_tensors="pt",
        )
        input_ids = enc_full["input_ids"]
        labels = input_ids.clone()

        prompt_tokens = processor.tokenizer(
            texts_prompt,
            add_special_tokens=False,
            padding=True,
            truncation=True,
            max_length=4096,
            return_tensors="pt",
        )
        pad_id = processor.tokenizer.pad_token_id
        prompt_lengths = (prompt_tokens["input_ids"] != pad_id).sum(dim=1)

        for i, p_len in enumerate(prompt_lengths):
            labels[i, :p_len] = -100
        labels[labels == pad_id] = -100

        enc_full["labels"] = labels
        return enc_full

    def collate_fn_evaluation(batch):
        images = [b["image"] for b in batch]
        questions = [b["question"] for b in batch]
        answers = [b["answer"] for b in batch]
        tasks = [b["task"] for b in batch]
        q_types = [b["q_type"] for b in batch]
        paths = [b["path"] for b in batch]

        prompts = [
            f"<|image|><|begin_of_text|>Question: {q}\nAnswer:"
            for q in questions
        ]

        enc = processor(
            images=images,
            text=prompts,
            padding=True,
            truncation=True,
            max_length=4096,
            return_tensors="pt",
        )

        return {
            "encoding": enc,
            "questions": questions,
            "answers": answers,
            "tasks": tasks,
            "q_types": q_types,
            "paths": paths,
        }

    return model, processor, collate_fn_training, collate_fn_evaluation
