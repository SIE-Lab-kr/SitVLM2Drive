# SitLLM2Drive

**SitLLM2Drive** is a dataset for autonomous vehicle scene understanding, featuring:
- 10,000+ richly annotated frames
- Object-level causal graphs
- Scene-level planning and safety metadata
- Over 2 million QA pairs for driving scenarios

## 📁 Dataset Structure
dataset/

├── video_0001.json # scene annotations

frames/

├── video_0001/ # corresponding images

## ✍️ Annotations
- **Caption**: Free-text scene summary
- **Maneuver**: Vehicle's goal (e.g. "Turn left")
- **Graph**: Causal object relationships

See `annotations_format.md` for full schema.


## 📜 License
[MIT License](LICENSE)

## 🔧 Scripts
Use tools in `scripts/` for analysis and statistics extraction.

## 📊 Statistics
- 495 videos
- 10k frames
- 2.08M Q&A pairs
- 76 unique object types

## 💡 Applications
- Causal reasoning in traffic
- Visual question answering for AVs


**Tasks**: Perception, Planning, Action Suggestions, Planning under uncertainty, Causal Reasoning, etc

**Modality**: Vision + Text + Graphs  

**Safety-Critical**: 24% of scenarios  
