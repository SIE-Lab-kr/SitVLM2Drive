import os
import json
import re
from pathlib import Path

from graphviz import Digraph
from PIL import Image, ImageDraw, ImageFont

# =============================
# CONFIG
# =============================


# Folder containing your JSON files
INPUT_DIR = r"/home/ahmed/Desktop/DatasetSit2VLMDrive/SitVLM2Drive/Sample of Dataset/data"      # <-- CHANGE THIS
# Root folder where graphs and annotated images will be saved
OUTPUT_DIR = r"/home/ahmed/Desktop/DatasetSit2VLMDrive/SitVLM2Drive/Sample of Dataset/graphs"          # <-- CHANGE THIS
# Root folder for images
IMAGES_DIR = r"/home/ahmed/Desktop/DatasetSit2VLMDrive/SitVLM2Drive/Sample of Dataset/frames"          # <-- CHANGE THIS
# Structure expected:
# IMAGES_DIR/
#     name1/          # same as json file stem
#         frame_0000.jpg
#         frame_0001.jpg
#     name2/
#         ...
GRAPH_FORMAT = "png"  # "png", "pdf", "svg", ...

ANNOTATED_SUBFOLDER = "annotated_frames"

# =============================
# COLORS & HELPERS
# =============================

# Node fill colors for Object_Safety
colors = {
    "Affects Safety": "red",
    "Potentially Affect Safety": "orange",
    "Does Not Affect Safety": "green",
    "Requires Monitoring": "blue",
    "Unknown": "gray",
}

# Colors for importance (used for edge label font color, NOT node fill)
importance_colors = {
    "high": "red",
    "mid": "orange",   # we'll map "medium" to "mid"
    "low": "green",
    None: "gray",
}

# Colors for status and position nodes
status_color = "lightgray"
position_color = "lightblue"

# Colors for Causal_Relation (edge line color)
relation_colors = {
    "direct": "red",
    "chain": "orange",
    "confounder": "purple",
    "correlations": "green",
    "unknown": "gray",
}


def determine_safety_status(safety_status):
    """Determine safety status (safe / unsafe / None) from free text."""
    if safety_status is None:
        return None

    if not isinstance(safety_status, str):
        safety_status = str(safety_status)

    text = safety_status.lower()

    # Unsafe first so "not safe" isn't mis-read as "safe"
    if "not safe" in text or "unsafe" in text:
        return "unsafe"

    if "safe" in text and "not safe" not in text and "unsafe" not in text:
        return "safe"

    # Heuristic for yes/no style
    if "yes" in text and "no" not in text:
        return "safe"
    if "no" in text and "yes" not in text:
        return "unsafe"

    return None


def clean_name(raw_id: str) -> str:
    """
    Turn IDs like 'car<bb>600,317,661,362<bb>' into 'car',
    'ego<po>711,708<po>' into 'ego', for display.
    """
    return re.split(r"<bb>|<po>", raw_id)[0]


def canonical_id(s: str) -> str:
    """
    Normalize object IDs so that variants like:
      'ego<po>711,708</po>' and 'ego<po>711,708<po>'
    are treated the same.

    Strategy: remove the '/' in closing tags, e.g. '</po>' -> '<po>'.
    """
    if not s:
        return s
    return s.replace("</", "<")


def pick_safety_color(object_safety):
    """
    Given Object_Safety (list or string), choose a fillcolor.
    Priority order:
      Affects Safety > Requires Monitoring > Potentially Affect Safety
      > Does Not Affect Safety > Unknown
    """
    if not object_safety:
        key = "Unknown"
    else:
        if isinstance(object_safety, str):
            safety_list = [object_safety]
        else:
            safety_list = list(object_safety)

        priority = [
            "Affects Safety",
            "Requires Monitoring",
            "Potentially Affect Safety",
            "Does Not Affect Safety",
        ]

        key = "Unknown"
        for p in priority:
            for s in safety_list:
                if p.lower() in str(s).lower():
                    key = p
                    break
            if key != "Unknown":
                break

    return colors.get(key, "gray")


def importance_to_color(importance_ranking: str):
    """
    Map importance ranking ('high', 'medium', 'low', 'none', None, ...)
    to importance_colors (used for edge label font color).
    """
    if not importance_ranking:
        return importance_colors[None]

    imp = importance_ranking.strip().lower()
    if imp == "medium":
        key = "mid"
    elif imp in ("high", "low"):
        key = imp
    else:
        key = None
    return importance_colors.get(key, "gray")


def relation_to_color(relation: str):
    """
    Map Causal_Relation to an edge (line) color.
    Expected relation values include 'Direct', 'Chain', 'Confounder', 'correlations'.
    """
    if not relation:
        return relation_colors["unknown"]

    rel = relation.strip().lower()

    if "direct" in rel:
        return relation_colors["direct"]
    if "chain" in rel:
        return relation_colors["chain"]
    if "confounder" in rel:
        return relation_colors["confounder"]
    if "correlation" in rel:
        return relation_colors["correlations"]

    return relation_colors["unknown"]


def is_ego_node(node_id: str, attrs: dict) -> bool:
    """Heuristic to detect ego node."""
    name = (attrs.get("obj_name") or clean_name(node_id) or "").lower()
    obj_type = (attrs.get("object_type") or "").lower()
    return name == "ego" or obj_type == "ego-ego"


def create_image_legend(width: int, bg_color: str = "white") -> Image.Image:
    """
    Create a legend image to be placed under the annotated frame image.
    Legend is laid out horizontally across the bottom.
    """
    # You can tweak this height if needed
    legend_height = 120
    img = Image.new("RGB", (width, legend_height), bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    x_margin = 10
    y = 8
    line_h = 16

    # ----- Title -----
    draw.text((x_margin, y), "Legend", fill="black", font=font)
    y += line_h * 2

    # =========================
    # 1) Object Safety (outline color)
    # =========================
    draw.text((x_margin, y), "Object Safety (outline color):", fill="black", font=font)
    y += line_h

    safety_entries = [
        ("Affects Safety",        colors["Affects Safety"]),
        ("Requires Monitoring",   colors["Requires Monitoring"]),
        ("Potentially Affect Safety", colors["Potentially Affect Safety"]),
        ("Does Not Affect Safety",    colors["Does Not Affect Safety"]),
        ("Unknown",               colors["Unknown"]),
    ]

    box_w = 18
    box_h = 10

    # divide full width into equal segments for horizontal layout
    seg_w_safety = max((width - 2 * x_margin) // max(1, len(safety_entries)), 80)

    for i, (label, col) in enumerate(safety_entries):
        x = x_margin + i * seg_w_safety
        # colored box
        draw.rectangle(
            (x, y + 3, x + box_w, y + 3 + box_h),
            fill=col,
            outline="black",
        )
        # label
        draw.text((x + box_w + 4, y), label, fill="black", font=font)

    y += line_h * 2

    # =========================
    # 2) Causal Relation (arrow color)
    # =========================
    draw.text((x_margin, y), "Causal Relation (arrow color):", fill="black", font=font)
    y += line_h

    relation_entries = [
        ("Direct",        relation_colors["direct"]),
        ("Chain",         relation_colors["chain"]),
        ("Confounder",    relation_colors["confounder"]),
        ("Correlations",  relation_colors["correlations"]),
        ("Unknown",       relation_colors["unknown"]),
    ]

    seg_w_rel = max((width - 2 * x_margin) // max(1, len(relation_entries)), 80)

    for i, (label, col) in enumerate(relation_entries):
        x = x_margin + i * seg_w_rel
        yy = y + box_h // 2
        # short line as arrow example
        draw.line((x, yy, x + box_w, yy), fill=col, width=3)
        draw.text((x + box_w + 4, y), label, fill="black", font=font)

    y += line_h * 2

    # =========================
    # 3) Ego vehicle explanation (single line)
    # =========================
    ego_text = (
        "Ego vehicle: thicker outline; "
        "green = safe, red = unsafe (from 'safe' field)."
    )
    draw.text((x_margin, y), ego_text, fill="black", font=font)

    return img

def add_legend(g: Digraph):
    """
    Add a legend node with an HTML table explaining:
      - node colors (Object_Safety)
      - edge colors (Causal_Relation)
      - importance (edge thickness & label text)
    """
    rows = []

    # Header
    rows.append('<TR><TD COLSPAN="3"><B>Legend</B></TD></TR>')

    # Object Safety
    rows.append('<TR><TD COLSPAN="3"><B>Object Safety (node fill color)</B></TD></TR>')
    for name, col in [
        ("Affects Safety", colors["Affects Safety"]),
        ("Requires Monitoring", colors["Requires Monitoring"]),
        ("Potentially Affect Safety", colors["Potentially Affect Safety"]),
        ("Does Not Affect Safety", colors["Does Not Affect Safety"]),
        ("Unknown", colors["Unknown"]),
    ]:
        rows.append(
            f'<TR>'
            f'<TD>{name}</TD>'
            f'<TD BGCOLOR="{col}" WIDTH="40"></TD>'
            f'<TD></TD>'
            f'</TR>'
        )

    # Causal Relation
    rows.append('<TR><TD COLSPAN="3"><B>Causal Relation (edge line color)</B></TD></TR>')
    for name, col in [
        ("Direct", relation_colors["direct"]),
        ("Chain", relation_colors["chain"]),
        ("Confounder", relation_colors["confounder"]),
        ("Correlations", relation_colors["correlations"]),
        ("Unknown", relation_colors["unknown"]),
    ]:
        rows.append(
            f'<TR>'
            f'<TD>{name}</TD>'
            f'<TD BGCOLOR="{col}" WIDTH="40"></TD>'
            f'<TD></TD>'
            f'</TR>'
        )

    # Importance
    rows.append('<TR><TD COLSPAN="3"><B>Importance</B></TD></TR>')
    rows.append('<TR><TD>High</TD><TD>Thicker edge</TD><TD>Label shows "[importance: high]"</TD></TR>')
    rows.append('<TR><TD>Medium</TD><TD>Normal edge</TD><TD>Label shows "[importance: medium]"</TD></TR>')
    rows.append('<TR><TD>Low</TD><TD>Normal edge</TD><TD>Label shows "[importance: low]"</TD></TR>')

    table_html = (
        '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">'
        + "".join(rows) +
        '</TABLE>>'
    )

    g.node("legend", label=table_html, shape="plaintext")


# =============================
# IMAGE ANNOTATION
# =============================

def annotate_image_for_frame(frame: dict,
                             nodes,
                             json_base_name: str,
                             frame_index: int,
                             out_dir: Path,
                             global_safety: str):
    """
    Draw bounding boxes / points and graph links (according to Causal_Relation)
    on the original image, then save an annotated image.
    Also append a legend strip at the bottom (not over the image).
    """
    image_id = frame.get("image_id")
    if not image_id:
        return

    images_root = Path(IMAGES_DIR)
    image_folder = images_root / json_base_name
    image_path = image_folder / image_id

    if not image_path.exists():
        print(f"  [WARN] Image not found for frame {frame_index}: {image_path}")
        return

    try:
        img = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"  [WARN] Could not open image {image_path}: {e}")
        return

    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    # Precompute node centers for edges: {canonical_id(node_id): (cx, cy)}
    node_centers = {}

    # =========================
    # 1) Draw objects (bbox / point) and compute centers
    # =========================
    for raw_node_id, attrs in nodes:
        node_id = canonical_id(raw_node_id)
        obj_name = attrs.get("obj_name") or clean_name(raw_node_id)
        object_safety = attrs.get("Object_Safety") or []
        boxes = attrs.get("boxes")
        point = attrs.get("point")
        importance = attrs.get("importance_ranking")

        # Outline color based on Object_Safety
        outline = pick_safety_color(object_safety)

        # Ego outline based on global safety
        if is_ego_node(raw_node_id, attrs):
            if global_safety == "unsafe":
                outline = "red"
            elif global_safety == "safe":
                outline = "green"

        # ---- Bounding box ----
        if boxes and len(boxes) == 4:
            x1, y1, x2, y2 = boxes
            # ensure x1 <= x2, y1 <= y2
            x1, x2 = sorted([x1, x2])
            y1, y2 = sorted([y1, y2])
            x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])

            width = 4 if is_ego_node(raw_node_id, attrs) else 3
            draw.rectangle((x1, y1, x2, y2), outline=outline, width=width)

            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            node_centers[node_id] = (cx, cy)

            label = obj_name
            if importance and importance.lower() != "none":
                label += f" ({importance})"

            draw.text((x1 + 2, y1 + 2), label, fill="white", font=font)

        # ---- Point object ----
        elif point and len(point) == 2:
            px, py = point
            px, py = int(px), int(py)
            r = 6
            width = 4 if is_ego_node(raw_node_id, attrs) else 3
            draw.ellipse((px - r, py - r, px + r, py + r),
                         outline=outline, width=width)

            node_centers[node_id] = (px, py)

            label = obj_name
            if importance and importance.lower() != "none":
                label += f" ({importance})"

            draw.text((px + 5, py + 5), label, fill="white", font=font)

    # =========================
    # 2) Draw graph links (ALL with Causal_Relation)
    # =========================
    def draw_arrow(start, end, color="white", width=2):
        """Draw a line with a triangle arrow head from start -> end."""
        sx, sy = start
        ex, ey = end

        # Main line
        draw.line([start, end], fill=color, width=width)

        # Arrow head
        dx = ex - sx
        dy = ey - sy
        length_sq = dx * dx + dy * dy
        if length_sq == 0:
            return  # same point, nothing to draw

        length = length_sq ** 0.5
        ux, uy = dx / length, dy / length  # unit vector

        arrow_len = 12   # arrow head length
        arrow_w = 8      # arrow head width

        bx = ex - ux * arrow_len
        by = ey - uy * arrow_len

        # Perpendicular
        px = -uy
        py = ux

        left = (bx + px * arrow_w / 2, by + py * arrow_w / 2)
        right = (bx - px * arrow_w / 2, by - py * arrow_w / 2)

        draw.polygon([(ex, ey), left, right], fill=color)

    for raw_node_id, attrs in nodes:
        src_id = canonical_id(raw_node_id)
        raw_target = attrs.get("Object_Causal") or attrs.get("object_causal")
        relation = attrs.get("Causal_Relation")
        importance = attrs.get("importance_ranking")

        # Use ALL relations that have both target and Causal_Relation
        if not (raw_target and relation):
            continue

        tgt_id = canonical_id(raw_target)

        if src_id not in node_centers or tgt_id not in node_centers:
            continue

        start = node_centers[src_id]
        end = node_centers[tgt_id]

        color = relation_to_color(relation)
        width = 4 if (importance and importance.strip().lower() == "high") else 2

        # Arrow from source -> target
        draw_arrow(start, end, color=color, width=width)

        # Relation label near middle of arrow
        mx = (start[0] + end[0]) / 2
        my = (start[1] + end[1]) / 2
        draw.text((mx + 5, my - 10), relation, fill="white", font=font)

    # =========================
    # 3) Append legend BELOW the image
    # =========================
    w, h = img.size
    legend_img = create_image_legend(width=w, bg_color="white")
    lw, lh = legend_img.size

    # Create new combined image: original on top, legend at bottom
    combined = Image.new("RGB", (w, h + lh), "white")
    combined.paste(img, (0, 0))
    combined.paste(legend_img, (0, h))

    # =========================
    # 4) Save annotated image
    # =========================
    annotated_dir = out_dir / ANNOTATED_SUBFOLDER
    annotated_dir.mkdir(parents=True, exist_ok=True)

    save_name = f"{frame_index:04d}_" + Path(image_id).name
    save_path = annotated_dir / save_name

    combined.save(save_path, format="PNG")
    print(f"  Annotated image saved: {save_path}")

# =============================
# GRAPH BUILDING (Graphviz)
# =============================

def build_causal_graph_for_frame(frame: dict,
                                 json_base_name: str,
                                 frame_index: int,
                                 out_dir: Path):
    image_id = frame.get("image_id", f"frame_{frame_index:04d}")
    nodes = frame.get("graph", {}).get("nodes", [])
    safety_text = frame.get("safe", "")

    # Graph name and base output path
    safe_image_id = image_id.replace("/", "_").replace(".", "_")
    out_base = out_dir / f"{frame_index:04d}_{safe_image_id}"

    g = Digraph(
        name=f"causal_{json_base_name}_{frame_index:04d}",
        comment=f"Causal graph for {image_id}",
        format=GRAPH_FORMAT,
    )

    # Basic styles
    g.attr("node", style="filled", shape="ellipse", fontname="Helvetica")
    g.attr("edge", fontname="Helvetica")

    # Background color based on global safety flag
    global_safety = determine_safety_status(safety_text)
    if global_safety == "unsafe":
        g.attr(bgcolor="mistyrose")
    elif global_safety == "safe":
        g.attr(bgcolor="honeydew")

    existing_nodes = set()

    # --- 1) Add main object nodes ---
    for raw_node_id, attrs in nodes:
        node_id = canonical_id(raw_node_id)
        obj_name = attrs.get("obj_name") or clean_name(raw_node_id)
        importance = attrs.get("importance_ranking")
        status = attrs.get("Status") or []
        object_safety = attrs.get("Object_Safety") or []

        if isinstance(status, list):
            status_str = ", ".join(status)
        else:
            status_str = str(status)

        label_parts = [obj_name]
        if importance and importance.lower() != "none":
            label_parts.append(f"[importance: {importance}]")
        if status_str:
            label_parts.append(status_str)

        label = "\n".join(label_parts)
        fillcolor = pick_safety_color(object_safety)
        fontcolor = "black"

        # Ego bigger & color by global safety
        if is_ego_node(raw_node_id, attrs):
            if global_safety == "unsafe":
                fillcolor = "red"
            elif global_safety == "safe":
                fillcolor = "green"

            g.node(
                node_id,
                label=label,
                fillcolor=fillcolor,
                fontcolor=fontcolor,
                shape="doublecircle",
                penwidth="3",
                fontsize="18",
                width="1.3",
                height="1.3",
            )
        else:
            g.node(
                node_id,
                label=label,
                fillcolor=fillcolor,
                fontcolor=fontcolor,
            )

        existing_nodes.add(node_id)

    # --- 2) Add status & position nodes ---
    for raw_node_id, attrs in nodes:
        base_id = canonical_id(raw_node_id)
        status = attrs.get("Status") or []
        position = attrs.get("position") or []

        if status:
            if isinstance(status, list):
                status_str = ", ".join(status)
            else:
                status_str = str(status)

            status_node_id = f"{base_id}_status"
            g.node(
                status_node_id,
                label=f"Status: {status_str}",
                shape="box",
                fillcolor=status_color,
            )
            g.edge(base_id, status_node_id, style="dotted", color="gray")

        if position:
            if isinstance(position, list):
                pos_str = ", ".join(position)
            else:
                pos_str = str(position)

            pos_node_id = f"{base_id}_pos"
            g.node(
                pos_node_id,
                label=f"Position: {pos_str}",
                shape="box",
                fillcolor=position_color,
            )
            g.edge(base_id, pos_node_id, style="dotted", color="gray")

    # --- 3) Add causal edges (for ALL Causal_Relation) ---
    for raw_node_id, attrs in nodes:
        src_id = canonical_id(raw_node_id)
        raw_target = attrs.get("Object_Causal") or attrs.get("object_causal")
        relation = attrs.get("Causal_Relation")
        importance = attrs.get("importance_ranking")

        # Use all relations that have a target and a Causal_Relation
        if not (raw_target and relation):
            continue

        tgt_id = canonical_id(raw_target)

        if tgt_id not in existing_nodes:
            g.node(tgt_id, label=clean_name(raw_target), fillcolor="white", fontcolor="black")
            existing_nodes.add(tgt_id)

        relation_color = relation_to_color(relation)
        label_color = importance_to_color(importance)
        penwidth = "2" if (importance and importance.strip().lower() == "high") else "1.2"

        g.edge(
            src_id,
            tgt_id,
            label=relation,
            color=relation_color,
            fontcolor=label_color,
            penwidth=penwidth,
        )

    # --- 4) Legend ---
    add_legend(g)

    # --- 5) Save DOT and render ---
    out_dir.mkdir(parents=True, exist_ok=True)

    g.save(str(out_base) + ".dot")
    g.render(filename=str(out_base), cleanup=True)
    print(f"  Graph: {out_base}.{GRAPH_FORMAT} and {out_base}.dot")

    # --- 6) Annotated image ---
    annotate_image_for_frame(
        frame=frame,
        nodes=nodes,
        json_base_name=json_base_name,
        frame_index=frame_index,
        out_dir=out_dir,
        global_safety=global_safety,
    )


# =============================
# MAIN LOOP
# =============================

def main():
    input_dir = Path(INPUT_DIR)
    output_root = Path(OUTPUT_DIR)
    output_root.mkdir(parents=True, exist_ok=True)

    for json_path in input_dir.glob("*.json"):
        json_base_name = json_path.stem
        print(f"Processing {json_path.name} ...")

        json_out_dir = output_root / json_base_name
        json_out_dir.mkdir(parents=True, exist_ok=True)

        try:
            with json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  Skipping {json_path.name} (JSON error: {e})")
            continue

        if not isinstance(data, list):
            print(f"  Skipping {json_path.name} (top-level is not a list of frames)")
            continue

        for idx, frame in enumerate(data):
            build_causal_graph_for_frame(
                frame=frame,
                json_base_name=json_base_name,
                frame_index=idx,
                out_dir=json_out_dir,
            )


if __name__ == "__main__":
    main()
