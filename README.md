# SitLLM2Drive: Scene-Intent-Task for Causal Planning in AVs
**SitVLM2Drive** is a multimodal benchmark dataset designed for autonomous vehicle (AV) perception, planning, and reasoning in complex real-world scenarios. It integrates rich scene-level intent annotations, object-level causal graphs, structured Q&A pairs, and safety-critical reasoning — aligned under complex real-world conditions.

[![Watch Demo]([docs/figs/sample_frame.jpg)](https://www.youtube.com/watch?v=dQw4w9WgXcQ](https://github.com/SIE-Lab-kr/SitLLM2Drive-/blob/main/Videos/CCoT.mp4))

---

## 📦 Dataset Overview

| Attribute              | Value                        |
|------------------------|------------------------------|
| Total Videos           | 495                          |
| Annotated Frames       | 10,250                       |
| QA Pairs               | 2,083,050                    |
| Unique Object Types    | 76                           |
| Safety-Critical Scenes | 24%                          |
| Causal Reasoning Types | Discovery, Association, Intervention, Counterfactual |
| AV Tasks Supported     | Perception, Prediction, Planning, Action |


## 📁 Dataset Structure
```bash
SitLLM2Drive/
├── JSON/                       # Annotations
│   ├── video_0001.json
│   ├── video_0002.json
│   └── ...
├── frames/                        # Frame images
│   ├── video_0001/
│   │   ├── frame_000001.jpg
│   │   └── ...
│   └── video_0002/
├── docs/                          # Extended documentation and visuals
│   ├── annotation_guide.pdf
├── figs/
│       ├── scene_example.jpg
│       └── graph_example.jpg
└── annotations_format.md         # JSON schema and semantic descriptions
```
## 🔍 Annotation Levels

- **Scene-Level**: Caption, maneuver, cause, goal, safety, regulation, and action suggestions.
- **Object-Level**: Entities (vehicles, signs, pedestrians, etc.) with positions, safety impact, causal role, and semantic tags.

# Annotation Format: SitLLM2Drive

Each Scene-Level contains:

- `image_id`: Frame file name (e.g., "frame_000012.jpg")
- `caption`: Free-text summary
- `maneuver`: Intent/behavior (e.g., "Turn left")
- `cause`: List of contributing factors
- `goal-oriented`: Long-term AV objective
- `QA`: List of planning-based reasoning QA pairs
- `safe`: Safety status + rationale
- `Action Suggestions`: Recommended maneuver
- `Traffic Regulations Suggestions`: Road rule prompts

Object-Level are annotated with:
- obj_name, object_type, Bounding boxes or keypoints `boxes` or `point` coordinates
- Position: Relative spatial location
- Status
- Impact on safety: Affects / Requires Monitoring / Does Not Affect
- `Is_causal`: Cause / Effect (graph-linked)

Supported Object Domains:
- **Vehicles** (moving, parked, turning)
- **Road Users** (pedestrians, cyclists)
- **Infrastructure** (traffic lights, signs, markings)
- **Geometry** (intersections, lanes, medians)
- **Hazards** (potholes, debris)

  
Each node follows the format:
```json
[
  "object_tag<bb>xmin,ymin,xmax,ymax<bb>",
  {
    "obj_name": "car",
    "object_type": "Ego-Vehicle",
    "boxes": [xmin, ymin, xmax, ymax],
    "Status": [...],
    "Object_Safety": [...],
    "position": [...],
    "Object_Causal": "ego<po>711,708<po>",
    "Causal_Relation": "Direct",
    "Is_causal": "Cause"
  }
]

## Graph Edges

Edges denote directed causal relationships between objects or between object and ego:

[
  ["traffic light<bb>700,39,737,130<bb>", "ego<po>711,708<po>", "Direct"]
]

## QA
{
  "Q": "How should the ego vehicle behave given the current intersection?",
  "A": "The ego vehicle should yield to oncoming traffic before turning left...",
  "Type": "CCot",
  "Task": "Planning-Based",
  ...
}

```

## 📊 Tasks Supported

- Visual Reasoning (Discovery, Associations, Interventions, Counterfactual )
- Scene Planning under Uncertainty
- Causal Analysis & Prediction
- Traffic Policy Compliance
- Visual QA for Driving (Planning, Prediction, Regulation, etc..)
- Safety status + rationale
- Scene Understanding & Captioning
- Intent & Maneuver Prediction


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
