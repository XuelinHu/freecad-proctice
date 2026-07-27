import os
from math import cos, pi, sin

import FreeCAD as App
import Mesh
import Part
import Sketcher


# Unit: millimeter.
PARAMS = {
    "base_size": 15.0,
    "top_size": 7.0,
    "height": 15.0,
    "hole_depth": 7.0,
    "hole_top_diameter": 3.0,
    "hole_bottom_diameter": 1.0,
    "thread_start_offset": 0.6,
    "thread_end_offset": 0.6,
    "thread_pitch": 1.1,
    "thread_groove_radius": 0.13,
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


def add_line(sketch, p1, p2):
    return sketch.addGeometry(
        Part.LineSegment(App.Vector(p1[0], p1[1], 0), App.Vector(p2[0], p2[1], 0)),
        False,
    )


def add_closed_polyline(sketch, points):
    lines = []
    for i, point in enumerate(points):
        nxt = points[(i + 1) % len(points)]
        lines.append(add_line(sketch, point, nxt))
    for i in range(len(lines)):
        sketch.addConstraint(Sketcher.Constraint("Coincident", lines[i], 2, lines[(i + 1) % len(lines)], 1))
    return lines


def centered_square_wire(size, z):
    half = size / 2.0
    points = [
        App.Vector(-half, -half, z),
        App.Vector(half, -half, z),
        App.Vector(half, half, z),
        App.Vector(-half, half, z),
        App.Vector(-half, -half, z),
    ]
    return Part.Wire(Part.makePolygon(points).Edges)


def hide_intermediates(doc, visible_names):
    for obj in doc.Objects:
        if obj.ViewObject is None:
            continue
        obj.ViewObject.Visibility = obj.Name in visible_names


def make_tapered_body(base_size, top_size, height):
    base_wire = centered_square_wire(base_size, 0)
    top_wire = centered_square_wire(top_size, height)
    return Part.makeLoft([base_wire, top_wire], True, False, False)


def make_tapered_hole_tool(top_z, depth, top_diameter, bottom_diameter):
    top_radius = top_diameter / 2.0
    bottom_radius = bottom_diameter / 2.0
    # Part.makeCone(radius1, radius2, ...) uses radius1 at the base point and
    # radius2 at the end of the direction vector.
    cone = Part.makeCone(bottom_radius, top_radius, depth, App.Vector(0, 0, top_z - depth), App.Vector(0, 0, 1))
    return cone


def radius_at_z(z, top_z, depth, top_diameter, bottom_diameter):
    bottom_z = top_z - depth
    t = (z - bottom_z) / depth
    return (bottom_diameter / 2.0) + t * ((top_diameter - bottom_diameter) / 2.0)


def make_internal_thread_groove_tool(
    top_z,
    depth,
    top_diameter,
    bottom_diameter,
    start_offset,
    end_offset,
    pitch,
    groove_radius,
):
    z_start = top_z - start_offset
    z_end = top_z - depth + end_offset
    thread_height = z_start - z_end
    turns = max(thread_height / pitch, 1.0)
    sample_count = max(int(turns * 48), 40)
    points = []

    for i in range(sample_count + 1):
        t = i / sample_count
        z = z_start - t * thread_height
        angle = 2.0 * pi * turns * t
        wall_radius = radius_at_z(z, top_z, depth, top_diameter, bottom_diameter)
        path_radius = wall_radius + groove_radius * 0.45
        points.append(App.Vector(path_radius * cos(angle), path_radius * sin(angle), z))

    path = Part.Wire(Part.makePolygon(points).Edges)
    first = points[0]
    profile = Part.Wire(Part.Circle(first, App.Vector(0, 0, 1), groove_radius).toShape())
    return path.makePipeShell([profile], True, True)


def build_model():
    p = PARAMS
    doc = new_doc("tapered_square_standoff_15x15_to_7x7")

    body = doc.addObject("PartDesign::Body", "Body_TaperedSquareStandoff")
    base_sketch = body.newObject("Sketcher::SketchObject", "Sketch_01_BaseSquare_15x15")
    half_base = p["base_size"] / 2.0
    add_closed_polyline(
        base_sketch,
        [
            (-half_base, -half_base),
            (half_base, -half_base),
            (half_base, half_base),
            (-half_base, half_base),
        ],
    )

    top_sketch = body.newObject("Sketcher::SketchObject", "Sketch_02_TopSquare_7x7")
    top_sketch.Placement = App.Placement(App.Vector(0, 0, p["height"]), App.Rotation())
    half_top = p["top_size"] / 2.0
    add_closed_polyline(
        top_sketch,
        [
            (-half_top, -half_top),
            (half_top, -half_top),
            (half_top, half_top),
            (-half_top, half_top),
        ],
    )

    loft_shape = make_tapered_body(p["base_size"], p["top_size"], p["height"])
    loft = doc.addObject("Part::Feature", "03_Loft_15x15_To_7x7_Height15")
    loft.Shape = loft_shape

    hole_tool = doc.addObject("Part::Feature", "04_Tool_Tapered_Center_Hole_3to1_Depth7")
    hole_tool.Shape = make_tapered_hole_tool(
        p["height"],
        p["hole_depth"],
        p["hole_top_diameter"],
        p["hole_bottom_diameter"],
    )

    final = doc.addObject("Part::Cut", "05_Cut_Tapered_Center_Hole")
    final.Base = loft
    final.Tool = hole_tool
    doc.recompute()

    thread_tool = doc.addObject("Part::Feature", "06_Tool_Internal_Thread_Groove")
    thread_tool.Shape = make_internal_thread_groove_tool(
        p["height"],
        p["hole_depth"],
        p["hole_top_diameter"],
        p["hole_bottom_diameter"],
        p["thread_start_offset"],
        p["thread_end_offset"],
        p["thread_pitch"],
        p["thread_groove_radius"],
    )

    threaded_final = doc.addObject("Part::Cut", "07_Cut_Internal_Thread_Groove")
    threaded_final.Base = final
    threaded_final.Tool = thread_tool
    threaded_final.Label = "Final_TaperedSquareStandoff"
    doc.recompute()
    final = threaded_final
    hide_intermediates(doc, [final.Name])

    fcstd = os.path.join(OUT_DIR, "tapered_square_standoff_15x15_to_7x7.FCStd")
    step = os.path.join(OUT_DIR, "tapered_square_standoff_15x15_to_7x7.step")
    stl = os.path.join(OUT_DIR, "tapered_square_standoff_15x15_to_7x7.stl")
    doc.saveAs(fcstd)
    final.Shape.exportStep(step)
    Mesh.export([final], stl)
    return doc, final, fcstd, step, stl


def main():
    doc, final, fcstd, step, stl = build_model()
    print("Generated tapered square standoff:")
    print(fcstd)
    print(step)
    print(stl)


if __name__ == "__main__":
    main()
