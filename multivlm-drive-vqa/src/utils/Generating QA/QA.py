import os
import json
import logging
import re
from shapely.geometry import Polygon, MultiPoint

# ------------------------------------------------------------
# Configure logging
# ------------------------------------------------------------
logging.basicConfig(
    filename='QA_generation.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# ========================= Helper Functions =============================
def determine_scenario(frame_data, image_id):
    """
    Determines the scenario type based on the image_id and objects' causal relations.
    
    Returns:
      - ("Attack", <description>) if image_id contains GaussianNoise, RandomNoise, or StickerPatch.
      - ("miss_detected", <description>) if image_id contains WhitePatch or BlackPatch.
      - ("OoD", <description>) if OoD-related objects are detected.
      - ("normal", "None") otherwise.
      
    Additionally, this function builds lists for all objects that have an attack indication and those that are considered Out-of-Distribution (OoD).
    """
    objects = frame_data.get('graph', {}).get('nodes', [])
    traffic_regulations = frame_data.get("Traffic Regulations Suggestions", "").strip()

    attack_objects = []
    noise_objects = []
    ood_objects = []
    for obj_id, obj_info in objects:
        obj_name = obj_info.get("obj_name", "").strip()
        boxes = obj_info.get("boxes", "")
        position = extract_position_description(obj_info)
        object_safety = obj_info.get("Object_Safety", [])
        
        # Only consider objects that affect safety.
        if "Affects Safety" in object_safety:
            # Check if the object is marked as causal.
            if obj_info.get("Is_causal", "").lower() == "cause":
                causal_relation = obj_info.get("Causal_Relation", "").lower()
                if "attack" in causal_relation:
                    attack_objects.append(f"{obj_name} <bb>{boxes}</bb> and positions: ({position})")
                elif "ood" in causal_relation:
                    ood_objects.append(f"{obj_name} <bb>{boxes}</bb> and positions: ({position})")
                elif "noise" in causal_relation:
                    noise_objects.append(f"{obj_name} <bb>{boxes}</bb> and positions: ({position})")
                    
    attack_desc = ""
    if attack_objects:
        attack_desc = "Attack objects detected: " + ", ".join(attack_objects) + ". "
    ood_desc = ""
    if ood_objects:
        ood_desc = "Out-of-Distribution objects detected: " + ", ".join(ood_objects) + ". "
    noise_desc = ""
    if ood_objects:
        noise_desc = "noise objects detected: " + ", ".join(ood_objects) + ". "
    
    
    elif any(x in image_id for x in ["WhitePatch", "BlackPatch"]):
        return "miss_detected", "The situation does not correspond to the overall scene, causing it to seem as though there needs to be some traffic rules "
    else:
        return "normal", "None"
    # Check image_id for known attack patterns.
    if any(x in image_id for x in ["GaussianNoise", "RandomNoise","StickerPatch"]):
        if noise_objects:
            return "Attack", ("The traffic sign does not align with the current situation, making it appear as though there is attacking noise on the object. " + noise_desc)
        if attack_objects:
            return "Attack", ("The situation for this traffic sign does not correspond to the overall scene, causing it to seem as though there is an attack using SitAttack. " + attack_desc)
        if ood_objects:
            return "OoD", ("The situation for this traffic sign does not correspond to the overall scene, causing it to seem as though there is an Out-of-Distribution objects detected. " + ood_desc)
    elif any(x in image_id for x in ["WhitePatch", "BlackPatch"]):
        return "miss_detected", ("The situation does not correspond to the overall scene, causing it to seem as though some traffic rules are not being followed. " + traffic_regulations)
    else:
        return "normal", "None"

def determine_safety_status(safety_status):
    # A simple check (can be further refined)
    if "unsafe" in safety_status.lower() or "no" in safety_status.lower():
        return "no", safety_status
    elif "safe" in safety_status.lower() or "yes" in safety_status.lower():
        return "Yes", safety_status
    else:
        return None, f"Ambiguous safety status: {safety_status}"

def extract_position_description(obj_info):
    """
    Joins the list of position strings into a single human-readable phrase.
    """
    position_data = obj_info.get("position", [])
    if isinstance(position_data, list):
        return ", ".join(pos.strip() for pos in position_data if pos.strip())
    return ""

def extract_status_description(obj_info):
    """
    Joins the list of position strings into a single human-readable phrase.
    """
    status_data = obj_info.get("status", [])
    if isinstance(status_data, list):
        return ", ".join(pos.strip() for pos in status_data if pos.strip())
    return ""

def categorize_turn_signs(objects):
    """
    Returns two sets: prohibited_turns and allowed_turns.
    """
    prohibited_turns = set()
    allowed_turns = set()
    for obj_id, obj_info in objects:
        label = obj_info.get("obj_name", "").strip().lower()
        if label in ["ts_no_u_turn", "ts_no_left_turn", "ts_no_right_turn", "ts_no_left_u_turn"]:
            if "no_u_turn" in label:
                prohibited_turns.add("No u-turn")
            if "no_left_turn" in label:
                prohibited_turns.add("No left")
            if "no_right_turn" in label:
                prohibited_turns.add("No right")
            if "ts_no_left_u_turn" in label:
                prohibited_turns.add("No Left U-Turn")
        elif label in ["ts_only_left_turn", "ts_only_right_turn", "ts_only_u_turn"]:
            if "only_left_turn" in label:
                allowed_turns.add("left")
            if "only_right_turn" in label:
                allowed_turns.add("right")
            if "only_u_turn" in label:
                allowed_turns.add("u-turn")
    return prohibited_turns, allowed_turns

def categorize_directional_arrows(objects):
    """
    Returns a set of allowed directions from directional arrow signs.
    """
    allowed_directions = set()
    for obj_id, obj_info in objects:
        label = obj_info.get("obj_name", "").strip().lower()
        if label in [
            "right directional arrow",
            "straight directional arrow",
            "left directional arrow",
            "left and straight directional arrow",
            "right and straight directional arrow"
        ]:
            if label == "right directional arrow":
                allowed_directions.add("right")
            elif label == "straight directional arrow":
                allowed_directions.add("straight")
            elif label == "left directional arrow":
                allowed_directions.add("left")
            elif label == "left and straight directional arrow":
                allowed_directions.update(["left", "straight"])
            elif label == "right and straight directional arrow":
                allowed_directions.update(["right", "straight"])
    return allowed_directions

def determine_intended_turn(steering):
    """
    Returns 'left', 'right', or 'straight' based on the steering angle.
    """
    if steering is None:
        return "unknown"
    elif steering < -5:
        return "left"
    elif steering > 5:
        return "right"
    else:
        return "straight"

def determine_importance_reasoning(obj_name, importance, position, status, goal):
    """
    Returns a text explanation for why an object is important.
    If the object name contains 'attack' (case-insensitive), an extra sentence is appended.
    """
    if importance not in ["low", "none"]:
        reasoning = f"The {obj_name} has an importance ranking of '{importance}'."
        if position:
            reasoning += f" It is located {position}."
        if status:
            reasoning += f" Its current status is {', '.join(status)}."
        if goal and importance == "high":
            reasoning += f" This object must be accounted for to achieve the goal: {goal}."
        if "attack" in obj_name.lower():
            reasoning += " This object appears to be associated with an attack scenario, requiring extra verification of situation according to other objects in scene."
        return reasoning

def determine_safety_reasoningSS(safety_status, ego_status, speed, steering):
    """
    Returns a detailed safety explanation.
    """
    if safety_status == "no":
        safety_reason = "The scene is unsafe due to the current conditions."
        if ego_status:
            safety_reason += f" The ego vehicle status is {', '.join(ego_status)}."
        if speed is not None and speed != 0:
            safety_reason += f" The ego vehicle is moving at {speed} MPh, which may be inappropriate."
        if steering is not None:
            direction = "straight" if steering == 0 else ("left" if steering < 0 else "right")
            safety_reason += f" The steering angle is {steering}° indicating a turn to the {direction}."
    else:
        safety_reason = "The scene is safe"
        if speed is not None and speed != 0:
            safety_reason += f" The ego vehicle is moving at a safe speed of {speed} MPh."
        if steering is not None:
            direction = "straight" if steering == 0 else ("left" if steering < 0 else "right")
            safety_reason += f" The steering angle is {steering}° indicating a turn to the {direction}."
    return safety_reason

def identify_high_ranking_objects(objects, ranking_threshold="high"):
    """
    Returns a list of object names (with positions) that have high importance and affect safety.
    """
    high_ranking_objects = []
    for obj_id, obj_info in objects:
        importance = obj_info.get("importance_ranking", "").lower()
        object_safety = obj_info.get("Object_Safety", [])
        if importance == ranking_threshold and "Affects Safety" in object_safety:
            obj_name = obj_info.get("obj_name", "").strip()
            status = extract_status_description(obj_info)
            position = extract_position_description(obj_info)
            high_ranking_objects.append(f"{obj_name} (positions: {position}, Status: {status})")
    return high_ranking_objects

def detect_markings(objects):
    """
    Identify road markings.
    """
    markings_list = []
    road_marking_labels = {
        "stop marking", "marking speed_limit_20", "pedestrian crossing marking",
        "bicycle lane", "lane marking", "hazard_zone", "speed_bump"
    }
    for obj_id, obj_info in objects:
        obj_name = obj_info.get("obj_name", "").strip().lower()
        if obj_name in road_marking_labels:
            markings_list.append({
                "obj_id": obj_id,
                "obj_name": obj_info.get("obj_name", ""),
                "position": obj_info.get("position", []),
                "status": obj_info.get("Status", "Unknown"),
                "importance": obj_info.get("importance_ranking", ""),
                "object_safety": obj_info.get("Object_Safety", [])
            })
    return markings_list

def detect_traffic_signs(objects):
    """
    Identify traffic signs.
    """
    traffic_sign_list = []
    traffic_sign_labels = {
        "ts_stop", "ts_yield", "ts_speed_limit_15", "ts_speed_limit_20", "ts_speed_limit_25",
        "ts_speed_limit_30", "ts_speed_limit_40", "ts_speed_limit_45", "ts_speed_limit_50",
        "ts_speed_limit_60", "ts_speed_limit_70", "ts_speed_limit_80", "ts_railroad_crossing",
        "railway_crossing_ahead_skew_left", "railway_crossing_ahead_skew_right",
        "ts_pedestrian_crossing", "ts_keep_left_road", "ts_keep_right_road", "ts_no_entry",
        "ts_parking", "ts_no_parking", "ts_school_zone", "ts_directional", "ts_warning",
        "ts_no_u_turn", "ts_no_left_u_turn", "ts_no_left_turn", "ts_no_right_turn", "ts_hospital",
        "ts_road_work", "ts_traffic_signal_ahead", "ts_roundabout_ahead", "ts_bus_stop",
        "ts_bicycle_crossing", "ts_construction_sign"
    }
    for obj_id, obj_info in objects:
        obj_name = obj_info.get("obj_name", "").strip().lower()
        if obj_name in traffic_sign_labels:
            traffic_sign_list.append({
                "obj_id": obj_id,
                "obj_name": obj_info.get("obj_name", ""),
                "position": obj_info.get("position", []),
                "boxes": obj_info.get("boxes", []),
                "Object_Causal": obj_info.get("Object_Causal",""),
                "Causal_Relation": obj_info.get("Causal_Relation",""),
                "Is_causal": obj_info.get("Is_causal", ""),
                "status": obj_info.get("Status", "Unknown"),
                "importance": obj_info.get("importance_ranking", ""),
                "object_safety": obj_info.get("Object_Safety", [])
            })
    return traffic_sign_list

def generate_rule_description(sign_name, boxes):
    """
    Generate a rule description based on the traffic sign identifier.
    
    This function covers all of the following types:
      - TS_Stop
      - TS_Yield
      - TS_Speed_Limit_XX (e.g., TS_Speed_Limit_15, TS_Speed_Limit_20, etc.)
      - TS_Railroad_Crossing
      - TS_Pedestrian_Crossing
      - TS_No_Entry
      - TS_Parking
      - TS_No_Parking
      - TS_School_Zone
      - TS_Directional (optionally with direction words: North, South, East, West)
      - TS_Warning
      - TS_No_U_Turn, TS_No_Left_Turn, TS_No_Right_Turn
      - TS_Hospital
      - TS_Road_Work
      - TS_Traffic_Signal_Ahead
      - TS_Roundabout_Ahead
      - TS_Bus_Stop
      - TS_Bicycle_Crossing
      - TS_keep_left_road, TS_keep_right_road
      - TS_No_left_U_Turn
      - Railway_Crossing_Ahead_Skew_Left
    """
    # Default rule description in case none of the conditions match.
    rule_description = f"{sign_name.replace('_', ' ').title()} sign imposes a rule requiring compliance."
    
    if sign_name.startswith("TS_Stop"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: Stop means the ego vehicle must come to a complete stop."
    elif sign_name.startswith("TS_Yield"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: Yield means the ego vehicle should give right-of-way to cross traffic."
    elif sign_name.startswith("TS_Speed_Limit"):
        speed_num = re.findall(r'\d+', sign_name)
        if speed_num:
            rule_description = f" <bb>{boxes}</bb>: The speed limit is {speed_num[0]} mph (or kph). The ego vehicle must not exceed this limit."
        else:
            rule_description = f" {sign_name} <bb>{boxes}</bb>:  A speed limit sign is detected; obey the specified speed limit."
            
    elif sign_name.startswith("TS_Railroad_Crossing"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: There is a railroad crossing ahead; reduce speed and be prepared to stop if necessary."
        
    elif sign_name.startswith("TS_Pedestrian_Crossing"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: There is a pedestrian crossing ahead; exercise caution and yield to pedestrians."
        
    elif sign_name.startswith("TS_No_Entry"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: No entry means the ego vehicle must not enter this road or area."
        
    elif sign_name.startswith("TS_Parking"):
        # You can adjust this if your system differentiates between parking and no parking.
        rule_description = f" {sign_name} <bb>{boxes}</bb>: Parking is allowed only in designated areas. Please check local regulations."
        
    elif sign_name.startswith("TS_No_Parking"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: No parking is allowed in the designated area."
    elif sign_name.startswith("TS_School_Zone"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: You are approaching a school zone; reduce speed and exercise caution due to children and school traffic."
        
    elif sign_name.startswith("TS_Warning"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: Warning signs indicate potential hazards. Proceed with caution."
        
    elif sign_name.startswith("TS_No_U_Turn"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: No U-turn is permitted here."
        
    elif sign_name.startswith("TS_No_Left_Turn"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: No left turn is permitted here."
        
    elif sign_name.startswith("TS_No_Right_Turn"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: No right turn is permitted here."
        
    elif sign_name.startswith("TS_Hospital"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: This sign indicates a hospital ahead; be cautious of emergency vehicles and pedestrians."
        
    elif sign_name.startswith("TS_Road_Work"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: Road work ahead; reduce speed and follow detour signs if provided."
    elif sign_name.startswith("TS_Traffic_Signal_Ahead"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: There is a traffic signal ahead; be prepared to stop or yield as needed."
    elif sign_name.startswith("TS_Roundabout_Ahead"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: There is a roundabout ahead; reduce speed and yield to traffic circulating within."
    elif sign_name.startswith("TS_Bus_Stop"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: This indicates a bus stop; be prepared to yield to boarding or alighting passengers."
    elif sign_name.startswith("TS_Bicycle_Crossing"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: A bicycle crossing is ahead; watch for cyclists and yield if necessary."
    elif sign_name.startswith("TS_keep_left_road"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: Keep left on the road; this sign directs vehicles to stay to the left."
    elif sign_name.startswith("TS_keep_right_road"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: Keep right on the road; this sign directs vehicles to stay to the right."
    elif sign_name.startswith("TS_No_left_U_Turn"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: No left U-turn is permitted here."
    elif sign_name.startswith("Railway_Crossing_Ahead_Skew_Left"):
        rule_description = f" {sign_name} <bb>{boxes}</bb>: There is a railway crossing ahead, skewed to the left; slow down and look out for trains."
    
    return rule_description

def detect_traffic_lights(objects):
    """
    Identify traffic lights.
    """
    traffic_light_list = []
    traffic_light_labels = {"traffic light", "traffic light pedestrian"}
    for obj_id, obj_info in objects:
        obj_name = obj_info.get("obj_name", "").strip().lower()
        if obj_name in traffic_light_labels:
            traffic_light_list.append({
                "obj_id": obj_id,
                "obj_name": obj_info.get("obj_name", ""),
                "position": obj_info.get("position", []),
                "light_status": obj_info.get("Status", "Unknown"),
                "TL_importance": obj_info.get("importance_ranking", ""),
                "TL_object_safety": obj_info.get("Object_Safety", [])
            })
    return traffic_light_list

def group_objects(frame_data):
    """
    Filter out objects with low or no importance and that do not affect safety.
    Then group the remaining objects into:
    - Infrastructure
    - Vehicles
    - Road Users
    - traffic sign
    The classification is done via keywords in the object's name.
    """
    nodes = frame_data.get("graph", {}).get("nodes", [])
    
    # Define keyword sets for grouping
    infra_keywords = {"road", "t-intersection", "intersection", "bridge", "traffic light", "marking", "lane", "sign", "crossing", "bollard", "barrier", "pedestrian crossing"}
    vehicle_keywords = {"ego", "car", "truck", "bus", "motorcycle", "police", "ambulance", "fire"}
    road_user_keywords = {"pedestrian", "cyclist", "bicycle", "skateboard", "stroller", "dog"}
    traffic_sign_keywords = {"ts_stop", "ts_yield", "ts_speed_limit", "ts_no_entry", "ts_no_parking","ts_directional", "ts_warning", "ts_no_u_turn", "ts_no_left_turn", "ts_no_right_turn","ts_only_left_turn", "ts_only_right_turn", "ts_only_u_turn"}
    traffic_signs = []
    infra_objs = []
    vehicle_objs = []
    road_user_objs = []
    
    for node in nodes:
        # Get importance ranking; assume the field is "importance_ranking"
        importance = node.get("importance_ranking", "").lower()
        if importance in ["low", "none", ""]:
            continue  # Ignore low or undefined importance
        
        # Check safety flags; assume the field "Object_Safety" is a list of flags
        safety_flags = node.get("Object_Safety", [])
        if not any(flag in safety_flags for flag in ["Affects Safety", "Potentially Affect Safety"]):
            continue  # Ignore objects that do not affect safety
        
        obj_name = node.get("obj_name", "").lower()
        # Group based on keywords found in the object name
        if any(kw in obj_name for kw in infra_keywords):
            infra_objs.append(node)
        elif any(kw in obj_name for kw in vehicle_keywords):
            vehicle_objs.append(node)
        elif any(kw in obj_name for kw in road_user_keywords):
            road_user_objs.append(node)
        # Check if any traffic sign keyword appears in the object name.
        if any(ts_kw in obj_name for ts_kw in traffic_sign_keywords):
            traffic_signs.append(node)    
    return infra_objs, vehicle_objs, road_user_objs, traffic_signs

# ====================== Q&A Generation Functions =========================

# def generate_expert_planning_humanized_qa(frame_data):
#     """
#     Generate a humanized, expert-level planning Q&A pair for an autonomous driving car.
    
#     The answer is structured as a chain-of-thought that:
#       1. Assesses the situation (metadata, safety, caption).
#       2. Defines the driving objective (goal and maneuver).
#       3. Analyzes the environment by grouping objects into:
#          - Infrastructure (e.g., intersections, crosswalks, bridges)
#          - Traffic Signs (all signs such as stop, yield, speed limit, directional)
#          - Vehicles
#          - Road Users
#       4. Explains inter-object relations (e.g., an intersection is regulated by a traffic light and yield sign).
#       5. Evaluates risks and makes a planning recommendation.
#     """
#     # --- Step 1: Situation Assessment ---
#     image_id = frame_data.get("image_id", "unknown")
#     safe_field = frame_data.get("safe", "unknown")
#     causes = frame_data.get("cause", [])
#     caption = frame_data.get("caption", "none")
#     causes_str = ", ".join(causes) if causes else "None"
    
#     # --- Step 2: Objective Definition ---
#     goal = frame_data.get("goal-oriented", "unknown")
#     maneuver = frame_data.get("maneuver", "unknown")
    
#     # --- Step 3: Environmental & Object Analysis ---
#     infra_objs, vehicle_objs, road_user_objs, traffic_signs = group_objects(frame_data)
    
#     # Format summaries for each group
#     def format_obj_list(obj_list):
#         lines = []
#         for obj in obj_list:
#             name = obj.get("obj_name", "unknown")
#             pos = extract_position_description(obj)
#             lines.append(f"{name} at [{pos}]")
#         return "; ".join(lines) if lines else "None"
    
#     infra_summary = format_obj_list(infra_objs)
#     vehicle_summary = format_obj_list(vehicle_objs)
#     road_user_summary = format_obj_list(road_user_objs)
#     traffic_sign_summary = format_obj_list(traffic_signs)
    
#     # Analyze infrastructure relations for common scenarios.
#     infra_narrative = ""
#     # Example: if there is an intersection, crosswalk, or pedestrian crossing.
#     for obj in infra_objs:
#         name = obj.get("obj_name", "").lower()
#         pos = extract_position_description(obj)
#         if "intersection" in name or "t-intersection" in name:
#             infra_narrative += f"I notice an intersection at [{pos}]. "
#         if "crosswalk" in name or "pedestrian crossing" in name:
#             infra_narrative += f"A crosswalk is present at [{pos}], which suggests pedestrian activity. "
    
#     if traffic_sign_summary != "None":
#         infra_narrative += f"The following traffic signs are observed: {traffic_sign_summary}. "
    
#     # --- Step 4: Maneuver Planning & Risk Evaluation ---
#     speed = frame_data.get("speed", "unknown")
#     steering = frame_data.get("steering", "unknown")
#     traffic_regulations = frame_data.get("Traffic Regulations Suggestions", "none")
#     action_suggestions = frame_data.get("Action Suggestions", "none")
    
#     # --- Step 5: Safety Evaluation & Final Recommendation ---
#     if "unsafe" in safe_field.lower() or "no" in safe_field.lower():
#         safety_evaluation = ("I assess the scene as unsafe—likely due to heavy traffic or ambiguous signals, "
#                              "which is further complicated by pedestrian zones or conflicting traffic signs.")
#         recommended_action = ("I recommend that the vehicle slow down, re-assess its maneuver, and yield when necessary, "
#                               "especially at the intersection or near the crosswalk. Caution and readiness to adjust are key.")
#     else:
#         safety_evaluation = ("The scene appears safe with clear signals and minimal hazards, although continuous vigilance is advised.")
#         recommended_action = ("The vehicle may proceed with its planned maneuver while keeping a close watch on the environment, "
#                               "particularly the traffic signs and pedestrian areas, to adjust if conditions change.")
    
    
#     # --- Compose the Chain-of-Thought Explanation ---
#     steps = []
#     steps.append("**Step 1: Situation Assessment**")
#     steps.append(f"- **Image ID:** {image_id}")
#     steps.append(f"- **Safety Status:** {safe_field} (Causes: {causes_str})")
#     steps.append(f"- **Caption:** {caption}")
#     steps.append("")
    
#     steps.append("**Step 2: Objective & Intent**")
#     steps.append(f"- **Goal:** {goal}")
#     steps.append(f"- **Intended Maneuver:** {maneuver}")
#     steps.append("")
    
#     steps.append("**Step 3: Environmental & Object Analysis**")
#     steps.append(f"- **Infrastructure:** {infra_summary}")
#     if infra_narrative:
#         steps.append(f"  * Detailed Insight: {infra_narrative}")
#     steps.append(f"- **Traffic Signs:** {traffic_sign_summary}")
#     steps.append(f"- **Vehicles:** {vehicle_summary}")
#     steps.append(f"- **Road Users:** {road_user_summary}")
#     steps.append("")
    
#     steps.append("**Step 4: Maneuver Planning & Risk Evaluation**")
#     steps.append(f"- **Vehicle Dynamics:** Speed = {speed}, Steering = {steering}")
#     steps.append(f"- **Traffic Regulations & Suggestions:** {traffic_regulations}; {action_suggestions}")
#     steps.append("")
    
#     steps.append("**Step 5: Safety Evaluation & Action Recommendation**")
#     steps.append(f"- **Safety Evaluation:** {safety_evaluation}")
#     steps.append(f"- **Recommended Action:** {recommended_action} (in line with the goal '{goal}')")
    
#     full_answer = "\n".join(steps)
    
#     # --- Build the Final Q&A Pair ---
#     qa_pair = {
#         "Q": "What is the planning decision for this driving scenario?",
#         "A": full_answer,
#         "Type": "Association",
#         "Task": "planning",
#         "question_task": "Expert Driving Planning",
#         "AV_Task": "Risk Detection",
#         "scene_scenario": frame_data.get("scene_scenario", "unknown")
#     }
#     return qa_pair

def generate_object_safety_categorization_qa(objects, scenario, scenario_type, predefined_categories=None):
    """
    Generate Q&A pairs for objects based on the combination of their 'Object_Safety'
    categories. If an object belongs to more than one category (for example,
    "Affects Safety" and "Requires Monitoring"), a combined question is generated.
    
    Args:
        objects (list): A list of tuples (obj_id, obj_info) where obj_info is a dict.
        scenario (str): Scenario information to be attached in each Q&A.
        scenario_type (str): (Unused in this example but kept for consistency.)
        predefined_categories (list, optional): List of safety categories. Defaults to None.
    
    Returns:
        list: A list of dictionaries, each representing a Q&A pair.
    """
    if predefined_categories is None:
        predefined_categories = [
            "Affects Safety",
            "Potentially Affect Safety",
            "Does Not Affect Safety",
            "Requires Monitoring"
        ]
    
    # Define phrases for each category to be used in questions and answers.
    category_phrases = {
        "Affects Safety": "affect safety",
        "Potentially Affect Safety": "potentially affect safety",
        "Does Not Affect Safety": "do not affect safety",
        "Requires Monitoring": "require monitoring"
    }
    
    # Group objects by the sorted tuple of safety categories they belong to.
    groups = {}
    for obj_id, obj_info in objects:
        obj_name = obj_info.get("obj_name", "").strip()
        # Only include valid categories from the predefined list.
        obj_categories = [cat for cat in obj_info.get("Object_Safety", []) if cat in predefined_categories]
        if not obj_categories:
            continue
        # Create a consistent key (a sorted tuple) for the combination of categories.
        key = tuple(sorted(obj_categories))
        groups.setdefault(key, set()).add(obj_name)
    
    qa_pairs = []
    for category_combo, obj_names in groups.items():
        # Build the combined phrase (e.g., "affect safety and require monitoring")
        phrases = [category_phrases[cat] for cat in category_combo]
        combined_phrase = " and ".join(phrases)
        
        # Formulate the question
        question = f"Which objects {combined_phrase}?"
        
        # Formulate the answer based on how many objects are in this group.
        sorted_obj_names = sorted(obj_names)
        if len(sorted_obj_names) == 1:
            answer = f"The object that {combined_phrase} is: {sorted_obj_names[0]}."
        else:
            answer = f"The following objects {combined_phrase} are: {', '.join(sorted_obj_names)}."
        
        qa_pairs.append({
            "Q": question,
            "A": answer,
            "Type": "Intervention",
            "Task": "Safety-Based Questions",
            "question_task": "Risk & Anomaly Detection",
            "AV_Task": "plan",
            "scene_scenario": scenario
        })
    
    return qa_pairs

def generate_traffic_markings_qa(ts_and_markings, scenario, scenario_type):
    """
    Generate Q&A for traffic road markings.
    """
    qa_list = []
    if not ts_and_markings:
        return qa_list
    names = [item['obj_name'] for item in ts_and_markings]
    unique_names = set(names)
    qa_list.append({
        "Q": "Which traffic road markings are present in the scene?",
        "A": f"road markings are present: {', '.join(unique_names)}.",
        "Type": "Discovery",
        "Task": "Object-Centric Questions",
        "question_task": "object direction",
        "AV_Task": "perception",
        "scene_scenario": scenario,
    })
    
    qa_list.append({
        "Q": "How many traffic road markings are present in the scene?",
        "A": f"the Number of road markings are present: {len(ts_and_markings)}",
        "Type": "Discovery",
        "Task": "Object-Centric Questions",
        "question_task": "Counting",
        "AV_Task": "perception",
        "scene_scenario": scenario,
    })
    
    for item in ts_and_markings:
        name = item["obj_id"]
        position = item["position"]
        status = item["status"]
        if isinstance(status, list):
            status_str = ', '.join(status) if status else "No status"
        else:
            status_str = str(status) if status else "No status"
        qa_list.append({
            "Q": f"Where is the {name} located?",
            "A": f"{name} is located at {position}",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "Position Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        qa_list.append({
            "Q": f"Where is the {name} status?",
            "A": f"{name} is status: {status_str}",
            "Type": "Discovery",
            "Task": "State Identification",
            "question_task": "State Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        qa_list.append({
            "Q": f"Where is the {name} located, and what is its status?",
            "A": f"{name} is located at {position}, with status: {status_str}",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "Position and State Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    return qa_list

def generate_traffic_sign_qa(traffic_signs, scenario, scenario_type):
    """
    Generate Q&A for traffic signs.
    """
    qa_list = []
    if not traffic_signs:
        return qa_list
    sign_names = [ts['obj_name'] for ts in traffic_signs]
    sign_positions = [ts['position'] for ts in traffic_signs]
    
    
    qa_list.append({
        "Q": "Which traffic signs are present in the scene, and where are they located?",
        "A": f"Traffic signs found: {', '.join(sign_names)} at positions {', '.join(str(pos) for pos in sign_positions)}",
        "Type": "Discovery",
        "Task": "Object-Centric Questions",
        "question_task": "object direction",
        "AV_Task": "perception",
        "scene_scenario": scenario,
    })
    qa_list.append({
        "Q": "How many traffic signs are present in the scene?",
        "A": f"number of traffic signs: {', '.join(sign_names)}. Total count: {len(traffic_signs)}",
        "Type": "Discovery",
        "Task": "Object-Centric Questions",
        "question_task": "Counting",
        "AV_Task": "perception",
        "scene_scenario": scenario,
    })
    for sign in traffic_signs:
        sign_name = sign['obj_name'].lower()
        sign_position = sign['position']
        status = sign["status"]
        boxes= str(sign["boxes"])
        if isinstance(status, list):
            status_str = ', '.join(status) if status else "No status"
        else:
            status_str = str(status) if status else "No status"
        qa_list.append({
            "Q": f"Where is the {sign_name} located, and what is its status?",
            "A": f"{sign_name} is located at {sign_position} <bb>{boxes}</bb>",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "Position Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        qa_list.append({
            "Q": f"Where is the {sign_name} located, and what is its status?",
            "A": f"{sign_name} status: {status_str}",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "State Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        qa_list.append({
            "Q": f"Where is the {sign_name} located, and what is its status?",
            "A": f"{sign_name} is located at {sign_position} <bb>{boxes}</bb>, with status: {status_str}",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "Position and State Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        
        rule_description = generate_rule_description(sign_name, boxes)
        qa_list.append({
            "Q": f"What rule does the {sign.get('obj_name', sign_name)} at position {sign_position} impose?",
            "A": rule_description,
            "Type": "Association",
            "Task": "Context-Based Questions",
            "question_task": "Scene Classification",
            "AV_Task": "plan",
            "scene_scenario": scenario,
        })
        
    return qa_list

def generate_traffic_light_qa(traffic_lights, scenario, scenario_type):
    """
    Generate Q&A for traffic lights.
    """
    qa_list = []
    if not traffic_lights:
        return qa_list
    
    # Q&A for overall count of traffic lights.
    num_lights = len(traffic_lights)
    qa_list.append({
        "Q": "How many traffic lights are present in the scene?",
        "A": f"There {'is' if num_lights == 1 else 'are'} {num_lights} traffic light{'s' if num_lights != 1 else ''} detected.",
        "Type": "Discovery",
        "Task": "Object-Centric Questions",
        "question_task": "Counting",
        "AV_Task": "perception",
        "scene_scenario": scenario,
    })
    # For each traffic light, split the Q&A into multiple questions.
    for tl in traffic_lights:
        obj_name = tl.get("obj_name", "traffic light")
        boxes= tl.get("boxes","")
        # Q&A for position.
        pos_list = tl.get("position", [])
        position = " ".join(pos_list) if pos_list else "an unknown position"
        qa_list.append({
            "Q": f"Where is the {obj_name} <bb>{boxes}</bb> located?",
            "A": f"The {obj_name} <bb>{boxes}</bb> is located at {position}.",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "object direction",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        
        # Q&A for status.
        status_list = tl.get("Status", [])
        status = " ".join(status_list) if status_list else "status unknown"
        qa_list.append({
            "Q": f"What is the current status of the {obj_name} <bb>{boxes}</bb> ?",
            "A": f"The current status of the {obj_name} <bb>{boxes}</bb>  is {status}.",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "State Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        
        # Q&A for importance ranking.
        importance = tl.get("importance_ranking", "not specified")
        qa_list.append({
            "Q": f"What is the importance ranking of the {obj_name} <bb>{boxes}</bb> ?",
            "A": f"The {obj_name} <bb>{boxes}</bb>  has a {importance} importance ranking.",
            "Type": "Association",
            "Task": "Context-Based Questions",
            "question_task": "Relationship",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        
        # Q&A for safety annotations.
        safety_objects = tl.get("Object_Safety", [])
        safety_text = ", ".join(safety_objects) if safety_objects else "no specific safety affecting"
        qa_list.append({
            "Q": f"What is affecting the ego's safety from this {obj_name} <bb>{boxes}</bb>?",
            "A": f"The {obj_name} is associated with the following safety: {safety_text}.",
            "Type": "Association",
            "Task": "Context-Based Questions",
            "question_task": "Relationship",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    return qa_list

def generate_drivable_area_qa(objects, frame_data, scenario, scenario_type):
    """
    Generate Q&A related to the drivable area.
    """
    qa_list = []
    drivable_object = None
    for obj in objects:
        oid, info = obj
        if info.get("obj_name", "").lower() == "drivable area":
            drivable_object = obj
            break
    if not drivable_object:
        qa_list.append({
            "Q": "Is there a drivable area for the ego?",
            "A": "No, a drivable area is not detected in the scene.",
            "Type": "Association",
            "Task": "Context-Based Questions",
            "question_task": "Scene Classification",
            "AV_Task": "plan",
            "scene_scenario": scenario,
        })
        return qa_list
    oid, info = drivable_object
    coordinates = "; ".join([f"({point[0]}, {point[1]})" for point in info.get("polyline", [])])
    try:
        polyline = info.get("polyline", [])
        if len(polyline) < 3:
            raise ValueError("Insufficient points to form a polygon.")
        if polyline[0] != polyline[-1]:
            closed_polyline = polyline + [polyline[0]]
        else:
            closed_polyline = polyline
        polygon = Polygon(closed_polyline)
        if not polygon.is_valid:
            print("Invalid polygon detected. Using convex hull to approximate the area.")
            polygon = MultiPoint(polyline).convex_hull
        area = polygon.area
        size_threshold = 50000
        size_category = "big" if area > size_threshold else "small"
    except Exception as e:
        print(f"Error calculating area: {e}")
        area = None
        size_category = "unknown"
    
    qa_list.append({
        "Q": "Is there a drivable area for the ego?",
        "A": "Yes, a drivable area is present.",
        "Type": "Discovery",
        "Type": "Association",
        "Task": "Context-Based Questions",
        "question_task": "Scene Classification",
        "AV_Task": "plan",
        "scene_scenario": scenario,
    })
    
    qa_list.append({
        "Q": "Is the drivable area big or small?",
        "A": f"The drivable area is {size_category}.",
        "Type": "Discovery",
        "Type": "Association",
        "Task": "Context-Based Questions",
        "question_task": "Scene Classification",
        "AV_Task": "plan",
        "scene_scenario": scenario,
    })
    
    qa_list.append({
        "Q": "Explain situational awareness concerning the ego in relation to the drivable area.",
        "A": (
            f"1) The scene includes a drivable area which is crucial for navigation. "
            f"2) The drivable area defines the safe navigable space. "
            f"3) It is categorized as a {size_category} area, affecting the ego's maneuvering strategy."
        ),
        "Type": "Association",
        "Task": "Context-Based Questions",
        "question_task": "Scene Classification",
        "AV_Task": "plan",
        "scene_scenario": scenario,
    })
    
    return qa_list

# def generate_relation_qa(relations, scenario, scenario_type):
#     """
#     Generate Q&A pairs from the relation edges.
#     Each relation is expected to be a list/tuple [source_id, target_id, attributes].
#     """
#     qa_list = []
#     if not relations:
#         return qa_list

#     for relation in relations:
#         if len(relation) != 3:
#             continue
#         source_id, target_id, attributes = relation
#         relation_text = attributes.get("relation", "related to")
#         relation_type = "causal" if attributes.get("causal") else "general"
#         qa_list.append({
#             "Q": f"What is the {relation_type} relationship between {source_id} and {target_id}?",
#             "A": f"{source_id} is {relation_text} {target_id}.",
#             "Type": "Association",
#             "Task": "Context-Based Questions",
#             "question_task": "Relationship",
#             "AV_Task": "plan",
#             "scene_scenario": scenario,
#         })
#     return qa_list

def generate_causal_relations(objects):
    """
      - "Object_Causal": the target object's id
      - "Causal_Relation": one of ("Direct", "Chain", "Confounder", "Collider", "Mediator", "correlations")
      - "Is_causal": either "Cause" or "Effect" (or empty)
    """
    edges = []
    ALLOWED_CAUSAL_RELATIONS = ("Direct", "Chain", "Confounder", "Collider", "Mediator", "correlations")
    for node in objects:
        node_id, node_info = node
        object_causal = node_info.get("Object_Causal", "").strip()
        causal_relation = node_info.get("Causal_Relation", "").strip()
        is_causal = node_info.get("Is_causal", "").strip()  # "Cause", "Effect", or empty
        if object_causal and is_causal in ("Cause", "Effect"):
            if causal_relation not in ALLOWED_CAUSAL_RELATIONS:
                causal_relation = "Direct"
            if is_causal == "Cause":
                edges.append([node_id, object_causal, {"relation": f"{causal_relation} (causal)", "causal": True}])
            elif is_causal == "Effect":
                edges.append([object_causal, node_id, {"relation": f"{causal_relation} (causal)", "causal": True}])
    return edges


##################### Our Generates a causal-chain-of-thought (CCoT) reasoning Q&A pair that provides step-by-step ######################################
def generate_ccot_reasoning(frame_data, scenario, scenario_type):
    """
    Generates a causal-chain-of-thought (CCoT) reasoning Q&A pair that provides step-by-step
    directional guidance for how the ego vehicle should act given the current conditions.
    
    The reasoning includes:
      - Identification of objects affecting safety.
      - Analysis of causal relations between objects and events.
      - Directional instructions for planned maneuvers and adherence to traffic regulations.
      - A concluding directive to pursue the intended goal when conditions allow.
    """
    # Extract basic frame data
    objects = frame_data.get('graph', {}).get('nodes', [])
    image_id = frame_data.get("image_id", "").strip()
    goal = frame_data.get("goal-oriented", "").strip()
    safety_status_raw = frame_data.get("safe", "").strip().lower()
    maneuver = frame_data.get("maneuver", "").strip()
    caption = frame_data.get("caption", "").strip()
    traffic_regulations = frame_data.get("Traffic Regulations Suggestions", "").strip()
    action_suggestions = frame_data.get("Action Suggestions", "").strip()
    
    # Determine safety status and reasoning (assumed helper function)
    safety_status, safety_reasoning = determine_safety_status(safety_status_raw)
    
    # Identify objects that impact safety with positional and status info.
    affecting_safety = []
    for obj_id, obj_info in objects:
        position = extract_position_description(obj_info)
        status = extract_status_description(obj_info)
        if "Affects Safety" in obj_info.get("Object_Safety", []):
            affecting_safety.append(f"{obj_id} (Position: {position}, Status: {status})")
    
    # Build description of causal relationships (assumed helper function)
    causal_edges = generate_causal_relations(objects)
    if causal_edges:
        causal_desc = ("Causal relations identified: " +
                       ", ".join([f"{edge[0]} → {edge[1]} (Relation: {edge[2]['relation']})" 
                                  for edge in causal_edges]) + ". ")
    else:
        causal_desc = ""
    
    # Initialize the chain-of-thought reasoning string with directional steps.
    cot_reasoning = ""
    
    # Step 1: Identify and detail safety-critical objects.
    if affecting_safety:
        cot_reasoning += (
            f"Step 1: Recognize that the following objects impact safety: {', '.join(affecting_safety)}. "
        )
    
    # Step 2: Outline causal relations (if any) to direct attention to key interactions.
    if causal_desc:
        cot_reasoning += f"Step 2: Observe that {causal_desc}"
    
    # Step 3: Incorporate scene details and maneuver intentions.
    cot_reasoning += (
        f"Step 3: Analyze the scene description: '{caption}'. "
        f"Then, determine the planned maneuver: '{maneuver}'. "
        f"Follow directional traffic regulation advice: '{traffic_regulations}'. "
    )
    
    # Step 4: Add any additional action suggestions as a further directive.
    if action_suggestions:
        cot_reasoning += (
            f"Step 4: After confirming no immediate collision risk, prepare to execute: '{action_suggestions}'. "
        )
    
    # Step 5: Conclude with safety evaluation and final goal direction.
    cot_reasoning += (
        f"Step 5: Conclude that the situation is {'unsafe' if safety_status == 'no' else 'safe'} "
        f"because: {safety_reasoning}. "
        f"Final Direction: Once conditions are optimal, proceed to achieve the goal: '{goal}'."
    )
    
    # Construct the Q&A based on the scenario type with additional directional stimulus.
    if scenario == "normal":
        q_text = (
            f"Using the provided scene details and directional steps, explain how the ego vehicle "
            f"should assess and decide when to '{goal}' under {'unsafe' if safety_status == 'no' else 'safe'} conditions. "
            f"Focus on safety-critical objects, causal relations, and maneuver directives."
        )
    
    elif scenario == "Attack":
        q_text = (
            f"Detail the step-by-step decision-making process for the ego vehicle to '{goal}' in an Attack scenario "
            f"({scenario_type}). Explain how safety objects, causal interactions, and traffic regulation directions "
            f"guide the vehicle's actions under {'unsafe' if safety_status == 'no' else 'safe'} conditions."
        )
    
    elif scenario == "OoD":
        q_text = (
            f"Describe the comprehensive decision-making process for the ego vehicle to '{goal}' when encountering "
            f"Out-of-Distribution objects ({scenario_type}). Include how the directional guidance on safety, maneuvers, "
            f"and traffic rules informs the final decision under {'unsafe' if safety_status == 'no' else 'safe'} conditions."
        )
    
    elif scenario == "miss_detected":
        q_text = (
            f"Explain the step-by-step reasoning for the ego vehicle to '{goal}' in a miss-detection scenario "
            f"({scenario_type}). Detail how the vehicle incorporates safety-critical information, causal analysis, "
            f"and directional maneuver suggestions while ensuring safety is maintained."
        )
    
    else:
        # Default prompt for any unspecified scenario.
        q_text = (
            f"Provide a detailed, step-by-step explanation on how the ego vehicle should decide when to '{goal}' "
            f"given the current conditions, with directional guidance on handling safety, maneuver planning, and "
            f"traffic regulations."
        )
    
    return {
        "Q": q_text,
        "A": cot_reasoning,
        "Type": "CCot",
        "Task": "Planning-Based Questions",
        "question_task": " Planning",
        "AV_Task": "plan",
        "scene_scenario": scenario,
    }


def generate_ccot_reasoning_1(frame_data, scenario, scenario_type):
    """
    Generates a 7-step causal-chain-of-thought (CCoT) reasoning explanation detailing how the ego vehicle should act.
    
    The seven steps include:
      1) Determining overall scene safety.
      2) Identifying explicit causes (if any).
      3) Reporting ego motion parameters (speed, steering).
      4) Describing the goal, maneuver, and caption details.
      5) Highlighting objects that affect or potentially affect safety, plus any causal relations.
      6) Presenting traffic regulations and action suggestions.
      7) Delivering a scenario-specific concluding directive.
      
    This function returns a Q&A pair that can be used in further decision-making processes.
    """
    # Extract basic frame data.
    objects = frame_data.get('graph', {}).get('nodes', [])
    safety_status_raw = frame_data.get("safe", "").strip().lower()
    cause_list = frame_data.get("cause", [])
    goal = frame_data.get("goal-oriented", "").strip()
    maneuver = frame_data.get("maneuver", "").strip()
    action_suggestions = frame_data.get("Action Suggestions", "").strip()
    traffic_regulations = frame_data.get("Traffic Regulations Suggestions", "").strip()
    speed = frame_data.get("speed", None)
    steering = frame_data.get("steering", None)
    caption = frame_data.get("caption", "").strip()
    
    # Step 1: Determine overall scene safety.
    if "unsafe" in safety_status_raw or "no" in safety_status_raw:
        current_safety = "unsafe"
    elif "safe" in safety_status_raw or "yes" in safety_status_raw:
        current_safety = "safe"
    else:
        current_safety = "ambiguous"
    step1 = f"1) Scene Safety: The environment is classified as '{current_safety}' based on the safety indicator."

    # Step 2: Identify explicit causes (if applicable).
    if cause_list:
        cause_str = ", ".join(cause_list)
        step2 = f"2) Cause Analysis: The unsafe condition is primarily due to: {cause_str}."
    else:
        step2 = "2) Cause Analysis: No explicit causes are provided or the scene is safe."

    # Step 3: Report ego motion parameters.
    motion_params = []
    if speed is not None:
        motion_params.append(f"speed = {speed} MPH")
    if steering is not None:
        motion_params.append(f"steering angle = {steering}°")
    if motion_params:
        motion_str = ", ".join(motion_params)
        step3 = f"3) Ego Motion: The current motion parameters are: {motion_str}."
    else:
        step3 = "3) Ego Motion: Motion parameters are unavailable."

    # Step 4: Describe goal, maneuver, and caption details.
    details = []
    if goal:
        details.append(f"goal: '{goal}'")
    if maneuver:
        details.append(f"maneuver: '{maneuver}'")
    if caption:
        details.append(f"scene description: '{caption}'")
    if details:
        step4 = f"4) Vehicle Intent: " + ", ".join(details) + "."
    else:
        step4 = "4) Vehicle Intent: No specific goal, maneuver, or scene description provided."

    # Step 5: Highlight objects affecting safety and report causal relations.
    affecting_safety_objects = []
    potentially_affecting_objects = []
    for obj_id, obj_info in objects:
        obj_name = obj_info.get("obj_name", "Unknown").strip()
        object_safety_list = obj_info.get("Object_Safety", [])
        if "Affects Safety" in object_safety_list:
            affecting_safety_objects.append(obj_name)
        elif "Potentially Affect Safety" in object_safety_list:
            potentially_affecting_objects.append(obj_name)
    parts = []
    if affecting_safety_objects:
        parts.append(f"Objects affecting safety: {', '.join(affecting_safety_objects)}")
    if potentially_affecting_objects:
        parts.append(f"Potentially affecting objects: {', '.join(potentially_affecting_objects)}")
    objects_info = "; ".join(parts) if parts else "No objects flagged for safety concerns."
    
    # Retrieve causal relations using your helper.
    causal_edges = generate_causal_relations(objects)
    if causal_edges:
        causal_str = "Causal relations: " + ", ".join(
            [f"{edge[0]} -> {edge[1]} (relation: {edge[2]['relation']})" for edge in causal_edges]
        )
    else:
        causal_str = "No causal relations observed."
    step5 = f"5) Object & Causal Analysis: {objects_info}. Additionally, {causal_str}."

    # Step 6: Present traffic regulations and action suggestions.
    if traffic_regulations or action_suggestions:
        suggestions = []
        if action_suggestions:
            suggestions.append(f"action: '{action_suggestions}'")
        if traffic_regulations:
            suggestions.append(f"traffic regulations: '{traffic_regulations}'")
        step6 = f"6) Traffic & Action Guidance: " + ", ".join(suggestions) + "."
    else:
        step6 = "6) Traffic & Action Guidance: No traffic regulations or action suggestions provided."

    # Step 7: Deliver a scenario-specific concluding directive.
    if scenario == "Attack":
        step7 = f"7) Conclusion: For an Attack scenario, adopt extreme caution and adjust the strategy accordingly ({scenario_type})."
    elif scenario == "OoD":
        step7 = f"7) Conclusion: Under Out-of-Distribution conditions, re-assess the environment with heightened vigilance ({scenario_type})."
    elif scenario == "miss_detected":
        step7 = f"7) Conclusion: With a miss-detection condition, be alert to unseen hazards and prepare for a re-scan ({scenario_type})."
    else:  # Normal scenario.
        if current_safety == "unsafe":
            step7 = "7) Conclusion: Given the unsafe condition, proceed with heightened caution."
        else:
            step7 = "7) Conclusion: As the scene is safe, the ego vehicle may proceed with its planned maneuver."
    
    # Combine all steps into the final chain-of-thought explanation.
    final_chain_of_thought = "\n".join([step1, step2, step3, step4, step5, step6, step7])
    
    return {
        "Q": ("Step-by-step, explain how the ego vehicle should handle the current situation "
              f"considering safety, causes, motion, intent, object interactions, and traffic guidance."),
        "A": final_chain_of_thought,
        "Type": "CCot",
        "Task": "Planning-Based Questions",
        "question_task": " Planning",
        "AV_Task": "plan",
        "scene_scenario": scenario,
    }


def generate_ccot_reasoning_2(frame_data, scenario, scenario_type):
    """
    Generates a causal-chain-of-thought (CCoT) explanation that follows a seven-step template with a scenario-specific twist.
    
    The seven steps include:
      1) Identify high-ranking objects affecting ego safety.
      2) Determine explicit causes.
      3) Assess ego motion parameters.
      4) Define the goal and recommended maneuver.
      5) Evaluate the safety status and integrate causal relations.
      6) Consider traffic regulations and suggested actions.
      7) Provide a scenario-specific conclusion and caption.
    
    The function returns a Q&A pair along with the raw causal edges for further processing.
    """
    # Extract key metadata.
    objects = frame_data.get('graph', {}).get('nodes', [])
    safety_status_raw = frame_data.get("safe", "").strip().lower()
    cause_list = frame_data.get("cause", [])
    goal = frame_data.get("goal-oriented", "").strip()
    maneuver = frame_data.get("maneuver", "").strip()
    action_suggestions = frame_data.get("Action Suggestions", "").strip()
    traffic_regulations = frame_data.get("Traffic Regulations Suggestions", "").strip()
    speed = frame_data.get("speed", None)
    steering = frame_data.get("steering", None)
    caption = frame_data.get("caption", "").strip()
    
    # Step 1: Identify High-Ranking Objects Affecting Ego Safety.
    high_ranking_objects = identify_high_ranking_objects(objects, ranking_threshold="high")
    if high_ranking_objects:
        high_ranking_str = ", ".join(high_ranking_objects)
    else:
        high_ranking_str = "No high-ranking objects affecting safety were identified."
    step1 = f"1) High-Ranking Objects: {high_ranking_str}"

    # Step 2: Determine Explicit Causes.
    if cause_list:
        causes_str = ", ".join(cause_list)
    else:
        causes_str = "No specific causes mentioned."
    step2 = f"2) Cause Determination: {causes_str}"

    # Step 3: Assess Ego Motion Parameters.
    motion_details = []
    if speed is not None:
        motion_details.append(f"speed = {speed} MPH")
    if steering is not None:
        motion_details.append(f"steering angle = {steering}°")
    ego_motion_str = ", ".join(motion_details) if motion_details else "Ego motion parameters are unavailable."
    step3 = f"3) Ego Motion: {ego_motion_str}"

    # Step 4: Define Goal and Recommended Maneuver.
    goal_str = f"goal = '{goal}'" if goal else "No specific goal provided."
    maneuver_str = f"maneuver = '{maneuver}'" if maneuver else "No maneuver recommended."
    step4 = f"4) Vehicle Intent: {goal_str}, {maneuver_str}"

    # Step 5: Evaluate Safety Status and Integrate Causal Relations.
    # Determine safety status using your helper function.
    safety_status, safety_reasoning = determine_safety_status(safety_status_raw)
    if safety_status == "no":
        safety_status_str = f"unsafe due to: {safety_reasoning}"
    elif safety_status == "yes":
        safety_status_str = f"safe; {safety_reasoning}"
    else:
        safety_status_str = f"ambiguous: {safety_reasoning}"
    
    # Gather objects that affect safety (both definite and potential).
    affecting_objects = []
    potential_objects = []
    for obj_id, obj_info in objects:
        obj_name = obj_info.get("obj_name", "Unknown").strip()
        safety_list = obj_info.get("Object_Safety", [])
        if "Affects Safety" in safety_list:
            affecting_objects.append(obj_name)
        elif "Potentially Affect Safety" in safety_list:
            potential_objects.append(obj_name)
    parts = []
    if affecting_objects:
        parts.append(f"affecting: {', '.join(affecting_objects)}")
    if potential_objects:
        parts.append(f"potentially affecting: {', '.join(potential_objects)}")
    objects_info = "; ".join(parts) if parts else "No objects flagged for safety concerns."
    
    # Retrieve causal relations.
    causal_edges = generate_causal_relations(objects)
    if causal_edges:
        causal_str = "Causal relations: " + ", ".join(
            [f"{edge[0]} -> {edge[1]} (relation: {edge[2]['relation']})" for edge in causal_edges]
        )
    else:
        causal_str = "No causal relations observed."
    step5 = (f"5) Safety Evaluation: The situation is identified as '{safety_status_str}'. "
             f"Additionally, {objects_info}. {causal_str}")

    # Step 6: Consider Traffic Regulations and Action Suggestions.
    if action_suggestions and traffic_regulations:
        traffic_str = f"action: '{action_suggestions}' under regulations: '{traffic_regulations}'"
    elif action_suggestions:
        traffic_str = f"action: '{action_suggestions}'"
    elif traffic_regulations:
        traffic_str = f"regulations: '{traffic_regulations}' (no specific action suggested)"
    else:
        traffic_str = "No traffic regulations or actions provided."
    step6 = f"6) Traffic & Action: {traffic_str}"

    # Step 7: Provide a Scenario-Specific Conclusion and Caption.
    if scenario == "Attack":
        conclusion = f"For an Attack scenario, adopt extreme caution and adjust strategy ({scenario_type})."
    elif scenario == "OoD":
        conclusion = f"Under Out-of-Distribution conditions, re-assess the environment with heightened vigilance ({scenario_type})."
    elif scenario == "miss_detected":
        conclusion = f"With a miss-detection condition, remain alert to unseen hazards and re-scan the environment ({scenario_type})."
    else:  # Normal scenario.
        if safety_status == "no":
            conclusion = "Due to unsafe conditions, proceed with heightened caution."
        else:
            conclusion = "As the scene is safe, follow the planned maneuver."
    caption_str = f"Caption: {caption}" if caption else "No caption provided."
    step7 = f"7) Conclusion: {conclusion}\n   {caption_str}"
    
    # Combine all steps into the final chain-of-thought explanation.
    cot_reasoning = "\n".join([step1, step2, step3, step4, step5, step6, step7])
    
    return {
        "Q": ("Provide a comprehensive, step-by-step explanation of how the ego vehicle should act "
              "based on the current scene analysis, safety evaluation, and traffic guidance."),
        "A": cot_reasoning,
        "Type": "CCot",
        "Task": "Planning-Based Questions",
        "question_task": " Planning",
        "AV_Task": "plan",
        "scene_scenario": scenario,
        # Optionally, you can add: "causal_edges": causal_edges  # for further processing.
    }

######################### QA bu Grouping ##################################
def generate_infrastructure_qa(objects, frame_data, scenario, scenario_type):
    """
    Generate Q&A for Ego-Infrastructure.
    """
    qa_list = []
    infrastructure_keywords = {
        "bridge", "crosswalk", "street furniture", "pedestrian crossing marking", "road", "bicycle lane",
        "train lane", "sidewalk", "t-intersection", "four-way intersection", "drivable area", "traffic light",
        "traffic light pedestrian", "ts_stop", "stop marking", "ts_yield", "ts_speed_limit_15", "ts_speed_limit_20",
        "ts_speed_limit_25", "ts_speed_limit_30", "ts_speed_limit_40", "ts_speed_limit_45", "ts_speed_limit_50",
        "ts_speed_limit_60", "ts_speed_limit_70", "ts_speed_limit_80", "ts_railroad_crossing",
        "railway_crossing_ahead_skew_left", "railway_crossing_ahead_skew_right", "ts_pedestrian_crossing",
        "ts_keep_left_road", "ts_keep_right_road", "ts_no_entry", "ts_parking", "ts_no_parking", "ts_school_zone",
        "ts_directional", "ts_warning", "ts_no_u_turn", "ts_no_left_u_turn", "ts_no_left_turn", "ts_no_right_turn",
        "ts_hospital", "ts_road_work", "ts_traffic_signal_ahead", "ts_roundabout_ahead", "ts_bus_stop",
        "ts_bicycle_crossing", "ts_construction_sign", "construction_zone", "bus station", "gas station",
        "manhole", "parking_space", "parking_lot", "parking_meter", "barrier", "bollard", "cone", "trash_bin",
        "tree", "pole", "road divider", "street sign"
    }
    infra_objects = [
        (oid, info) for (oid, info) in objects
        if info.get("obj_name", "").lower() in infrastructure_keywords
    ]
    
    if infra_objects:
        infra_names = [inf[1]["obj_name"] for inf in infra_objects]
        unique_infra = set(infra_names)
        qa_list.append({
            "Q": "What infrastructure is present in the scene?",
            "A": f"Infrastructure objects found: {', '.join(unique_infra)}",
            "Type": "Association",
            "Task": "Context-Based Questions",
            "question_task": "Scene Classification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    has_T_intersection = any("t-intersection" in inf[1]["obj_name"].lower() for inf in infra_objects)
    has_intersection = any("four-way intersection" in inf[1]["obj_name"].lower() for inf in infra_objects)
    has_roundabout = any("roundabout" in inf[1]["obj_name"].lower() for inf in infra_objects)
    
    scene_elements = []
    if has_T_intersection:
        scene_elements.append("T-intersection")
    if has_intersection:
        scene_elements.append("4 way intersection")
    if has_roundabout:
        scene_elements.append("roundabout")
    
    if scene_elements:
        qa_list.append({
            "Q": "Is this a driving situation involving an 4 way intersection, T-intersection or roundabout?",
            "A": f"The scene includes: {', '.join(scene_elements)}",
            "Type": "Association",
            "Task": "Context-Based Questions",
            "question_task": "Scene Classification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    for oid, info in infra_objects:
        pos = info.get("position", "Unknown")
        qa_list.append({
            "Q": f"What objects are located at {pos}?",
            "A": f"{info.get('obj_name', 'Unknown')} is located at {pos}.",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "Position Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    for oid, info in infra_objects:
        pos = info.get("position", "Unknown")
        qa_list.append({
            "Q": f"Where can I find {oid}?",
            "A": f"You can find object {oid} ({info.get('obj_name', '')}) at {pos}.",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "Position Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    for oid, info in infra_objects:
        pos = info.get("position", "Unknown")
        status = info.get("Status", [])
        status_str = ", ".join(status) if status else "No status info"
        qa_list.append({
            "Q": f"What is the status of {oid} on {pos}?",
            "A": f"The status of object {oid} is: {status_str}",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "State Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    # Add Q&A for traffic signs, lights, and markings
    traffic_signs = detect_traffic_signs(objects)
    qa_list.extend(generate_traffic_sign_qa(traffic_signs, scenario, scenario_type))
    
    traffic_lights = detect_traffic_lights(objects)
    qa_list.extend(generate_traffic_light_qa(traffic_lights, scenario, scenario_type))
    
    ts_and_markings = detect_markings(objects)
    qa_list.extend(generate_traffic_markings_qa(ts_and_markings, scenario, scenario_type))
    
    return qa_list

def generate_vehicle_qa(objects, frame_data, scenario, scenario_type):
    """
    Generate Q&A for the Ego-Vehicle category.
    """
    qa_list = []
    vehicle_keywords = {
        "car", "truck", "bus", "motorcycle", "construction vehicle",
        "police vehicle", "ambulance", "fire truck"
    }
    vehicle_objects = [
        (oid, info) for (oid, info) in objects
        if info.get("obj_name", "").lower() in vehicle_keywords
    ]


    has_police = any("police vehicle" in inf[1]["obj_name"].lower() for inf in vehicle_objects)
    has_ambulance= any("ambulance" in inf[1]["obj_name"].lower() for inf in vehicle_objects)
    has_fire = any("fire truck" in inf[1]["obj_name"].lower() for inf in vehicle_objects)
    has_construction = any("construction vehicle" in inf[1]["obj_name"].lower() for inf in vehicle_objects)

    vehicle_elements = []
    if has_police:
        vehicle_elements.append("police vehicle")
    if has_ambulance:
        vehicle_elements.append("ambulance")
    if has_fire:
        vehicle_elements.append("fire truck")
    if has_construction:
        vehicle_elements.append("construction vehicle")
    
    if vehicle_elements:
        qa_list.append({
            "Q": "Is this a driving situation involving a police vehicle, ambulance, construction vehicle or fire truck?",
            "A": f"yes, includes: {', '.join(vehicle_elements)}",
            "Type": "Association",
            "Task": "Object-Centric Questions",
            "question_task": "existence",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    if vehicle_objects:
        names = [v[1]["obj_name"] for v in vehicle_objects]
        unique_types = set(names)
        qa_list.append({
            "Q": "What types of vehicles are present in the scene, and how many are there?",
            "A": f"There are {len(vehicle_objects)} vehicles in total. Types: {', '.join(unique_types)}",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "Counting",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    for oid, info in vehicle_objects:
        pos = info.get("position", "Unknown")
        qa_list.append({
            "Q": f"Where can I find {oid}?",
            "A": f"The object {info.get('obj_name', '').strip()} is at position {pos}.",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "Position Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    for oid, info in vehicle_objects:
        pos = info.get("position", "Unknown")
        status = info.get("Status", [])
        status_str = ", ".join(status) if status else "No status info"
        qa_list.append({
            "Q": f"What is the status of {oid} on {pos}?",
            "A": f"The status of object {oid} is: {status_str}",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "State Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        
    for oid, info in vehicle_objects:
        pos = info.get("position", "Unknown")
        qa_list.append({
            "Q": f"Where can I find {oid}?",
            "A": f"You can find object {oid} ({info.get('obj_name', '')}) at {pos}.",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "Position Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    for oid, info in vehicle_objects:
        pos = info.get("position", "Unknown")
        status = info.get("Status", [])
        status_str = ", ".join(status) if status else "No status info"
        qa_list.append({
            "Q": f"What is the status of {oid} on {pos}?",
            "A": f"The status of object {oid} is: {status_str}",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "State Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    # Additional spatial Q&A for emergency vehicles.
    emergency_keywords = {"police vehicle", "ambulance", "fire truck"}
    emergency_vehicle_objects = [
        (oid, info) for (oid, info) in vehicle_objects
        if info.get("obj_name", "").lower() in emergency_keywords
    ]
    
    for oid, info in emergency_vehicle_objects:
        pos = info.get("position", "Unknown")
        if isinstance(pos, list):
            pos = " ".join(pos)
        status = info.get("Status", [])
        # The emergency statuses might include phrases such as:
        # "Emergency Lights On", "Emergency Lights Off", "Flashing Lights", "Responding", "Patrolling", "drivable area"
        emergency_status_str = ", ".join(status) if status else "No emergency status provided"
        qa_list.append({
            "Q": f"What are the spatial details and emergency status of {info.get('obj_name', 'emergency vehicle')} {oid}?",
            "A": (f"The {info.get('obj_name', 'emergency vehicle')} is located at {pos}. "
                  f"Its emergency status includes: {emergency_status_str}."),
            "Type": "Association",
            "Task": "Object-Centric Questions",
            "question_task": "State Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    return qa_list

def generate_road_users_qa(objects, frame_data, scenario, scenario_type):
    """
    Generate Q&A pairs for the Ego-Road Users category.
    
    This function produces several questions covering various aspects of the road users:
      1. Overall depiction of road users in the scene.
      2. Overall count of road users.
      3. For each road user:
           - Their location (position)
           - Their current status
           - Their importance ranking (if provided)
           - Their safety annotations (if provided)
           - Their exiting status (if available)
           - A localized count question (how many are in the area near their position)
    
    The function assumes each road user object is represented as a tuple (oid, info)
    where info is a dictionary that may include the following keys:
      - "obj_name": Name/type of the road user.
      - "position": Either a string or a list of strings describing location.
      - "Status": A list (or string) of status information.
      - "importance_ranking" or "importance": A string denoting its importance.
      - "Object_Safety": A list of safety annotations.
      - "exiting": (Optional) A boolean or string indicating if the road user is exiting.
    
    Args:
        objects (list): A list of tuples (oid, info) for each detected object.
        frame_data (dict): (Unused here, but available for additional frame-related info.)
        scenario (str): The scene description.
        scenario_type (str): The type of scenario.
    
    Returns:
        list: A list of Q&A dictionaries.
    """
    qa_list = []
    
    # Define keywords for road users.
    road_user_keywords = {
        "pedestrian", "cyclist", "bicycle", "dog", "skateboard", 
        "baby stroller", "flat car trolley", "handbag"
    }
    
    # Filter objects based on road user keywords.
    road_user_objects = [
        (oid, info) for (oid, info) in objects
        if info.get("obj_name", "").lower() in road_user_keywords
    ]
    
    # If any road users are detected, add overall Q&A.
    if road_user_objects:
        # Overall depiction of road users.
        names = [info.get("obj_name", "unknown") for oid, info in road_user_objects]
        unique_users = set(names)
        qa_list.append({
            "Q": "What are the road users depicted in the scene?",
            "A": f"The road users in this scene include: {', '.join(unique_users)}.",
            "Type": "Association",
            "Task": "Context-Based Questions",
            "question_task": "Scene Classification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        # Overall count of road users.
        qa_list.append({
            "Q": "How many road users are present in the scene?",
            "A": f"There are {len(road_user_objects)} road user(s) detected.",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "Counting",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    # Generate Q&A for each individual road user.
    for oid, info in road_user_objects:
        obj_name = info.get("obj_name", "unknown road user")
        
        # Normalize position: join if it's a list.
        pos = info.get("position", "Unknown")
        if isinstance(pos, list):
            pos = " ".join(pos)
        
        # Normalize status.
        status = info.get("Status", [])
        if isinstance(status, list):
            status_str = ", ".join(status) if status else "unknown"
        else:
            status_str = status or "unknown"
        
        # Check for importance ranking.
        importance = info.get("importance_ranking") or info.get("importance", "not specified")
        
        # Get safety annotations.
        safety_list = info.get("Object_Safety", [])
        safety_str = ", ".join(safety_list) if safety_list else "none"
        
        # Exiting status (if available).
        exiting = info.get("exiting", None)
        if exiting is None:
            exiting_str = "not specified"
        elif isinstance(exiting, bool):
            exiting_str = "Yes" if exiting else "No"
        else:
            exiting_str = str(exiting)
        
        # Q: Where is the road user located?
        qa_list.append({
            "Q": f"Where is the {oid} located?",
            "A": f"The {oid} is located at {pos}.",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "Position Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        
        # Q: What is the current status of the road user?
        qa_list.append({
            "Q": f"What is the status of the {oid}?",
            "A": f"The current status of the {oid} is: {status_str}.",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "State Identification",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        
        # Q: What is the importance ranking of the road user?
        qa_list.append({
            "Q": f"What is the importance ranking of the {oid}?",
            "A": f"The {oid} has an importance ranking of: {importance}.",
            "Type": "Association",
            "Task": "Context-Based Questions",
            "question_task": "Relationship",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        
        # Q: What safety annotations are associated with the road user?
        qa_list.append({
            "Q": f"What safety annotations are associated with the {oid}?",
            "A": f"The {oid} has the following safety annotations: {safety_str}.",
            "Type": "Intervention",
            "Task": "Safety-Based Questions",
            "question_task": "Risk & Anomaly Detection",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        
        # Q: Is the road user exiting the scene? (if such information exists)
        if "exiting" in info:
            qa_list.append({
                "Q": f"Is the {oid} exiting the scene?",
                "A": f"The exiting status of the {oid} is: {exiting_str}.",
                "Type": "Discovery",
                "Task": "Object-Centric Questions",
                "question_task": "existence",
                "AV_Task": "perception",
                "scene_scenario": scenario,
            })
    
    return qa_list

def generate_ego_qa(objects, frame_data, scenario, scenario_type):
    """
    Generate Q&A for the Ego-Ego category.
    """
    qa_list = []
    ego_object = None
    for oid, info in objects:
        if info.get("obj_name", "").strip().lower() == "ego":
            ego_object = (oid, info)
            break
    speed = frame_data.get("speed", None)
    steering = frame_data.get("steering", None)
    
    if ego_object:
        position = ego_object[1].get("position", "Unknown")
        qa_list.append({
            "Q": "Where is the ego located now?",
            "A": f"The ego is located at {position}",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "Object-Centric Questions",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    ego_status_info = []
    if speed is not None:
        ego_status_info.append(f"Speed: {speed}")
    if steering is not None:
        ego_status_info.append(f"Steering: {steering}")
    
    if ego_status_info:
        qa_list.append({
            "Q": "What is the status of the ego? (Speed and steering)",
            "A": " and ".join(ego_status_info),
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "Object-Centric Questions",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    caption = frame_data.get("caption", "")
    qa_list.append({
        "Q": "Explain the current situation for this scene.",
        "A": f"The ego is navigating the environment with {caption}",
        "Type": "Association",
        "Task": "Object-Centric Questions",
        "question_task": "Context-Based Questions",
        "AV_Task": "perception",
        "scene_scenario": scenario,
    })
    
    maneuver = frame_data.get("maneuver", "")
    if maneuver:
        qa_list.append({
            "Q": "Explain the maneuver that can be performed in this situation.",
            "A": maneuver,
            "Type": "Intervention",
            "Task": "Object-Centric Questions",
            "question_task": "Planning-Based Questions",
            "AV_Task": "plan",
            "scene_scenario": scenario,
        })
    
    return qa_list

def generate_global_qa(frame_data, objects, scenario, scenario_type):
    """
    Generate global Q&A for the scene.
    """
    qa_list = []
    goal = frame_data.get("goal-oriented", "")
    maneuver = frame_data.get("maneuver", "")
    safe_field = frame_data.get("safe", "")
    cause = frame_data.get("cause", [])
    safety_status, safety_reasoning = determine_safety_status(safe_field)
    action_suggestions = frame_data.get("Action Suggestions", "").strip()
    traffic_regulations = frame_data.get("Traffic Regulations Suggestions", "").strip()
    speed = frame_data.get("speed", None)
    steering = frame_data.get("steering", None)
    relations = frame_data.get('graph', {}).get('edges', [])

    # Goal question (context-based)
    if goal:
        qa_list.append({
            "Q": "What is the ego vehicle's current goal in this situation?",
            "A": goal,
            "Type": "Association",
            "Task": "Object-Centric Questions",
            "question_task": "Context-Based Questions",
            "AV_Task": "plan",
            "scene_scenario": scenario,
        })
    
    # Maneuver question (context-based)
    if maneuver:
        qa_list.append({
            "Q": f"What is the best maneuver the ego vehicle can perform in this scene according to {goal}?",
            "A": maneuver,
            "Type": "Association",
            "Task": "Planning-Based Questions",
            "question_task": "Planning",
            "AV_Task": "plan",
            "scene_scenario": scenario,
        })
    
    # Action suggestion (safety-based, intervention)
    if action_suggestions:
        qa_list.append({
            "Q": f"What action should the vehicle take next to achieve {goal}?",
            "A": f"Current speed: {speed} MPh, Steering: {steering}. Recommended Action: {action_suggestions}",
            "Type": "Intervention",
            "Task": "Event(Temporal)-Based Questions",
            "question_task": "Predictive",
            "AV_Task": "action",
            "scene_scenario": scenario,
        })
        qa_list.append({
            "Q": f"What traffic regulations should the ego vehicle consider to achieve {goal}?",
            "A": f"The ego vehicle should consider: {traffic_regulations}.",
            "Type": "Intervention",
            "Task": "Planning-Based Questions",
            "question_task": "Planning",
            "AV_Task": "plan",
            "scene_scenario": scenario,
        })
    
    # Overall safety status (explanation-based)
    if safety_status is not None:
        qa_list.append({
            "Q": "Is the current situation considered safe?",
            "A": f"{safety_status}. Reasoning: {safety_reasoning}",
            "Type": "Intervention",
            "Task": "Safety-Based Questions",
            "question_task": "Safety-Based Questions",
            "AV_Task": "action",
            "scene_scenario": scenario,
        })
    
    # Existence questions (object-centric)
    for obj_id, obj_info in objects:
        obj_name = obj_info.get("obj_name", "").strip()
        status = obj_info.get("Status", "Unknown")
        qa_list.append({
            "Q": f"Is there a {obj_id} in the scene?",
            "A": f"Yes, a {obj_name} is present with status '{status}'.",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "existence",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        qa_list.append({
            "Q": f"Is there not an {obj_name} in the scene?",
            "A": f"No, a {obj_name} is present with status '{status}'.",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "existence",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    # Causes for safety issues (association)
    if cause:
        causes_str = ', '.join(cause)
        qa_list.append({
            "Q": "What are the causes of the current safety issue?",
            "A": causes_str,
            "Type": "Association",
            "Task": "Object-Centric Questions",
            "question_task": "Scene Classification",
            "AV_Task": "prediction",
            "scene_scenario": scenario,
        })
    
    # Counting objects (discovery)
    if len(objects) > 0:
        qa_list.append({
            "Q": "How many objects are detected in total from the driving view?",
            "A": f"There are {len(objects)} objects detected in the scene.",
            "Type": "Discovery",
            "Task": "Object-Centric Questions",
            "question_task": "Counting",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        
    # Safety categories Q&A (Association type, reasoning about objects)
    safety_categorization_qa = generate_object_safety_categorization_qa(objects, scenario, scenario_type)
    qa_list.extend(safety_categorization_qa)
    
    # Generate QA from relation edges ---
    # relation_qa = generate_relation_qa(relations, scenario, scenario_type)
    # qa_list.extend(relation_qa)
    
    # Causal Relations QA (if any causal relations were added in the frame)
    causal_edges = generate_causal_relations(objects)
    if causal_edges:
        qa_list.append({
            "Q": "Are there any causal relationships between objects in the scene?",
            "A": f"Causal relationships detected: {causal_edges}",
            "Type": "Association",
            "Task": "Planning-Based Questions",
            "question_task": "Relationship",
            "AV_Task": "plan",
            "scene_scenario": scenario,
        })
    
    
    return qa_list

# ======================= High-Level Q&A Generation =======================

def generate_qa(objects, frame_data, previous_frame=None, next_frame=None):
    """
    Generate a list of Q&A pairs for a given frame.
    """
    qa_list = []
    
    goal = frame_data.get("goal-oriented", "").strip()
    maneuver = frame_data.get("maneuver", "").strip()
    action_suggestions = frame_data.get("Action Suggestions", "").strip()
    traffic_regulations = frame_data.get("Traffic Regulations Suggestions", "").strip()
    caption = frame_data.get("caption", "")
    cause = frame_data.get("cause", [])
    safety_status_raw = frame_data.get("safe", "").strip()
    safety_status, safety_reasoning = determine_safety_status(safety_status_raw)
    objects = frame_data.get('graph', {}).get('nodes', [])
    speed = frame_data.get("speed", None)
    steering = frame_data.get("steering", None)
    
    image_id = frame_data.get("image_id", "").strip()
    scenario, scenario_type = determine_scenario(frame_data, image_id)
    
    # Generate Q&A from various categories
    infra_qa = generate_infrastructure_qa(objects, frame_data, scenario, scenario_type)
    vehicle_qa = generate_vehicle_qa(objects, frame_data, scenario, scenario_type)
    road_user_qa = generate_road_users_qa(objects, frame_data, scenario, scenario_type)
    ego_qa = generate_ego_qa(objects, frame_data, scenario, scenario_type)
    global_qa = generate_global_qa(frame_data, objects, scenario, scenario_type)
    drivable_area = generate_drivable_area_qa(objects, frame_data, scenario, scenario_type)
    
    combined_qa = infra_qa + vehicle_qa + road_user_qa + ego_qa + global_qa + drivable_area
    qa_list.extend(combined_qa)
    
    cot_qa_full1 = generate_ccot_reasoning_1(frame_data, scenario, scenario_type)
    qa_list.append(cot_qa_full1)

    cot_qa_full2 = generate_ccot_reasoning_2(frame_data, scenario, scenario_type)
    qa_list.append(cot_qa_full2)
    
        
    cot_qa = generate_ccot_reasoning(frame_data, scenario, scenario_type)
    qa_list.append(cot_qa)
    
    # expert_planning_qa = generate_expert_planning_humanized_qa(frame_data)
    # qa_list.append(expert_planning_qa)

    # Speed-related Q&A (Event/Temporal)
    if speed is not None:
        qa_list.append({
            "Q": "What is the ego vehicle's current speed?",
            "A": f"The current speed is {speed} MPh.",
            "Type": "Intervention",
            "Task": "Event(Temporal)-Based Questions",
            "question_task": "Predictive",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        if previous_frame:
            previous_speed = previous_frame.get("speed", None)
            if previous_speed is not None:
                speed_diff = speed - previous_speed
                qa_list.append({
                    "Q": "Predict the ego vehicle's acceleration or deceleration compared to the previous frame.",
                    "A": f"The vehicle {'accelerated' if speed_diff > 0 else 'decelerated'} by {abs(speed_diff)} MPh compared to the previous frame.",
                    "Type": "Intervention",
                    "Task": "Event(Temporal)-Based Questions",
                    "question_task": "Predictive",
                    "AV_Task": "perception",
                    "scene_scenario": scenario,
                })
        if next_frame:
            next_speed = next_frame.get("speed", None)
            if next_speed is not None:
                speed_diff = next_speed - speed
                qa_list.append({
                    "Q": "Predict the ego vehicle's acceleration or deceleration in the next frame.",
                    "A": f"The vehicle is expected to {'accelerate' if speed_diff > 0 else 'decelerate'} by {abs(speed_diff)} MPh in the next frame.",
                    "Type": "Intervention",
                            "question_task": "Event(Temporal)-Based Questions",
                    "AV_Task": "prediction",
                    "scene_scenario": scenario,
                })
        speed_limit = None  # Initialize to None at the start
        for obj_id, obj_info in objects:
            label = obj_info.get("obj_name", "").strip()
            if label.startswith("TS_Speed_Limit_"):
                try:
                    speed_limit = int(label.split("TS_Speed_Limit_")[1])
                    logging.info(f"Detected speed limit sign: {speed_limit} MPh.")
                    break
                except (IndexError, ValueError) as e:
                    logging.error(f"Error extracting speed limit from label '{label}': {e}")
                    continue
        
        threshold = speed_limit if speed_limit is not None else 25
        if speed > threshold:
            qa_list.append({
                "Q": "Is the vehicle exceeding the speed limit?",
                "A": f"Yes, the current speed of {speed} MPh exceeds the speed limit of {threshold} MPh.",
                "Type": "Intervention",
                "Task": "Event(Temporal)-Based Questions",
                "question_task": "Predictive",
                "AV_Task": "perception",
                "scene_scenario": scenario,
            })
        else:
            qa_list.append({
                "Q": "Is the vehicle moving within the speed limit?",
                "A": f"Yes, the current speed of {speed} MPh is within the speed limit of {threshold} MPh.",
                "Type": "Intervention",
                "Task": "Event(Temporal)-Based Questions",
                "question_task": "Predictive",
                "AV_Task": "perception",
                "scene_scenario": scenario,
            })
        
        if speed_limit:
            qa_list.append({
                "Q": "What is the applicable speed limit in this area?",
                "A": f"The speed limit is {speed_limit} MPh.",
                "Type": "Discovery",
                "Type": "Intervention",
                "Task": "Event(Temporal)-Based Questions",
                "question_task": "Predictive",
                "AV_Task": "perception",
                "scene_scenario": scenario,
            })
    
    # Turning and Steering Q&A (Intervention and Object-Centric)
    prohibited_turns, allowed_turns = categorize_turn_signs(objects)
    allowed_directions = categorize_directional_arrows(objects)
    intended_turn = determine_intended_turn(steering)
    
    if intended_turn in prohibited_turns:
        qa_list.append({
            "Q": f"Is the ego vehicle attempting to turn {intended_turn} where it is prohibited?",
            "A": f"Yes, the ego vehicle is attempting to turn {intended_turn}, but a 'No {intended_turn.capitalize()} Turn' sign is present.",
            "Type": "Intervention",
            "Task": "Event(Temporal)-Based Questions",
            "question_task": "Predictive",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        qa_list.append({
            "Q": f"Should the ego vehicle proceed with the {intended_turn} turn?",
            "A": f"No, it should adjust its steering to comply with regulations.",
            "Type": "Intervention",
            "Task": "Event(Temporal)-Based Questions",
            "question_task": "Predictive",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    else:
        if allowed_turns:
            if intended_turn in allowed_turns:
                qa_list.append({
                    "Q": f"Is the ego vehicle allowed to turn {intended_turn} in this area?",
                    "A": f"Yes, the ego vehicle is turning {intended_turn}, which is allowed.",
                    "Type": "Discovery",
                    "Task": "Planning-Based Questions",
                    "question_task": "Object-Centric Questions",
                    "AV_Task": "perception",
                    "scene_scenario": scenario,
                })
            else:
                qa_list.append({
                    "Q": f"Is the ego vehicle allowed to turn {intended_turn} in this area?",
                    "A": f"No, the ego vehicle is not allowed to turn {intended_turn} as only specific turns are permitted.",
                    "Type": "Intervention",
                    "question_task": "Safety-Based Questions",
                    "AV_Task": "plan",
                    "scene_scenario": scenario,
                })
        elif allowed_directions:
            if intended_turn in allowed_directions:
                qa_list.append({
                    "Q": f"Is the ego vehicle allowed to turn {intended_turn} in this area?",
                    "A": f"Yes, the ego vehicle is turning {intended_turn}, which is permitted by directional arrow signs.",
                    "Type": "Discovery",
                    "Task": "Planning-Based Questions",
                    "question_task": "Object-Centric Questions",
                    "AV_Task": "perception",
                    "scene_scenario": scenario,
                })
            else:
                qa_list.append({
                    "Q": f"Is the ego vehicle allowed to turn {intended_turn} in this area?",
                    "A": f"No, the ego vehicle is not allowed to turn {intended_turn} as per the directional arrow signs.",
                    "Type": "Intervention",
                    "Task": "Planning-Based Questions",
                    "question_task": "Safety-Based Questions",
                    "AV_Task": "action",
                    "scene_scenario": scenario,
                })
        else:
            if intended_turn in {"left", "right", "u-turn"}:
                qa_list.append({
                    "Q": f"Is the ego vehicle allowed to turn {intended_turn} in this area?",
                    "A": f"Yes, there are no restrictions preventing a {intended_turn} turn if safe.",
                    "Type": "Discovery",
                    "Task": "Planning-Based Questions",
                    "question_task": "Object-Centric Questions",
                    "AV_Task": "perception",
                    "scene_scenario": scenario,
                })
    
    if steering is not None:
        direction_description = intended_turn
        qa_list.append({
            "Q": "What is the ego vehicle's current steering angle?",
            "A": f"The steering angle is {steering}° indicating it is {direction_description}.",
            "Type": "Discovery",
            "Task": "Planning-Based Questions",
            "question_task": "Object-Centric Questions",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
        
        if intended_turn == "left":
            qa_list.append({
                "Q": "Is the vehicle steering to the left?",
                "A": "Yes, it is steering to the left.",
                "Type": "Discovery",
                "Task": "Planning-Based Questions",
                "question_task": "Object-Centric Questions",
                "AV_Task": "controlling",
                "scene_scenario": scenario,
            })
        elif intended_turn == "right":
            qa_list.append({
                "Q": "Is the vehicle steering to the right?",
                "A": "Yes, it is steering to the right.",
                "Type": "Discovery",
                "Task": "Planning-Based Questions",
                "question_task": "Object-Centric Questions",
                "AV_Task": "controlling",
                "scene_scenario": scenario,
            })
        elif intended_turn == "straight":
            qa_list.append({
                "Q": "Is the vehicle going straight?",
                "A": "Yes, it is moving straight with minimal steering input.",
                "Type": "Discovery",
                "Task": "Planning-Based Questions",
                "question_task": "Object-Centric Questions",
                "AV_Task": "controlling",
                "scene_scenario": scenario,
            })
        else:
            qa_list.append({
                "Q": "Is the vehicle's intended direction clear?",
                "A": "The intended direction is unknown.",
                "Type": "Discovery",
                "Task": "Planning-Based Questions",
                "question_task": "Object-Centric Questions",
                "AV_Task": "perception",
                "scene_scenario": scenario,
            })
    
    if steering is not None:
        qa_list.append({
            "Q": "What is the ego vehicle's current steering angle?",
            "A": f"{steering}°.",
            "Type": "Discovery",
            "Task": "Planning-Based Questions",
            "question_task": "Object-Centric Questions",
            "AV_Task": "perception",
            "scene_scenario": scenario,
        })
    
    for obj_id, obj_info in objects:
        obj_name = obj_info.get("obj_name", "").strip()
        importance = obj_info.get("importance_ranking", "").strip()
        position = extract_position_description(obj_info)
        status = obj_info.get("Status", [])
        if importance:
            reasoning = determine_importance_reasoning(obj_name, importance, position, status, goal)
            qa_list.append({
                "Q": f"Why is the {obj_name} considered important in this scenario?",
                "A": reasoning,
                "Type": "Association",
                "Task": "Planning-Based Questions",
                "question_task": "Explanation-Based Questions",
                "AV_Task": "plan",
                "scene_scenario": scenario,
            })
    
    ego_status = None
    for obj_id, obj_info in objects:
        if obj_info.get("obj_name", "").strip().lower() == "ego":
            ego_status = obj_info.get("Status", [])
    
    safety_reasoning_full = determine_safety_reasoningSS(safety_status, ego_status, speed, steering)
    qa_list.append({
        "Q": "Explain the safety status reasoning.",
        "A": safety_reasoning_full,
        "Type": "Association",
        "Task": "planning",
        "question_task": "Explanation-Based Questions",
        "AV_Task": "plan",
        "scene_scenario": scenario,
    })


    # Optionally, sort the Q&A by a defined order for Type (here we use a simple mapping)
    type_order = {"Discovery": 1, "Association": 2, "Intervention": 3, "Counterfactual": 4}
    qa_list = sorted(qa_list, key=lambda x: type_order.get(x['Type'], 99))
    
    return qa_list

def update_json_with_new_qa(json_dir):
    """
    Process all JSON files in the input directory, generate Q&A pairs for each frame,
    and save the updated JSON files.
    """
    for json_file_name in os.listdir(json_dir):
        if not json_file_name.endswith(".json"):
            logging.warning(f"Skipping non-JSON file: {json_file_name}")
            continue
        input_json_path = os.path.join(json_dir, json_file_name)
        try:
            with open(input_json_path, 'r', encoding='utf-8') as json_file:
                video_data = json.load(json_file)
            logging.info(f"Successfully loaded JSON file: {json_file_name}")
        except json.JSONDecodeError as e:
            logging.error(f"JSONDecodeError in file {json_file_name}: {e}")
            continue
        except Exception as e:
            logging.error(f"Unexpected error reading file {json_file_name}: {e}")
            continue
        
        if not isinstance(video_data, list):
            logging.error(f"Expected list of frames in file {json_file_name}, got {type(video_data)}")
            continue
        
        for frame_index, frame_data in enumerate(video_data):
            objects = frame_data.get('graph', {}).get('nodes', [])
            previous_frame = video_data[frame_index - 1] if frame_index > 0 else None
            next_frame = video_data[frame_index + 1] if frame_index < len(video_data) - 1 else None
            

            
            updated_qa = generate_qa(objects, frame_data, previous_frame, next_frame)
            frame_data['QA'] = updated_qa
        
        try:
            with open(input_json_path, 'w', encoding='utf-8') as json_file:
                json.dump(video_data, json_file, indent=4)
            logging.info(f"Successfully updated and saved: {json_file_name}")
        except Exception as e:
            logging.error(f"Error writing JSON file {json_file_name}: {e}")

if __name__ == "__main__":
    input_folder = 'E:/Situational Awareness/Last Dataset/HAD/Sample - Copy'
    if not os.path.exists(input_folder):
        logging.error(f"Input folder does not exist: {input_folder}")
    else:
        update_json_with_new_qa(input_folder)
        logging.info("Q&A generation and updating completed.")
