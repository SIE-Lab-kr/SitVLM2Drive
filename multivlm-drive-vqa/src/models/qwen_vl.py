import torch
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor


def build_qwen_vl(model_id=None):
    if model_id is None:
        model_id = "Qwen/Qwen2.5-VL-7B-Instruct"

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16 if device.type == "cuda" else torch.float32,
        device_map=None,
    )
    processor = AutoProcessor.from_pretrained(model_id)

    def collate_fn_training(batch):
        images = [b["image"] for b in batch]
        questions = [b["question"] for b in batch]
        answers = [b["answer"] for b in batch]

        messages_full = []
        messages_prompt = []
        for q, a in zip(questions, answers):
            user_content = [
                {"type": "image"},
                {"type": "text", "text": f"Question: {q}"},
            ]
            messages_full.append(
                [
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": f"Answer: {a}"},
                ]
            )
            messages_prompt.append(
                [
                    {"role": "user", "content": user_content},
                ]
            )

        texts_full = [
            processor.apply_chat_template(
                msg, tokenize=False, add_generation_prompt=False
            )
            for msg in messages_full
        ]
        texts_prompt = [
            processor.apply_chat_template(
                msg, tokenize=False, add_generation_prompt=True
            )
            for msg in messages_prompt
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

        pad_id = processor.tokenizer.pad_token_id
        prompt_tokens = processor.tokenizer(
            texts_prompt,
            padding=True,
            truncation=True,
            max_length=4096,
            return_tensors="pt",
        )
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

        messages_prompt = []
        for q in questions:
            user_content = [
                {"type": "image"},
                {"type": "text", "text": f"Question: {q}"},
            ]
            messages_prompt.append(
                [
                    {"role": "user", "content": user_content},
                ]
            )

        texts_prompt = [
            processor.apply_chat_template(
                msg, tokenize=False, add_generation_prompt=True
            )
            for msg in messages_prompt
        ]

        enc = processor(
            images=images,
            text=texts_prompt,
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
