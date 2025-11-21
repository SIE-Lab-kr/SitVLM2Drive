import os
import json
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from textwrap import wrap

# Define colors for Object_Safety
colors = {
    "Affects Safety": "red",
    "Potentially Affect Safety": "orange",
    "Does Not Affect Safety": "green",
    "Requires Monitoring": "blue",
    "Unknown": "gray"
}

# Define arrow colors for importance ranking
arrow_colors = {
    "high": "red",
    "mid": "orange",
    "low": "green",
    None: "gray"
}

# Colors for status and position nodes
status_color = "lightgray"
position_color = "lightblue"

def wrap_text(text, width=15):
    """Wraps text for better readability inside nodes."""
    return '\n'.join(wrap(text, width))

def determine_safety_status(safety_status):
    """Determine safety status based on the input."""
    if "unsafe" in safety_status.lower() or "no" in safety_status.lower():
        return "unsafe"
    elif "safe" in safety_status.lower() or "yes" in safety_status.lower():
        return "safe"
    else:
        return None

def draw_clean_dag_with_legend(categories, safe_color, caption, output_path):
    """Draw the directed acyclic graph (DAG) with legends and save the output."""
    G = nx.DiGraph()

    # Add central Safety node
    G.add_node("SAFE", color=safe_color, size=4000, label="Ego", subset=0)

    # Add categories, objects, and their details (status and position)
    for category, objects in categories.items():
        G.add_node(category, color="teal", size=3000, label=wrap_text(category), subset=1)
        G.add_edge("SAFE", category)

        for obj_name, details in objects.items():
            if obj_name.lower() == "ego":  # Skip ego object name
                continue
            obj_color = colors.get(details['safety'], 'gray')
            G.add_node(obj_name, color=obj_color, size=2500, label=wrap_text(obj_name), subset=2)
            G.add_edge(category, obj_name, color=arrow_colors.get(details['importance'], "gray"))

            # Add status and position as sub-nodes
            if "status" in details:
                status_node = f"{obj_name}_status"
                G.add_node(status_node, color=status_color, size=2000, label=wrap_text(details['status']), subset=3)
                G.add_edge(obj_name, status_node, color="gray")

            if "position" in details:
                position_node = f"{obj_name}_position"
                G.add_node(position_node, color=position_color, size=2000, label=wrap_text(details['position']), subset=3)
                G.add_edge(obj_name, position_node, color="gray")

    # Generate positions using a multipartite layout
    pos = nx.multipartite_layout(G, subset_key="subset", align="horizontal")

    # Scale layout to increase spacing
    for key, value in pos.items():
        pos[key] = (value[0] * 2, value[1] * 2)

    # Extract node attributes for styling
    node_colors = [G.nodes[node].get('color', 'gray') for node in G.nodes]
    node_sizes = [G.nodes[node].get('size', 800) for node in G.nodes]
    edge_colors = [G.edges[edge].get('color', 'black') for edge in G.edges]
    labels = nx.get_node_attributes(G, 'label')

    plt.figure(figsize=(20, 14))  # Increase figure size to reduce overlapping
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes)
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, arrowstyle='->', arrowsize=15)

    # Adjust text alignment and font size in nodes
    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight='bold',
                            verticalalignment='center', horizontalalignment='center')

    # Add caption below the diagram
    plt.title(wrap_text(caption, width=100), fontsize=14, weight='bold')

    # Add legend for node colors
    legend_elements_shapes = [
        Patch(facecolor=color, edgecolor='black', label=label)
        for label, color in colors.items()
    ]

    # Add status and position color to the legend
    legend_elements_shapes += [
        Patch(facecolor=safe_color, edgecolor='black', label="Ego-> SAFE = green, unsafe = red"),
        Patch(facecolor=status_color, edgecolor='black', label="Status"),
        Patch(facecolor=position_color, edgecolor='black', label="Position")
    ]

    # Add legend for arrow colors
    legend_elements_arrows = [
        Line2D([0], [0], color=color, lw=2, label=f"Importance: {key}")
        for key, color in arrow_colors.items()
    ]

    plt.legend(handles=legend_elements_shapes + legend_elements_arrows, loc='lower left', fontsize=10, frameon=True, title="Legend")

    # Save the diagram
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")

def process_json_file(json_file, output_folder):
    """Process a single JSON file and generate diagrams."""
    with open(json_file, "r") as f:
        data = json.load(f)

    base_name = os.path.splitext(os.path.basename(json_file))[0]
    json_output_folder = os.path.join(output_folder, base_name)
    os.makedirs(json_output_folder, exist_ok=True)

    for frame_index, frame in enumerate(data):
        if "graph" not in frame or "nodes" not in frame["graph"]:
            continue

        categories = {}
        safety_status = determine_safety_status(frame.get("safe", ""))
        safe_color = 'green' if safety_status == "safe" else 'red'
        caption = frame.get("caption", "No caption provided")

        for node in frame["graph"]["nodes"]:
            if len(node) != 2:
                continue
            node_id, attributes = node
            object_type = attributes.get("object_type", "Unknown")
            obj_name = attributes.get("obj_name", "Unknown")
            object_safety = attributes.get("Object_Safety", ["Unknown"])
            object_safety = object_safety[0] if isinstance(object_safety, list) and object_safety else "Unknown"
            importance_ranking = attributes.get("importance_ranking", None)
            status = ", ".join(attributes.get("Status", ["Unknown"]))
            position = ", ".join(attributes.get("position", ["Unknown"]))

            if object_type not in categories:
                categories[object_type] = {}

            categories[object_type][obj_name] = {
                'safety': object_safety,
                'importance': importance_ranking,
                'status': status,
                'position': position
            }

        output_path = os.path.join(json_output_folder, f"frame_{frame_index}.png")
        draw_clean_dag_with_legend(categories, safe_color, caption, output_path)

def process_json_folder(input_folder, output_folder):
    """Process all JSON files in a folder."""
    os.makedirs(output_folder, exist_ok=True)
    json_files = [f for f in os.listdir(input_folder) if f.endswith(".json")]

    for json_file in json_files:
        process_json_file(os.path.join(input_folder, json_file), output_folder)


input_folder = "/home/ahmed/Desktop/DatasetSit2VLMDrive/SitVLM2Drive/Sample of Dataset/data"
output_folder = "/home/ahmed/Desktop/DatasetSit2VLMDrive/SitVLM2Drive/Sample of Dataset/diagrams"

process_json_folder(input_folder, output_folder)
