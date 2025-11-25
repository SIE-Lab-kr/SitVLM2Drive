# SitVLM2Drive: A Causal Reasoning QA Benchmark for Situational Awareness in Autonomous Driving
**SitVLM2Drive** is a multimodal benchmark dataset designed for autonomous vehicle (AV) perception, planning, and reasoning in complex real-world scenarios. It integrates rich scene-level intent annotations, object-level causal graphs, structured Q&A pairs, and safety-critical reasoning — aligned under complex real-world conditions.

[![Watch the video](https://img.youtube.com/vi/YVAGqxpPudw/0.jpg)](https://www.youtube.com/watch?v=YVAGqxpPudw)

---

## 📦 Dataset Overview

| Attribute              | Value                        |
|------------------------|------------------------------|
| Total Videos           | 495                          |
| Annotated Frames       | 10,250                       |
| QA Pairs               | 2,083,050                    |
| Unique Object Types    | 76                           |
| Causal Reasoning Types | Discovery, Association, Intervention, Counterfactual |
| AV Tasks Supported     | Perception, Prediction, Planning, Action |


🚗 Qualitative Scenarios
We provide four illustrative cases:
  Normal Scenario
  Missed Detection Scenario
  Out-of-Distribution Scenario
  Adversarial Attack Scenario

## 📁 Project Structure
```bash
SitLLM2Drive/
├── Sample of Dataset
├──   ├──JSON/ # Annotations into three folders called: data for all data, by_AV_Task, and by_AV_Task
│     │  ├── video_0001.json
│     │  ├── video_0002.json
│     └── ...
├──   frames/                        # Frame images
│     ├── video_0001/
│     │   ├── frame_000001.jpg
│     │   └── ...
│     └── video_0002/
├──   graphs/
│     ├── video_0001/
│     │   ├── frame_000001_diagram.png
│     │   ├── frame_000001_diagram.dot
│     │   └── ...
│     └── video_0002/
├── docs/                          # Extended documentation and visuals
│   ├── annotation_guide.pdf
│   ├── Supplementary Material– Dataset.pdf
├── figs/
│       ├── example.png
│       └── ...
└── multivlm-drive-vqa/
│     ├── models/
│     │  ├── internvl_vl.py
│     │  ├── llama_vl.py
│     │  ├── qwen_vl.py
│     │
│     └── utils/
│     │  ├── Annotator GUI
│     │  ├── Generating QA
│     │  ├── Generating_caption_maneuver
│     │  ├── Position --H Shape
│     │  ├── Creatinggraph.py
│     │  ├── utils.py
│     └
│     ├── train.py
│     └── metrics.py
│     ├── chatGPT_Eval.ipynb
│     └── data.py
└──
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
- `QA`: List of causal-based reasoning QA pairs
- `safe`: Safety status + rationale
- `Action Suggestions`: Recommended maneuver
- `Traffic Regulations Suggestions`: Road rule prompts

Object-Level are annotated with:
- obj_name, object_type, Bounding boxes or keypoints `boxes` or `point` coordinates
- Position: Relative spatial location
- Status
- Impact on safety: Affects / Requires Monitoring / Does Not Affect
- `Is_causal`: Cause / Effect

Supported Object Domains:
- **Vehicles** (moving, parked, turning, ...)
- **Road Users** (pedestrians, cyclists, ...)
- **Infrastructure** (traffic lights, signs, markings, ...)
- **Geometry** (intersections, lanes, medians, ...)
- **Hazards** (potholes, debris, ...)

  
example:
```json
{
  "Objects": [
    [
      "car<bb>500,300,560,360<bb>",
      {
        "obj_name": "car",
        "object_type": "Ego-Vehicle",
        "boxes": [500, 300, 560, 360],
        "Status": ["Moving", "Turning Left"],
        "Object_Safety": ["Affects Safety"],
        "position": ["In Intersection", "Left of Ego"],
        "Object_Causal": "ego<po>711,708<po>",
        "Causal_Relation": "Direct",
        "Is_causal": "Cause"
      }
    ],
    [
      "traffic light<bb>700,39,737,130<bb>",
      {
        "obj_name": "traffic light",
        "object_type": "Infrastructure",
        "boxes": [700, 39, 737, 130],
        "Status": ["Green"],
        "Object_Safety": ["Does Not Affect Safety"],
        "position": ["Above Intersection", "Ahead of Ego"],
        "Object_Causal": "ego<po>711,708<po>",
        "Causal_Relation": "Indirect",
        "Is_causal": "Effect"
      }
    ]
  ],

  "Graph_Edges": [
    ["traffic light<bb>700,39,737,130<bb>", "ego<po>711,708<po>", "Indirect"],
    ["car<bb>500,300,560,360<bb>", "ego<po>711,708<po>", "Direct"]
  ],

  "QA": [
    {
      "Q": "How should the ego vehicle behave given the current intersection?",
      "A": "1) Scene Safety: The environment is classified as 'unsafe' based on the safety indicator.\n2) Cause Analysis in condition is primarily due to: Intersection Congestion, Right-of-Way.\n3) Ego Motion: The current motion parameters are: speed = 0.0 MPH, steering angle = -1.2\u00b0.\n4) Vehicle Intent: goal: 'Turn left', maneuver: 'yield to oncoming traffic and wait to turn left when traffic in the oncoming lane is clear and make the left turn then continue down the block then stop at intersection and turns left and the stop light is green i am stopped at the light  i am waiting to turn left i turn left and after all cars in oncoming traffic either turn or keep straight', scene description: 'cars are coming in the opposite lane and while are waiting to turn left ... then the stop light is green cars are coming i turn left'.\n5) Object & Causal Analysis: Objects affecting safety: traffic light, car, car, traffic light, TS_Yield, traffic light, car, T-Intersection, crosswalk, crosswalk, car, car, car; Potentially affecting objects: pedestrian, pedestrian, TS_No_U_Turn, Manhole. Additionally, Causal relations: traffic light<bb>700,39,737,130<bb> -> ego<po>711,708<po> (relation: Direct (causal)), car<bb>600,317,661,362<bb> -> ego<po>711,708<po> (relation: Chain (causal)), car<bb>345,320,472,398<bb> -> ego<po>711,708<po> (relation: Chain (causal)), traffic light<bb>283,201,306,249<bb> -> ego<po>711,708<po> (relation: Direct (causal)), TS_Yield<bb>800,51,838,92<bb> -> ego<po>711,708<po> (relation: Confounder (causal)), traffic light<bb>1142,186,1180,257<bb> -> ego<po>711,708<po> (relation: Direct (causal)), car<bb>659,315,687,337<bb> -> ego<po>711,708<po> (relation: Chain (causal)), car<bb>408,332,583,429<bb> -> ego<po>711,708<po> (relation: Chain (causal)), car<bb>680,313,698,331<bb> -> ego<po>711,708<po> (relation: Chain (causal)), car<bb>705,300,721,317<bb> -> ego<po>711,708<po> (relation: Chain (causal)).\n6) Traffic & Action Guidance: action: 'Yield', traffic regulations: 'TS_Yield'.\n7) Conclusion: Given the unsafe condition, proceed with heightened caution.",
      "Type": "CCot",
      "Task": "Planning-Based",
      "question_task": "Context-Based",
      "AV_Task": "plan",
      "scene_scenario": "Normal"
    },
    {
      "Q": "What is the causal relationship between the ego vehicle and the oncoming car?",
      "A": "The oncoming cars is directly influencing the ego vehicle’s decision to wait before turning left. causal relationship graph car<bb>659,315,687,337<bb> -> ego<po>711,708<po> (relation: Chain (causal)), car<bb>408,332,583,429<bb> -> ego<po>711,708<po> (relation: Chain (causal)), car<bb>680,313,698,331<bb> -> ego<po>711,708<po> (relation: Chain (causal)), car<bb>705,300,721,317<bb> -> ego<po>711,708<po> (relation: Chain (causal)).",
      "Type": "Association",
      "Task": "Planning-Based",
      "question_task": "Explanation-Based",
      "AV_Task": "prediction",
      "scene_scenario": "Normal"
    }
  ]
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

## 🧠 Causal Graph Visualization

SitVLM2Drive does not only provide bounding boxes and Q&A pairs – it also encodes **explicit causal structure** between objects, scene context, and the ego vehicle.

### Single-Frame Example

The figure below shows one frame with:

- **Color-coded object outlines** by *Object_Safety*  
  - Red – *Affects Safety*  
  - Orange – *Potentially Affect Safety*  
  - Blue – *Requires Monitoring*  
  - Green – *Does Not Affect Safety*  
- **Ego vehicle** highlighted with a **thicker outline**, whose color reflects the scene-level safety label  
  - Green – scene labeled as *safe*  
  - Red – scene labeled as *unsafe*  
- **Directed arrows** between objects, color-coded by **Causal_Relation**  
  - Red – *Direct*  
  - Orange – *Chain*  
  - Purple – *Confounder*  
  - Green – *Correlations*  
- Object labels optionally include **importance ranking** (high / medium / low), which reflects the driver’s attention priority.

<p align="center">
  <img src="Sample of Dataset/graphs/test0001/annotated_frames/0000_frame_0000.jpg" alt="Single-frame causal graph visualization" width="80%">
</p>

### Multi-Frame Causal Strip

To illustrate temporal evolution, we also render a **sequence of annotated frames** as a horizontal strip.  
This allows you to see how the causal graph and safety-critical objects change as the ego vehicle approaches an intersection.

<p align="center">
  <img src="Sample of Dataset/graphs/test0001/test0001_annotated_strip.png" alt="Temporal strip of frames with causal graph overlays and shared legend" width="100%">
</p>

These visualizations are generated directly from the JSON annotations in:

```bash
Sample of Dataset/
├── data/        # JSON annotations (per video)
├── frames/      # Raw frame images (per video)
└── graphs/      # Auto-generated diagrams and annotated frames
    └── video_xxxx/
        ├── annotated_frames/
            └── 0000_frame_0001.jpg #image annotated with causal graph
        ├── 0000_frame_0000_diagram.dot
        ├── 0000_frame_0000_diagram.png
        ├── ...
        └── video_xxxx_causal_strip_sample.png
```
## 🔐 License

### Data Access Requirements
SitVLM2Drive is based on a curated subset of the Honda Research Institute – Advice Dataset (HAD). Due to licensing restrictions, the original HAD dataset cannot be redistributed through this repository. Users must download the HAD dataset directly from the Honda Research Institute (HRI) under their terms of use.

### Eligibility Requirements
According to HRI’s licensing terms:
- The HAD dataset is available for non-commercial research use only.
- Users must be affiliated with a university.
- Requests must be submitted using an official university email address.

### How to Obtain the HAD Dataset
To utilize SitVLM2Drive, you must first acquire the HAD dataset through one of the official HRI channels:
- **Official Dataset Page:** [HAD Dataset](https://usa.honda-ri.com/had)
- **Direct Dataset Request Form:** [Request Form](https://usa.honda-ri.com/dataset-request-form?dataset=had)

## SitVLM2Drive Licensing
The annotations, causal graphs, and QA pairs associated with SitVLM2Drive are provided under a non-commercial research license since they are derived from the HAD dataset. 

You may use, modify, and extend SitVLM2Drive only for non-commercial academic research purposes.

For those affiliated with a university, an alternative request link for our dataset is available here: [Request Link](https://docs.google.com/forms/d/e/1FAIpQLSdUrMu3t3zgc4NSzA7rJbWeQDrGYR6KDMHQQEIv31pbLWj2JA/viewform?usp=publish-editor).

## 📚 Citation

If you use this dataset in your work, please cite: Will editing after Acceptance


```bibtex 
@misc{SitLLM2Drive2025,
  title={SitVLM2Drive: A Causal Reasoning QA Benchmark for Situational Awareness in Autonomous Driving},
  author={Our Name et al.},
  year={2025},
  url={https://github.com/SIE-Lab-kr/SitLLM2Drive-}
}
