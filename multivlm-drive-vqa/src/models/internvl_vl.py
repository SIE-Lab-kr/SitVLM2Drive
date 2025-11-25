import torch
from transformers import AutoModelForImageTextToText, AutoProcessor


def build_internvl_vl(model_id=None):
    """
    Tested with: OpenGVLab/InternVL3_5-8B (HF style)
    For InternVL3.5 HF models, make sure they are compatible with AutoModelForImageTextToText.
    """
    if model_id is None:
        model_id = "OpenGVLab/InternVL3_5-8B"

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = AutoModelForImageTextToText.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16 if device.type == "cuda" else torch.float32,
        low_cpu_mem_usage=True,
    )
    processor = AutoProcessor.from_pretrained(model_id)

    def collate_fn_training(batch):
        messages_batch = []
        for sample in batch:
            img = sample["image"]
            q = sample["question"]
            a = sample["answer"]

            conv = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": img},
                        {"type": "text", "text": f"Question: {q}"},
                    ],
                },
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": f"Answer: {a}"},
                    ],
                },
            ]
            messages_batch.append(conv)

        inputs = processor.apply_chat_template(
            messages_batch,
            add_generation_prompt=False,
            tokenize=True,
            padding=True,
            return_tensors="pt",
            return_dict=True,
        )

        input_ids = inputs["input_ids"]
        labels = input_ids.clone()
        pad_id = processor.tokenizer.pad_token_id
        labels[labels == pad_id] = -100

        cfg = model.config
        if hasattr(cfg, "image_token_id") and cfg.image_token_id is not None:
            labels[labels == cfg.image_token_id] = -100

        inputs["labels"] = labels
        return inputs

    def collate_fn_evaluation(batch):
        messages_batch = []
        questions = []
        answers = []
        tasks = []
        q_types = []
        paths = []

        for sample in batch:
            img = sample["image"]
            q = sample["question"]

            conv = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": img},
                        {"type": "text", "text": f"Question: {q}"},
                    ],
                }
            ]
            messages_batch.append(conv)

            questions.append(q)
            answers.append(sample["answer"])
            tasks.append(sample["task"])
            q_types.append(sample["q_type"])
            paths.append(sample["path"])

        encoding = processor.apply_chat_template(
            messages_batch,
            add_generation_prompt=True,
            tokenize=True,
            padding=True,
            return_tensors="pt",
            return_dict=True,
        )

        return {
            "encoding": encoding,
            "questions": questions,
            "answers": answers,
            "tasks": tasks,
            "q_types": q_types,
            "paths": paths,
        }

    return model, processor, collate_fn_training, collate_fn_evaluation
