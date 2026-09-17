"""Generate a small four-wheel steering ESP32 rover.

The result is a FreeCAD assembly that can be exported as STEP and imported by
Fusion 360.  All dimensions are millimeters and are kept in PARAMS so the
model can be regenerated for a different servo or controller board.
"""

from __future__ import annotations

import os
import sys
from math import cos, radians, sin

import FreeCAD as App
import Import
import Mesh
import Part


ROOT = os.path.dirname(os.path.abspath(__file__))
WHEEL_SCRIPT_DIR = os.path.normpath(os.path.join(ROOT, "..", "servo_wheel_360"))
if WHEEL_SCRIPT_DIR not in sys.path:
    sys.path.insert(0, WHEEL_SCRIPT_DIR)

from make_servo_wheel import PARAMS as WHEEL_PARAMS  # noqa: E402
from make_servo_wheel import build_wheel  # noqa: E402


PARAMS = {
    # Chassis envelope.
    "chassis_length": 140.0,
    "chassis_width": 110.0,
    "chassis_base_thickness": 4.0,
    "chassis_wall_height": 24.0,
    "chassis_wall_thickness": 3.0,
    "chassis_corner_radius": 5.0,
    # Wheel and steering layout.
    "wheel_diameter": 64.0,
    "wheel_width": 12.0,
    "wheel_center_x": 48.0,
    "wheel_center_y": 64.0,
    "wheel_center_z": 35.0,
    "steering_knuckle_radius": 5.0,
    "steering_knuckle_height": 30.0,
    "axle_diameter": 6.0,
    # SG90/MG90S-size servo envelope. Replace with the measured model.
    "servo_length": 23.0,
    "servo_width": 12.5,
    "servo_height": 24.0,
    "servo_mount_plate_thickness": 3.0,
    # ESP32 DevKit carrier.
    "esp32_board_length": 55.0,
    "esp32_board_width": 28.0,
    "esp32_tray_length": 72.0,
    "esp32_tray_width": 43.0,
    "esp32_tray_thickness": 2.5,
    "esp32_standoff_diameter": 7.0,
    "esp32_standoff_height": 8.0,
    "esp32_screw_diameter": 2.6,
    # Printed-part clearances and fasteners.
    "lid_thickness": 3.0,
    "lid_lip_depth": 5.0,
    "mount_screw_diameter": 3.2,
}


OUT_DIR = os.path.join(ROOT, "output")
os.makedirs(OUT_DIR, exist_ok=True)


def box(length, width, height, x, y, z):
    return Part.makeBox(length, width, height, App.Vector(x, y, z))


def cylinder(radius, height, x, y, z, direction=None):
    direction = direction or App.Vector(0, 0, 1)
    return Part.makeCylinder(radius, height, App.Vector(x, y, z), direction)


def rounded_prism(length, width, height, radius, z):
    """Make a rounded rectangle by filleting only the vertical edges."""
    shape = box(length, width, height, -length / 2.0, -width / 2.0, z)
    vertical_edges = []
    for edge in shape.Edges:
        vertices = edge.Vertexes
        if len(vertices) == 2 and abs(vertices[0].Point.z - vertices[1].Point.z) > height - 0.01:
            vertical_edges.append(edge)
    return shape.makeFillet(radius, vertical_edges)


def add_feature(doc, group, name, label, shape, color):
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape
    if obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color
    group.addObject(obj)
    return obj


def add_parameter_object(doc):
    obj = doc.addObject("App::FeaturePython", "ModelParameters")
    obj.Label = "Model Parameters (mm)"
    for key, value in PARAMS.items():
        obj.addProperty("App::PropertyLength", key, "Dimensions")
        setattr(obj, key, value)
    obj.addProperty("App::PropertyString", "ServoNote", "Notes")
    obj.ServoNote = "SG90/MG90S-size envelope; measure the actual servo before printing"
    obj.addProperty("App::PropertyString", "BoardNote", "Notes")
    obj.BoardNote = "ESP32 DevKit 55 x 28 mm envelope"
    return obj


def build_chassis(params):
    length = params["chassis_length"]
    width = params["chassis_width"]
    base_t = params["chassis_base_thickness"]
    wall_h = params["chassis_wall_height"]
    wall_t = params["chassis_wall_thickness"]
    outer = rounded_prism(length, width, base_t, params["chassis_corner_radius"], 0.0)

    # Build the four walls as a ring. Keeping the electronics opening clear
    # makes the upper cover removable and leaves room for wiring.
    inner = rounded_prism(length - 2 * wall_t, width - 2 * wall_t, wall_h, max(1.0, params["chassis_corner_radius"] - wall_t), base_t)
    walls = outer.fuse(inner.cut(box(length - 2 * wall_t, width - 2 * wall_t, wall_h + 0.1, -(length - 2 * wall_t) / 2.0, -(width - 2 * wall_t) / 2.0, base_t)))

    # Four reinforced mounting bosses for the lid.
    bosses = None
    for x in (-length / 2.0 + 11.0, length / 2.0 - 11.0):
        for y in (-width / 2.0 + 11.0, width / 2.0 - 11.0):
            boss = cylinder(5.5, wall_h - 2.0, x, y, base_t)
            boss = boss.cut(cylinder(params["mount_screw_diameter"] / 2.0, wall_h, x, y, base_t - 0.1))
            bosses = boss if bosses is None else bosses.fuse(boss)

    body = walls.fuse(bosses)

    # USB opening at the front wall and cable slots at both side walls.
    usb = box(18.0, wall_t + 2.0, 10.0, -9.0, -width / 2.0 - 1.0, 10.0)
    side_slot_left = box(18.0, wall_t + 2.0, 7.0, -9.0, -width / 2.0 - 1.0, 17.0)
    side_slot_right = box(18.0, wall_t + 2.0, 7.0, -9.0, width / 2.0 - wall_t - 1.0, 17.0)
    body = body.cut(usb).cut(side_slot_left).cut(side_slot_right)
    return body.removeSplitter()


def build_lid(params):
    length = params["chassis_length"]
    width = params["chassis_width"]
    thickness = params["lid_thickness"]
    lip = params["lid_lip_depth"]
    plate = rounded_prism(length, width, thickness, params["chassis_corner_radius"], params["chassis_wall_height"] + params["chassis_base_thickness"])
    lip_outer = rounded_prism(length - 6.0, width - 6.0, lip, max(1.0, params["chassis_corner_radius"] - 2.0), params["chassis_wall_height"] + params["chassis_base_thickness"] - lip)
    lip_inner = rounded_prism(length - 12.0, width - 12.0, lip + 1.0, max(1.0, params["chassis_corner_radius"] - 4.0), params["chassis_wall_height"] + params["chassis_base_thickness"] - lip - 0.5)
    rim = lip_outer.cut(lip_inner)

    # Ventilation slots above the controller and two holes for indicator LEDs.
    for x in (-18.0, -6.0, 6.0, 18.0):
        rim = rim.cut(box(5.0, 2.5, thickness + 1.0, x - 2.5, -14.0, params["chassis_wall_height"] + params["chassis_base_thickness"] - 0.5))
    for x in (-28.0, 28.0):
        rim = rim.cut(cylinder(2.0, thickness + 1.0, x, 30.0, params["chassis_wall_height"] + params["chassis_base_thickness"] - 0.5))
    return plate.fuse(rim).removeSplitter()


def build_tray(params):
    length = params["esp32_tray_length"]
    width = params["esp32_tray_width"]
    tray = rounded_prism(length, width, params["esp32_tray_thickness"], 3.0, params["chassis_base_thickness"] + 2.0)
    # Four corner feet are fused to the tray and drilled for M2.5 screws.
    for x in (-length / 2.0 + 7.0, length / 2.0 - 7.0):
        for y in (-width / 2.0 + 7.0, width / 2.0 - 7.0):
            foot = cylinder(params["esp32_standoff_diameter"] / 2.0, params["esp32_standoff_height"], x, y, params["chassis_base_thickness"] + 2.0)
            foot = foot.cut(cylinder(params["esp32_screw_diameter"] / 2.0, params["esp32_standoff_height"] + 1.0, x, y, params["chassis_base_thickness"] + 1.5))
            tray = tray.fuse(foot)
    return tray.removeSplitter()


def build_esp32_dummy(params):
    board = rounded_prism(params["esp32_board_length"], params["esp32_board_width"], 1.6, 2.0, params["chassis_base_thickness"] + 2.0 + params["esp32_standoff_height"])
    # USB connector envelope on the front edge.
    usb = box(8.0, 10.0, 5.0, -4.0, -params["esp32_board_width"] / 2.0 - 3.0, params["chassis_base_thickness"] + 2.0 + params["esp32_standoff_height"])
    return board.fuse(usb).removeSplitter()


def servo_shapes(params, side, x):
    y_sign = -1.0 if side == "L" else 1.0
    wall_y = y_sign * params["chassis_width"] / 2.0
    inward_y = wall_y - y_sign * (params["servo_width"] + 4.0)
    servo_y = min(wall_y, inward_y) if y_sign < 0 else inward_y
    servo = box(params["servo_length"], params["servo_width"], params["servo_height"], x - params["servo_length"] / 2.0, servo_y, 11.0)

    # The plate is fixed to the side wall; the two ears represent the servo's
    # mounting tabs and leave a visible screw path.
    plate_y = wall_y - y_sign * params["servo_mount_plate_thickness"] if y_sign < 0 else wall_y
    plate = box(31.0, params["servo_mount_plate_thickness"], 30.0, x - 15.5, min(plate_y, plate_y + y_sign * params["servo_mount_plate_thickness"]), 8.0)
    ear_a = box(4.0, params["servo_width"] + 6.0, 5.0, x - 15.5, min(wall_y - 2.0, wall_y + y_sign * (params["servo_width"] + 4.0)), 32.0)
    ear_b = box(4.0, params["servo_width"] + 6.0, 5.0, x + 11.5, min(wall_y - 2.0, wall_y + y_sign * (params["servo_width"] + 4.0)), 32.0)
    bracket = plate.fuse(ear_a).fuse(ear_b)

    knuckle = cylinder(params["steering_knuckle_radius"], params["steering_knuckle_height"], x, y_sign * (params["chassis_width"] / 2.0 + 7.0), 8.0)
    axle_start = y_sign * (params["chassis_width"] / 2.0 + 5.0)
    axle = cylinder(params["axle_diameter"] / 2.0, 15.0, x, axle_start, params["wheel_center_z"], App.Vector(0, y_sign, 0))
    return servo, bracket, knuckle, axle


def set_transparency(obj, value):
    if obj.ViewObject is not None:
        obj.ViewObject.Transparency = value


def export_objects(objects, name):
    step_path = os.path.join(OUT_DIR, name + ".step")
    stl_path = os.path.join(OUT_DIR, name + ".stl")
    Import.export(objects, step_path)
    Mesh.export(objects, stl_path)
    return step_path, stl_path


def main():
    doc = App.newDocument("esp32_servo_rover")
    params_obj = add_parameter_object(doc)

    chassis_group = doc.addObject("App::DocumentObjectGroup", "Chassis")
    chassis_group.Label = "Chassis / Enclosure"
    steering_group = doc.addObject("App::DocumentObjectGroup", "Steering")
    steering_group.Label = "4 Servos and Steering Brackets"
    wheels_group = doc.addObject("App::DocumentObjectGroup", "Wheels")
    wheels_group.Label = "4 Wheels"
    electronics_group = doc.addObject("App::DocumentObjectGroup", "Electronics")
    electronics_group.Label = "ESP32 Controller"

    chassis = add_feature(doc, chassis_group, "ChassisBody", "Chassis lower body", build_chassis(PARAMS), (0.25, 0.28, 0.32))
    lid = add_feature(doc, chassis_group, "ChassisLid", "Removable top cover", build_lid(PARAMS), (0.55, 0.58, 0.62))
    set_transparency(lid, 35)

    tray = add_feature(doc, electronics_group, "ESP32Tray", "ESP32 DevKit mounting tray", build_tray(PARAMS), (0.75, 0.45, 0.15))
    board = add_feature(doc, electronics_group, "ESP32Envelope", "ESP32 DevKit envelope", build_esp32_dummy(PARAMS), (0.15, 0.42, 0.18))
    set_transparency(board, 15)

    wheel_shape = build_wheel(dict(WHEEL_PARAMS, wheel_diameter=PARAMS["wheel_diameter"], wheel_width=PARAMS["wheel_width"]))
    assembly_objects = [chassis, lid, tray, board]
    for index, (x, side) in enumerate((
        (-PARAMS["wheel_center_x"], "L-front"),
        (PARAMS["wheel_center_x"], "L-rear"),
        (-PARAMS["wheel_center_x"], "R-front"),
        (PARAMS["wheel_center_x"], "R-rear"),
    ), start=1):
        y = -PARAMS["wheel_center_y"] if side.startswith("L") else PARAMS["wheel_center_y"]
        wheel = add_feature(doc, wheels_group, "Wheel%02d" % index, "%s wheel" % side, wheel_shape.copy(), (0.10, 0.10, 0.12))
        wheel.Placement = App.Placement(App.Vector(x, y, PARAMS["wheel_center_z"]), App.Rotation(App.Vector(1, 0, 0), 90 if y < 0 else -90))
        servo, bracket, knuckle, axle = servo_shapes(PARAMS, "L" if y < 0 else "R", x)
        servo_obj = add_feature(doc, steering_group, "Servo%02d" % index, "%s SG90 servo envelope" % side, servo, (0.85, 0.15, 0.12))
        bracket_obj = add_feature(doc, steering_group, "ServoBracket%02d" % index, "%s servo bracket" % side, bracket, (0.85, 0.65, 0.10))
        knuckle_obj = add_feature(doc, steering_group, "Knuckle%02d" % index, "%s steering knuckle" % side, knuckle, (0.72, 0.42, 0.10))
        axle_obj = add_feature(doc, steering_group, "Axle%02d" % index, "%s axle" % side, axle, (0.55, 0.55, 0.58))
        set_transparency(servo_obj, 25)
        assembly_objects.extend([wheel, servo_obj, bracket_obj, knuckle_obj, axle_obj])

    doc.recompute()
    fcstd_path = os.path.join(OUT_DIR, "esp32_servo_rover_assembly.FCStd")
    doc.saveAs(fcstd_path)
    assembly_step, assembly_stl = export_objects(assembly_objects, "esp32_servo_rover_assembly")

    # Export the main printable parts separately for Fusion 360 or slicing.
    individual = {
        "chassis_lower_body": [chassis],
        "chassis_lid": [lid],
        "esp32_mounting_tray": [tray],
        "esp32_board_envelope": [board],
    }
    for name, objects in individual.items():
        export_objects(objects, name)
    for index in range(1, 5):
        export_objects([doc.getObject("Wheel%02d" % index)], "wheel_%02d" % index)
        export_objects([doc.getObject("ServoBracket%02d" % index)], "servo_bracket_%02d" % index)

    print("Generated:")
    print(fcstd_path)
    print(assembly_step)
    print(assembly_stl)
    print("Parts: %d objects" % len(assembly_objects))


if __name__ == "__main__":
    main()
