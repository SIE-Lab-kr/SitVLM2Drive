# SitLLM2Drive: Scene-Intent-Task for Causal Planning in AVs

SitLLM2Drive is a multi-modal dataset for autonomous vehicle (AV) research. It integrates scene-level planning context, object-level causal graphs, and high-level reasoning questions to evaluate perception, planning, and safety under complex real-world conditions.

## 🌐 Dataset Overview

- **495** urban driving videos
- **10,000+** annotated frames
- **2.08 million** QA pairs (reasoning & planning tasks)
- **76** unique object types
- **24%** scenes labeled as safety-critical

## 📁 Dataset Structure

SitLLM2Drive/
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── dataset/                       # Annotations
│   ├── video_0001.json
│   ├── video_0002.json
│   └── ...
├── frames/                        # Frame images
│   ├── video_0001/
│   │   ├── frame_000001.jpg
│   │   └── ...
│   └── video_0002/
├── scripts/                       # Utility and analysis tools
│   ├── extract_statistics.py
│   └── visualize_annotations.py
├── docs/                          # Extended documentation and visuals
│   ├── annotation_guide.pdf
│   ├── dataset_card.md
│   └── figs/
│       ├── scene_example.jpg
│       └── graph_example.jpg
└── annotations_format.md         # JSON schema and semantic descriptions



## 🔍 Annotation Levels

- **Scene-Level**: Caption, maneuver, cause, goal, safety, regulation, and action suggestions.
- **Object-Level**: Entities (vehicles, signs, pedestrians, etc.) with positions, safety impact, causal role, and semantic tags.

# Annotation Format: SitLLM2Drive

Each frame-level JSON contains:

- `image_id`: Frame file name (e.g., "frame_000012.jpg")
- `caption`: Free-text summary
- `maneuver`: Intent/behavior (e.g., "Turn left")
- `cause`: List of contributing factors
- `graph`: Semantic object-level graph
- `QA`: List of planning-based reasoning QA pairs
- `safe`: Safety assessment
- `Action Suggestions`: Recommended maneuver
- `Traffic Regulations Suggestions`: Road rule prompts

## Graph Node Schema

Each node follows the format:
```json
[
  "object_tag<bb>xmin,ymin,xmax,ymax<bb>",
  {
    "obj_name": "car",
    "boxes": [xmin, ymin, xmax, ymax],
    "importance_ranking": "high",
    "Status": [...],
    ...
  }
]

## Graph Edges

Edges denote directed causal relationships between objects or between object and ego:

[
  ["traffic light<bb>700,39,737,130<bb>", "ego<po>711,708<po>", "Direct"]
]


## 📊 Tasks Supported

- Visual Reasoning (Discovery, Interventions, Associations)
- Scene Planning under Uncertainty
- Causal Analysis & Prediction
- Traffic Policy Compliance
- Visual QA for Driving

## 🔐 License

Released under the [MIT License](LICENSE).

## 📚 Citation

If you use this dataset in your work, please cite:

```bibtex
@misc{SitLLM2Drive2025,
  title={SitLLM2Drive: Scene-Intent-Task Dataset for Causal Planning in Autonomous Driving},
  author={Your Name et al.},
  year={2025},
  url={https://github.com/your-org/SitLLM2Drive}
}
