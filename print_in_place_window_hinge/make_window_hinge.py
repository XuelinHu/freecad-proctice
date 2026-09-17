import os
from math import cos, pi, sin

import FreeCAD as App
import Mesh
import Part


# Unit: millimeter. Defaults target a 0.4 mm FDM nozzle and 0.2 mm layers.
PARAMS = {
    "hinge_length": 80.0,
    "leaf_width": 36.0,
    "leaf_thickness": 3.2,
    "barrel_outer_radius": 4.5,
    "pin_radius": 2.0,
    "radial_clearance": 0.45,
    "axial_clearance": 0.50,
    "knuckle_count": 9,
    "polygon_sides": 16,
    "mount_hole_radius": 2.4,
    "mount_hole_y": (18.0, 62.0),
    "leaf_barrel_gap": 0.25,
    "leaf_barrel_overlap": 0.8,
    "pair_spacing": 12.0,
}


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)


def new_doc(name):
    try:
        existing = App.getDocument(name)
    except Exception:
        existing = None
    if existing is not None:
        App.closeDocument(name)
    return App.newDocument(name)


def polygon_prism_along_y(radius, length, y_start, center_z, sides, center_x=0.0):
    points = []
    # A bottom vertex puts the outer barrel directly on the build plate.
    start_angle = -pi / 2.0
    for index in range(sides):
        angle = start_angle + 2.0 * pi * index / sides
        points.append(
            App.Vector(
                center_x + radius * cos(angle),
                y_start,
                center_z + radius * sin(angle),
            )
        )
    points.append(points[0])
    wire = Part.makePolygon(points)
    return Part.Face(wire).extrude(App.Vector(0, length, 0))


def cut_mounting_holes(leaf, hole_x):
    result = leaf
    for hole_y in PARAMS["mount_hole_y"]:
        tool = Part.makeCylinder(
            PARAMS["mount_hole_radius"],
            PARAMS["leaf_thickness"] + 0.4,
            App.Vector(hole_x, hole_y, -0.2),
        )
        result = result.cut(tool)
    return result


def make_hinge_halves():
    p = PARAMS
    outer_r = p["barrel_outer_radius"]
    axis_z = outer_r
    barrel_gap = p["leaf_barrel_gap"]
    overlap = p["leaf_barrel_overlap"]

    left_x = -outer_r - barrel_gap - p["leaf_width"]
    left_leaf = Part.makeBox(
        p["leaf_width"],
        p["hinge_length"],
        p["leaf_thickness"],
        App.Vector(left_x, 0, 0),
    )
    right_x = outer_r + barrel_gap
    right_leaf = Part.makeBox(
        p["leaf_width"],
        p["hinge_length"],
        p["leaf_thickness"],
        App.Vector(right_x, 0, 0),
    )

    left_hole_x = left_x + p["leaf_width"] * 0.48
    right_hole_x = right_x + p["leaf_width"] * 0.52
    left_leaf = cut_mounting_holes(left_leaf, left_hole_x)
    right_leaf = cut_mounting_holes(right_leaf, right_hole_x)

    pin = Part.makeCylinder(
        p["pin_radius"],
        p["hinge_length"],
        App.Vector(0, 0, axis_z),
        App.Vector(0, 1, 0),
    )
    left_shape = left_leaf.fuse(pin)
    right_shape = right_leaf

    gap_total = (p["knuckle_count"] - 1) * p["axial_clearance"]
    knuckle_length = (p["hinge_length"] - gap_total) / p["knuckle_count"]
    inner_r = p["pin_radius"] + p["radial_clearance"]

    y_start = 0.0
    for index in range(p["knuckle_count"]):
        outer = polygon_prism_along_y(
            outer_r,
            knuckle_length,
            y_start,
            axis_z,
            p["polygon_sides"],
        )
        if index % 2 == 0:
            # These knuckles tie the continuous pin to the left leaf.
            connector = Part.makeBox(
                overlap + barrel_gap,
                knuckle_length,
                p["leaf_thickness"],
                App.Vector(-outer_r - barrel_gap, y_start, 0),
            )
            left_shape = left_shape.fuse(outer).fuse(connector)
        else:
            inner = polygon_prism_along_y(
                inner_r,
                knuckle_length + 0.2,
                y_start - 0.1,
                axis_z,
                p["polygon_sides"],
            )
            sleeve = outer.cut(inner)
            connector = Part.makeBox(
                overlap + barrel_gap,
                knuckle_length,
                p["leaf_thickness"],
                App.Vector(outer_r - overlap, y_start, 0),
            )
            right_shape = right_shape.fuse(sleeve).fuse(connector)
        y_start += knuckle_length + p["axial_clearance"]

    return left_shape.removeSplitter(), right_shape.removeSplitter()


def add_parameters(obj):
    for name, value in PARAMS.items():
        prop_name = "Param_" + name
        obj.addProperty("App::PropertyString", prop_name, "Print parameters")
        if isinstance(value, tuple):
            value = ", ".join(str(item) for item in value)
        setattr(obj, prop_name, str(value))


def add_feature(doc, name, label, shape, color):
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape
    add_parameters(obj)
    if obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color
    return obj


def save_document_without_backup(doc, path):
    if os.path.exists(path):
        os.remove(path)
    doc.saveAs(path)


def export_stl(obj, path):
    if os.path.exists(path):
        os.remove(path)
    Mesh.export([obj], path)


def export_step(shape, path):
    if os.path.exists(path):
        os.remove(path)
    shape.exportStep(path)


def build_all():
    left_shape, right_shape = make_hinge_halves()
    hinge_shape = Part.makeCompound([left_shape, right_shape])

    if not left_shape.isValid() or not right_shape.isValid() or not hinge_shape.isValid():
        raise RuntimeError("Generated an invalid hinge; check the model parameters.")

    common_volume = left_shape.common(right_shape).Volume
    if common_volume > 1e-6:
        raise RuntimeError("The two moving hinge halves intersect.")

    hinge_doc = new_doc("print_in_place_window_hinge")
    left_obj = add_feature(
        hinge_doc,
        "LeftLeafWithIntegralPin",
        "Left leaf with integral continuous pin",
        left_shape,
        (0.72, 0.78, 0.86),
    )
    right_obj = add_feature(
        hinge_doc,
        "RightLeafWithCaptiveSleeves",
        "Right leaf with captive sleeves",
        right_shape,
        (0.93, 0.66, 0.18),
    )
    export_obj = hinge_doc.addObject("Part::Feature", "HingeExport")
    export_obj.Label = "Complete print-in-place hinge"
    export_obj.Shape = hinge_shape
    if export_obj.ViewObject is not None:
        export_obj.ViewObject.Visibility = False
    hinge_doc.recompute()

    single_fcstd = os.path.join(OUT_DIR, "print_in_place_window_hinge.FCStd")
    single_step = os.path.join(OUT_DIR, "print_in_place_window_hinge.step")
    single_stl = os.path.join(OUT_DIR, "print_in_place_window_hinge.stl")
    save_document_without_backup(hinge_doc, single_fcstd)
    export_step(hinge_shape, single_step)
    export_stl(export_obj, single_stl)

    pair_doc = new_doc("print_in_place_window_hinge_pair")
    second_hinge = hinge_shape.copy()
    pair_offset = 2.0 * (
        PARAMS["leaf_width"]
        + PARAMS["barrel_outer_radius"]
        - PARAMS["leaf_barrel_overlap"]
    ) + PARAMS["pair_spacing"]
    second_hinge.translate(App.Vector(0, pair_offset, 0))
    pair_shape = Part.makeCompound([hinge_shape, second_hinge])
    pair_obj = add_feature(
        pair_doc,
        "TwoCompleteHingesPrintPlate",
        "Two complete print-in-place hinges",
        pair_shape,
        (0.76, 0.80, 0.86),
    )
    pair_doc.recompute()

    pair_fcstd = os.path.join(OUT_DIR, "print_in_place_window_hinge_pair.FCStd")
    pair_step = os.path.join(OUT_DIR, "print_in_place_window_hinge_pair.step")
    pair_stl = os.path.join(OUT_DIR, "print_in_place_window_hinge_pair.stl")
    save_document_without_backup(pair_doc, pair_fcstd)
    export_step(pair_shape, pair_step)
    export_stl(pair_obj, pair_stl)

    print("Generated print-in-place window hinge:")
    for path in (single_fcstd, single_step, single_stl, pair_fcstd, pair_step, pair_stl):
        print(path)
    print("Moving parts in one hinge:", len(hinge_shape.Solids))
    print("Moving parts in pair plate:", len(pair_shape.Solids))
    print("Interference volume:", common_volume)
    print(
        "Single hinge bounds:",
        hinge_shape.BoundBox.XLength,
        hinge_shape.BoundBox.YLength,
        hinge_shape.BoundBox.ZLength,
    )


if __name__ == "__main__":
    build_all()
