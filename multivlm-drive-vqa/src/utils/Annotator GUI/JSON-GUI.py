import json
import os
import copy
import pyperclip
from tkinter import (
    Tk, Label, Button, Entry, Canvas, Listbox, Menu, filedialog, END, StringVar,
    Frame, ttk, Scrollbar, VERTICAL, HORIZONTAL, MULTIPLE, Radiobutton, messagebox, colorchooser, simpledialog, Checkbutton, BooleanVar
)

from PIL import Image, ImageTk, ImageDraw, ImageOps
from copy import deepcopy
import numpy as np
import logging

try:
    from PIL import Resampling
except ImportError:
    Resampling = Image

# Configure logging at the beginning of your script
logging.basicConfig(filename='image_editor.log', level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')

def check_file_permissions(self):
    if os.access(self.json_path, os.W_OK):
        print("File is writable")
    else:
        print("File is not writable")
        
common_vehicle_status = [
    "Moving", "Stopped", "Parked", "Turning Left", "Turning Right", "U-Turning","Parking", "Braking", "Decelerating", "Accelerating", "Reversing","Overtaking", "Yielding", 
    "Rear Brake Light On", "Hazard Lights On","Turned Right Lights On", "Turned Left Lights On", "Brake Lights On","Changing Lane Left", "Changing Lane Right", "Following",
    "Crossing","Avoiding", "Approaching", "Is Not Visible", "Driver Exiting Vehicle","Loading", "Unloading", "Right-of-Way","Sudden Stop by Vehicle","Vehicle Double Parking", 
    "Vehicle Backing Up","Car Door Opening","Vehicle Turning Without Signal","Vehicle Drifting","Vehicle Parked Illegally", "Vehicle Broken Down", "Vehicle Blocking Driveway",
    "Unsecured Load on Vehicle","driving on heavy traffic density Decelerating and Accelerating","Partially obstructing lanes",
]

emergency_vehicle_status = [
    "Emergency Lights On", "Emergency Lights Off", "Flashing Lights", "Responding",
    "Patrolling","drivable area"
] + common_vehicle_status

common_lane_status = ["Visible", "Obstructed", "Faded", "Not Visible", "Lane_Bus_Lane", "Lane_Railroad","Lane_Bike_Lane","Crosswalk Blocked"]

common_sign_status = [
    "Visible", "Obstructed", "Damaged", "Faded", "Missing", "Not Visible",
    "Clean", "Dirty", "Worn", "Graffiti", "Operational", "Non-Operational",
    "Flashing", "Temporary", "Right-of-Way"
]

common_intersection_status = [
    "Visible", "Obstructed", "Controlled", "Uncontrolled", "Not Visible", "Right-of-Way", "stope sign Controlled",
]

common_light_status = [
    "Red", "Yellow", "Green", "Flashing Red", "Flashing Yellow",
    "Flashing Green", "Off", "Not Visible", "Is Controlling the", "Is Controlling Opposite Direction", "Right-of-Way", "Is Controlling the straight direction", "Is Controlling the left direction", "Is Controlling the right direction"]

common_road_status = ["One-lane", "Two-lane", "Three-lane", "Four-lane", "Five-lanes",
"Turn Lane Added", "Left Turn Only Lane","Right Turn Only Lane","Temporary Lane Shift","Lane Reduction Ahead","Lane Marking Faded",
#separates opposing directions
"Median-Raised", "Median-Depressed","Median-Closed","Median-None",

"Median_Flush_Lane_Solid_Line_White", 
"Median_Flush_Lane_Dashed_Line_White", 
"Median_Flush_Lane_Double_Line_White",
"Median_Flush_Lane_Solid_Line_Yellow",
"Median_Flush_Lane_Dashed_Line_Yellow",
"Median_Flush_Lane_Double_Line_Yellow",

"Lane_Solid_Line_White_1", 
"Lane_Dashed_Line_White_1", 
"Lane_Double_Line_White_1",
"Lane_Solid_Line_Yellow_1",
"Lane_Dashed_Line_Yellow_1",
"Lane_Double_Line_Yellow_1",

"Lane_Solid_Line_White_2", 
"Lane_Dashed_Line_White_2", 
"Lane_Double_Line_White_2",
"Lane_Solid_Line_Yellow_2",
"Lane_Dashed_Line_Yellow_2",
"Lane_Double_Line_Yellow_2",


"Falling Object", 
"Road Obstruction",
"Fallen Tree or Branch",
"Road Blockage",
"Trash Can in the Road",
"main road", 
"non main road"
]

object_status_options = {
    # Vehicles
    "ego": common_vehicle_status,
    "car": common_vehicle_status,
    "car door": ["Open", "Closed", "Locked", "Unlocked"],
    "truck": common_vehicle_status,
    "construction vehicle": common_vehicle_status + ["Under Construction", "Hazardous Materials"],
    "bus": common_vehicle_status + ["Boarding", "Alighting"],
    "ambulance": emergency_vehicle_status,
    "fire truck": emergency_vehicle_status,
    "police vehicle": emergency_vehicle_status,
    "train": ["Moving", "Stopped", "Right-of-Way"],
    "fake_car": ["Not Real", "Reflecting from Car"],
    "airplane": ["Taking Off", "In Flight", "Landing", "Right-of-Way"],
    
    "motorcycle": common_vehicle_status + ["Parked"],
    "bicycle": ["Riding", "Stopped", "Turning Left", "Turning Right", "Parked", "Right-of-Way"],
    "rider": ["Riding", "Stopped", "Turning Left", "Turning Right", "Parked", "Right-of-Way"],
    "pedestrian": ["Walking", "Running", "Standing", "Right-of-Way","Children Playing","Sudden Pedestrian Entry","Jaywalking"],
    "handbag": ["Carried", "Dropped", "Left in Vehicle", "Right-of-Way"],
    "dog": ["Walking", "Running", "Sitting", "Barking", "Right-of-Way", "walking with owner", "rope for tying", " without a rope for tying"],
    "skateboard": ["Riding", "Stopped", "Parked", "Right-of-Way"],
    "baby stroller": ["In Use", "Folded", "Parked", "Right-of-Way"],
    "flat car trolley": ["Moving", "Stopped", "Loading", "Unloading", "Right-of-Way"],
    
    # Traffic Signals and Signs
    "TS_Stop": common_sign_status,
    "TS_Yield": common_sign_status,
    "TS_Speed_Limit_15": common_sign_status + ["Speeding", "Compliant"],
    "TS_Speed_Limit_20": common_sign_status,
    "TS_Speed_Limit_25": common_sign_status + ["Speeding", "Compliant"],
    "TS_Speed_Limit_30": common_sign_status,
    "TS_Speed_Limit_40": common_sign_status,
    "TS_Speed_Limit_45": common_sign_status + ["Speeding", "Compliant"],
    "TS_Speed_Limit_50": common_sign_status,
    "TS_Speed_Limit_60": common_sign_status,
    "TS_Speed_Limit_70": common_sign_status,
    "TS_Speed_Limit_80": common_sign_status,
    "TS_Railroad_Crossing": common_sign_status + ["Active", "Inactive"],
    "TS_Pedestrian_Crossing": common_sign_status,
    "TS_No_Entry": common_sign_status,
    "TS_Parking": common_sign_status,
    "TS_No_Parking": common_sign_status,
    "TS_School_Zone": common_sign_status,
    "TS_Directional": common_sign_status + ["North", "South", "East", "West"],
    "TS_Warning": common_sign_status,
    "TS_No_U_Turn": common_sign_status,
    "TS_No_Left_Turn": common_sign_status,
    "TS_No_Right_Turn": common_sign_status,
    "TS_Hospital": common_sign_status,
    "TS_Road_Work": common_sign_status + ["Active", "Inactive"],
    "TS_Traffic_Signal_Ahead": common_sign_status,
    "TS_Roundabout_Ahead": common_sign_status,
    "TS_Bus_Stop": common_sign_status,
    "TS_Bicycle_Crossing": common_sign_status,
    "TS_keep_left_road": common_sign_status,
    "TS_keep_right_road":  common_sign_status,
    "TS_No_left_U_Turn":  common_sign_status,
    "Railway_Crossing_Ahead_Skew_Left": common_sign_status,
    "traffic light": common_light_status,
    "traffic light pedestrian": common_light_status + ["Walk", "Don't Walk"],

    # Road Infrastructure
    "bridge":common_intersection_status,
    
    "T-Intersection": common_intersection_status,
    "Four-Way Intersection": common_intersection_status,
    "road": common_road_status,
    "crosswalk": ["Visible", "Obstructed", "zebra", "Controlled", "Uncontrolled", "Not Visible", "have sign", "Unmarked", "Right-of-Way", "Between two lines" , "Clear of pedestrians" , "pedestrians on it"],
    "sidewalk": common_sign_status,
    "bicycle lane": common_lane_status + ["Dedicated", "Shared"],
    "Train Lane": ["Occupied", "Empty", "Maintenance", "Right-of-Way"]+common_lane_status,
    "drivable area": ["Clear", "Blocked", "Under Construction"],
    "bus stop": ["Occupied", "Empty", "Right-of-Way"]+common_lane_status,
    "gas station": ["Open", "Closed", "Under Maintenance", "Right-of-Way"]+common_lane_status,
    "Street_Furniture": ["Available", "Damaged", "Obstructed", "Under Maintenance", "Right-of-Way"],
    "Manhole": ["Open", "Closed", "Damaged", "Obstructed"],

    "Stop Marking": ["Visible", "Obstructed", "Faded", "Not Visible"],
    "Pedestrian Crossing Marking": common_sign_status,
    "right directional arrow": ["Active", "Inactive", "Flashing", "Visible", "Obstructed", "Faded", "Not Visible"],
    "straight directional arrow": ["Active", "Inactive", "Flashing", "Visible", "Obstructed", "Faded", "Not Visible"],
    "left directional arrow":["Active", "Inactive", "Flashing", "Visible", "Obstructed", "Faded", "Not Visible"],
    "left and straight directional arrow": ["Active", "Inactive", "Flashing", "Visible", "Obstructed", "Faded", "Not Visible"],
    "right and straight directional arrow": ["Active", "Inactive", "Flashing", "Visible", "Obstructed", "Faded", "Not Visible"],

    # Parking and Obstructions
    "Parking_Space": ["Occupied", "Empty", "Reserved"],
    "Parking_Lot": ["Full", "Available", "Closed"],
    "Parking_Meter": ["Active", "Inactive", "Out of Order"],

    # Environmental Hazards
    "Debris": ["Present", "Removed", "Obstructing"],
    "Pothole": ["Present", "Repaired", "Marked for Repair"],
    "Cone": ["Placed", "Missing", "Displaced"],
    "Barrier": ["Raised", "Lowered", "Fixed", "Movable"],
    "Bollard": ["Fixed", "Removable", "Broken"],
    "trash bin": ["Full", "Empty", "Overturned"],
    "tree": ["Standing", "Fallen", "Obstructing Road"],
    "Pole": ["Fixed", "Damaged"],
    "Construction_Zone": ["Active", "Inactive"],

    # Additional Objects
    "street sign": common_sign_status,
    "road divider": common_road_status,
    "Trash_Bin":common_sign_status,
}
# Common Position Lists
common_vehicle_position = [
    #spatial objects 
    "is in road","is off-road","Left side of", "Right side of", "Center side of", "is Ahead of" ,"is Far from", "is Near from","Before intersection","At intersection", "After intersection", 
    "Near pedestrian crosswalk","Near school zone", "Next to traffic light", "On overhead gantry","Near bus stop",

    "Lane 1", "Lane 2", "Lane 3", "Center lane", "Shoulder left","Shoulder right", "On ramp", "Off ramp",
    #Dynamic Positioning Include relative velocities or trajectories, such as "Approaching Intersection at 30 mph" or "Decelerating before Stop Sign" 
    "Is Driving on intersection", "Is Waiting at intersection", "Is Stopping at intersection", 
    "is Approaching Intersection","is Leaving Intersection","is Crossing Intersection","is Near Intersection","is Entering Intersection","is Exiting Intersection",
    
    "Is Moving across", "On Ramp", "Off Ramp", 
    "On Overpass", "Under Bridge", "Under Overpass", "Before", "Is At",
    "After", "Near of", "Far of", "Opposite side of", "Is Approaching",
    "Is Crossing", "Is Entering", "Is Exiting", "In same lane of",
    "In different lane of", "On Opposite Lane of", "On different lane of",
    "In", "On shoulder", "Entering Driveway", "Exiting Driveway",
    "Passing on Right", "Passing on Left",
    
    #3D Spatial Information
    "is Above","is Below", "is Behind of","is Under","is Inside","is Outside","is Ahead of","is Hidden behind of",  
    
    #Possessive 
    "is Part of","Contains","has","Consists of",
    #Semantic 
    "is Using","is Carrying","In Tunnel", "On Bridge","is At Intersection", "Is Parked on parking space", "Is Parked on shoulder", "is Entering", "is Exiting",  "section-1",
            "section-2",
            "section-3",
            "section-4",
            "section-5", 
]

# Completed Object Position Options Dictionary
object_position_options = {
    # Vehicles
    "ego": common_vehicle_position,

    "car": common_vehicle_position ,
    "car door": common_vehicle_position + ["On driver side", "On passenger side"],
    "truck": common_vehicle_position ,
    "construction vehicle": common_vehicle_position  + ["On construction site", "Near construction zone"],
    "bus": common_vehicle_position + ["At bus stop (left)", "At bus stop (right)"],
    "ambulance": common_vehicle_position + ["On emergency route"],
    "fire truck": common_vehicle_position + ["On emergency route"],
    "police vehicle": common_vehicle_position + ["On emergency route", "Patrolling", "Police Checkpoint", ],
    "train": ["At station", "On tracks", "Under bridge", "Over crossing", "Near depot"] + common_vehicle_position,
    "fake_car": ["In lane (phantom)", "Off road", "On road", "Near phantom barrier"]+ common_vehicle_position,
    "airplane": [ "Above runway", "Near runway", "In terminal vicinity", "On taxiway"],
    "motorcycle": common_vehicle_position ,
    "bicycle": common_vehicle_position + ["In bike lane (left)", "In bike lane (right)"],
    "rider": common_vehicle_position + ["In bike lane (left)", "In bike lane (right)"],

    "pedestrian": ["Crossing in front of (left to right)", "Crossing in front of (right to left)",
        "On sidewalk (left)", "On sidewalk (right)", "Near crosswalk"] + common_vehicle_position,

    "handbag": ["On ground near sidewalk", "Carried by pedestrian"],
    "dog": ["On leash near sidewalk", "Running on road", "Sitting near owner"]+common_vehicle_position,
    "skateboard": ["Riding near sidewalk", "Stopped on road", "Parked at skate park"]+ common_vehicle_position,
    "baby stroller": ["In use on sidewalk", "Folded near curb", "Parked in designated area"]+ common_vehicle_position,
    "flat car trolley": ["Loading at station", "Unloading at station", "Moving on tracks"]+ common_vehicle_position,

    # Traffic Signals and Signs
    "TS_Stop": common_vehicle_position,
    "TS_Yield": common_vehicle_position,
    "TS_Speed_Limit_15": common_vehicle_position,
    "TS_Speed_Limit_20":  common_vehicle_position,
    "TS_Speed_Limit_25":  common_vehicle_position,
    "TS_Speed_Limit_30":  common_vehicle_position,
    "TS_Speed_Limit_40":  common_vehicle_position,
    "TS_Speed_Limit_45":  common_vehicle_position,
    "TS_Speed_Limit_50":  common_vehicle_position,
    "TS_Speed_Limit_60":  common_vehicle_position,
    "TS_Speed_Limit_70":  common_vehicle_position,
    "TS_Speed_Limit_80":  common_vehicle_position,
    "TS_Railroad_Crossing":  common_vehicle_position + ["Active", "Inactive"],
    "TS_Pedestrian_Crossing":  common_vehicle_position,
    "TS_No_Entry":  common_vehicle_position,
    "TS_Parking":  common_vehicle_position,
    "TS_No_Parking": common_vehicle_position,
    "TS_School_Zone":  common_vehicle_position,
    "TS_Directional":  common_vehicle_position + ["North", "South", "East", "West"],
    "TS_Warning": common_vehicle_position,
    "TS_No_U_Turn":  common_vehicle_position,
    "TS_No_Left_Turn":  common_vehicle_position,
    "TS_No_Right_Turn":  common_vehicle_position,
    "TS_Hospital":  common_vehicle_position,
    "TS_Road_Work":  common_vehicle_position + ["Active", "Inactive"],
    "TS_Traffic_Signal_Ahead":  common_vehicle_position,
    "TS_Roundabout_Ahead":  common_vehicle_position,
    "TS_Bus_Stop":  common_vehicle_position,
    "TS_Bicycle_Crossing":  common_vehicle_position,
    "TS_keep_left_road":  common_vehicle_position,
    "TS_keep_right_road":  common_vehicle_position,
    "TS_No_left_U_Turn":   common_vehicle_position,
    "Railway_Crossing_Ahead_Skew_Left": common_vehicle_position,

    "traffic light":  ["Above intersection", "Adjacent to road", "Near pedestrian path"]+common_vehicle_position,
    "traffic light pedestrian":["Walk signal active", "Don't Walk signal active"]+common_vehicle_position,

    # Road Infrastructure
    "bridge":common_vehicle_position,
    "T-Intersection": common_vehicle_position,
    "Four-Way Intersection": common_vehicle_position,

    "crosswalk":  common_vehicle_position,
    "sidewalk": common_vehicle_position,
    "bicycle lane": ["Left side of road", "Right side of road", "Adjacent to sidewalk"],
    "Train Lane": ["Occupied", "Empty", "Under maintenance", "Near station"] + common_vehicle_position,
    "drivable area": ["Clear", "Blocked", "Under construction", "Wet", "Snow-covered"]+ common_vehicle_position,
    "bus stop": ["In bus bay", "Outside bus bay"]+ common_vehicle_position,
    "gas station": ["On main road side", "On service road side", "Near entrance", "Near exit"]+ common_vehicle_position,
    "Street_Furniture": ["Available", "Damaged", "Obstructed", "Under maintenance","On sidewalk left", "On sidewalk right"]+ common_vehicle_position,
    "Manhole": ["In road (center)", "In road (side)", "On sidewalk", "Near curb"] + common_vehicle_position,

    "Stop Marking": common_vehicle_position,
    "Pedestrian Crossing Marking":  common_vehicle_position,
    "right directional arrow":  common_vehicle_position,
    "straight directional arrow":  common_vehicle_position,
    "left directional arrow": common_vehicle_position,
    "left and straight directional arrow":  common_vehicle_position,
    "right and straight directional arrow":  common_vehicle_position,

    # Parking and Obstructions
    "Parking_Space":  ["In parking lot"]+common_vehicle_position,
    "Parking_Lot": ["Near entrance", "Near exit", "Covered area", "Uncovered area","Reserved section", "General section"]+common_vehicle_position,
    "Parking_Meter": ["At curbside left", "At curbside right", "In parking zone"]+common_vehicle_position,

    # Environmental Hazards
    "Debris": ["In road (center)", "In road (side)", "On sidewalk", "Near curb"]+common_vehicle_position,
    "Pothole": ["On road left", "On road right", "Near intersection", "Far from intersection"]+common_vehicle_position,
    "Cone": ["Placed on road", "Removed from road", "Displaced to sidewalk","Near construction zone"]+common_vehicle_position,
    "Barrier": ["Raised on road", "Lowered on road", "Fixed at location","Movable near construction site"]+common_vehicle_position,
    "Bollard": ["Fixed on sidewalk", "Removable on sidewalk", "Broken on sidewalk","Near entrance", "Near exit"]+common_vehicle_position,
    "trash bin": ["On sidewalk (left)", "On sidewalk (right)", "In road","Near park area", "Near building entrance"]+common_vehicle_position,
    "tree": ["On sidewalk (left)", "On sidewalk (right)", "In road","Near intersection", "In median"]+common_vehicle_position,
    "Pole": ["Fixed on sidewalk", "Fixed on road", "Damaged on sidewalk","Damaged on road"]+common_vehicle_position,
    "Construction_Zone": ["Active", "Inactive", "Near entrance", "Near exit","On road left", "On road right"]+common_vehicle_position,
    
    # Additional Objects
    "street sign": common_vehicle_position,
    "road divider": ["Solid white", "Dashed white", "Double solid white", "Faded","Near intersection", "Between lanes"] + common_vehicle_position,
}

class ImageEditor:
    def __init__(self, master):
        self.master = master
        self.master.title("Image Editor")
        self.data = []
        self.image_index = 0
        self.selected_node_index = None
        self.selected_edge_index = None
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.json_path = None
        self.image_folder = None
        self.json_files = []
        self.json_index = 0
        self.original_img = None  # Holds the PIL Image
        self.tk_img = None        # Holds the PhotoImage for Tkinter
        self.master.bind("<Delete>", self.delete_selected_node)
        self.master.bind("<F1>", self.copy_object_id)
        self.polyline_points = []  # Stores points for the polyline
        self.is_drawing_polyline = False
        
        # Frame-level checkbox states
        self.frame_checked_var = BooleanVar(value=False)
        self.frame_confirmed_var = BooleanVar(value=False)
        
        
        self.object_safety_vars = {}
        self.object_safety_options = [
            "Affects Safety",
            "Potentially Affect Safety",
            "Does Not Affect Safety",
            "Requires Monitoring"
        ]

        # Patch Attack Variables
        self.attack_type_var = StringVar(value="WhitePatch")
        
        self.static_objects = [
            # Traffic Signals and Signs
            "traffic light","Traffic_Light_Pedestrian","TS_Stop","Stop Marking","TS_Yield","TS_Speed_Limit_20","TS_Speed_Limit_30","TS_Speed_Limit_40","TS_Speed_Limit_50","TS_Speed_Limit_60","TS_Speed_Limit_70","TS_Speed_Limit_80",
            "TS_Railroad_Crossing","TS_Pedestrian_Crossing","TS_No_Entry","TS_Parking","TS_No_Parking","TS_School_Zone","TS_Directional","TS_Warning","TS_No_U_Turn","TS_No_Left_Turn","TS_No_Right_Turn","TS_Hospital","TS_Road_Work",
            "TS_Traffic_Signal_Ahead","TS_Roundabout_Ahead","TS_Bus_Stop","TS_Bicycle_Crossing","TS_Construction_Sign",
            
            # Road Infrastructure
            "crosswalk","marking_Pedestrian_Crossing","road","Sidewalk","T-Intersection","Four-Way Intersection","Hazard_Zone","Speed_Bump","Construction_Zone","right directional arrow","straight directional arrow","left directional arrow","Manhole",
            "left and straight directional arrow","right and straight directional arrow"

            "Bus station", "gas station",

            # Parking and Obstructions
            "Parking_Space","Parking_Lot","Parking_Meter","Barrier","Bollard","Cone","Trash_Bin","Tree","Pole",

            # Environmental Hazards
            "Debris","Pothole"
        ]

        self.dynamic_objects = [
            "ego",
            "car","bus","train","truck","construction vehicle",
            
            "fake_car",
            
            "airplane",
            
            "ambulance","police vehicle","fire truck",
            
            "motorcycle",
            
            "pedestrian","bicycle","rider","baby stroller"
        ]

        
        self.is_moving = False
        self.move_start_x = None
        self.move_start_y = None
        self.selected_bbox_initial = None

        self.draw_mode = StringVar(value="bbox")  
        self.free_draw_coords = []  
        
        
        self.position_var = StringVar(value="ahead")  

        self.create_widgets()
        self.create_menu()

        
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        
        
    def create_widgets(self):
        
        self.canvas = Canvas(self.master, bg='white')
        self.canvas.grid(row=0, column=0, rowspan=40, columnspan=6, sticky="nsew")

        self.v_scrollbar = Scrollbar(self.master, orient=VERTICAL, command=self.canvas.yview)
        self.v_scrollbar.grid(row=0, column=7, rowspan=40, sticky="ns")
        self.h_scrollbar = Scrollbar(self.master, orient=HORIZONTAL, command=self.canvas.xview)
        self.h_scrollbar.grid(row=40, column=0, columnspan=6, sticky="ew")

        self.canvas.config(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)


        # JSON file name label
        self.json_file_name_label = Label(self.master, text="JSON File:")
        self.json_file_name_label.grid(row=0, column=7, sticky="ew", padx=5, pady=5)

        # Frame for navigation Entry and Button
        self.json_navigation_frame = Frame(self.master)
        self.json_navigation_frame.grid(row=0, column=8, sticky="ew", padx=5, pady=5)

        # Entry widget for JSON file navigation
        self.json_search_entry = Entry(self.json_navigation_frame, width=20)
        self.json_search_entry.pack(side="left", padx=5)

        # "Go" button
        self.json_go_button = Button(self.json_navigation_frame, text="Go", command=self.go_to_json_file)
        self.json_go_button.pack(side="left", padx=5)

        self.id_label = Label(self.master, text="Image ID:")
        self.id_label.grid(row=1, column=7, sticky="ew")
        self.id_value_label = Label(self.master, text="")
        self.id_value_label.grid(row=1, column=8, sticky="ew")

        self.caption_label = Label(self.master, text="Caption:")
        self.caption_label.grid(row=2, column=7, sticky="ew")
        self.caption_entry = Entry(self.master)
        self.caption_entry.grid(row=2, column=8, sticky="ew")

        self.maneuver_label = Label(self.master, text="Car Maneuver:")
        self.maneuver_label.grid(row=3, column=7, sticky="ew")
        self.maneuver_entry = Entry(self.master)
        self.maneuver_entry.grid(row=3, column=8, sticky="ew")
        
        self.cause_label = Label(self.master, text="Cause:")
        self.cause_label.grid(row=4, column=7, sticky="ew")
        
        self.cause_label = Label(self.master, text="Cause:")
        self.cause_label.grid(row=4, column=7, sticky="ew")
        
        self.cause_listbox = Listbox(self.master, selectmode=MULTIPLE, height=8, exportselection=False)
        
        causes =[
            "Improper Turn",  
            "Abrupt Lane Change",  
            "Intersection Congestion",  
            "Red Light Violation",  
            "Traffic Congestion",  
            "Stopped Traffic Ahead",  
            "Slow-Moving Traffic",  
            "Right-of-Way",
            "Car Accident Ahead",  
            "Wrong-Way Driving",  
            "Cars parking on the shoulder",  
            "Sinkhole",                
            "Street Flooding",
            "Low Visibility", 
            "Sun Glare",
            "Shadow on Road",
            "Detour Ahead",
            "One-Way Street",
            "Failure to yield right-of-way",
            "Light traffic density",
            "moderate traffic density",
            "heavy traffic density",
            "Rainy conditions",
            "Snowy or Icy roads",
            "Foggy conditions",
            "Windy conditions",
            "Dust storms or sandstorms",
            "Night-time",
            "Day-time"
            "Improper or illegal parking near intersections",
            "Cars parking on the shoulder or partially",
            "obstructing lanes",
            "Children playing near the road",
            "Partially obstructing lanes",
            "Large trucks or buses causing visibility or maneuverability issues"
        ]
        
        self.previous_status_selection = []
        self.previous_position_selection = []
        self.previous_cause_selection = []
        
        
        for cause in causes:
            self.cause_listbox.insert(END, cause)

        self.cause_listbox.grid(row=4, column=8, sticky="ew")

        
        self.cause_listbox.bind("<<ListboxSelect>>", self.on_cause_select)


        self.goal_oriented_label = Label(self.master, text="Goal-Oriented:")
        self.goal_oriented_label.grid(row=5, column=7, sticky="ew")
        self.goal_oriented_entry = Entry(self.master)
        self.goal_oriented_entry.grid(row=5, column=8, sticky="ew")

        self.safe_label = Label(self.master, text="Safe:")
        self.safe_label.grid(row=6, column=7, sticky="ew")
        self.safe_entry = Entry(self.master)
        self.safe_entry.grid(row=6, column=8, sticky="ew")

        self.Action_Suggestions_label = Label(self.master, text="Action Suggestions:")
        self.Action_Suggestions_label.grid(row=7, column=7, sticky="ew")
        self.Action_Suggestions_entry = Entry(self.master)
        self.Action_Suggestions_entry.grid(row=7, column=8, sticky="ew")

        self.Traffic_Regulations_Suggestions_label = Label(self.master, text="Traffic Regulations Suggestions:")
        self.Traffic_Regulations_Suggestions_label.grid(row=8, column=7, sticky="ew")
        self.Traffic_Regulations_Suggestions_entry = Entry(self.master)
        self.Traffic_Regulations_Suggestions_entry.grid(row=8, column=8, sticky="ew")

        bbox_frame = Frame(self.master)
        bbox_frame.grid(row=9, column=8, columnspan=2, sticky="ew")

        self.bbox_xmin_label = Label(bbox_frame, text="xmin:")
        self.bbox_xmin_label.pack(side="left")
        self.bbox_xmin_entry = Entry(bbox_frame, width=5)
        self.bbox_xmin_entry.pack(side="left")
        
        self.bbox_ymin_label = Label(bbox_frame, text="ymin:")
        self.bbox_ymin_label.pack(side="left")
        self.bbox_ymin_entry = Entry(bbox_frame, width=5)
        self.bbox_ymin_entry.pack(side="left")
        
        self.bbox_xmax_label = Label(bbox_frame, text="xmax:")
        self.bbox_xmax_label.pack(side="left")
        self.bbox_xmax_entry = Entry(bbox_frame, width=5)
        self.bbox_xmax_entry.pack(side="left")
        
        self.bbox_ymax_label = Label(bbox_frame, text="ymax:")
        self.bbox_ymax_label.pack(side="left")
        self.bbox_ymax_entry = Entry(bbox_frame, width=5)
        self.bbox_ymax_entry.pack(side="left")
        
        self.status_label = Label(self.master, text="Status:")
        self.status_label.grid(row=10, column=7, sticky="ew")
        
        self.status_listbox = Listbox(self.master, selectmode=MULTIPLE, height=5, exportselection=False)
        self.status_listbox.grid(row=10, column=8, sticky="ew")
        
        self.position_label = Label(self.master, text="Position:")
        self.position_label.grid(row=11, column=7, sticky="ew")
        
        self.position_listbox = Listbox(self.master, selectmode=MULTIPLE, height=5, exportselection=False) 
        self.position_listbox.grid(row=11, column=8, sticky="ew")
        
        self.status_listbox.bind("<<ListboxSelect>>", self.on_status_select)
        self.position_listbox.bind("<<ListboxSelect>>", self.on_position_select)
        
        self.obj_name_label = Label(self.master, text="Object Name:")
        self.obj_name_label.grid(row=12, column=7, sticky="ew")
        self.obj_name_var = StringVar()
        self.obj_name_combobox = ttk.Combobox(self.master, textvariable=self.obj_name_var)
        self.obj_name_combobox['values'] = (
            "ego",  
            "car", 
            "car door",
            "fake_car",  
            "airplane",  
            "bus",  
            "train",  
            "truck", 
            "construction vehicle",
            
            "ambulance",  
            "police vehicle",  
            "fire truck", 
            
            "motorcycle",  
            "pedestrian",  
            "handbag",
            "bicycle",  
            "rider",  
            "dog",
            "skateboard",
            
            "bridge",
            "crosswalk",  
            "Street Furniture",
            "Pedestrian Crossing Marking",
            "road",
            "bicycle lane",
            "Train Lane",
            "sidewalk",  
            "T-Intersection",  
            "Four-Way Intersection", 
            "section-1",
            "section-2",
            "section-3",
            "section-4",
            "section-5",
            "drivable area",
            
            "traffic light",  
            "traffic light pedestrian", 
            
            "baby stroller",
            "flat car trolley",
            
            "TS_Stop",
            "Stop Marking",  
            "TS_Yield",  
            "TS_Speed_Limit_15",
            "TS_Speed_Limit_20",
            "TS_Speed_Limit_25",
            "TS_Speed_Limit_30",  
            "TS_Speed_Limit_40",  
            "TS_Speed_Limit_45",
            "TS_Speed_Limit_50",  
            "TS_Speed_Limit_60",  
            "TS_Speed_Limit_70",  
            "TS_Speed_Limit_80",  
            "TS_Railroad_Crossing",
            "Railway_Crossing_Ahead_Skew_Left",
            "Railway_Crossing_Ahead_Skew_Right",
            "TS_Pedestrian_Crossing",  
            "TS_keep_left_road",
            "TS_keep_right_road",
            "TS_No_Entry",  
            "TS_Parking",  
            "TS_No_Parking",  
            "TS_School_Zone",  
            "TS_Directional",  
            "TS_Warning",  
            "TS_No_U_Turn",
            "TS_No_left_U_Turn",
            "TS_No_Left_Turn",  
            "TS_No_Right_Turn",  
            "TS_Hospital",  
            "TS_Road_Work",  
            "TS_Traffic_Signal_Ahead",  
            "TS_Roundabout_Ahead",  
            "TS_Bus_Stop",  
            "TS_Bicycle_Crossing",  
            "Marking Speed_Limit_20",
            "Hazard_Zone",  
            "Speed_Bump",  
            "TS_Construction_Sign",  
            "Construction_Zone",  
            "Bus station",
            "gas station",
            
            
            "right directional arrow",  
            "straight directional arrow",
            "left directional arrow",
            "left and straight directional arrow",
            "right and straight directional arrow",
            "Manhole",
            
            "Parking_Space",  
            "Parking_Lot",  
            "Parking_Meter",  
            
            "Debris",
            "Pothole",
            "Barrier",  
            "Bollard",  
            "Cone",  
            "Trash_Bin",  
            "Tree",
            "Pole", 
            "road divider",
            "street sign",
        )

        self.obj_name_combobox.grid(row=12, column=8, sticky="ew")


        # Object Safety Label
        self.object_safety_label = Label(self.master, text="Object Safety:")
        self.object_safety_label.grid(row=13, column=7, sticky="ew")

        # Frame for radio buttons
        self.object_safety_frame = Frame(self.master)
        self.object_safety_frame.grid(row=13, column=8, sticky="ew")

        # Create Object Safety Checkboxes
        for option in self.object_safety_options:
            var = BooleanVar()
            self.object_safety_vars[option] = var
            checkbox = Checkbutton(
                self.object_safety_frame,
                text=option,
                variable=var,
                command=self.on_object_safety_change
            )
            checkbox.pack(side="left")

        
        
        self.importance_ranking_label = Label(self.master, text="Importance Ranking:")
        self.importance_ranking_label.grid(row=14, column=7, sticky="ew")
        
        importance_ranking_frame = Frame(self.master)
        importance_ranking_frame.grid(row=14, column=8, sticky="ew", padx=10, pady=5)
        self.importance_ranking_var = StringVar(value="medium")
        
        self.low_radiobutton = Radiobutton(importance_ranking_frame, text="None", variable=self.importance_ranking_var, value="none")
        self.low_radiobutton.pack(side="left", padx=5)
        
        self.low_radiobutton = Radiobutton(importance_ranking_frame, text="Low", variable=self.importance_ranking_var, value="low")
        self.low_radiobutton.pack(side="left", padx=5)

        self.medium_radiobutton = Radiobutton(importance_ranking_frame, text="Medium", variable=self.importance_ranking_var, value="medium")
        self.medium_radiobutton.pack(side="left", padx=5)

        self.high_radiobutton = Radiobutton(importance_ranking_frame, text="High", variable=self.importance_ranking_var, value="high")
        self.high_radiobutton.pack(side="left", padx=5)

        
        self.object_type_label = Label(self.master, text="Is causal:")
        self.object_type_label.grid(row=15, column=7, sticky="ew")

        
        object_type_frame = Frame(self.master)
        object_type_frame.grid(row=15, column=8, sticky="ew", padx=10, pady=5)

        self.object_type_var = StringVar(value="none")  
        
        self.static_radiobutton = Radiobutton(object_type_frame, text="none", variable=self.object_type_var, value="none")
        self.static_radiobutton.pack(side="left", padx=5)
        
        self.Cause_radiobutton = Radiobutton(object_type_frame, text="Cause", variable=self.object_type_var, value="Cause")
        self.Cause_radiobutton.pack(side="left", padx=5)

        self.dynamic_radiobutton = Radiobutton(object_type_frame, text="Effect", variable=self.object_type_var, value="Effect")
        self.dynamic_radiobutton.pack(side="left", padx=5)
        
        
        #16
        self.Object_Causal_label = Label(self.master, text="Object casual:")
        self.Object_Causal_label.grid(row=16, column=7, sticky="ew")
        self.Object_Causal_var = StringVar()
        self.Object_Causal_combobox = ttk.Combobox(self.master, textvariable=self.Object_Causal_var)
        self.Object_Causal_combobox['values'] = ("ego<po>711,708<po>")
        self.Object_Causal_combobox.grid(row=16, column=8, sticky="ew")
        #17
        self.Causal_Relation_label = Label(self.master, text="Casual Relation:")
        self.Causal_Relation_label.grid(row=17, column=7, sticky="ew")
        self.Causal_Relation_var = StringVar()
        self.Causal_Relation_combobox = ttk.Combobox(self.master, textvariable=self.Causal_Relation_var)
        self.Causal_Relation_combobox['values'] = (
            "Direct",
            "Chain", 
            "Confounder", 
            "Collider", 
            "Mediator", 
            "correlations"
        )
        self.Causal_Relation_combobox.grid(row=17, column=8, sticky="ew")
        
        self.object_id_label = Label(self.master, text="Object ID:")  
        self.object_id_label.grid(row=18, column=7, sticky="ew", padx=5, pady=5)  
        
        self.object_id_entry = Entry(self.master)  
        self.object_id_entry.grid(row=18, column=8, sticky="ew", padx=5, pady=5)
        
        self.object_id_label = Label(self.master, text="Object ID:")
        self.object_id_label.grid(row=18, column=7, sticky="ew")
        self.object_id_entry = Entry(self.master)
        self.object_id_entry.grid(row=18, column=8, sticky="ew")
        
        self.drawing_mode_frame = Frame(self.master)
        self.drawing_mode_frame.grid(row=19, column=7, columnspan=2, sticky="ew")
        
        self.bbox_radio = Radiobutton(self.drawing_mode_frame, text="Bounding Box", variable=self.draw_mode, value="bbox")
        self.bbox_radio.pack(side="left")
        self.lane_radio = Radiobutton(self.drawing_mode_frame, text="Lane", variable=self.draw_mode, value="lane")
        self.lane_radio.pack(side="left")
        self.free_draw_radio = Radiobutton(self.drawing_mode_frame, text="Free Draw", variable=self.draw_mode, value="free")
        self.free_draw_radio.pack(side="left")
        self.point_radio = Radiobutton(self.drawing_mode_frame, text="Point", variable=self.draw_mode, value="point")
        self.point_radio.pack(side="left")
        
        self.polyline_radio = Radiobutton(self.drawing_mode_frame, text="Polyline", variable=self.draw_mode, value="polyline")
        self.polyline_radio.pack(side="left")


        self.buttons_frame = Frame(self.master)
        self.buttons_frame.grid(row=20, column=7, columnspan=2, sticky="ew")

        self.add_button = Button(self.buttons_frame, text="Add Object", command=self.add_node)
        self.add_button.pack(side="left", padx=2, pady=2)

        self.update_button = Button(self.buttons_frame, text="Update Object", command=self.update_node)
        self.update_button.pack(side="left", padx=2, pady=2)

        self.update_all_objects_button = Button(self.buttons_frame, text="Update All Objects Type", command=self.update_all_objects)
        self.update_all_objects_button.pack(side="left", padx=2, pady=2)
        
        self.update_multiple_button = Button(self.buttons_frame, text="Update Selected Objects", command=self.update_selected_objects)
        self.update_multiple_button.pack(side="left", padx=2, pady=2)
        
        
        self.delete_button = Button(self.buttons_frame, text="-----------------")
        self.delete_button.pack(side="left", padx=2, pady=2)
        
        self.delete_button = Button(self.buttons_frame, text="Delete Selected Object", command=self.delete_selected_node)
        self.delete_button.pack(side="left", padx=2, pady=2)

        self.object_id_frame_label = Label(self.master, text="Object ID List:")
        self.object_id_frame_label.grid(row=21, column=7, columnspan=2, sticky="ew")
        self.object_id_listbox = Listbox(self.master, selectmode=MULTIPLE, height=5, exportselection=False)
        self.object_id_listbox.grid(row=22, column=7, columnspan=2, sticky="ew")

        self.object_level_listbox = Listbox(self.master, selectmode=MULTIPLE)
        self.object_level_listbox.grid(row=23, column=7, columnspan=2, sticky="nsew")
        
        self.edges_frame = Frame(self.master)
        self.edges_frame.grid(row=23, column=7, columnspan=2, sticky="ew")

        self.obj1_label = Label(self.edges_frame, text="Object 1:")
        self.obj1_label.grid(row=0, column=0, sticky="ew")
        self.obj1_var = StringVar()
        self.obj1_combobox = ttk.Combobox(self.edges_frame, textvariable=self.obj1_var)
        self.obj1_combobox.grid(row=0, column=1, sticky="ew")

        self.obj2_label = Label(self.edges_frame, text="Object 2:")
        self.obj2_label.grid(row=1, column=0, sticky="ew")
        self.obj2_var = StringVar()
        self.obj2_combobox = ttk.Combobox(self.edges_frame, textvariable=self.obj2_var)
        self.obj2_combobox.grid(row=1, column=1, sticky="ew")

        self.relation_label = Label(self.edges_frame, text="Relation:")
        self.relation_label.grid(row=2, column=0, sticky="ew")
        self.relation_var = StringVar()
        self.relation_combobox = ttk.Combobox(self.edges_frame, textvariable=self.relation_var, height=3)
        self.relation_combobox['values'] = (
                                            
                                            "is Above",  
                                            "is Below",  
                                            "is Behind",  
                                            "is In front of",  
                                            "is Near",  
                                            "is Far from",  
                                            "is Left of",  
                                            "is Right of",  
                                            "is Inside",  
                                            "is Outside",  
                                            "is Ahead of",  
                                            "is Under",  
                                            "is Facing away from",  
                                            "is Obstructed by",  
                                            "is Hidden behind",  
                                            "is Controlling opposite direction",  
                                            "is Not visible",  

                                            
                                            "is At Intersection",  
                                            "is Approaching Intersection",  
                                            "is Leaving Intersection",  
                                            "is Crossing Intersection",  
                                            "is Near Intersection",  
                                            "is Entering Intersection",  
                                            "is Exiting Intersection",  

                                            
                                            "Has",  
                                            "is Part of",  
                                            "is Wearing",  
                                            "Contains",  

                                            
                                            "is Carrying",  
                                            "is Using",  
                                            "is Parked in",  
                                            "is Driving on",  
                                            "is Waiting at",  
                                            "is Entering",  
                                            "is Exiting",  
                                            "is Stopping at",  
                                            "is Moving across",  

                                            
                                            "Affects",  
                                            "Crosses",  
                                            "Enters",  
                                            "Exits",  
                                            "Passes by",  
                                            "Blocks",  
                                            "Impacts",  
                                            "Merges into",  
                                            "Overtakes",  
                                            "Follows",  
                                            "Yields to",  
                                            "Stops for",  

                                            
                                            "is Related to",  
                                            "is Connected to",  
                                            "is Similar to",  
                                            "is Linked to",  
                                            "Controlled by",  
                                            )
        
        self.relation_combobox.grid(row=2, column=1, sticky="ew")

        self.add_edge_button = Button(self.edges_frame, text="Add Edge", command=self.add_edge)
        self.add_edge_button.grid(row=3, column=0, sticky="ew")
        
        
        self.add_edge_S_button = Button(self.edges_frame, text="Add Edge from Selecting", command=self.add_edge_selecting)
        self.add_edge_S_button.grid(row=3, column=1, sticky="ew")
        
        self.edit_edge_button = Button(self.edges_frame, text="Edit Edge", command=self.edit_edge)
        self.edit_edge_button.grid(row=3, column=2, sticky="ew")

        self.delete_edge_button = Button(self.edges_frame, text="Delete Edge", command=self.delete_edge)
        self.delete_edge_button.grid(row=3, column=3, sticky="ew")
        
        
        self.delete_all_edges_button = Button(self.edges_frame, text="Delete All Edges", command=self.delete_all_edges)
        self.delete_all_edges_button.grid(row=3, column=4, columnspan=2, sticky="ew")


        self.edges_listbox = Listbox(self.master, selectmode=MULTIPLE, height=5, exportselection=False)
        self.edges_listbox.grid(row=24, column=7, columnspan=2, sticky="ew")

        
        self.question_label = Label(self.master, text="Question:")#, font=("Helvetica", 12, "bold"))
        self.question_label.grid(row=25, column=7, sticky="ew")
        self.question_entry = Entry(self.master)#, font=("Helvetica", 12))
        self.question_entry.grid(row=25, column=8, sticky="ew")

        self.answer_label = Label(self.master, text="Answer:")#, font=("Helvetica", 12, "bold"))
        self.answer_label.grid(row=26, column=7, sticky="ew")
        self.answer_entry = Entry(self.master)#, font=("Helvetica", 12))
        self.answer_entry.grid(row=26, column=8, sticky="ew")

        self.type_label = Label(self.master, text="Type:")#, font=("Helvetica", 12, "bold"))
        self.type_label.grid(row=27, column=7, sticky="ew")
        self.type_var = StringVar()
        self.type_combobox = ttk.Combobox(self.master, textvariable=self.type_var)#, font=("Helvetica", 12))
        self.type_combobox['values'] = ("Discovery", "Association", "Intervention", "Counterfactual")
        self.type_combobox.grid(row=27, column=8, sticky="ew")

        self.create_patch_controls()

        self.task_label = Label(self.master, text="Task:")#, font=("Helvetica", 12, "bold"))
        self.task_label.grid(row=28, column=7, sticky="ew")
        self.task_entry = Entry(self.master)#, font=("Helvetica", 12))
        self.task_entry.grid(row=28, column=8, sticky="ew")

        self.add_qa_button = Button(self.master, text="Add Q&A", command=self.add_qa)#, font=("Helvetica", 12, "bold"))
        self.add_qa_button.grid(row=29, column=7, columnspan=2, sticky="ew")

        self.qa_listbox = Listbox(self.master)#, font=("Helvetica", 12))
        self.qa_listbox.grid(row=30, column=7, columnspan=2, sticky="nsew")
        
        
        self.buttons1_frame = Frame(self.master)
        self.buttons1_frame.grid(row=31, column=7, columnspan=2, sticky="ew")

        self.edit_qa_button = Button(self.buttons1_frame, text="Edit Q&A", command=self.edit_qa)
        self.edit_qa_button.pack(side="left", padx=2, pady=2)

        self.delete_qa_button = Button(self.buttons1_frame, text="Delete Q&A", command=self.delete_qa)
        self.delete_qa_button.pack(side="left", padx=2, pady=2)

        self.save_button = Button(self.buttons1_frame, text="Save Changes", command=self.save_changes)
        self.save_button.pack(side="left", padx=2, pady=2)
        
        
        
        
        # Parent frame for everything on this row
        attack_frame = ttk.Frame(self.master)
        attack_frame.grid(row=34, column=7, columnspan=2, sticky="ew", padx=5, pady=5)

        # 1) Attack Type Label
        attack_type_label = ttk.Label(attack_frame, text="Select Attack Type:")
        attack_type_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")

        # 2) Attack Type Combobox
        attack_type_dropdown = ttk.Combobox(attack_frame, textvariable=self.attack_type_var)
        attack_type_dropdown['values'] = ("WhitePatch", "BlackPatch", "StickerPatch", "GaussianNoise", "RandomNoise")
        attack_type_dropdown.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        # 3) "Apply Attack" Button
        apply_attack_button = Button(attack_frame, text="Apply Attack", command=self.apply_selected_attack)
        apply_attack_button.grid(row=0, column=2, padx=5, pady=2, sticky="w")

        # 4) "Save Attack" Button
        save_attack_button = Button(attack_frame, text="Save Attack",
                                    command=lambda: self.save_attack(self.original_img, self.attack_type_var.get()))
        save_attack_button.grid(row=0, column=3, padx=5, pady=2, sticky="w")

        # 5) Frame Check Status Label
        frame_check_label = ttk.Label(attack_frame, text="Frame Check Status:")
        frame_check_label.grid(row=0, column=4, padx=(20, 5), pady=2, sticky="e")

        # 6) "Checked" Checkbox
        self.frame_checked_checkbox = Checkbutton(
            attack_frame,
            text="Checked",
            variable=self.frame_checked_var,
            command=self.on_frame_checkbox_changed
        )
        self.frame_checked_checkbox.grid(row=0, column=5, padx=2, pady=2, sticky="w")

        # 7) "Confirmed" Checkbox
        self.frame_confirmed_checkbox = Checkbutton(
            attack_frame,
            text="Confirmed",
            variable=self.frame_confirmed_var,
            command=self.on_frame_checkbox_changed
        )
        self.frame_confirmed_checkbox.grid(row=0, column=6, padx=2, pady=2, sticky="w")

        # Configure columns so content hugs to the left, but expands if needed.
        for col in range(7):
            attack_frame.grid_columnconfigure(col, weight=0)
        
        # self.coord_label = Label(self.master, text="")
        # self.coord_label.grid(row=34, column=8, columnspan=2, sticky="ew")

        self.canvas.bind("<Button-1>", self.canvas_click)
        self.canvas.bind("<Button-3>", self.start_draw)
        self.canvas.bind("<Double-Button-1>", self.end_polyline_draw)  # Handle double-click to end polyline

        self.canvas.bind("<B3-Motion>", self.update_draw)
        self.canvas.bind("<ButtonRelease-3>", self.end_draw)
        self.canvas.bind("<B1-Motion>", self.move_bbox)
        self.canvas.bind("<ButtonRelease-1>", self.end_move)
        self.object_level_listbox.bind("<<ListboxSelect>>", self.on_object_level_select)
        self.edges_listbox.bind("<<ListboxSelect>>", self.on_edge_select)
        self.qa_listbox.bind("<<ListboxSelect>>", self.on_qa_select)
        # Bind the F2 key to trigger the on_f2_press function
        self.master.bind("<F2>", self.on_f2_press)
        self.master.bind("<Left>", self.move_left)
        self.master.bind("<Right>", self.move_right)
        self.master.bind("<Up>", self.move_up)
        self.master.bind("<Down>", self.move_down)

        for i in range(41):
            self.master.grid_rowconfigure(i, weight=1)
        for i in range(9):
            self.master.grid_columnconfigure(i, weight=1)

        self.master.bind("<Configure>", self.on_resize)
        
    def create_menu(self):
        menu = Menu(self.master)
        self.master.config(menu=menu)

        file_menu = Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open JSON Directory", command=self.load_json_directory)
        file_menu.add_command(label="Open Image Directory", command=self.load_image_directory)  # New Option
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.master.quit)

        navigate_menu = Menu(menu, tearoff=0)
        menu.add_cascade(label="Navigate", menu=navigate_menu)
        navigate_menu.add_command(label="Next JSON", command=self.next_json)
        navigate_menu.add_command(label="Previous JSON", command=self.prev_json)
        navigate_menu.add_command(label="Next Image", command=self.next_image)
        navigate_menu.add_command(label="Previous Image", command=self.prev_image)


    def load_image_directory(self):
        # Ask the user to select an image directory
        directory = filedialog.askdirectory(title="Select Image Directory")
        
        if directory:
            # Supported image extensions
            image_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff")
            images = [f for f in os.listdir(directory) if f.lower().endswith(image_extensions)]
            
            if not images:
                messagebox.showwarning("No Images Found", "The selected directory does not contain any supported image files.")
                return


            # Get the name of the image folder
            folder_name = os.path.basename(directory)

            # Define the static path for the JSON file with the folder name
            json_filename = f"{folder_name}.json"
            # E:/Situational Awareness/nuScenes/v1.0-mini
            json_path = os.path.join("HAD/frames/test0001/", json_filename)  # Replace with your desired static path

            # List to hold the combined data for all frames
            combined_json_data = []

            # Loop through each image in the directory and create its JSON entry
            for image_file in images:
                image_basename, _ = os.path.splitext(image_file)

                # Create the entry for this image
                image_data = {
                    "image_id": image_file,
                    "caption": "",
                    "maneuver": "",
                    "graph": {
                        "nodes": [],
                        "edges": []
                    },
                    "goal-oriented": "",
                    "safe": "",
                    "Action Suggestions": "",
                    "Traffic Regulations Suggestions": "",
                    "cause": [],
                    "QA": []
                }

                # Append the image data to the combined JSON list
                combined_json_data.append(image_data)

            # Save the combined data as a single JSON file
            with open(json_path, 'w') as output_json:
                json.dump(combined_json_data, output_json, indent=4)

            # Inform the user that the JSON file has been created
            messagebox.showinfo("JSON Creation", f"Combined JSON file has been saved to: {json_path}")


    def update_all_objects(self):
        
        if 0 <= self.image_index < len(self.data):
            nodes = self.data[self.image_index].get("graph", {}).get("nodes", [])
            
            # for node in nodes:
            #     obj = node[1]
            #     obj_name = obj.get("obj_name", "")
            #     Object_Causal = obj.get("Object_Causal", "")
            #     Causal_Relation = obj.get("Causal_Relation", "")
                
            #     # if obj_name in self.static_objects:
            #     #     obj["object_type"] = "Static"
            #     # elif obj_name in self.dynamic_objects:
            #     #     obj["object_type"] = "Dynamic"
            
            
            self.populate_nodes_list()
            self.draw_bboxes()
            
            
            messagebox.showinfo("Update Complete", "All objects have been updated based on their type (Static/Dynamic).")

    def on_object_name_select(self, event=None):
        selected_object = self.obj_name_var.get()
        
        status_options = object_status_options.get(selected_object, [])
        position_options = object_position_options.get(selected_object, [])

        
        self.status_listbox.delete(0, END)
        for status in status_options:
            self.status_listbox.insert(END, status)

        self.position_listbox.delete(0, END)
        for position in position_options:
            self.position_listbox.insert(END, position)



    def share_specific_data_with_next_image(self):
        if self.image_index < len(self.data) - 1:  
            next_image_data = self.data[self.image_index + 1]  
            current_image_data = self.data[self.image_index]  

            
            next_image_data["caption"] = current_image_data.get("caption", "")
            next_image_data["maneuver"] = current_image_data.get("maneuver", "")
            next_image_data["cause"] = current_image_data.get("cause", [])  
            next_image_data["goal-oriented"] = current_image_data.get("goal-oriented", "")
            next_image_data["safe"] = current_image_data.get("safe", "")
            next_image_data["Action Suggestions"] = current_image_data.get("Action Suggestions", "")
            next_image_data["Traffic Regulations Suggestions"] = current_image_data.get("Traffic Regulations Suggestions", "")
            
            self.save_changes()


    def on_resize(self, event):
        canvas_width = event.width - 200
        canvas_height = event.height
        self.canvas.config(width=canvas_width, height=canvas_height)

    def load_json_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.json_files = []
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith(".json"):
                        self.json_files.append(os.path.join(root, file))
            if self.json_files:
                self.json_index = 0
                self.load_json(self.json_files[self.json_index])

    def load_json(self, file_path):
        self.json_path = file_path
        with open(file_path) as f:
            self.data = json.load(f)
        self.image_folder = os.path.join(os.path.dirname(file_path), "../frames", os.path.basename(file_path).split('.')[0])
        self.image_index = 0
        self.update_json_file_label()
        self.load_image()
        self.populate_nodes_list()
        self.update_id_label()
        self.update_fields()
        self.populate_qa_list()
        self.populate_edges_list()
        self.populate_object_id_list()

    def delete_all_edges(self):
        if 0 <= self.image_index < len(self.data):
            
            self.data[self.image_index]["graph"]["edges"] = []
            
            self.populate_edges_list()
            self.draw_bboxes()

    def load_image(self):
        image_id = self.data[self.image_index]["image_id"]
        self.image_path = os.path.join(self.image_folder, image_id)
        self.img = Image.open(self.image_path)
        self.img = ImageTk.PhotoImage(self.img)
        
        # Load the original PIL Image
        self.original_img = Image.open(self.image_path)
    
        # Convert to PhotoImage for Tkinter display
        self.tk_img = ImageTk.PhotoImage(self.original_img)
    
        self.canvas.create_image(0, 0, anchor="nw", image=self.img)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
        self.check_and_update_all_relations()
        self.draw_bboxes()  
        self.populate_nodes_list()  
        self.populate_edges_list()  

        
    def draw_bboxes(self):
        """
        This function draws bounding boxes, lanes, freehand drawings, or points on the canvas
        and displays the object class (obj_name) inside or near the drawn shape.
        """
        
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.img)
        
        # Ensure the ego object is present before drawing
        self.add_ego_node()
        
        nodes = self.data[self.image_index].get("graph", {}).get("nodes", [])
        
        
        for i, node in enumerate(nodes):
            obj_id = node[0]
            obj = node[1]  
            bbox = obj.get("boxes", [])
            lane = obj.get("lane", [])
            coords = obj.get("coords", [])
            point = obj.get("point", [])
            polyline = obj.get("polyline", [])
            
            importance_ranking = obj.get("importance_ranking", "low")
            obj_name = obj.get("obj_name", "Unknown").lower()  # Make object name case-insensitive
            
            
            # Skip drawing the bounding box if the importance ranking is "None" or for other conditions
            if importance_ranking.lower() == "nonetest":
                self.add_relation_for_low_importance_object(obj_id)
                continue
        
        
            color = "red" if i != self.selected_node_index else "blue"  
            
            
            if len(bbox) == 4:
                
                self.canvas.create_rectangle(
                    bbox[0], bbox[1], bbox[2], bbox[3], outline=color, width=2
                )
                
                text_x, text_y = bbox[0], bbox[1] - 20  
                obj_name = obj.get("obj_name", "Unknown")
                self.canvas.create_text(
                    text_x, text_y,
                    text=obj_name,
                    anchor="nw",
                    fill="green",  
                    font=("Helvetica", 14, "bold")  
                )

            
            elif len(lane) == 4:
                
                self.canvas.create_line(
                    lane[0], lane[1], lane[2], lane[3], fill=color, width=2
                )
                text_x, text_y = lane[0], lane[1] - 20  
                obj_name = obj.get("obj_name", "Unknown")
                self.canvas.create_text(
                    text_x, text_y,
                    text=obj_name,
                    anchor="nw",
                    fill="green",
                    font=("Helvetica", 14, "bold")
                )

            
            elif len(coords) > 1:
                
                for j in range(1, len(coords)):
                    self.canvas.create_line(
                        coords[j - 1][0], coords[j - 1][1], coords[j][0], coords[j][1], fill=color
                    )
                text_x, text_y = coords[0][0], coords[0][1] - 20  
                obj_name = obj.get("obj_name", "Unknown")
                self.canvas.create_text(
                    text_x, text_y,
                    text=obj_name,
                    anchor="nw",
                    fill="green",
                    font=("Helvetica", 14, "bold")
                )

            
            elif len(point) == 2:
                
                self.canvas.create_oval(
                    point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3, fill=color
                )
                text_x, text_y = point[0], point[1] - 20  
                obj_name = obj.get("obj_name", "Unknown")
                self.canvas.create_text(
                    text_x, text_y,
                    text=obj_name,
                    anchor="nw",
                    fill="green",
                    font=("Helvetica", 14, "bold")
                )
            
            elif polyline:
                for j in range(1, len(polyline)):
                    self.canvas.create_line(
                        polyline[j - 1][0], polyline[j - 1][1],
                        polyline[j][0], polyline[j][1],
                        fill=color, width=2
                    )
                text_x, text_y = polyline[0][0], polyline[0][1] - 20
                obj_name = obj.get("obj_name", "Unknown")
                self.canvas.create_text(
                    text_x, text_y,
                    text=obj_name,
                    anchor="nw",
                    fill="green",
                    font=("Helvetica", 14, "bold")
                )


    def populate_nodes_list(self):
        self.object_level_listbox.delete(0, END)  
        if 0 <= self.image_index < len(self.data):
            nodes = self.data[self.image_index].get("graph", {}).get("nodes", [])
            for node in nodes:
                obj = node[1]
                bbox = obj.get("boxes", [])
                lane = obj.get("lane", [])
                coords = obj.get("coords", [])
                point = obj.get("point", [])  
                status = ", ".join(obj.get("Status", []))  
                position = ", ".join(obj.get("position", []))  
                object_type = obj.get("Is_causal", "")
                object_rank = obj.get("importance_ranking", "")

                
                if bbox:
                    self.object_level_listbox.insert(
                        END,
                        f"({obj['obj_name']}, {object_rank}, {object_type}): BBox {bbox} (Status: {status}), {position}"
                    )
                elif lane:
                    self.object_level_listbox.insert(
                        END,
                        f"({obj['obj_name']}, {object_rank},  {object_type}): Lane {lane} (Status: {status}), {position}"
                    )
                elif coords:
                    self.object_level_listbox.insert(
                        END,
                        f"({obj['obj_name']}, {object_rank},  {object_type}): Free Draw {coords} (Status: {status}), {position}"
                    )
                elif point:  
                    self.object_level_listbox.insert(
                        END,
                        f"({obj['obj_name']}, {object_rank},  {object_type}): Point {point} (Status: {status}), {position}"
                    )
                else:
                    self.object_level_listbox.insert(
                        END,
                        f"({obj['obj_name']}, {object_rank},  {object_type}): (Status: {status}), {position}"
                    )

            
            self.obj1_combobox['values'] = [node[0] for node in nodes]
            self.obj2_combobox['values'] = [node[0] for node in nodes]
            
            #self.obj2_combobox['values'] = [node[0] for node in nodes]


    def populate_edges_list(self):
        self.edges_listbox.delete(0, END)
        if 0 <= self.image_index < len(self.data):
            edges = self.data[self.image_index].get("graph", {}).get("edges", [])
            for edge in edges:
                self.edges_listbox.insert(END, f"{edge[0]} ({self.get_obj_name(edge[0])}) -> {edge[1]} ({self.get_obj_name(edge[1])}): {edge[2]['relation']}")

    def get_obj_name(self, node_id):
        nodes = self.data[self.image_index].get("graph", {}).get("nodes", [])
        for node in nodes:
            if node[0] == node_id:
                return node[1]["obj_name"]
        return ""

    def populate_object_id_list(self):
        self.object_id_listbox.delete(0, END)
        if 0 <= self.image_index < len(self.data):
            nodes = self.data[self.image_index].get("graph", {}).get("nodes", [])
            for node in nodes:
                self.object_id_listbox.insert(END, node[0])

    def populate_qa_list(self):
        self.qa_listbox.delete(0, END)
        if 0 <= self.image_index < len(self.data):
            qa_list = self.data[self.image_index].get("QA", [])
            for qa in qa_list:
                display_text = f"Q: {qa['Q']}\nA: {qa['A']} (Type: {qa.get('Type', 'N/A')}, Task: {qa.get('Task', 'N/A')})"
                self.qa_listbox.insert(END, display_text)

    def add_qa(self):
        question = self.question_entry.get()
        answer = self.answer_entry.get()
        qa_type = self.type_combobox.get()
        task = self.task_entry.get()
        if question and answer and qa_type and task:
            self.data[self.image_index].setdefault("QA", []).append({
                "Q": question,
                "A": answer,
                "Type": qa_type,
                "Task": task
            })
            self.populate_qa_list()
            self.question_entry.delete(0, END)
            self.answer_entry.delete(0, END)
            self.type_combobox.set("")
            self.task_entry.delete(0, END)

    def edit_qa(self):
        selected_index = self.qa_listbox.curselection()
        if selected_index:
            index = selected_index[0]
            question = self.question_entry.get()
            answer = self.answer_entry.get()
            qa_type = self.type_combobox.get()
            task = self.task_entry.get()
            if question and answer and qa_type and task:
                self.data[self.image_index]["QA"][index] = {
                    "Q": question,
                    "A": answer,
                    "Type": qa_type,
                    "Task": task
                }
                self.populate_qa_list()
                self.question_entry.delete(0, END)
                self.answer_entry.delete(0, END)
                self.type_combobox.set("")
                self.task_entry.delete(0, END)

    def on_qa_select(self, event):
        selected_index = self.qa_listbox.curselection()
        if selected_index:
            index = selected_index[0]
            qa = self.data[self.image_index]["QA"][index]
            self.question_entry.delete(0, END)
            self.question_entry.insert(0, qa["Q"])
            self.answer_entry.delete(0, END)
            self.answer_entry.insert(0, qa["A"])
            self.type_combobox.set(qa.get("Type", ""))
            self.task_entry.delete(0, END)
            self.task_entry.insert(0, qa.get("Task", ""))

    def delete_qa(self):
        selected_index = self.qa_listbox.curselection()
        if selected_index:
            index = selected_index[0]
            del self.data[self.image_index]["QA"][index]
            self.populate_qa_list()
            
    def generate_object_id(self, obj_name, obj_type, coords):
        if obj_type == "bbox":
            xmin, ymin, xmax, ymax = coords
            object_id = f"{obj_name}<bb>{int(xmin)},{int(ymin)},{int(xmax)},{int(ymax)}<bb>"
        elif obj_type == "point":
            x, y = coords
            object_id = f"{obj_name}<po>{int(x)},{int(y)}<po>"
        elif obj_type == "lane":
            start_x, start_y, end_x, end_y = coords
            object_id = f"{obj_name}<la>{int(start_x)},{int(start_y)},{int(end_x)},{int(end_y)}</la>"
        elif obj_type == "free":
            start_x, start_y = coords[0]
            end_x, end_y = coords[-1]
            object_id = f"{obj_name}<fe>{int(start_x)},{int(start_y)},{int(end_x)},{int(end_y)}</fe>"
        elif obj_type == "polyline":
            start_x, start_y = coords[0]
            end_x, end_y = coords[-1]
            object_id = f"{obj_name}<pl>{int(start_x)},{int(start_y)},{int(end_x)},{int(end_y)}</pl>"
        else:
            raise ValueError(f"Unsupported drawing type: {obj_type}")
        return object_id


    def add_node(self):
        obj_name = self.obj_name_combobox.get()
        Object_Causal = self.Object_Causal_combobox.get()
        Causal_Relation = self.Causal_Relation_combobox.get()

        Object_Safety = [option for option, var in self.object_safety_vars.items() if var.get()]


        
        selected_status_indices = self.status_listbox.curselection()
        status = [self.status_listbox.get(i) for i in selected_status_indices]

        
        selected_position_indices = self.position_listbox.curselection()
        position = [self.position_listbox.get(i) for i in selected_position_indices]

        
        importance_ranking = self.importance_ranking_var.get()
        object_type = self.object_type_var.get()

        nodes = self.data[self.image_index].setdefault("graph", {}).setdefault("nodes", [])
        draw_mode = self.draw_mode.get()

        if draw_mode == "bbox":
            bbox = [float(self.bbox_xmin_entry.get()), float(self.bbox_ymin_entry.get()), float(self.bbox_xmax_entry.get()), float(self.bbox_ymax_entry.get())]
            
            
            node_id = self.generate_object_id(obj_name, "bbox", bbox)
            
            
            nodes.append([node_id, {
                "obj_name": obj_name  or "bbox",
                "Object_Causal": Object_Causal,
                "Causal_Relation": Causal_Relation,
                "Is_causal": object_type,
                "boxes": bbox,
                "importance_ranking": importance_ranking,
                "Object_Safety": Object_Safety,
                "Status": status,  
                "position": position  
            }])

        elif draw_mode == "lane":
            lane = [self.start_x, self.start_y, self.end_x, self.end_y]
            
            
            node_id = self.generate_object_id(obj_name, "lane", lane)

            
            nodes.append([node_id, {
                "obj_name": obj_name or "lane",
                "Object_Causal": Object_Causal,
                "Causal_Relation": Causal_Relation,
                "Is_causal": object_type,
                "lane": lane,
                "importance_ranking": importance_ranking,
                "Object_Safety": Object_Safety,
                "Status": status,  
                "position": position  
                }]) 

        elif draw_mode == "free":
            coords = self.free_draw_coords.copy()
            
            
            node_id = self.generate_object_id(obj_name, "free", coords)

            
            nodes.append([node_id, {
                "obj_name": obj_name or "FreeDraw",
                "Object_Causal": Object_Causal,
                "Causal_Relation": Causal_Relation,
                "Is_causal": object_type,
                "coords": coords,
                "importance_ranking": importance_ranking,
                "Object_Safety": Object_Safety,
                "Status": status,  
                "position": position  
                }]) 

        elif draw_mode == "point":
            point = [self.start_x, self.start_y]
            
            
            node_id = self.generate_object_id(obj_name, "point", point)
            
            nodes.append([node_id, {
                "obj_name": obj_name or "Point",
                "Object_Causal": Object_Causal,
                "Causal_Relation": Causal_Relation,
                "Is_causal": object_type,
                "point": point,
                "importance_ranking": importance_ranking,
                "Object_Safety": Object_Safety,
                "Status": status,  
                "position": position  
            }])

        self.populate_nodes_list()
        self.populate_object_id_list()
        self.draw_bboxes()
        self.save_changes()  
        
        # Refresh the PhotoImage if necessary
        self.tk_img = ImageTk.PhotoImage(self.original_img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
        self.save_changes()


    def share_specific_data_with_all_images(self):
        if 0 <= self.image_index < len(self.data):  
            current_image_data = self.data[self.image_index]  

            
            for image_data in self.data:
                image_data["caption"] = current_image_data.get("caption", "")
                image_data["maneuver"] = current_image_data.get("maneuver", "")
                image_data["cause"] = current_image_data.get("cause", [])  
                image_data["goal-oriented"] = current_image_data.get("goal-oriented", "")
                image_data["safe"] = current_image_data.get("safe", "")
                image_data["Action Suggestions"] = current_image_data.get("Action Suggestions", "")
                image_data["Traffic Regulations Suggestions"] = current_image_data.get("Traffic Regulations Suggestions", "")

            
            self.save_changes()

            
            print("Shared data with all images successfully!____green")

    def on_status_select(self, event):
        current_selection = [self.status_listbox.get(i) for i in self.status_listbox.curselection()]

        obj1 = self.obj1_combobox.get()  # First object from combobox
        obj2 = self.selected_bbox_object_id  # Second object from the bounding box (if any)

        if obj1 and obj2 == obj1:  # Only proceed if obj2 (bbox object) matches obj1 from combobox
            # Remove previous status-based relations for this object
            self.remove_previous_status_relations(obj1)

            # Add new relations based on the current status selection
            for status in current_selection:
                self.add_self_relation(obj1, status)  # Create self-relation for statuses
            
        else:
            # If obj1 and obj2 do not match, no relation should be made
            print(f"Object from combobox {obj1} does not match the selected bounding box {obj2}, no relation created.")
            print("Object mismatch: {obj1} != {obj2}.____red")

        # Handle the addition/removal of statuses in the JSON data
        for item in current_selection:
            if item not in self.previous_status_selection:
                self.add_status_to_json(item)

        for item in self.previous_status_selection:
            if item not in current_selection:
                self.remove_status_from_json(item)

        self.previous_status_selection = current_selection


    # Helper function to add a self-relation based on status
    def add_self_relation(self, obj1, relation):
        edges = self.data[self.image_index].setdefault("graph", {}).setdefault("edges", [])
        edges.append([obj1, obj1, {"relation": relation}])  # Self-relation (object relates to itself)
        self.populate_edges_list()  # Update the list of edges

    # Helper function to remove previous status-based relations
    def remove_previous_status_relations(self, obj1):
        edges = self.data[self.image_index].get("graph", {}).get("edges", [])
        self.data[self.image_index]["graph"]["edges"] = [
            edge for edge in edges if not (edge[0] == obj1 and edge[1] == obj1 and "relation" in edge[2])
        ]




    def on_position_select(self, event):
        current_selection = [self.position_listbox.get(i) for i in self.position_listbox.curselection()]

    
        obj1 = self.obj1_combobox.get()  # First object from combobox
        obj2 = self.selected_bbox_object_id  # Second object from the selected bounding box

        # Ensure obj1 and obj2 are both selected
        if obj1 and obj2:
            # Remove any previous relations between these two objects based on position
            self.remove_previous_position_relations(obj1, obj2)

            # Add new relations based on the current selection
            for position in current_selection:
                self.add_relation(obj1, obj2, position)

        for item in current_selection:
            if item not in self.previous_position_selection:
                self.add_position_to_json(item)

        
        for item in self.previous_position_selection:
            if item not in current_selection:
                self.remove_position_from_json(item)

        
        self.previous_position_selection = current_selection


    # Helper function to remove previous position relations between two objects
    def remove_previous_position_relations(self, obj1, obj2):
        edges = self.data[self.image_index].get("graph", {}).get("edges", [])
        self.data[self.image_index]["graph"]["edges"] = [
            edge for edge in edges if not (edge[0] == obj1 and edge[1] == obj2 and "relation" in edge[2])
        ]
        
    
    # Helper function to add a relation
    def add_relation(self, obj1, obj2, relation):
        edges = self.data[self.image_index].setdefault("graph", {}).setdefault("edges", [])
        edges.append([obj1, obj2, {"relation": relation}])
        self.populate_edges_list()  # Update the list of edges

    def on_cause_select(self, event):
        current_selection = [self.cause_listbox.get(i) for i in self.cause_listbox.curselection()]

        obj1 = self.obj1_combobox.get()  # First object from combobox
        background_object = "background"  # Representing the environment or background

        if obj1:
            # Remove previous cause-based relations between obj1 and background
            self.remove_previous_cause_relations(obj1, background_object)

            # Add new relations based on the current cause selection
            for cause in current_selection:
                self.add_cause_relation(obj1, background_object, cause)  # Only handle cause relations

        # Handle changes in the selected causes (adding/removing them from the object)
        for item in current_selection:
            if item not in self.previous_cause_selection:
                self.add_cause_to_json(item)

        for item in self.previous_cause_selection:
            if item not in current_selection:
                self.remove_cause_from_json(item)

        # Store the new cause selection
        self.previous_cause_selection = current_selection

    # Helper function to add a cause relation between obj1 and the background
    def add_cause_relation(self, obj1, obj2, cause):
        edges = self.data[self.image_index].setdefault("graph", {}).setdefault("edges", [])
        edges.append([obj1, obj2, {"relation": cause}])  # Cause relation between obj1 and background
        self.populate_edges_list()  # Update the list of edges

    # Helper function to remove previous cause-based relations between the object and the background
    def remove_previous_cause_relations(self, obj1, obj2):
        background_object = "background"
        edges = self.data[self.image_index].get("graph", {}).get("edges", [])
        self.data[self.image_index]["graph"]["edges"] = [
            edge for edge in edges if not (edge[0] == obj1 and edge[1] == background_object and "relation" in edge[2])
        ]
        self.populate_edges_list()
            
            
    def add_status_to_json(self, status):
        if self.selected_node_index is not None:
            node = self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][1]
            
            # Ensure "Status" is initialized as a list if it's not already a list
            if "Status" not in node or not isinstance(node["Status"], list):
                node["Status"] = []  # Initialize as an empty list if it doesn't exist or is not a list
            
            # Now we can safely append the status
            node["Status"].append(status)
            
            # Save changes to the dataset
            self.save_changes()

    
    def remove_status_from_json(self, status):
        if self.selected_node_index is not None:
            node = self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][1]
            if "Status" in node and status in node["Status"]:
                node["Status"].remove(status)
                self.save_changes()  

    
    def add_position_to_json(self, position):
        if self.selected_node_index is not None:
            node = self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][1]
            if "position" not in node:
                node["position"] = []
            node["position"].append(position)
            self.save_changes()  

    
    def remove_position_from_json(self, position):
        if self.selected_node_index is not None:
            node = self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][1]
            if "position" in node and position in node["position"]:
                node["position"].remove(position)
                self.save_changes()  

    
    def add_cause_to_json(self, cause):
        if self.image_index is not None:
            if "cause" not in self.data[self.image_index]:
                self.data[self.image_index]["cause"] = []
            self.data[self.image_index]["cause"].append(cause)
            self.save_changes()  

    
    def remove_cause_from_json(self, cause):
        if self.image_index is not None:
            if "cause" in self.data[self.image_index] and cause in self.data[self.image_index]["cause"]:
                self.data[self.image_index]["cause"].remove(cause)
                self.save_changes()  
    
    def update_status_and_position_listbox(self, obj):
        """
        This function updates the Status and Position listboxes for the selected object
        and adds any missing values found in the JSON but not in the listbox options.
        """
        
        status_options = object_status_options.get(obj["obj_name"], [])  
        self.status_listbox.delete(0, END)  
        
        
        for status in status_options:
            self.status_listbox.insert(END, status)
        
        
        current_statuses = obj.get("Status", [])
        for status in current_statuses:
            if status not in status_options:
                self.status_listbox.insert(END, status)  
        
        
        position_options = object_position_options.get(obj["obj_name"], [])  
        self.position_listbox.delete(0, END)  

        
        for position in position_options:
            self.position_listbox.insert(END, position)

        
        current_positions = obj.get("position", [])
        for position in current_positions:
            if position not in position_options:
                self.position_listbox.insert(END, position)  
    
    def share_selected_object_with_next_images(self):
        """
        Copies the selected object's attributes and appends it to all frames.
        This ensures that the object is only copied once per frame, and each copy is independent.
        """
        if self.selected_node_index is not None:
            
            current_node = self.data[self.image_index]["graph"]["nodes"][self.selected_node_index]
            current_node_id = current_node[0]  
            current_obj = current_node[1]  

            print(f"Copying object {current_node_id} from frame {self.image_index} to all frames (only if not already present).")

            
            for frame_index in range(len(self.data)):
                frame_nodes = self.data[frame_index]["graph"]["nodes"]

                
                if not any(node[0] == current_node_id for node in frame_nodes):
                    
                    copied_node = [current_node_id, deepcopy(current_obj)]

                    
                    frame_nodes.append(copied_node)

                    print(f"Copied object {current_node_id} to frame {frame_index}.")
                else:
                    print(f"Object {current_node_id} already exists in frame {frame_index}, skipping copy.")

            
            self.save_changes()

            
            print("Copy Complete Object {current_node_id}___green")
        else:
            messagebox.showwarning("No Selection", "No object is selected to copy.")


    def remove_relation_for_low_importance_object(self, obj_id):
        """
        Removes the relation indicating that the object is not affecting safety and goal-oriented outcomes.
        """
        ego_id = self.add_ego_node()
        edges = self.data[self.image_index].get("graph", {}).get("edges", [])

        # Define the relation description to remove
        relation_description = "is not affecting safety and goal-oriented outcomes"

        # Filter out the relation that matches the criteria
        self.data[self.image_index]["graph"]["edges"] = [
            edge for edge in edges if not (
                edge[0] == obj_id and edge[1] == ego_id and edge[2]["relation"] == relation_description
            )
        ]
        self.populate_edges_list()  # Update the edge list display in the UI if applicable

    def check_and_update_all_relations(self):
        """
        Automatically checks all objects for their importance ranking.
        Adds or removes relations based on the current importance ranking.
        """
        nodes = self.data[self.image_index].get("graph", {}).get("nodes", [])
        
        for node in nodes:
            obj_id = node[0]
            obj = node[1]
            importance_ranking = obj.get("importance_ranking", "low").lower()

            # if importance_ranking == "none":
            #     # Ensure relation is added if importance ranking is "None"
            #     # self.add_relation_for_low_importance_object(obj_id)
            # else:
            #     # Ensure relation is removed if importance ranking is not "None"
            #     self.remove_relation_for_low_importance_object(obj_id)


    def on_importance_ranking_change(self, *args):
        if self.updating_variables:
            return
        if self.selected_node_index is not None:
            new_importance_ranking = self.importance_ranking_var.get()
            print(f"Importance Ranking changed to: {new_importance_ranking}")
            self.updating_variables = True
            obj = self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][1]
            obj["importance_ranking"] = new_importance_ranking

            # Synchronize Object Safety based on Importance Ranking
            if new_importance_ranking.lower() == "low":
                # Automatically check "Does Not Affect Safety"
                self.object_safety_vars["Does Not Affect Safety"].set(True)
                # Optionally, uncheck other safety options
                for option, var in self.object_safety_vars.items():
                    if option != "Does Not Affect Safety":
                        var.set(False)
            else:
                # If "Does Not Affect Safety" was previously set, reset it
                if self.object_safety_vars["Does Not Affect Safety"].get():
                    self.object_safety_vars["Does Not Affect Safety"].set(False)
                    # Optionally, set a default safety status
                    self.object_safety_vars["Affects Safety"].set(True)

            self.updating_variables = False

            # Save changes and update UI
            self.save_changes()
            self.populate_nodes_list()
            self.populate_edges_list()
            self.draw_bboxes()

            # Provide feedback
            print("Importance ranking updated and saved.____green")
        else:
            # No object selected
            print("No object selected to update++++red")
            print("No object selected to update Importance Ranking.")

    def on_object_safety_change(self):
        if self.updating_variables:
            return
        if self.selected_node_index is not None:
            self.updating_variables = True
            obj = self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][1]
            
            # Update Object_Safety in JSON
            selected_safeties = [option for option, var in self.object_safety_vars.items() if var.get()]
            obj["Object_Safety"] = selected_safeties

            # Check for conflicting selections
            if "Affects Safety" in selected_safeties and "Does Not Affect Safety" in selected_safeties:
                messagebox.showerror("Error", "An object cannot both affect and not affect safety.")
                # Revert the last change or enforce rules
                # For simplicity, uncheck "Does Not Affect Safety"
                self.object_safety_vars["Does Not Affect Safety"].set(False)
                obj["Object_Safety"].remove("Does Not Affect Safety")
            elif "Does Not Affect Safety" in selected_safeties:
                # If "Does Not Affect Safety" is selected, set Importance Ranking to "low"
                self.importance_ranking_var.set("low")
                # Optionally, uncheck other safety options
                for option, var in self.object_safety_vars.items():
                    if option != "Does Not Affect Safety":
                        var.set(False)
            else:
                # If "Does Not Affect Safety" is not selected and Importance Ranking was "low", reset it
                if self.importance_ranking_var.get().lower() == "low":
                    self.importance_ranking_var.set("medium")
                    # Optionally, set a default safety status
                    self.object_safety_vars["Affects Safety"].set(True)

            self.updating_variables = False

            # Save changes and update UI
            self.save_changes()
            self.populate_nodes_list()
            self.populate_edges_list()
            self.draw_bboxes()

            # Provide feedback
            print("Object safety status updated.___green")
        else:
            # No object selected
            print("No object selected.+++++red")
            print("No object selected to update Object Safety.")


    def update_node(self):
        if self.selected_node_index is not None:
            nodes = self.data[self.image_index]["graph"]["nodes"]
            obj = nodes[self.selected_node_index][1]
            old_node_id = nodes[self.selected_node_index][0]
            old_importance_ranking = obj.get("importance_ranking", "low")
            new_importance_ranking = self.importance_ranking_var.get()
            obj_name = self.obj_name_combobox.get()
            
            Object_Causal = self.Object_Causal_combobox.get()
            Causal_Relation = self.Causal_Relation_combobox.get()
            
            obj_type = obj.get("obj_type", "")

            # Update importance ranking
            obj["importance_ranking"] = new_importance_ranking

            # Update object properties
            obj["obj_name"] = obj_name
            obj["Object_Causal"] = Object_Causal
            obj["Causal_Relation"] = Causal_Relation
            obj["Object_Safety"] = [option for option, var in self.object_safety_vars.items() if var.get()]
            obj["Is_causal"] = self.object_type_var.get()

            # Handle status and position
            selected_statuses = [self.status_listbox.get(i) for i in self.status_listbox.curselection()]
            selected_positions = [self.position_listbox.get(i) for i in self.position_listbox.curselection()]
            obj["Status"] = selected_statuses
            obj["position"] = selected_positions

            # Generate new node ID based on object type
            if "boxes" in obj:
                obj_type = "bbox"
                bbox = obj.get("boxes", [])
                new_node_id = self.generate_object_id(obj_name, "bbox", bbox)
            elif "point" in obj:
                obj_type = "point"
                point = obj.get("point", [])
                new_node_id = self.generate_object_id(obj_name, "point", point)
            elif "lane" in obj:
                obj_type = "lane"
                lane = obj.get("lane", [])
                new_node_id = self.generate_object_id(obj_name, "lane", lane)
            elif "coords" in obj:
                obj_type = "free"
                coords = obj.get("coords", [])
                new_node_id = self.generate_object_id(obj_name, "free", coords)
            elif "polyline" in obj:
                obj_type = "polyline"
                polyline = obj.get("polyline", [])
                new_node_id = self.generate_object_id(obj_name, "polyline", polyline)
            else:
                messagebox.showerror("Error", f"Unsupported drawing type: {obj_type}")
                return

            # Update node ID if changed
            if new_node_id != old_node_id:
                existing_ids = [node[0] for idx, node in enumerate(nodes) if idx != self.selected_node_index]
                if new_node_id in existing_ids:
                    messagebox.showerror("Error", "Object ID already exists.")
                    return
                nodes[self.selected_node_index][0] = new_node_id

                # Update edges with new node ID
                edges = self.data[self.image_index]["graph"].get("edges", [])
                for edge in edges:
                    if edge[0] == old_node_id:
                        edge[0] = new_node_id
                    if edge[1] == old_node_id:
                        edge[1] = new_node_id

            # Refresh UI and save changes
            self.populate_nodes_list()
            self.populate_object_id_list()
            self.populate_edges_list()
            self.draw_bboxes()
            self.save_changes()
        else:
            messagebox.showwarning("Warning", "No node selected for updating.")


    def delete_selected_node(self, event=None):
        if self.selected_node_index is not None:
            
            node_id = self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][0]
            edges = self.data[self.image_index]["graph"].get("edges", [])
            edges_to_remove = [edge for edge in edges if edge[0] == node_id or edge[1] == node_id]
            for edge in edges_to_remove:
                edges.remove(edge)

            
            del self.data[self.image_index]["graph"]["nodes"][self.selected_node_index]
            self.selected_node_index = None

            
            self.populate_nodes_list()
            self.populate_object_id_list()
            self.populate_edges_list()
            self.draw_bboxes()

            
            self.save_changes()

            
            print("Node deleted and changes saved._____green")
        else:
            
            messagebox.showinfo("No Selection", "No node is selected to delete.") 


    def add_edge(self):
        obj1 = self.obj1_combobox.get()
        obj2 = self.obj2_combobox.get()
        relation = self.relation_combobox.get()
        if obj1 and obj2 and relation:
            edges = self.data[self.image_index].setdefault("graph", {}).setdefault("edges", [])
            edges.append([obj1, obj2, {"relation": relation}])
            self.populate_edges_list()
            
    def add_edge_selecting(self):
        obj1 = self.obj1_combobox.get()  # First object from combobox
        obj2 = self.selected_bbox_object_id  # Second object from the selected bounding box
        relation = self.relation_combobox.get()  # Relation type from the combobox

        if obj1 and obj2 and relation:
            edges = self.data[self.image_index].setdefault("graph", {}).setdefault("edges", [])
            edges.append([obj1, obj2, {"relation": relation}])
            self.populate_edges_list()
        else:
            messagebox.showwarning("Selection Error", "Please ensure both objects are selected and a relation is defined.")


    def on_edge_select(self, event):
        selected_index = self.edges_listbox.curselection()
        if selected_index:
            index = selected_index[0]
            edge = self.data[self.image_index]["graph"]["edges"][index]
            self.obj1_combobox.set(edge[0])
            self.obj2_combobox.set(edge[1])
            self.relation_combobox.set(edge[2]["relation"])
            self.selected_edge_index = index

    def edit_edge(self):
        if self.selected_edge_index is not None:
            obj1 = self.obj1_combobox.get()
            obj2 = self.obj2_combobox.get()
            relation = self.relation_combobox.get()
            if obj1 and obj2 and relation:
                self.data[self.image_index]["graph"]["edges"][self.selected_edge_index] = [obj1, obj2, {"relation": relation}]
                self.populate_edges_list()

    def delete_edge(self):
        if self.selected_edge_index is not None:
            del self.data[self.image_index]["graph"]["edges"][self.selected_edge_index]
            self.selected_edge_index = None
            self.populate_edges_list()

    def save_changes(self):
        if self.json_path:
            try:
                
                self.update_json_data()

                
                with open(self.json_path, 'w') as f:
                    json.dump(self.data, f, indent=4)

                
                print("Changes saved successfully!___green")
            except Exception as e:
                
                print("Error saving data: {e}+++ red")


    def update_selected_objects(self):
        """
        Updates all selected objects based on the current input values in the UI.
        """
        selected_indices = self.object_level_listbox.curselection()  # Get the indices of selected objects

        if not selected_indices:
            messagebox.showinfo("No Selection", "Please select at least one object to update.")
            return

        # Get the new values from the input fields
        new_importance_ranking = self.importance_ranking_var.get()
        new_status = [self.status_listbox.get(i) for i in self.status_listbox.curselection()]
        new_position = [self.position_listbox.get(i) for i in self.position_listbox.curselection()]
        new_object_safety = [option for option, var in self.object_safety_vars.items() if var.get()]
        
        new_Causal = self.object_type_var.get()
        new_Object_Causal =self.Object_Causal_combobox.get()
        new_Causal_Relation =  self.Causal_Relation_combobox.get()
        
        
        print(new_Causal)
        print(new_Object_Causal)
        print(new_Causal_Relation)

        # Iterate over selected objects and apply the changes
        for index in selected_indices:
            node = self.data[self.image_index]["graph"]["nodes"][index]
            obj_id = node[0]
            obj = node[1]

            # Update the object properties
            obj["importance_ranking"] = new_importance_ranking
            obj["Status"] = new_status
            obj["position"] = new_position
            obj["Object_Safety"] = new_object_safety
            obj["Is_causal"] = new_Causal
            obj["Object_Causal"] = new_Object_Causal
            obj["Causal_Relation"] = new_Causal_Relation
            # # Handle importance ranking changes (add or remove relations)
            # if new_importance_ranking.lower() == "none":
            #     self.add_relation_for_low_importance_object(obj_id)
            # else:
            #     self.remove_relation_for_low_importance_object(obj_id)

        # Refresh the UI components after updating the objects
        self.populate_nodes_list()
        self.populate_edges_list()
        self.draw_bboxes()
        self.save_changes()

        # Notify the user of the successful update
        print(f"Update SuccessfulSelected objects have been updated")







    def next_json(self):
        self.json_index = (self.json_index + 1) % len(self.json_files)
        self.load_json(self.json_files[self.json_index])

    def prev_json(self):
        self.json_index = (self.json_index - 1) % len(self.json_files)
        self.load_json(self.json_files[self.json_index])

    def next_image(self, event=None):
        self.update_json_data()  
        self.image_index = (self.image_index + 1) % len(self.data)
        self.load_image()
        self.update_fields()  
        self.populate_nodes_list()
        self.update_id_label()
        self.populate_qa_list()
        self.populate_edges_list()
        self.populate_object_id_list()

    def prev_image(self, event=None):
        self.update_json_data()  
        self.image_index = (self.image_index - 1) % len(self.data)
        self.load_image()
        self.update_fields()  
        self.populate_nodes_list()
        self.update_id_label()
        self.populate_qa_list()
        self.populate_edges_list()
        self.populate_object_id_list()

    # def share_data_with_next_image(self):
    #     if self.image_index < len(self.data) - 1:
    #         next_image_data = self.data[self.image_index + 1]
    #         current_image_data = self.data[self.image_index]

    #         next_image_data["caption"] = current_image_data.get("caption", "")
    #         next_image_data["graph"] = copy.deepcopy(current_image_data.get("graph", {}))
    #         next_image_data["QA"] = copy.deepcopy(current_image_data.get("QA", []))

    def share_data_with_next_image(self):
        """Share all relevant data (caption, graph, QA, cause, etc.) from the current frame to the next frame."""
        if self.image_index < len(self.data) - 1:
            current_image_data = self.data[self.image_index]
            next_image_data = self.data[self.image_index + 1]

            # Copy top-level fields
            # next_image_data["caption"] = current_image_data.get("caption", "")
            # next_image_data["maneuver"] = current_image_data.get("maneuver", "")
            next_image_data["cause"] = copy.deepcopy(current_image_data.get("cause", []))
            next_image_data["goal-oriented"] = current_image_data.get("goal-oriented", "")
            next_image_data["safe"] = current_image_data.get("safe", "")
            next_image_data["Action Suggestions"] = current_image_data.get("Action Suggestions", "")
            next_image_data["Traffic Regulations Suggestions"] = current_image_data.get("Traffic Regulations Suggestions", "")

            # Copy graph and QA deeply
            next_image_data["graph"] = copy.deepcopy(current_image_data.get("graph", {}))
            next_image_data["QA"] = copy.deepcopy(current_image_data.get("QA", []))

        #     messagebox.showinfo("Share Data", "Data shared with the next frame successfully!")
        # else:
        #     messagebox.showwarning("Share Data", "No next frame available.")

    def share_data_with_all_images(self):
        """Share all relevant data from the current frame to all subsequent frames."""
        if self.image_index < len(self.data) - 1:
            current_image_data = self.data[self.image_index]

            for i in range(self.image_index + 1, len(self.data)):
                # self.data[i]["caption"] = current_image_data.get("caption", "")
                # self.data[i]["maneuver"] = current_image_data.get("maneuver", "")
                self.data[i]["cause"] = copy.deepcopy(current_image_data.get("cause", []))
                self.data[i]["goal-oriented"] = current_image_data.get("goal-oriented", "")
                self.data[i]["safe"] = current_image_data.get("safe", "")
                self.data[i]["Action Suggestions"] = current_image_data.get("Action Suggestions", "")
                self.data[i]["Traffic Regulations Suggestions"] = current_image_data.get("Traffic Regulations Suggestions", "")

                # Deep copy graph and QA
                self.data[i]["graph"] = copy.deepcopy(current_image_data.get("graph", {}))
                self.data[i]["QA"] = copy.deepcopy(current_image_data.get("QA", []))

            messagebox.showinfo("Share Data", "Data shared with all subsequent frames successfully!")
        else:
            messagebox.showwarning("Share Data", "No subsequent frames available.")

    def clear_data_in_next_image(self):
        """Clear data in the next frame (if exists)."""
        if self.image_index < len(self.data) - 1:
            next_image_data = self.data[self.image_index + 1]
            # Clear out fields
            # next_image_data["caption"] = ""
            # next_image_data["maneuver"] = ""
            next_image_data["cause"] = []
            next_image_data["goal-oriented"] = ""
            next_image_data["safe"] = ""
            next_image_data["Action Suggestions"] = ""
            next_image_data["Traffic Regulations Suggestions"] = ""
            next_image_data["graph"] = {"nodes": [], "edges": []}
            next_image_data["QA"] = []

            messagebox.showinfo("Clear Data", "Data cleared from the next frame.")
        else:
            messagebox.showwarning("Clear Data", "No next frame available to clear.")

    def clear_data_in_all_subsequent_images(self):
        """Clear data in all subsequent frames."""
        if self.image_index < len(self.data) - 1:
            for i in range(self.image_index + 1, len(self.data)):
                # self.data[i]["caption"] = ""
                # self.data[i]["maneuver"] = ""
                self.data[i]["cause"] = []
                self.data[i]["goal-oriented"] = ""
                self.data[i]["safe"] = ""
                self.data[i]["Action Suggestions"] = ""
                self.data[i]["Traffic Regulations Suggestions"] = ""
                self.data[i]["graph"] = {"nodes": [], "edges": []}
                self.data[i]["QA"] = []

            messagebox.showinfo("Clear Data", "Data cleared from all subsequent frames.")
        else:
            messagebox.showwarning("Clear Data", "No subsequent frames available to clear.")
    # def show_coords(self, event):
    #     x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
    #     self.coord_label.config(text=f"X: {x}, Y: {y}")

    def canvas_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.selected_node_index = None
        self.selected_bbox_object_id = None  # Track the selected second object


        if 0 <= self.image_index < len(self.data):
            nodes = self.data[self.image_index].get("graph", {}).get("nodes", [])
            for i, node in enumerate(nodes):
                obj = node[1]
                bbox = obj.get("boxes", [])
                lane = obj.get("lane", [])
                coords = obj.get("coords", [])
                point = obj.get("point", [])
                polyline = obj.get("polyline", [])  

                
                if (len(bbox) == 4 and bbox[0] - 5 <= x <= bbox[2] + 5 and bbox[1] - 5 <= y <= bbox[3] + 5):
                    self.selected_node_index = i
                    self.selected_bbox_object_id = node[0]  # Capture the object ID
                    self.update_textboxes(node[0], obj)
                    self.is_moving = True
                    self.move_start_x = x
                    self.move_start_y = y
                    self.selected_bbox_initial = bbox.copy()
                    break
                
                elif (len(lane) == 4 and min(lane[0], lane[2]) - 5 <= x <= max(lane[0], lane[2]) + 5 and
                    min(lane[1], lane[3]) - 5 <= y <= max(lane[1], lane[3]) + 5):
                    self.selected_node_index = i
                    self.selected_bbox_object_id = node[0]  # Capture the object ID
                    self.update_textboxes(node[0], obj)
                    self.is_moving = True
                    self.move_start_x = x
                    self.move_start_y = y
                    self.selected_bbox_initial = lane.copy()
                    break
                
                elif len(point) == 2 and point[0] - 5 <= x <= point[0] + 5 and point[1] - 5 <= y <= point[1] + 5:
                    self.selected_node_index = i
                    self.selected_bbox_object_id = node[0]  # Capture the object ID
                    self.update_textboxes(node[0], obj)
                    self.is_moving = True
                    self.move_start_x = x
                    self.move_start_y = y
                    self.selected_bbox_initial = point.copy()
                    break
                elif coords:
                    for coord in coords:
                        if coord[0] - 5 <= x <= coord[0] + 5 and coord[1] - 5 <= y <= coord[1] + 5:
                            self.selected_node_index = i
                            self.selected_bbox_object_id = node[0]  # Capture the object ID
                            self.update_textboxes(node[0], obj)
                            self.is_moving = True
                            self.move_start_x = x
                            self.move_start_y = y
                            self.selected_bbox_initial = coords.copy()
                            break
                elif  polyline:
                    if self.is_point_near_polyline(x, y, polyline):
                        self.selected_node_index = i
                        self.selected_bbox_object_id = node[0]
                        self.update_textboxes(node[0], obj)
                        self.is_moving = True
                        self.move_start_x = x
                        self.move_start_y = y
                        self.selected_bbox_initial = [pt for pt in polyline]
                        break
            self.draw_bboxes()

    def is_point_near_polyline(self, x, y, polyline, threshold=10):
        for i in range(len(polyline) - 1):
            x1, y1 = polyline[i]
            x2, y2 = polyline[i + 1]
            if self.is_point_near_line_segment(x, y, x1, y1, x2, y2, threshold):
                return True
        return False

    def is_point_near_line_segment(self, px, py, x1, y1, x2, y2, threshold):
        # Calculate the distance from point to the line segment
        line_mag = ((x2 - x1)**2 + (y2 - y1)**2)**0.5

        if line_mag < 1e-6:
            # The line segment is a point
            dist = ((px - x1)**2 + (py - y1)**2)**0.5
            return dist <= threshold

        # Parameterize the line segment
        u = ((px - x1)*(x2 - x1) + (py - y1)*(y2 - y1)) / (line_mag ** 2)

        if u < 0 or u > 1:
            # Closest point does not fall within the line segment
            # Check distance to endpoints
            dist1 = ((px - x1)**2 + (py - y1)**2)**0.5
            dist2 = ((px - x2)**2 + (py - y2)**2)**0.5
            return min(dist1, dist2) <= threshold
        else:
            # Compute the closest point on the line segment
            ix = x1 + u * (x2 - x1)
            iy = y1 + u * (y2 - y1)
            dist = ((px - ix)**2 + (py - iy)**2)**0.5
            return dist <= threshold

    def move_bbox(self, event):
        if self.is_moving and self.selected_node_index is not None:
            dx = self.canvas.canvasx(event.x) - self.move_start_x
            dy = self.canvas.canvasy(event.y) - self.move_start_y
            obj = self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][1]
            bbox = obj.get("boxes", [])
            lane = obj.get("lane", [])
            coords = obj.get("coords", [])
            point = obj.get("point", [])  
            polyline = obj.get("polyline", [])
            
            if bbox:
                bbox[0] = max(0, bbox[0] + dx)
                bbox[1] = max(0, bbox[1] + dy)
                bbox[2] = max(0, bbox[2] + dx)
                bbox[3] = max(0, bbox[3] + dy)
                obj["boxes"] = bbox

                
                new_node_id = self.generate_object_id(obj["obj_name"], "bbox", bbox)
                self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][0] = new_node_id
            elif lane:
                lane[0] += dx
                lane[1] += dy
                lane[2] += dx
                lane[3] += dy
                obj["lane"] = lane

                
                new_node_id = self.generate_object_id(obj["obj_name"], "lane", lane)
                self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][0] = new_node_id
            elif coords:
                for i in range(len(coords)):
                    coords[i] = (coords[i][0] + dx, coords[i][1] + dy)
                obj["coords"] = coords

                
                new_node_id = self.generate_object_id(obj["obj_name"], "free", coords)
                self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][0] = new_node_id
            elif point:
                point[0] += dx
                point[1] += dy
                obj["point"] = point  

                
                new_node_id = self.generate_object_id(obj["obj_name"], "point", point)
                self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][0] = new_node_id

            elif  polyline:
                new_polyline = []
                for pt in self.selected_bbox_initial:
                    new_pt = (pt[0] + dx, pt[1] + dy)
                    new_polyline.append(new_pt)
                obj["polyline"] = new_polyline

                # Update node ID if necessary
                new_node_id = self.generate_object_id(obj["obj_name"], "polyline", new_polyline)
                self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][0] = new_node_id

                self.move_start_x += dx
                self.move_start_y += dy

            
            self.draw_bboxes()
            self.update_textboxes(self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][0], obj)
            self.save_changes()  



    def move_left(self, event):
        self.move_bbox_by_offset(-1, 0)

    def move_right(self, event):
        self.move_bbox_by_offset(1, 0)

    def move_up(self, event):
        self.move_bbox_by_offset(0, -1)

    def move_down(self, event):
        self.move_bbox_by_offset(0, 1)

    def move_bbox_by_offset(self, dx, dy):
        if self.selected_node_index is not None:
            obj = self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][1]
            bbox = obj.get("boxes", [])
            lane = obj.get("lane", [])
            coords = obj.get("coords", [])
            polyline = obj.get("polyline", [])
            
            if bbox:
                bbox[0] = max(0, bbox[0] + dx)
                bbox[1] = max(0, bbox[1] + dy)
                bbox[2] = max(0, bbox[2] + dx)
                bbox[3] = max(0, bbox[3] + dy)
                obj["boxes"] = bbox
                
            elif polyline:
                new_polyline = []
                for pt in polyline:
                    new_pt = (pt[0] + dx, pt[1] + dy)
                    new_polyline.append(new_pt)
                obj["polyline"] = new_polyline
            
            elif lane:
                lane[0] += dx
                lane[1] += dy
                lane[2] += dx
                lane[3] += dy
                obj["lane"] = lane
            elif coords:
                for i in range(len(coords)):
                    coords[i] = (coords[i][0] + dx, coords[i][1] + dy)
                obj["coords"] = coords
            self.draw_bboxes()
            self.update_textboxes(self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][0], obj)

    def end_move(self, event):
        if self.is_moving:
            self.is_moving = False
            self.selected_bbox_initial = None
            self.populate_nodes_list()

    
    def copy_object_id(self, event=None):
        """
        Copy the object ID of the selected node to the clipboard.
        """
        if self.selected_node_index is not None:
            
            node_id = self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][0]

            
            pyperclip.copy(node_id)
            print(f"Copied Object ID to clipboard: {node_id}")
        else:
            print("No object selected to copy the ID from.")


    def start_draw(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)

        
        self.draw_mode_value = self.draw_mode.get()

        if self.draw_mode_value == "bbox":
            self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='blue')
        elif self.draw_mode_value == "lane":
            self.rect = self.canvas.create_line(self.start_x, self.start_y, self.start_x, self.start_y, fill='blue', width=2)
        elif self.draw_mode_value == "free":
            self.free_draw_coords = [(self.start_x, self.start_y)]
            self.rect = None  
            self.canvas.bind("<B3-Motion>", self.update_free_draw)
        elif self.draw_mode_value == "point":
            self.rect = self.canvas.create_oval(self.start_x - 2, self.start_y - 2, self.start_x + 2, self.start_y + 2, fill='blue')  
            
        elif self.draw_mode_value == "polyline":
            self.is_drawing_polyline = True
            self.polyline_points = [(self.start_x, self.start_y)]
            self.canvas.unbind("<Button-1>")
            self.canvas.bind("<Button-1>", self.add_polyline_point)
            self.canvas.bind("<Double-Button-1>", self.end_polyline_draw)

        
        
    def update_draw(self, event):
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        
        draw_mode = self.draw_mode.get()

        if draw_mode == "bbox" and self.rect:
            
            self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)
        elif draw_mode == "lane" and self.rect:
            
            self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)
        elif draw_mode == "free" and self.rect:
            
            pass
        elif draw_mode == "point" and self.rect:
            
            self.canvas.coords(self.rect, cur_x - 2, cur_y - 2, cur_x + 2, cur_y + 2)  


    def end_draw(self, event):
        end_x, end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        
        draw_mode = self.draw_mode.get()

        obj_name = self.obj_name_combobox.get()
        
        Object_Causal = self.Object_Causal_combobox.get()
        Causal_Relation = self.Causal_Relation_combobox.get()

        
        selected_status_indices = self.status_listbox.curselection()
        status = [self.status_listbox.get(i) for i in selected_status_indices]

        
        selected_position_indices = self.position_listbox.curselection()
        position = [self.position_listbox.get(i) for i in selected_position_indices]
        
        Object_Safety = [option for option, var in self.object_safety_vars.items() if var.get()]

        importance_ranking = self.importance_ranking_var.get()
        object_type = self.object_type_var.get()

        
        node_id = None

        if draw_mode == "bbox":
            bbox = [self.start_x, self.start_y, end_x, end_y]
            
            
            node_id = self.generate_object_id(obj_name, "bbox", bbox)
            
            self.save_bbox(obj_name, bbox, importance_ranking, status, Object_Safety, object_type, Object_Causal, Causal_Relation, node_id, position)

        elif draw_mode == "lane":
            lane = [self.start_x, self.start_y, end_x, end_y]
            
            
            node_id = self.generate_object_id(obj_name,"lane", lane)

            self.save_lane(obj_name, lane, importance_ranking, status, Object_Safety, object_type, Object_Causal, Causal_Relation, node_id, position)

        elif draw_mode == "free":
            self.canvas.unbind("<B3-Motion>")  
            if self.free_draw_coords:
                
                
                node_id = self.generate_object_id(obj_name, "free", self.free_draw_coords)
                
                self.save_free_draw(obj_name, self.free_draw_coords, importance_ranking, status, Object_Safety, object_type, Object_Causal, Causal_Relation, node_id, position)

        elif draw_mode == "point":
            point = [self.start_x, self.start_y]
            
            
            node_id = self.generate_object_id(obj_name, "point", point)
            
            self.save_point(obj_name, point, importance_ranking, status, Object_Safety, object_type, Object_Causal, Causal_Relation, node_id, position)

        
        self.free_draw_coords = []
        self.canvas.delete(self.rect)
        self.populate_nodes_list()
        self.populate_object_id_list()
        self.draw_bboxes()

        
        self.save_changes()



    def update_free_draw(self, event):
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.free_draw_coords.append((cur_x, cur_y))
        if len(self.free_draw_coords) > 1:
            self.canvas.create_line(
                self.free_draw_coords[-2][0], self.free_draw_coords[-2][1],
                cur_x, cur_y, fill='blue'
            )

    def add_polyline_point(self, event):
        if self.is_drawing_polyline:
            x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            self.polyline_points.append((x, y))
            if len(self.polyline_points) > 1:
                self.canvas.create_line(
                    self.polyline_points[-2][0], self.polyline_points[-2][1],
                    self.polyline_points[-1][0], self.polyline_points[-1][1],
                    fill='blue', width=2
                )
    
    
    def end_polyline_draw(self, event):
        if self.is_drawing_polyline:
            self.is_drawing_polyline = False
            self.canvas.unbind("<Button-1>")
            self.canvas.unbind("<Double-Button-1>")
            self.save_polyline()
            self.polyline_points = []
            # Rebind canvas_click for object selection
            self.canvas.bind("<Button-1>", self.canvas_click)


    def update_free_draw(self, event):
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.free_draw_coords.append((cur_x, cur_y))
        if len(self.free_draw_coords) > 1:
            self.canvas.create_line(
                self.free_draw_coords[-2][0], self.free_draw_coords[-2][1],
                cur_x, cur_y, fill='blue'
            )
    def save_free_draw(self, obj_name, coords, importance_ranking, status, Object_Safety, object_type, Object_Causal, Causal_Relation, node_id, position):
        nodes = self.data[self.image_index].setdefault("graph", {}).setdefault("nodes", [])
        
        
        nodes.append([
            node_id,
            {
                "obj_name": obj_name or "FreeDraw",
                "Is_causal": object_type,
                "obj_causal": Object_Causal,
                "Causal_Relation": Causal_Relation,
                "coords": coords,
                "importance_ranking": importance_ranking,
                "Status": status,
                "Object_Safety": Object_Safety,
                "position": position  
            }
        ])

    def save_lane(self, obj_name, lane, importance_ranking, status, Object_Safety, object_type, Object_Causal, Causal_Relation, node_id, position):
        nodes = self.data[self.image_index].setdefault("graph", {}).setdefault("nodes", [])
        
        
        nodes.append([
            node_id,
            {
                "obj_name": obj_name or "Lane",
                "Is_causal": object_type,
                "obj_causal": Object_Causal,
                "Causal_Relation": Causal_Relation,
                "lane": lane,
                "importance_ranking": importance_ranking,
                "Status": status,
                "Object_Safety": Object_Safety,
                "position": position  
            }
        ])

    def save_point(self, obj_name, point, importance_ranking, status, Object_Safety, object_type, Object_Causal, Causal_Relation, node_id, position):
        nodes = self.data[self.image_index].setdefault("graph", {}).setdefault("nodes", [])
        
        
        nodes.append([
            node_id,
            {
                "obj_name": obj_name or "Point",
                "Is_causal": object_type,
                "obj_causal": Object_Causal,
                "Causal_Relation": Causal_Relation,
                "point": point,
                "importance_ranking": importance_ranking,
                "Status": status,
                "Object_Safety": Object_Safety,
                "position": position  
            }
        ])


    def save_bbox(self, obj_name, bbox, importance_ranking, status, Object_Safety, object_type, Object_Causal, Causal_Relation, node_id, position):
        nodes = self.data[self.image_index].setdefault("graph", {}).setdefault("nodes", [])
                
        
        nodes.append([
            node_id,  
            {
                "obj_name": obj_name,
                "Is_causal": object_type,
                "obj_causal": Object_Causal,
                "Causal_Relation": Causal_Relation,
                "boxes": bbox,
                "importance_ranking": importance_ranking,
                "Status": status,
                "Object_Safety": Object_Safety,
                "position": position  
            }
        ])

    def save_polyline(self):
        obj_name = "drivable area"
        object_type = self.object_type_var.get()

        node_id = self.generate_object_id(obj_name, "polyline", self.polyline_points)

        nodes = self.data[self.image_index].setdefault("graph", {}).setdefault("nodes", [])
        nodes.append([
            node_id,
            {
                "obj_name": obj_name,
                "Is_causal": object_type,
                "polyline": self.polyline_points.copy(),
                "importance_ranking": "high",
                "Status": [],
                "Object_Safety": "",
                "position": [],
                "obj_type": "polyline"  # Ensure this field is set
            }
        ])

        self.populate_nodes_list()
        self.populate_object_id_list()
        self.draw_bboxes()
        self.save_changes()


    def update_id_label(self):
        if 0 <= self.image_index < len(self.data):
            # Retrieve the total number of frames
            total_frames = len(self.data)
            # Convert current index to 1-based for human-friendly display
            current_frame_number = self.image_index + 1
            
            # Get the image ID (or "N/A" if not present)
            image_id = self.data[self.image_index].get("image_id", "N/A")
            
            # Construct the display text: e.g., "frame0003.jpg (3/12)"
            display_text = f"{image_id} ({current_frame_number}/{total_frames})"
            
            self.id_value_label.config(text=display_text)
        else:
            # If there's no valid frame, show "N/A"
            self.id_value_label.config(text="N/A")

    def update_json_file_label(self):
        current_json_name = os.path.basename(self.json_path)
        total_json_files = len(self.json_files)
        current_json_index = self.json_index + 1  # Indices start at 0
        self.json_file_name_label.config(
            text=f"JSON File: {current_json_name} ({current_json_index}/{total_json_files})"
        )


    def update_fields(self):
        
        self.caption_entry.delete(0, END)
        self.caption_entry.insert(0, self.data[self.image_index].get("caption", ""))

        self.maneuver_entry.delete(0, END)
        self.maneuver_entry.insert(0, self.data[self.image_index].get("maneuver", ""))

        self.goal_oriented_entry.delete(0, END)
        self.goal_oriented_entry.insert(0, self.data[self.image_index].get("goal-oriented", ""))

        self.safe_entry.delete(0, END)
        self.safe_entry.insert(0, self.data[self.image_index].get("safe", ""))

        self.Action_Suggestions_entry.delete(0, END)
        self.Action_Suggestions_entry.insert(0, self.data[self.image_index].get("Action Suggestions", ""))

        self.Traffic_Regulations_Suggestions_entry.delete(0, END)
        self.Traffic_Regulations_Suggestions_entry.insert(0, self.data[self.image_index].get("Traffic Regulations Suggestions", ""))
        
        # 2) Load the frame-level checkbox states
        current_image_data = self.data[self.image_index]
        self.frame_checked_var.set(current_image_data.get("frame_checked", False))
        self.frame_confirmed_var.set(current_image_data.get("frame_confirmed", False))


        
        
        
        saved_causes = self.data[self.image_index].get("cause", [])
        current_selections = [self.cause_listbox.get(i) for i in self.cause_listbox.curselection()]

        
        if set(saved_causes) != set(current_selections):
            self.cause_listbox.selection_clear(0, END)
            for cause in saved_causes:
                try:
                    index = self.cause_listbox.get(0, END).index(cause)
                    self.cause_listbox.selection_set(index)
                except ValueError:
                    print(" ** not saved causes and current selections +++++red")  

        self.object_id_listbox.delete(0, END)
        nodes = self.data[self.image_index].get("graph", {}).get("nodes", [])
        for node in nodes:
            self.object_id_listbox.insert(END, node[0])

        self.populate_qa_list()

    def update_json_data(self):
        
        if 0 <= self.image_index < len(self.data):
            current_image_data = self.data[self.image_index]
            current_image_data["caption"] = self.caption_entry.get()
            current_image_data["maneuver"] = self.maneuver_entry.get()
            current_image_data["goal-oriented"] = self.goal_oriented_entry.get()
            current_image_data["safe"] = self.safe_entry.get()
            current_image_data["Action Suggestions"] = self.Action_Suggestions_entry.get()
            current_image_data["Traffic Regulations Suggestions"] = self.Traffic_Regulations_Suggestions_entry.get()

            
            selected_causes = [self.cause_listbox.get(i) for i in self.cause_listbox.curselection()]
            current_image_data["cause"] = selected_causes


            
            qa_list = []
            for i in range(self.qa_listbox.size()):
                qa_text = self.qa_listbox.get(i).strip()
                if qa_text:
                    q_line, rest = qa_text.split('\nA: ')
                    q = q_line[3:].strip()  
                    a_part, type_task_part = rest.split(' (Type: ')
                    a = a_part.strip()
                    type_part, task_part = type_task_part.split(', Task: ')
                    qa_type = type_part.strip()
                    task = task_part[:-1].strip()  
                    qa_list.append({"Q": q, "A": a, "Type": qa_type, "Task": task})
            current_image_data["QA"] = qa_list


    def on_frame_checkbox_changed(self):
        """
        Called whenever the 'Checked' or 'Confirmed' checkbox for the frame is toggled.
        Updates the JSON data for the current frame in memory.
        """
        if 0 <= self.image_index < len(self.data):
            current_image_data = self.data[self.image_index]

            # Update the JSON with the new checkbox states
            current_image_data["frame_checked"] = bool(self.frame_checked_var.get())
            current_image_data["frame_confirmed"] = bool(self.frame_confirmed_var.get())

            # Optionally save immediately:
            # self.save_changes()



    def on_object_level_select(self, event):
        if len(self.object_level_listbox.curselection()) == 1:
            index = self.object_level_listbox.curselection()[0]
            self.selected_node_index = index
            obj_id = self.data[self.image_index]["graph"]["nodes"][index][0]
            obj = self.data[self.image_index]["graph"]["nodes"][index][1]
            
            
            self.update_textboxes(obj_id, obj)
            
            
            self.update_status_and_position_listbox(obj)
            
            
            self.draw_bboxes()


    def update_textboxes(self, obj_id, obj):
        
        self.updating_variables = True  # Prevent traces from firing
        self.object_id_entry.delete(0, END)
        self.object_id_entry.insert(0, obj_id)
        self.obj_name_combobox.set(obj["obj_name"])
        
        # self.Object_Causal_combobox.get(obj["Object_Causal"])
        # self.Causal_Relation_combobox.get(obj["Causal_Relation"])

        selected_object = obj["obj_name"]
        
        self.update_status_and_position_listbox(obj)

        status_options = object_status_options.get(selected_object, [])
        position_options = object_position_options.get(selected_object, [])

        
        self.status_listbox.delete(0, END)
        for status in status_options:
            self.status_listbox.insert(END, status)

        self.position_listbox.delete(0, END)
        for position in position_options:
            self.position_listbox.insert(END, position)

        
        selected_statuses = obj.get("Status", [])
        selected_positions = obj.get("position", [])

        
        for status in selected_statuses:
            try:
                index = self.status_listbox.get(0, END).index(status)
                self.status_listbox.selection_set(index)
            except ValueError:
                pass  

        
        for position in selected_positions:
            try:
                index = self.position_listbox.get(0, END).index(position)
                self.position_listbox.selection_set(index)
            except ValueError:
                pass  
        

        self.importance_ranking_var.set(obj.get("importance_ranking", "medium"))  
        self.object_type_var.set(obj.get("Is_causal", "none"))  
        

        # Set Object Safety Checkboxes
        object_safety = obj.get("Object_Safety", [])
        for option, var in self.object_safety_vars.items():
            var.set(option in object_safety)
            
            

        self.updating_variables = False  # Allow traces again
        
        
        bbox = obj.get("boxes", [])
        lane = obj.get("lane", [])
        point = obj.get("point", [])  
        polyline = obj.get("polyline", [])
        
        if bbox:
            self.bbox_xmin_entry.delete(0, END)
            self.bbox_xmin_entry.insert(0, bbox[0])
            self.bbox_ymin_entry.delete(0, END)
            self.bbox_ymin_entry.insert(0, bbox[1])
            self.bbox_xmax_entry.delete(0, END)
            self.bbox_xmax_entry.insert(0, bbox[2])
            self.bbox_ymax_entry.delete(0, END)
            self.bbox_ymax_entry.insert(0, bbox[3])
        elif point:
            
            self.bbox_xmin_entry.delete(0, END)
            self.bbox_xmin_entry.insert(0, point[0])
            self.bbox_ymin_entry.delete(0, END)
            self.bbox_ymin_entry.insert(0, point[1])
            self.bbox_xmax_entry.delete(0, END)
            self.bbox_xmax_entry.delete(0, END)  

        elif polyline:
            # Handle polyline-specific updates if needed
            pass
        else:
            self.bbox_xmin_entry.delete(0, END)
            self.bbox_ymin_entry.delete(0, END)
            self.bbox_xmax_entry.delete(0, END)
            self.bbox_ymax_entry.delete(0, END)

    def on_f2_press(self, event=None):
        """
        This function is triggered when F2 is pressed.
        It updates the combobox for object 1 (relation) based on the currently selected bounding box object ID.
        """
        if self.selected_node_index is not None:
            # Get the selected object (bounding box) from the data
            selected_node = self.data[self.image_index]["graph"]["nodes"][self.selected_node_index]
            obj_id = selected_node[0]  # Get the object ID from the selected node

            # Update the obj1_combobox with the selected object's ID
            self.obj1_combobox.set(obj_id)  # Set the combobox value to the selected object ID

            # Optionally, display a message indicating that the combobox was updated
            print(f"Combobox for Object 1 updated to object ID: {obj_id}")
        else:
            # If no bounding box is selected, provide a message to indicate that
            print("No bounding box is selected to update the combobox.")


    def go_to_json_file(self):
        input_value = self.json_search_entry.get().strip()
        if not input_value:
            messagebox.showerror("Error", "Please enter a JSON index or filename.")
            return
        
        if input_value.isdigit():
            # If input is a number, treat it as an index
            json_index = int(input_value) - 1  # Subtract 1 because indices start from 0
            if 0 <= json_index < len(self.json_files):
                self.json_index = json_index
                self.load_json(self.json_files[self.json_index])
            else:
                messagebox.showerror("Error", "Index out of range.")
        else:
            # Treat input as a filename
            matching_files = [f for f in self.json_files if os.path.basename(f) == input_value]
            if matching_files:
                self.json_index = self.json_files.index(matching_files[0])
                self.load_json(matching_files[0])
            else:
                messagebox.showerror("Error", "JSON file not found.")


    def add_ego_node(self):
        """
        Ensures that an 'ego' object is present in the graph as a node with a point representation.
        Adds the 'ego' node if it doesn't already exist.
        """
        nodes = self.data[self.image_index].setdefault("graph", {}).setdefault("nodes", [])

        # Check if an 'ego' node already exists
        for node in nodes:
            obj = node[1]
            if obj["obj_name"].lower() == "ego" and "point" in obj:
                return node[0]  # Return the existing ego node ID if found

        # Create a new 'ego' node with a default point if it doesn't exist  unscene 760,879  DADA =741, 640,   HAD =711, 708,   BDD= 682,697
        new_ego_id = self.generate_object_id("ego", "point", [711, 708])
        ego_object = [
            new_ego_id,
            {
                "obj_name": "ego",
                "Is_causal": "Effect",
                "obj_causal": "",
                "Causal_Relation": "",
                "point": [711, 708],
                "importance_ranking": "high",
                "Status": [],
                "Object_Safety": "",
                "position": []
            }
        ]
        nodes.append(ego_object)
        return new_ego_id

    def on_object_type_change(self, *args):
        if self.selected_node_index is not None:
            obj = self.data[self.image_index]["graph"]["nodes"][self.selected_node_index][1]
            obj["Is_causal"] = self.object_type_var.get()
            self.save_changes()
            self.populate_nodes_list()
            print("Object type updated and saved___green")
        else:
             print("No object selected to update.___red")

    def create_patch_controls(self):
        """ Create controls for applying different types of adversarial attacks. """
        self.navigation_frame = Frame(self.master)
        self.navigation_frame.grid(row=41, column=0, columnspan=6, sticky="ew")

        self.prev_button = Button(self.navigation_frame, text="Previous Image", command=self.prev_image)
        self.prev_button.pack(side='left', expand=True, fill='x')

        self.next_button = Button(self.navigation_frame, text="Next Image", command=self.next_image)
        self.next_button.pack(side='left', expand=True, fill='x')

        self.prev_json_button = Button(self.navigation_frame, text="Previous JSON", command=self.prev_json)
        self.prev_json_button.pack(side='left', expand=True, fill='x')

        self.next_json_button = Button(self.navigation_frame, text="Next JSON", command=self.next_json)
        self.next_json_button.pack(side='left', expand=True, fill='x')

        self.share_specific_data_button = Button(self.navigation_frame, text="UpperSection2NextImage", command=self.share_specific_data_with_next_image)
        self.share_specific_data_button.pack(side='left', expand=True, fill='x')
        
        
        self.share_all_specific_data_button = Button(self.navigation_frame, text="UpperSection2AllImage", command=self.share_specific_data_with_all_images)
        self.share_all_specific_data_button.pack(side='left', expand=True, fill='x')

        self.share_data_button = Button(self.navigation_frame, text="SelectObj2all", command=self.share_selected_object_with_next_images)
        self.share_data_button.pack(side='left', expand=True, fill='x')
        
        self.share_data_button = Button(self.navigation_frame, text="Objs2NextImage", command=self.share_data_with_next_image)
        self.share_data_button.pack(side='left', expand=True, fill='x')
        
        
    def apply_patch(self, bbox, color):
        """ Apply a solid color patch (white/black) to the selected object's bounding box. """
        try:
            if isinstance(self.original_img, Image.Image):
                draw = ImageDraw.Draw(self.original_img)
                draw.rectangle(bbox, fill=color)
                self.update_canvas()
                print(f"{color.capitalize()} patch applied to the bounding box {bbox}.")
            else:
                print("Error: Original image is not loaded correctly.")
                messagebox.showerror("Error", "Original image is not loaded correctly.")
        except Exception as e:
            print(f"Error applying {color} patch: {e}")

    def apply_gaussian_noise(self, bbox):
        """ Apply Gaussian noise to the selected bounding box in self.original_img. """
        if isinstance(self.original_img, Image.Image):
            region = self.original_img.crop(bbox)
            region_np = np.array(region)

            mean = 0
            sigma = 25
            gaussian = np.random.normal(mean, sigma, region_np.shape).astype(np.uint8)

            noisy_image = np.clip(region_np + gaussian, 0, 255).astype(np.uint8)
            noisy_region = Image.fromarray(noisy_image)
            self.original_img.paste(noisy_region, bbox)
            self.update_canvas()

    def apply_random_noise(self, bbox):
        """ Apply random noise to the selected bounding box in self.original_img. """
        if isinstance(self.original_img, Image.Image):
            region = self.original_img.crop(bbox)
            region_np = np.array(region)

            random_noise = np.random.randint(0, 256, region_np.shape, dtype=np.uint8)
            noisy_image = np.clip(region_np + random_noise, 0, 255)

            noisy_region = Image.fromarray(noisy_image.astype(np.uint8))
            self.original_img.paste(noisy_region, bbox)
            self.update_canvas()

    from PIL import Image, ImageOps, ImageDraw, ImageEnhance, ImageFilter

    def apply_sticker_patch(self, bbox):
        """ Apply a sticker image to the selected bounding box by choosing an image from the device. """
        try:
            sticker_path = filedialog.askopenfilename(
                title="Select Sticker Image",
                filetypes=(("Image Files", "*.png;*.jpg;*.jpeg"), ("All Files", "*.*"))
            )

            if not sticker_path:
                print("No image selected for sticker patch.")
                return

            sticker_img = Image.open(sticker_path)
            bbox_width = bbox[2] - bbox[0]
            bbox_height = bbox[3] - bbox[1]

            sticker_img = sticker_img.resize((bbox_width, bbox_height), Image.Resampling.LANCZOS)

            # Ensure both images have an alpha channel for compositing
            base_img = self.original_img.crop(bbox).convert("RGBA")
            sticker_img = sticker_img.convert("RGBA")

            # Apply sticker using alpha compositing
            sticker_img = Image.alpha_composite(base_img, sticker_img)

            # Paste back into the original image
            self.original_img.paste(sticker_img, bbox)
            self.update_canvas()

            print(f"Sticker applied from {sticker_path} onto the bounding box {bbox}.")

        except Exception as e:
            print(f"Error applying sticker patch: {e}")


    def apply_selected_attack(self):
        try:
            if isinstance(self.original_img, Image.Image):
                selected_attack = self.attack_type_var.get()

                if self.selected_node_index is not None:
                    selected_node = self.data[self.image_index]["graph"]["nodes"][self.selected_node_index]
                    bbox = selected_node[1].get("boxes", [])

                    if not bbox:
                        print("No bounding box found for the selected object.")
                        return

                    bbox = list(map(int, bbox))

                    if selected_attack == "WhitePatch":
                        self.apply_patch(bbox, "white")
                    elif selected_attack == "BlackPatch":
                        self.apply_patch(bbox, "black")
                    elif selected_attack == "GaussianNoise":
                        self.apply_gaussian_noise(bbox)
                    elif selected_attack == "RandomNoise":
                        self.apply_random_noise(bbox)
                    elif selected_attack == "StickerPatch":
                        self.apply_sticker_patch(bbox)

                    self.update_canvas()
                    logging.info(f"Applied {selected_attack} to object at index {self.selected_node_index}.")
                else:
                    print("No object selected for attack.")
                    messagebox.showerror("Error", "No object selected for attack.")
            else:
                print("Error: Original image is not a PIL Image.")
                messagebox.showerror("Error", "Original image is not loaded correctly.")
        except Exception as e:
            logging.error(f"Error applying attack: {e}")
            messagebox.showerror("Error", f"An error occurred while applying the attack: {e}")




    def save_attack(self, image, attack_name):
        """Save the attacked image in the original frames folder and update JSON to reflect the new frame."""
        try:
            # Step 1: Save attacked image in the original frames folder.
            original_image_path = self.image_path
            image_folder, image_filename = os.path.split(original_image_path)

            # Define the attacked image's new filename with a counter
            image_basename, image_extension = os.path.splitext(image_filename)

            # Extract the frame number from the image_basename
            try:
                frame_number = int(image_basename.split('_')[-1])
                frame_number= frame_number+1
            except ValueError:
                raise ValueError(f"Invalid image basename format: {image_basename}. Could not extract frame number.")

            counter = 1
            attacked_image_filename = f"{image_basename}_{attack_name}_{counter}{image_extension}"

            # Ensure we don't overwrite previous attacks; find the next available counter
            while os.path.exists(os.path.join(image_folder, attacked_image_filename)):
                counter += 1
                attacked_image_filename = f"{image_basename}_{attack_name}_{counter}{image_extension}"

            attacked_image_path = os.path.join(image_folder, attacked_image_filename)

            # Save the attacked image in the original frames folder
            image.save(attacked_image_path)

            # Step 2: Update JSON file with new frame reference.
            original_json_path = self.json_path

            with open(original_json_path, 'r+') as json_file:
                json_data = json.load(json_file)

                if frame_number >= len(json_data):
                    raise IndexError(f"Frame number {frame_number} is out of bounds for the JSON data.")

                # Create the new entry for the attacked frame in the JSON format
                new_frame_entry = {
                    "image_id": attacked_image_filename,
                    "caption": json_data[frame_number]["caption"],  # Copy original caption
                    "speed": json_data[frame_number]["speed"],
                    "steering": json_data[frame_number]["steering"],
                    "graph": json_data[frame_number]["graph"],  # Copy the entire graph of the original image
                    "goal-oriented": json_data[frame_number]["goal-oriented"],
                    "maneuver": json_data[frame_number]["maneuver"],
                    "QA": json_data[frame_number]["QA"],
                    "safe": json_data[frame_number]["safe"],
                    "Action Suggestions": json_data[frame_number]["Action Suggestions"],
                    "Traffic Regulations Suggestions": json_data[frame_number]["Traffic Regulations Suggestions"],
                    "cause": json_data[frame_number]["cause"],
                }

                # Append the new frame entry to the JSON data
                json_data.append(new_frame_entry)

                # Move the file pointer to the beginning and overwrite the file
                json_file.seek(0)
                json.dump(json_data, json_file, indent=4)
                json_file.truncate()

            # Step 3: Print paths for the saved image and JSON
            print(f"Saved attacked image: {attacked_image_path}")
            print(f"Updated JSON with attacked frame: {original_json_path}")

            # Optionally notify the user
            messagebox.showinfo("Save Successful", f"Image saved at: {attacked_image_path}\nJSON updated at: {original_json_path}")

        except Exception as e:
            print(f"Error saving attack image and JSON: {e}")
            messagebox.showerror("Error", f"Error saving attack image and JSON: {e}")


    def update_canvas(self):
        """ Refresh the canvas to show the updated image. """
        self.tk_img = ImageTk.PhotoImage(self.original_img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

def main():
    root = Tk()
    root.state('zoomed')
    editor = ImageEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()