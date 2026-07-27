import os
from math import cos, radians, sin

import FreeCAD as App
import Mesh
import Part
import Sketcher


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
}


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)


def polar_xy(radius, angle_deg):
    angle = radians(angle_deg)
    return radius * cos(angle), radius * sin(angle)


def body_new_sketch(body, name, z=0.0):
    sketch = body.newObject("Sketcher::SketchObject", name)
    sketch.Placement = App.Placement(App.Vector(0, 0, z), App.Rotation())
    return sketch


def add_circle(sketch, x, y, radius):
    geo_index = sketch.addGeometry(
        Part.Circle(App.Vector(x, y, 0), App.Vector(0, 0, 1), radius),
        False,
    )
    sketch.addConstraint(Sketcher.Constraint("Coincident", geo_index, 3, -1, 1))
    sketch.addConstraint(Sketcher.Constraint("Radius", geo_index, radius))
    return geo_index


def add_circle_without_origin_constraint(sketch, x, y, radius):
    geo_index = sketch.addGeometry(
        Part.Circle(App.Vector(x, y, 0), App.Vector(0, 0, 1), radius),
        False,
    )
    sketch.addConstraint(Sketcher.Constraint("Radius", geo_index, radius))
    return geo_index


def add_pad(body, name, sketch, length):
    pad = body.newObject("PartDesign::Pad", name)
    pad.Profile = sketch
    pad.Length = length
    return pad


def add_pocket(body, name, sketch, length, reversed_direction=True):
    pocket = body.newObject("PartDesign::Pocket", name)
    pocket.Profile = sketch
    pocket.Length = length
    pocket.Reversed = reversed_direction
    return pocket


def hide_sketches_and_intermediate_features(doc, final_name):
    for obj in doc.Objects:
        if obj.ViewObject is None:
            continue
        obj.ViewObject.Visibility = obj.Name == final_name


def main():
    params = PARAMS
    doc = App.newDocument("servo_wheel_360_partdesign")
    body = doc.addObject("PartDesign::Body", "Body_ServoWheel360")
    doc.recompute()

    wheel_width = params["wheel_width"]
    hub_top_z = wheel_width + params["hub_height"]
    through_depth = hub_top_z + 2.0

    wheel_sketch = body_new_sketch(body, "Sketch_01_Wheel_Profile", 0.0)
    add_circle(wheel_sketch, 0.0, 0.0, params["wheel_diameter"] / 2.0)
    pad_wheel = add_pad(body, "Pad_02_Wheel", wheel_sketch, wheel_width)
    doc.recompute()

    hub_sketch = body_new_sketch(body, "Sketch_03_FrontHub_Profile", wheel_width)
    add_circle(hub_sketch, 0.0, 0.0, params["hub_diameter"] / 2.0)
    pad_hub = add_pad(body, "Pad_04_FrontHub", hub_sketch, params["hub_height"])
    doc.recompute()

    center_sketch = body_new_sketch(body, "Sketch_05_Center_Screw_Hole", hub_top_z)
    add_circle(center_sketch, 0.0, 0.0, params["center_screw_hole_diameter"] / 2.0)
    pocket_center = add_pocket(body, "Pocket_06_Center_Screw_Hole", center_sketch, through_depth)
    doc.recompute()

    horn_pocket_sketch = body_new_sketch(body, "Sketch_07_ServoHorn_Pocket", hub_top_z)
    add_circle(horn_pocket_sketch, 0.0, 0.0, params["servo_horn_pocket_diameter"] / 2.0)
    pocket_horn = add_pocket(
        body,
        "Pocket_08_ServoHorn_Pocket",
        horn_pocket_sketch,
        params["servo_horn_pocket_depth"],
    )
    doc.recompute()

    horn_screw_sketch = body_new_sketch(body, "Sketch_09_Horn_Screw_Holes_4x", hub_top_z)
    horn_radius = params["horn_screw_bolt_circle_diameter"] / 2.0
    for i in range(4):
        x, y = polar_xy(horn_radius, i * 90.0)
        add_circle_without_origin_constraint(horn_screw_sketch, x, y, params["horn_screw_hole_diameter"] / 2.0)
    pocket_horn_screws = add_pocket(
        body,
        "Pocket_10_Horn_Screw_Holes_4x",
        horn_screw_sketch,
        through_depth,
    )
    doc.recompute()

    spoke_sketch = body_new_sketch(body, "Sketch_11_Spoke_Cutouts_6x", hub_top_z)
    spoke_radius = params["spoke_cutout_bolt_circle_diameter"] / 2.0
    for i in range(params["spoke_cutout_count"]):
        x, y = polar_xy(spoke_radius, i * 360.0 / params["spoke_cutout_count"])
        add_circle_without_origin_constraint(spoke_sketch, x, y, params["spoke_cutout_diameter"] / 2.0)
    pocket_spokes = add_pocket(
        body,
        "Pocket_12_Spoke_Cutouts_6x",
        spoke_sketch,
        through_depth,
    )
    doc.recompute()

    final_obj = pocket_spokes
    body.Tip = final_obj
    hide_sketches_and_intermediate_features(doc, final_obj.Name)
    doc.recompute()

    fcstd_path = os.path.join(OUT_DIR, "servo_wheel_360_partdesign.FCStd")
    step_path = os.path.join(OUT_DIR, "servo_wheel_360_partdesign.step")
    stl_path = os.path.join(OUT_DIR, "servo_wheel_360_partdesign.stl")

    doc.saveAs(fcstd_path)
    final_obj.Shape.exportStep(step_path)
    Mesh.export([final_obj], stl_path)

    print("Generated PartDesign sketch model:")
    print(fcstd_path)
    print(step_path)
    print(stl_path)


if __name__ == "__main__":
    main()
