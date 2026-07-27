import os
from math import cos, radians, sin

import FreeCAD as App
import Mesh
import Part


# Unit: millimeter.
PARAMS = {
    "wheel_diameter": 64.0,
    "wheel_width": 12.0,
    "hub_diameter": 27.0,
    "hub_height": 4.0,
    "servo_horn_pocket_diameter": 20.8,
    "servo_horn_pocket_depth": 2.6,
    "center_screw_hole_diameter": 2.4,
    "horn_screw_hole_diameter": 2.2,
    "horn_screw_bolt_circle_diameter": 15.0,
    "spoke_cutout_count": 6,
    "spoke_cutout_diameter": 8.0,
    "spoke_cutout_bolt_circle_diameter": 39.0,
    "rim_groove_count": 16,
    "rim_groove_width": 1.8,
    "rim_groove_depth": 1.0,
}


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)


def cylinder(radius, height, z_min):
    return Part.makeCylinder(
        radius,
        height,
        App.Vector(0, 0, z_min),
        App.Vector(0, 0, 1),
    )


def add_shape(doc, name, shape):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


def add_cut(doc, name, base, tool):
    obj = doc.addObject("Part::Cut", name)
    obj.Base = base
    obj.Tool = tool
    return obj


def add_fuse(doc, name, base, tool):
    obj = doc.addObject("Part::Fuse", name)
    obj.Base = base
    obj.Tool = tool
    return obj


def polar_xy(radius, angle_deg):
    angle = radians(angle_deg)
    return radius * cos(angle), radius * sin(angle)


def make_hole_group(count, bolt_circle_diameter, hole_diameter, z_min, height):
    holes = []
    radius = bolt_circle_diameter / 2.0
    for i in range(count):
        x, y = polar_xy(radius, i * 360.0 / count)
        hole = Part.makeCylinder(
            hole_diameter / 2.0,
            height,
            App.Vector(x, y, z_min),
            App.Vector(0, 0, 1),
        )
        holes.append(hole)
    return Part.makeCompound(holes)


def make_rim_groove_group(params):
    wheel_radius = params["wheel_diameter"] / 2.0
    wheel_width = params["wheel_width"]
    groove_count = params["rim_groove_count"]
    groove_depth = params["rim_groove_depth"]
    groove_width = params["rim_groove_width"]
    grooves = []

    for i in range(groove_count):
        angle_deg = i * 360.0 / groove_count
        box = Part.makeBox(
            groove_width,
            groove_depth + 2.0,
            wheel_width + 2.0,
            App.Vector(-groove_width / 2.0, wheel_radius - groove_depth, -wheel_width / 2.0 - 1.0),
        )
        box.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), angle_deg + 90.0)
        grooves.append(box)

    return Part.makeCompound(grooves)


def hide_intermediate_objects(doc, final_obj):
    for obj in doc.Objects:
        if obj.ViewObject is not None:
            obj.ViewObject.Visibility = obj == final_obj


def main():
    params = PARAMS
    doc = App.newDocument("servo_wheel_360_history")

    wheel_width = params["wheel_width"]
    hub_height = params["hub_height"]
    total_z_min = -wheel_width / 2.0 - 1.0
    total_height = wheel_width + hub_height + 2.0

    wheel_body = add_shape(
        doc,
        "01_WheelBody_Cylinder",
        cylinder(params["wheel_diameter"] / 2.0, wheel_width, -wheel_width / 2.0),
    )
    front_hub = add_shape(
        doc,
        "02_FrontHub_Cylinder",
        cylinder(params["hub_diameter"] / 2.0, hub_height, wheel_width / 2.0),
    )
    fused = add_fuse(doc, "03_Fuse_WheelBody_FrontHub", wheel_body, front_hub)

    center_hole = add_shape(
        doc,
        "04_Tool_CenterScrewHole",
        cylinder(params["center_screw_hole_diameter"] / 2.0, total_height, total_z_min),
    )
    cut_center = add_cut(doc, "05_Cut_CenterScrewHole", fused, center_hole)

    pocket_z = wheel_width / 2.0 + hub_height - params["servo_horn_pocket_depth"]
    horn_pocket = add_shape(
        doc,
        "06_Tool_ServoHornPocket",
        cylinder(params["servo_horn_pocket_diameter"] / 2.0, params["servo_horn_pocket_depth"] + 1.0, pocket_z),
    )
    cut_pocket = add_cut(doc, "07_Cut_ServoHornPocket", cut_center, horn_pocket)

    horn_screw_holes = add_shape(
        doc,
        "08_Tool_HornScrewHoles_4x",
        make_hole_group(
            4,
            params["horn_screw_bolt_circle_diameter"],
            params["horn_screw_hole_diameter"],
            total_z_min,
            total_height,
        ),
    )
    cut_horn_screws = add_cut(doc, "09_Cut_HornScrewHoles", cut_pocket, horn_screw_holes)

    spoke_cutouts = add_shape(
        doc,
        "10_Tool_SpokeCutouts_6x",
        make_hole_group(
            params["spoke_cutout_count"],
            params["spoke_cutout_bolt_circle_diameter"],
            params["spoke_cutout_diameter"],
            total_z_min,
            total_height,
        ),
    )
    cut_spokes = add_cut(doc, "11_Cut_SpokeCutouts", cut_horn_screws, spoke_cutouts)

    rim_grooves = add_shape(doc, "12_Tool_RimGripGrooves_16x", make_rim_groove_group(params))
    final_wheel = add_cut(doc, "13_Final_ServoWheel360", cut_spokes, rim_grooves)

    doc.recompute()
    hide_intermediate_objects(doc, final_wheel)

    fcstd_path = os.path.join(OUT_DIR, "servo_wheel_360_history.FCStd")
    stl_path = os.path.join(OUT_DIR, "servo_wheel_360_history.stl")
    step_path = os.path.join(OUT_DIR, "servo_wheel_360_history.step")

    doc.saveAs(fcstd_path)
    final_wheel.Shape.exportStep(step_path)
    Mesh.export([final_wheel], stl_path)

    print("Generated history model:")
    print(fcstd_path)
    print(step_path)
    print(stl_path)


if __name__ == "__main__":
    main()
