# Multi-VLM Drive VQA (LLaMA, Qwen, InternVL)

This repo trains and evaluates **Vision-Language Models (VLMs)** on a Sit2VLMDrive dataset driving
question–answering dataset with video frames (`frames/`) and annotations (`json/`).

Supported backends:

- **LLaMA Vision** ( `meta-llama/Llama-3.2-11B-Vision`)
- **Qwen2.5-VL** (`Qwen/Qwen2.5-VL-7B-Instruct`)
- **InternVL** ( `OpenGVLab/InternVL3-1B-hf`)

Common features:

- Shared dataset loader (`Sit2VLMDrive`)
- Evaluation metrics:
  - BLEU-1...4, ROUGE-1/2/L, CIDEr
  - BERTScore (P/R/F1)
  - Accuracy, Precision, Recall, F1-Score
- Evaluation at epochs **1, 5, 10** only (configurable)
- Logs to CSV + per-epoch predictions + simple loss/F1 plots

---

```bash
git clone https://github.com/<Our-username>/multivlm-drive-vqa.git
cd multivlm-drive-vqa

# Create environment (example with conda)
conda create -n vlm-env python=3.12 -y
conda activate vlm-env

pip install -r requirements.txt


<DATA_ROOT>/
├─ frames/
│   ├─ video_1/
│   │   ├─ frame_0001.jpg
│   │   └─ ...
│   └─ video_2/
│       └─ ...
└─ json/
    ├─ video_1.json
    └─ video_2.json


[
  {
    "image_id": "frame_0001.jpg",
    "QA": [
      {
        "Q": "What is in front of the car?",
        "A": "A pedestrian is crossing.",
        "Task": "risk_assessment",
        "Type": "CCot"
      }
    ]
  }
]


3. Training

Basic usage:

python train.py \
  --data-root /home/USER/set2Drive \
  --model-type llama \
  --model-id meta-llama/Llama-3.2-11B-Vision \
  --output-dir result_llama


Other backends:

# Qwen2.5-VL
python train.py \
  --data-root /home/USER/set2Drive \
  --model-type qwen \
  --model-id Qwen/Qwen2.5-VL-7B-Instruct \
  --output-dir result_qwen

# InternVL (HF 1B model – good starting point)
python train.py \
  --data-root /home/USER/set2Drive \
  --model-type internvl \
  --model-id OpenGVLab/InternVL3-1B-hf \
  --output-dir result_internvl


Useful flags:

--epochs (default 10)

--batch-size (default 1 – increase carefully)

--eval-epochs (default 1 5 10)

--q-type-filter (e.g. CCot)

Example:

python train.py \
  --data-root /home/USER/set2Drive \
  --model-type qwen \
  --model-id Qwen/Qwen2.5-VL-7B-Instruct \
  --q-type-filter CCot \
  --epochs 10 \
  --eval-epochs 1 5 10 \
  --output-dir result_qwen_ccot

4. Outputs

Each run writes into --output-dir, e.g. result_qwen_ccot/:

training_eval_log.csv – per-epoch logs

predictions_epoch_1.csv, predictions_epoch_5.csv, predictions_epoch_10.csv

final_predictions.csv – last evaluated epoch

loss_curve.png – train/val loss

metric_curve_F1.png – F1-score vs evaluated epochs

best_model/checkpoint_epoch_X/ – best checkpoint (lowest validation loss)

5. Notes

For very large models (LLaMA Vision 11B, Qwen2.5-VL-7B, InternVL3.5-1B),
you may need 4-bit quantization + LoRA and multiple GPUs.

This repo is structured so you can plug in your own fine-tuning tricks
(QLoRA, DDP, deepspeed, FSDP, etc.) inside the model-specific files in src/models/.
