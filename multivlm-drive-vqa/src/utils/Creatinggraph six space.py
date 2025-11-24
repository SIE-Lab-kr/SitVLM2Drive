import os
import json
import subprocess
from textwrap import wrap

import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

# Optional: global style tweaks for a more professional look
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.titlesize": 16,
    "axes.titleweight": "bold",
    "figure.dpi": 150,
    "figure.facecolor": "white"
})

# Try to enable DOT export (via pydot)
try:
    from networkx.drawing.nx_pydot import write_dot
    HAS_PYDOT = True
except ImportError:
    HAS_PYDOT = False
    write_dot = None

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
    if not isinstance(text, str):
        text = str(text)
    return '\n'.join(wrap(text, width))


def determine_safety_status(safety_status):
    """Determine safety status based on the input."""
    if not isinstance(safety_status, str):
        safety_status = str(safety_status)

    if "unsafe" in safety_status.lower() or "no" in safety_status.lower():
        return "unsafe"
    elif "safe" in safety_status.lower() or "yes" in safety_status.lower():
        return "safe"
    else:
        return None


def save_dot_graph(G, dot_output_path):
    """
    Save the graph as a DOT file, and also create a PNG from the DOT
    using the Graphviz `dot` command (if available).
    """
    if not HAS_PYDOT or write_dot is None:
        print(f"Skipping DOT export (pydot / graphviz Python bindings not installed). Intended path: {dot_output_path}")
        return

    # Write DOT file
    write_dot(G, dot_output_path)
    print(f"Saved DOT: {dot_output_path}")

    # Now try to create a PNG from the DOT using the `dot` command
    base, _ = os.path.splitext(dot_output_path)
    png_from_dot_path = base + "_dot.png"

    try:
        subprocess.run(
            ["dot", "-Tpng", dot_output_path, "-o", png_from_dot_path],
            check=True
        )
        print(f"Saved PNG from DOT: {png_from_dot_path}")
    except FileNotFoundError:
        print("Graphviz 'dot' command not found on PATH. Skipping PNG-from-DOT export.")
    except subprocess.CalledProcessError as e:
        print(f"Error running 'dot' to create PNG from DOT: {e}")


def build_graph(categories, safe_color):
    """
    Build and return a NetworkX DiGraph from the categories structure.
    This graph is then used for both visualization and DOT export.
    """
    G = nx.DiGraph()

    # Add central Safety node
    G.add_node("SAFE", color=safe_color, size=4500, label="Ego", subset=0)

    # Add categories, objects, and their details (status and position)
    for category, objects in categories.items():
        G.add_node(
            category,
            color="teal",
            size=3200,
            label=wrap_text(category),
            subset=1
        )
        G.add_edge("SAFE", category)

        for obj_name, details in objects.items():
            if isinstance(obj_name, str) and obj_name.lower() == "ego":
                # Skip ego object name
                continue

            obj_color = colors.get(details.get('safety', 'Unknown'), 'gray')
            G.add_node(
                obj_name,
                color=obj_color,
                size=2600,
                label=wrap_text(obj_name),
                subset=2
            )
            G.add_edge(
                category,
                obj_name,
                color=arrow_colors.get(details.get('importance'), "gray")
            )

            # Add status and position as sub-nodes
            if "status" in details:
                status_node = f"{obj_name}_status"
                G.add_node(
                    status_node,
                    color=status_color,
                    size=2100,
                    label=wrap_text(details['status'], width=18),
                    subset=3
                )
                G.add_edge(obj_name, status_node, color="gray")

            if "position" in details:
                position_node = f"{obj_name}_position"
                G.add_node(
                    position_node,
                    color=position_color,
                    size=2100,
                    label=wrap_text(details['position'], width=18),
                    subset=3
                )
                G.add_edge(obj_name, position_node, color="gray")

    return G


def draw_clean_dag_with_legend(categories, safe_color, caption, png_output_path, dot_output_path=None):
    """
    Draw the directed acyclic graph (DAG) with legends and save the PNG.
    Also optionally save the graph as a DOT file and generate a PNG via Graphviz.
    """
    # Build graph
    G = build_graph(categories, safe_color)

    # Optionally save DOT (and PNG-from-DOT)
    if dot_output_path is not None:
        save_dot_graph(G, dot_output_path)

    # Generate positions using a multipartite layout (layered graph look)
    pos = nx.multipartite_layout(G, subset_key="subset", align="horizontal")

    # Scale layout to increase spacing between layers
    for key, value in pos.items():
        pos[key] = (value[0] * 4.0, value[1] * 3.0)

    # Extract node attributes for styling
    node_colors = [G.nodes[node].get('color', 'gray') for node in G.nodes]
    node_sizes = [G.nodes[node].get('size', 800) for node in G.nodes]
    edge_colors = [G.edges[edge].get('color', 'black') for edge in G.edges]
    labels = nx.get_node_attributes(G, 'label')

    # Slightly scale figure size based on number of nodes to avoid clutter
    n_nodes = max(G.number_of_nodes(), 10)
    width = min(24, 14 + n_nodes * 0.15)
    height = min(16, 8 + n_nodes * 0.10)

    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_axis_off()
    ax.set_facecolor("white")

    # Draw nodes with subtle borders
    nx.draw_networkx_nodes(
        G,
        pos,
        node_color=node_colors,
        node_size=node_sizes,
        edgecolors="#333333",
        linewidths=0.8,
        ax=ax
    )

    # Draw edges with nicer arrows and slight curvature
    nx.draw_networkx_edges(
        G,
        pos,
        edge_color=edge_colors,
        arrowstyle='-|>',
        arrowsize=16,
        width=1.2,
        connectionstyle='arc3,rad=0.05',
        alpha=0.9,
        ax=ax
    )

    # Draw labels with consistent font sizes
    for node, (x, y) in pos.items():
        label = labels.get(node, "")
        if not label:
            continue

        subset = G.nodes[node].get("subset", 2)
        if subset == 0:
            fsize = 11
            weight = "bold"
        elif subset == 1:
            fsize = 10
            weight = "bold"
        else:
            fsize = 8
            weight = "semibold"

        ax.text(
            x,
            y,
            label,
            ha='center',
            va='center',
            fontsize=fsize,
            fontweight=weight
        )

    # Add caption as a clear title
    wrapped_caption = "\n".join(wrap(caption, width=90))
    fig.suptitle(wrapped_caption, y=0.98)

    # Legend for node colors
    legend_elements_shapes = [
        Patch(facecolor=color, edgecolor='black', label=label)
        for label, color in colors.items()
    ]

    # Add status and position color to the legend
    legend_elements_shapes += [
        Patch(
            facecolor=safe_color,
            edgecolor='black',
            label="Ego (overall safety)"
        ),
        Patch(facecolor=status_color, edgecolor='black', label="Status node"),
        Patch(facecolor=position_color, edgecolor='black', label="Position node"),
    ]

    # Legend for arrow colors
    legend_elements_arrows = [
        Line2D(
            [0],
            [0],
            color=color,
            lw=2,
            label=f"Importance: {key}"
        )
        for key, color in arrow_colors.items()
    ]

    # Place combined legend below the plot, more compact and professional
    all_handles = legend_elements_shapes + legend_elements_arrows
    ax.legend(
        handles=all_handles,
        loc='upper center',
        bbox_to_anchor=(0.5, -0.06),
        ncol=3,
        frameon=True,
        title="Legend"
    )

    fig.tight_layout(rect=[0, 0.05, 1, 0.95])
    fig.savefig(png_output_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved PNG (matplotlib layout): {png_output_path}")


def process_json_file(json_file, output_folder):
    """Process a single JSON file and generate diagrams (.png + .dot + .png from .dot)."""
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
            if isinstance(object_safety, list) and object_safety:
                object_safety = object_safety[0]
            elif not isinstance(object_safety, str):
                object_safety = "Unknown"

            importance_ranking = attributes.get("importance_ranking", None)

            status_list = attributes.get("Status", ["Unknown"])
            if isinstance(status_list, list):
                status = ", ".join(status_list)
            else:
                status = str(status_list)

            position_list = attributes.get("position", ["Unknown"])
            if isinstance(position_list, list):
                position = ", ".join(position_list)
            else:
                position = str(position_list)

            if object_type not in categories:
                categories[object_type] = {}

            categories[object_type][obj_name] = {
                'safety': object_safety,
                'importance': importance_ranking,
                'status': status,
                'position': position
            }

        png_output_path = os.path.join(json_output_folder, f"frame_{frame_index}.png")
        dot_output_path = os.path.join(json_output_folder, f"frame_{frame_index}.dot")

        draw_clean_dag_with_legend(
            categories,
            safe_color,
            caption,
            png_output_path,
            dot_output_path=dot_output_path
        )


def process_json_folder(input_folder, output_folder):
    """Process all JSON files in a folder."""
    os.makedirs(output_folder, exist_ok=True)
    json_files = [f for f in os.listdir(input_folder) if f.endswith(".json")]

    for json_file in json_files:
        full_path = os.path.join(input_folder, json_file)
        print(f"Processing: {full_path}")
        process_json_file(full_path, output_folder)


if __name__ == "__main__":
    # Update these paths as needed
    input_folder = "/home/ahmed/Desktop/DatasetSit2VLMDrive/SitVLM2Drive/Sample of Dataset/data"
    output_folder = "/home/ahmed/Desktop/DatasetSit2VLMDrive/SitVLM2Drive/Sample of Dataset/diagrams"

    process_json_folder(input_folder, output_folder)
