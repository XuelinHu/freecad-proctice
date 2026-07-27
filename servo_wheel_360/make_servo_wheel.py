import os
from math import cos, degrees, radians, sin

import FreeCAD as App
import Part
import Mesh


# Unit: millimeter.
# Default target: a small 360-degree continuous-rotation hobby servo wheel.
# Mounting strategy: embed the servo's original round horn in the front pocket,
# then fasten it through the printed wheel with small screws.
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


def cylinder(radius, height, z_min, name="cylinder"):
    return Part.makeCylinder(
        radius,
        height,
        App.Vector(0, 0, z_min),
        App.Vector(0, 0, 1),
    )


def through_hole(radius, x, y, z_min, height):
    return Part.makeCylinder(
        radius,
        height,
        App.Vector(x, y, z_min),
        App.Vector(0, 0, 1),
    )


def polar_xy(radius, angle_deg):
    angle = radians(angle_deg)
    return radius * cos(angle), radius * sin(angle)


def add_circular_holes(shape, count, bolt_circle_diameter, hole_diameter, z_min, height):
    radius = bolt_circle_diameter / 2.0
    for i in range(count):
        x, y = polar_xy(radius, i * 360.0 / count)
        shape = shape.cut(through_hole(hole_diameter / 2.0, x, y, z_min, height))
    return shape


def add_rim_grooves(shape, params):
    wheel_radius = params["wheel_diameter"] / 2.0
    wheel_width = params["wheel_width"]
    groove_count = params["rim_groove_count"]
    groove_depth = params["rim_groove_depth"]
    groove_width = params["rim_groove_width"]

    # Vertical shallow cuts around the outer face give rigid filament wheels
    # a little more grip without needing flexible filament.
    for i in range(groove_count):
        angle = radians(i * 360.0 / groove_count)
        radial_x = cos(angle)
        radial_y = sin(angle)
        tangent_angle = degrees(angle) + 90.0

        box = Part.makeBox(
            groove_width,
            groove_depth + 2.0,
            wheel_width + 2.0,
            App.Vector(-groove_width / 2.0, wheel_radius - groove_depth, -wheel_width / 2.0 - 1.0),
        )
        box.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), tangent_angle)
        shape = shape.cut(box)
    return shape


def build_wheel(params):
    wheel_radius = params["wheel_diameter"] / 2.0
    wheel_width = params["wheel_width"]
    hub_radius = params["hub_diameter"] / 2.0
    hub_height = params["hub_height"]

    body = cylinder(wheel_radius, wheel_width, -wheel_width / 2.0, "wheel_body")
    hub = cylinder(hub_radius, hub_height, wheel_width / 2.0, "front_hub")
    shape = body.fuse(hub)

    total_z_min = -wheel_width / 2.0 - 1.0
    total_height = wheel_width + hub_height + 2.0

    shape = add_circular_holes(
        shape,
        params["spoke_cutout_count"],
        params["spoke_cutout_bolt_circle_diameter"],
        params["spoke_cutout_diameter"],
        total_z_min,
        total_height,
    )
    shape = add_circular_holes(
        shape,
        4,
        params["horn_screw_bolt_circle_diameter"],
        params["horn_screw_hole_diameter"],
        total_z_min,
        total_height,
    )

    center_hole = cylinder(params["center_screw_hole_diameter"] / 2.0, total_height, total_z_min)
    pocket_z = wheel_width / 2.0 + hub_height - params["servo_horn_pocket_depth"]
    horn_pocket = cylinder(
        params["servo_horn_pocket_diameter"] / 2.0,
        params["servo_horn_pocket_depth"] + 1.0,
        pocket_z,
    )

    shape = shape.cut(center_hole)
    shape = shape.cut(horn_pocket)
    shape = add_rim_grooves(shape, params)

    shape = shape.removeSplitter()
    return shape


def main():
    doc = App.newDocument("servo_wheel_360")
    shape = build_wheel(PARAMS)

    obj = doc.addObject("Part::Feature", "servo_wheel_360")
    obj.Shape = shape
    doc.recompute()

    fcstd_path = os.path.join(OUT_DIR, "servo_wheel_360.FCStd")
    step_path = os.path.join(OUT_DIR, "servo_wheel_360.step")
    stl_path = os.path.join(OUT_DIR, "servo_wheel_360.stl")

    doc.saveAs(fcstd_path)
    shape.exportStep(step_path)
    Mesh.export([obj], stl_path)

    print("Generated:")
    print(fcstd_path)
    print(step_path)
    print(stl_path)


if __name__ == "__main__":
    main()
