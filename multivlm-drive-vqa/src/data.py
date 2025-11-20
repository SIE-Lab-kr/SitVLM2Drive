import os
import json
from glob import glob
from typing import List, Optional

from PIL import Image
from torch.utils.data import Dataset


class DrivingVideoDataset(Dataset):
    def __init__(self, root_dir: str, q_type_filter: Optional[List[str]] = None):
        """
        root_dir: path containing 'frames/' and 'json/'.
        q_type_filter: list of question types to include. If None, include all.
        """
        self.root_dir = root_dir
        self.frames_dir = os.path.join(root_dir, "frames")
        self.json_dir = os.path.join(root_dir, "json")
        self.json_files = glob(os.path.join(self.json_dir, "*.json"))

        self.samples = []  # (img_path, question, answer, task, q_type)

        for json_path in self.json_files:
            video_name = os.path.splitext(os.path.basename(json_path))[0]
            with open(json_path, "r", encoding="utf-8") as f:
                data_list = json.load(f)

            for entry in data_list:
                img_id = entry["image_id"]
                img_path = os.path.join(self.frames_dir, video_name, img_id)
                qa_list = entry.get("QA", [])

                # if no QA, optionally keep as no_type
                if not qa_list:
                    if q_type_filter is None or "no_type" in (q_type_filter or []):
                        self.samples.append((img_path, "", "", "no_task", "no_type"))
                    continue

                for qa in qa_list:
                    question = qa.get("Q", "")
                    answer = qa.get("A", "")
                    task = qa.get("Task", "no_task")
                    q_type = qa.get("Type", "no_type")

                    if q_type_filter is not None and q_type not in q_type_filter:
                        continue

                    self.samples.append((img_path, question, answer, task, q_type))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, question, answer, task, q_type = self.samples[idx]
        image = Image.open(img_path).convert("RGB")
        return {
            "image": image,
            "question": question,
            "answer": answer,
            "task": task,
            "q_type": q_type,
            "path": img_path,
        }
