import os
import json
import random

import networkx as nx
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torch.nn.functional as F

from torch_geometric.data import Data
from torch_geometric.loader import DataLoader
from torch_geometric.nn import (
    GCNConv,
    SAGEConv,
    GINConv,
    GATConv,
    TransformerConv,
    global_mean_pool
)

from torchvision import models, transforms
from PIL import Image


# ============================================================
# Utility: safety status parsing
# ============================================================

def determine_safety_status(safety_status):
    """Determine safety status based on frame['safe'] string."""
    if not isinstance(safety_status, str):
        safety_status = str(safety_status)

    s = safety_status.lower()
    if "unsafe" in s or "no" in s:
        return "unsafe"
    elif "safe" in s or "yes" in s:
        return "safe"
    else:
        return None


# ============================================================
# Graph construction (with semantic groups and flags)
# ============================================================

def build_graph_from_categories_and_semantics(
    categories,
    safety_label,
    goal_text,
    action_text,
    traffic_text,
    flags
):
    """
    Build and return a NetworkX DiGraph from:
      - object categories (nodes from the JSON 'graph')
      - scene-level semantics: goal, action suggestions, traffic regulations
    Flags control ablation of semantic groups.
    """
    include_importance = flags.get("include_importance", True)
    include_status = flags.get("include_status", True)
    include_safety = flags.get("include_safety", True)
    include_position = flags.get("include_position", True)
    include_goal = flags.get("include_goal", True)
    include_action = flags.get("include_action", True)
    include_traffic = flags.get("include_traffic", True)
    include_causal = flags.get("include_causal", True)

    G = nx.DiGraph()

    # Central SAFE node
    safe_color = "green" if safety_label == "safe" else "red"
    G.add_node(
        "SAFE",
        subset=0,
        label="Ego",
        color=safe_color
    )

    # Object / category structure
    for category, objects in categories.items():
        # Category node
        G.add_node(
            category,
            subset=1,
            label=category,
            color="teal"
        )
        G.add_edge("SAFE", category)

        for obj_name, details in objects.items():
            if isinstance(obj_name, str) and obj_name.lower() == "ego":
                continue

            # Base object node
            G.add_node(
                obj_name,
                subset=2,
                label=obj_name,
                color="gray"
            )
            G.add_edge(category, obj_name)

            # Status node
            if include_status and details.get("status", ""):
                status_node = f"{obj_name}_status"
                G.add_node(
                    status_node,
                    subset=3,
                    label=details["status"],
                    color="lightgray"
                )
                G.add_edge(obj_name, status_node)

            # Position node
            if include_position and details.get("position", ""):
                position_node = f"{obj_name}_position"
                G.add_node(
                    position_node,
                    subset=3,
                    label=details["position"],
                    color="lightblue"
                )
                G.add_edge(obj_name, position_node)

            # Importance node
            if include_importance and details.get("importance", ""):
                importance_node = f"{obj_name}_importance"
                G.add_node(
                    importance_node,
                    subset=3,
                    label=details["importance"],
                    color="gold"
                )
                G.add_edge(obj_name, importance_node)

            # Object_Safety node
            if include_safety and details.get("safety", ""):
                safety_node = f"{obj_name}_safety"
                G.add_node(
                    safety_node,
                    subset=3,
                    label=details["safety"],
                    color="red"
                )
                G.add_edge(obj_name, safety_node)

            # Causal node
            if include_causal and details.get("causal_info", ""):
                causal_node = f"{obj_name}_causal"
                G.add_node(
                    causal_node,
                    subset=3,
                    label=details["causal_info"],
                    color="brown"
                )
                G.add_edge(obj_name, causal_node)

    # Scene-level semantic nodes (goal / action / regulations)
    if include_goal and isinstance(goal_text, str) and goal_text.strip():
        G.add_node(
            "goal_oriented",
            subset=4,
            label=goal_text,
            color="purple"
        )
        G.add_edge("SAFE", "goal_oriented")

    if include_action and isinstance(action_text, str) and action_text.strip():
        G.add_node(
            "action_suggestions",
            subset=4,
            label=action_text,
            color="orange"
        )
        G.add_edge("SAFE", "action_suggestions")

    if include_traffic and isinstance(traffic_text, str) and traffic_text.strip():
        G.add_node(
            "traffic_reg_suggestions",
            subset=4,
            label=traffic_text,
            color="green"
        )
        G.add_edge("SAFE", "traffic_reg_suggestions")

    return G


def frame_to_graph_data(frame, flags):
    """
    Convert a single frame (from JSON) into a PyG Data object
    (graph only, no image yet), with ablation flags.
    Returns Data or None if label can't be determined.
    """
    safety_status = determine_safety_status(frame.get("safe", ""))
    if safety_status is None:
        return None  # skip frames with unknown label

    # Scene-level text fields
    goal_text = frame.get("goal-oriented", "")
    action_text = frame.get("Action Suggestions", "")
    traffic_text = frame.get("Traffic Regulations Suggestions", "")

    # Build categories structure from nodes
    categories = {}
    if "graph" not in frame or "nodes" not in frame["graph"]:
        return None

    for node in frame["graph"]["nodes"]:
        if len(node) != 2:
            continue

        node_id, attributes = node
        object_type = attributes.get("object_type", "Unknown")
        obj_name = attributes.get("obj_name", "Unknown")

        # Semantic fields for this object
        status_list = attributes.get("Status", [])
        if isinstance(status_list, list):
            status = ", ".join(status_list)
        else:
            status = str(status_list)

        position_list = attributes.get("position", [])
        if isinstance(position_list, list):
            position = ", ".join(position_list)
        else:
            position = str(position_list)

        importance = attributes.get("importance_ranking", "")
        object_safety_list = attributes.get("Object_Safety", [])
        if isinstance(object_safety_list, list):
            object_safety = ", ".join(object_safety_list)
        else:
            object_safety = str(object_safety_list)

        # Causal fields
        object_causal = attributes.get("Object_Causal", "") or attributes.get("object_causal", "")
        causal_relation = attributes.get("Causal_Relation", "")
        is_causal = attributes.get("Is_causal", "")

        causal_parts = []
        if object_causal:
            causal_parts.append(object_causal)
        if causal_relation:
            causal_parts.append(causal_relation)
        if is_causal:
            causal_parts.append(is_causal)
        causal_info = " | ".join(causal_parts)

        if object_type not in categories:
            categories[object_type] = {}

        categories[object_type][obj_name] = {
            "status": status,
            "position": position,
            "importance": importance,
            "safety": object_safety,
            "causal_info": causal_info
        }

    # Build NetworkX graph with scene semantics & flags
    G = build_graph_from_categories_and_semantics(
        categories,
        safety_label=safety_status,
        goal_text=goal_text,
        action_text=action_text,
        traffic_text=traffic_text,
        flags=flags
    )

    # Convert to PyG Data
    data_obj = graph_to_data(G, safety_status)
    return data_obj


def graph_to_data(G, label):
    """
    Convert a NetworkX graph into a PyTorch Geometric Data object.

    Node features:
      [ subset,
        in_degree,
        out_degree,
        is_SAFE,
        is_category,
        is_object,
        is_status_node,
        is_position_node,
        is_importance_node,
        is_safety_node,
        is_causal_node,
        is_goal_node,
        is_action_node,
        is_traffic_node ]

    Label: 1 for safe, 0 for unsafe.
    """
    node_list = list(G.nodes())
    node_index = {node: i for i, node in enumerate(node_list)}

    # Edges: undirected (add both directions)
    edges = []
    for u, v in G.edges():
        ui = node_index[u]
        vi = node_index[v]
        edges.append([ui, vi])
        edges.append([vi, ui])

    if edges:
        edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    else:
        edge_index = torch.empty((2, 0), dtype=torch.long)

    x_list = []
    for node in node_list:
        attrs = G.nodes[node]
        subset = float(attrs.get("subset", 0))
        in_deg = float(G.in_degree(node))
        out_deg = float(G.out_degree(node))

        name_str = str(node)

        is_safe_node = 1.0 if name_str == "SAFE" else 0.0
        is_category = 1.0 if (subset == 1) else 0.0
        is_object = 1.0 if (subset == 2) else 0.0
        is_status = 1.0 if name_str.endswith("_status") else 0.0
        is_position = 1.0 if name_str.endswith("_position") else 0.0
        is_importance = 1.0 if name_str.endswith("_importance") else 0.0
        is_safety = 1.0 if name_str.endswith("_safety") else 0.0
        is_causal = 1.0 if name_str.endswith("_causal") else 0.0
        is_goal = 1.0 if name_str == "goal_oriented" else 0.0
        is_action = 1.0 if name_str == "action_suggestions" else 0.0
        is_traffic = 1.0 if name_str == "traffic_reg_suggestions" else 0.0

        x_list.append([
            subset,
            in_deg,
            out_deg,
            is_safe_node,
            is_category,
            is_object,
            is_status,
            is_position,
            is_importance,
            is_safety,
            is_causal,
            is_goal,
            is_action,
            is_traffic
        ])

    x = torch.tensor(x_list, dtype=torch.float)
    y = torch.tensor([1.0 if label == "safe" else 0.0], dtype=torch.float)

    return Data(x=x, edge_index=edge_index, y=y)


def load_multimodal_dataset_variant(json_root, frames_root, flags):
    """
    Load graphs + image paths for a given ablation variant.

    json_root/videoName.json
    frames_root/videoName/frame_xxxx.jpg

    Returns:
        graphs: list[Data] (with .image_idx field)
        image_paths: list[str]
    """
    json_files = [f for f in os.listdir(json_root) if f.endswith(".json")]
    graphs = []
    image_paths = []

    for json_file in json_files:
        video_name = os.path.splitext(json_file)[0]
        json_path = os.path.join(json_root, json_file)
        image_dir = os.path.join(frames_root, video_name)

        print(f"[Flags={flags}] Reading {json_path}")
        with open(json_path, "r") as f:
            data = json.load(f)

        for frame in data:
            image_id = frame.get("image_id", None)
            if image_id is None:
                continue
            image_path = os.path.join(image_dir, image_id)

            data_obj = frame_to_graph_data(frame, flags)
            if data_obj is None:
                continue

            image_paths.append(image_path)
            image_idx = len(image_paths) - 1
            data_obj.image_idx = image_idx

            graphs.append(data_obj)

    print(f"Loaded {len(graphs)} graphs with images for this variant.")
    return graphs, image_paths


# ============================================================
# Image preprocessing
# ============================================================

def get_image_transform():
    """Standard ImageNet-like preprocessing."""
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        ),
    ])


def load_images_from_indices(image_idx_tensor, all_image_paths, device, transform):
    """
    Given a 1D tensor of image indices, load images from disk
    and return a batch tensor [B, 3, H, W].
    """
    image_idx_tensor = image_idx_tensor.cpu()
    paths = [all_image_paths[int(i)] for i in image_idx_tensor]
    imgs = []
    for p in paths:
        img = Image.open(p).convert("RGB")
        img = transform(img)
        imgs.append(img)
    imgs = torch.stack(imgs, dim=0).to(device)
    return imgs


# ============================================================
# Multimodal model: Image + Graph, with multiple GNN backbones
# ============================================================

class ImageEncoder(nn.Module):
    """ResNet-18 backbone producing a global image embedding."""
    def __init__(self):
        super().__init__()
        base = models.resnet18(weights=None)  # no pretrained download
        modules = list(base.children())[:-1]  # remove final FC
        self.cnn = nn.Sequential(*modules)
        self.out_dim = base.fc.in_features  # usually 512

    def forward(self, x):
        feat = self.cnn(x)           # [B, C, 1, 1]
        feat = feat.view(feat.size(0), -1)  # [B, C]
        return feat                  # typically C=512


class GraphEncoderGCN(nn.Module):
    def __init__(self, in_channels, hidden_channels=64):
        super().__init__()
        self.conv1 = GCNConv(in_channels, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, hidden_channels)
        self.hidden_channels = hidden_channels

    def forward(self, x, edge_index, batch):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=0.2, training=self.training)

        x = self.conv2(x, edge_index)
        x = F.relu(x)

        x = global_mean_pool(x, batch)
        return x


class GraphEncoderSAGE(nn.Module):
    def __init__(self, in_channels, hidden_channels=64):
        super().__init__()
        self.conv1 = SAGEConv(in_channels, hidden_channels)
        self.conv2 = SAGEConv(hidden_channels, hidden_channels)
        self.hidden_channels = hidden_channels

    def forward(self, x, edge_index, batch):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=0.2, training=self.training)

        x = self.conv2(x, edge_index)
        x = F.relu(x)

        x = global_mean_pool(x, batch)
        return x


class GraphEncoderGAT(nn.Module):
    def __init__(self, in_channels, hidden_channels=32, heads=4):
        super().__init__()
        self.conv1 = GATConv(in_channels, hidden_channels, heads=heads,
                             concat=False, dropout=0.2)
        self.conv2 = GATConv(hidden_channels, hidden_channels, heads=heads,
                             concat=False, dropout=0.2)
        self.hidden_channels = hidden_channels

    def forward(self, x, edge_index, batch):
        x = self.conv1(x, edge_index)
        x = F.elu(x)
        x = F.dropout(x, p=0.3, training=self.training)

        x = self.conv2(x, edge_index)
        x = F.elu(x)

        x = global_mean_pool(x, batch)
        return x


class GraphEncoderTransformer(nn.Module):
    def __init__(self, in_channels, hidden_channels=32, heads=4):
        super().__init__()
        self.conv1 = TransformerConv(
            in_channels,
            hidden_channels,
            heads=heads,
            concat=False,
            dropout=0.2
        )
        self.conv2 = TransformerConv(
            hidden_channels,
            hidden_channels,
            heads=heads,
            concat=False,
            dropout=0.2
        )
        self.hidden_channels = hidden_channels

    def forward(self, x, edge_index, batch):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=0.3, training=self.training)

        x = self.conv2(x, edge_index)
        x = F.relu(x)

        x = global_mean_pool(x, batch)
        return x


class MultiModalModel(nn.Module):
    """
    Full multimodal model:
      - GraphEncoder (one of: GCN, GraphSAGE, GAT, Transformer)
      - ImageEncoder (ResNet-18)
      - Fusion + classifier -> safe vs unsafe.
    """
    def __init__(self, in_channels, graph_backbone: str = "Transformer"):
        super().__init__()

        graph_backbone = graph_backbone.lower()
        if graph_backbone == "gcn":
            self.graph_enc = GraphEncoderGCN(in_channels, hidden_channels=64)
            g_hidden = 64
        elif graph_backbone == "graphsage":
            self.graph_enc = GraphEncoderSAGE(in_channels, hidden_channels=64)
            g_hidden = 64
        elif graph_backbone == "gat":
            self.graph_enc = GraphEncoderGAT(in_channels, hidden_channels=32, heads=4)
            g_hidden = 32
        elif graph_backbone == "transformer":
            self.graph_enc = GraphEncoderTransformer(in_channels, hidden_channels=32, heads=4)
            g_hidden = 32
        else:
            raise ValueError(f"Unknown graph_backbone: {graph_backbone}")

        self.image_enc = ImageEncoder()
        fusion_in_dim = g_hidden + self.image_enc.out_dim

        fusion_hidden = 128
        self.classifier = nn.Sequential(
            nn.Linear(fusion_in_dim, fusion_hidden),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(fusion_hidden, 1)
        )

    def forward(self, x, edge_index, batch, images):
        g_emb = self.graph_enc(x, edge_index, batch)   # [B, g_hidden]
        img_emb = self.image_enc(images)               # [B, img_dim]
        fused = torch.cat([g_emb, img_emb], dim=-1)
        out = self.classifier(fused).view(-1)          # [B]
        return out


# ============================================================
# Metrics, evaluation, training
# ============================================================

def compute_binary_metrics(logits, labels):
    """
    Compute accuracy, precision, recall, F1, confusion matrix.
    logits: tensor [N]
    labels: tensor [N] with values 0 or 1
    """
    probs = torch.sigmoid(logits)
    preds = (probs >= 0.5).float()

    labels = labels.float()
    N = labels.numel()

    if N == 0:
        return {
            "num_samples": 0,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "tp": 0,
            "tn": 0,
            "fp": 0,
            "fn": 0
        }

    tp = int(((preds == 1) & (labels == 1)).sum().item())
    tn = int(((preds == 0) & (labels == 0)).sum().item())
    fp = int(((preds == 1) & (labels == 0)).sum().item())
    fn = int(((preds == 0) & (labels == 1)).sum().item())

    accuracy = (tp + tn) / N if N > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "num_samples": N,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn
    }


def evaluate_model(model, loader, device, transform, all_image_paths):
    model.eval()
    all_logits = []
    all_labels = []

    if loader is None:
        return compute_binary_metrics(torch.tensor([]), torch.tensor([]))

    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            images = load_images_from_indices(batch.image_idx, all_image_paths, device, transform)
            logits = model(batch.x, batch.edge_index, batch.batch, images)
            labels = batch.y.view(-1)
            all_logits.append(logits.cpu())
            all_labels.append(labels.cpu())

    if not all_logits:
        return compute_binary_metrics(torch.tensor([]), torch.tensor([]))

    logits_all = torch.cat(all_logits, dim=0)
    labels_all = torch.cat(all_labels, dim=0)
    return compute_binary_metrics(logits_all, labels_all)


def train_multimodal_model_for_variant_and_backbone(
    variant_name,
    backbone_name,
    graphs,
    image_paths,
    output_root,
    num_epochs=25,
    batch_size=8,
    lr=1e-4
):
    """
    Train the multimodal model (graph + image) for one (ablation variant, backbone).
    Saves metrics and training curves inside:
        output_root/variant_name/backbone_name/
    Returns metrics + training history.
    """
    if len(graphs) < 2:
        print(f"[{variant_name}/{backbone_name}] Not enough graphs to train (need >= 2).")
        return None

    random.seed(42)
    torch.manual_seed(42)
    random.shuffle(graphs)

    n_total = len(graphs)
    if n_total >= 10:
        n_train = int(0.7 * n_total)
        n_val = int(0.15 * n_total)
    else:
        n_train = max(1, int(0.8 * n_total))
        n_val = max(0, int(0.1 * n_total))
    n_test = n_total - n_train - n_val
    if n_test < 0:
        n_test = 0
        n_val = n_total - n_train

    train_graphs = graphs[:n_train]
    val_graphs = graphs[n_train:n_train + n_val]
    test_graphs = graphs[n_train + n_val:]

    print(f"[{variant_name}/{backbone_name}] Split: "
          f"train={len(train_graphs)}, val={len(val_graphs)}, test={len(test_graphs)}")

    train_loader = DataLoader(train_graphs, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_graphs, batch_size=batch_size, shuffle=False) if val_graphs else None
    test_loader = DataLoader(test_graphs, batch_size=batch_size, shuffle=False) if test_graphs else None

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[{variant_name}/{backbone_name}] Using device: {device}")

    in_channels = graphs[0].x.size(1)
    model = MultiModalModel(in_channels=in_channels, graph_backbone=backbone_name).to(device)

    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)

    transform = get_image_transform()

    history = {
        "train_loss": [],
        "val_f1": []
    }

    run_dir = os.path.join(output_root, variant_name, backbone_name)
    os.makedirs(run_dir, exist_ok=True)

    # Training loop
    for epoch in range(1, num_epochs + 1):
        model.train()
        total_loss = 0.0
        total_graphs = 0

        for batch in train_loader:
            batch = batch.to(device)
            images = load_images_from_indices(batch.image_idx, image_paths, device, transform)

            optimizer.zero_grad()
            logits = model(batch.x, batch.edge_index, batch.batch, images)
            labels = batch.y.view(-1)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * batch.num_graphs
            total_graphs += batch.num_graphs

        avg_loss = total_loss / max(total_graphs, 1)
        history["train_loss"].append(avg_loss)

        val_metrics = evaluate_model(model, val_loader, device, transform, image_paths)
        history["val_f1"].append(val_metrics["f1"])

        print(f"[{variant_name}/{backbone_name}] Epoch {epoch:03d} - "
              f"Train Loss: {avg_loss:.4f} | Val F1: {val_metrics['f1']:.4f}")

    # Final evaluation
    train_metrics = evaluate_model(model, train_loader, device, transform, image_paths)
    val_metrics = evaluate_model(model, val_loader, device, transform, image_paths)
    test_metrics = evaluate_model(model, test_loader, device, transform, image_paths)

    metrics = {
        "num_graphs": n_total,
        "train_size": len(train_graphs),
        "val_size": len(val_graphs),
        "test_size": len(test_graphs),
        "train_metrics": train_metrics,
        "val_metrics": val_metrics,
        "test_metrics": test_metrics
    }

    # Save metrics JSON
    metrics_path = os.path.join(run_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=4)
    print(f"[{variant_name}/{backbone_name}] Saved metrics to: {metrics_path}")

    # Plot training loss
    plt.figure(figsize=(8, 5))
    plt.plot(history["train_loss"], label="Train Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title(f"{variant_name}/{backbone_name} - Training Loss")
    plt.grid(True, alpha=0.3)
    plt.legend()
    loss_path = os.path.join(run_dir, "training_loss.png")
    plt.savefig(loss_path, bbox_inches="tight")
    plt.close()

    # Plot validation F1
    plt.figure(figsize=(8, 5))
    plt.plot(history["val_f1"], label="Val F1")
    plt.xlabel("Epoch")
    plt.ylabel("F1")
    plt.title(f"{variant_name}/{backbone_name} - Validation F1")
    plt.grid(True, alpha=0.3)
    plt.legend()
    f1_path = os.path.join(run_dir, "val_f1.png")
    plt.savefig(f1_path, bbox_inches="tight")
    plt.close()

    print(f"[{variant_name}/{backbone_name}] Saved curves to: {run_dir}")

    metrics["history"] = history
    return metrics


# ============================================================
# Ablation + model comparison main
# ============================================================

def main():
    # Adjust this root to your dataset:
    # dataset_root/
    #   frames/
    #       videoName/ frame_0000.jpg ...
    #   json/
    #       videoName.json
    dataset_root = "/home/ahmed/Desktop/DatasetSit2VLMDrive/SitVLM2Drive/Sample of Dataset"
    json_root = os.path.join(dataset_root, "json")
    frames_root = os.path.join(dataset_root, "frames1")

    output_root = os.path.join(dataset_root, "multimodal_ablation")
    os.makedirs(output_root, exist_ok=True)

    # Ablation settings over semantic groups
    ablations = {
        "full": {
            "include_importance": True,
            "include_status": True,
            "include_safety": True,
            "include_position": True,
            "include_goal": True,
            "include_action": True,
            "include_traffic": True,
            "include_causal": True
        },
     "causal": {
            "include_importance": False,
            "include_status": False,
            "include_safety": False,
            "include_position": False,
            "include_goal": False,
            "include_action": False,
            "include_traffic": False,
            "include_causal": True
        },
        "Six-Space": {
            "include_importance": True,
            "include_status": True,
            "include_safety": True,
            "include_position": True,
            "include_goal": True,
            "include_action": True,
            "include_traffic": True,
            "include_causal": False
        }
        # "no_importance": {
        #     "include_importance": False,
        #     "include_status": True,
        #     "include_safety": True,
        #     "include_position": True,
        #     "include_goal": True,
        #     "include_action": True,
        #     "include_traffic": True,
        #     "include_causal": True
        # },
        # "no_status": {
        #     "include_importance": True,
        #     "include_status": False,
        #     "include_safety": True,
        #     "include_position": True,
        #     "include_goal": True,
        #     "include_action": True,
        #     "include_traffic": True,
        #     "include_causal": True
        # },
        # "no_safety": {
        #     "include_importance": True,
        #     "include_status": True,
        #     "include_safety": False,
        #     "include_position": True,
        #     "include_goal": True,
        #     "include_action": True,
        #     "include_traffic": True,
        #     "include_causal": True
        # },
        # "no_position": {
        #     "include_importance": True,
        #     "include_status": True,
        #     "include_safety": True,
        #     "include_position": False,
        #     "include_goal": True,
        #     "include_action": True,
        #     "include_traffic": True,
        #     "include_causal": True
        # },
        # "no_goal_action_traffic": {
        #     "include_importance": True,
        #     "include_status": True,
        #     "include_safety": True,
        #     "include_position": True,
        #     "include_goal": False,
        #     "include_action": False,
        #     "include_traffic": False,
        #     "include_causal": True
        # },
    }

    # Graph backbones to compare (SOTA-ish + baselines)
    backbones = ["GCN", "GraphSAGE", "GAT", "Transformer"]

    all_results = {}

    for variant_name, flags in ablations.items():
        print("=" * 100)
        print(f"Loading data for ablation variant: {variant_name} with flags={flags}")
        graphs, image_paths = load_multimodal_dataset_variant(json_root, frames_root, flags)
        if len(graphs) < 2:
            print(f"[{variant_name}] Not enough graphs, skipping this variant.")
            continue

        all_results[variant_name] = {}

        for backbone in backbones:
            print("-" * 80)
            print(f"Training model backbone: {backbone} on variant: {variant_name}")
            metrics = train_multimodal_model_for_variant_and_backbone(
                variant_name,
                backbone,
                graphs,
                image_paths,
                output_root,
                num_epochs=5,
                batch_size=8,
                lr=1e-4
            )
            if metrics is not None:
                all_results[variant_name][backbone] = metrics

    if not all_results:
        print("No results produced. Check dataset paths/labels.")
        return

    # Save global metrics
    summary_path = os.path.join(output_root, "multimodal_ablation_metrics.json")
    with open(summary_path, "w") as f:
        json.dump(all_results, f, indent=4)
    print(f"\nSaved global ablation + model comparison metrics to: {summary_path}")

    # Quick console summary: test F1 for each (variant, model)
    print("\n=== Global Summary: Test F1 per Variant / Backbone ===")
    for variant_name, models_dict in all_results.items():
        print(f"\n[Variant: {variant_name}]")
        for backbone, res in models_dict.items():
            f1 = res["test_metrics"]["f1"]
            print(f"  {backbone}: Test F1 = {f1:.4f}")


if __name__ == "__main__":
    main()
