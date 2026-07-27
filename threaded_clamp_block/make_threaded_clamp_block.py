import os
from math import cos, pi, sin

import FreeCAD as App
import Mesh
import Part
import Sketcher


# Unit: millimeter.
PARAMS = {
    "block_x": 30.0,
    "block_y": 30.0,
    "block_z": 50.0,
    "slot_y_start": 5.0,
    "slot_y_end": 25.0,
    "slot_z_start": 15.0,
    "hole_diameter": 10.0,
    "hole_depth_y": 28.0,
    "thread_pitch": 1.5,
    "thread_groove_radius": 0.20,
    "bolt_shaft_diameter": 9.2,
    "bolt_thread_radius": 5.05,
    "bolt_shaft_length": 18.0,
    "bolt_knob_diameter": 22.0,
    "bolt_knob_thickness": 8.0,
    "bolt_knob_teeth": 20,
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


def hide_intermediates(doc, visible_names):
    for obj in doc.Objects:
        if obj.ViewObject is None:
            continue
        obj.ViewObject.Visibility = obj.Name in visible_names


def cylinder_y(radius, length, x, y, z):
    return Part.makeCylinder(radius, length, App.Vector(x, y, z), App.Vector(0, 1, 0))


def make_helical_path_y(radius, y_start, y_end, x_center, z_center, pitch, samples_per_turn=20):
    length = y_end - y_start
    turns = max(abs(length) / pitch, 1.0)
    sample_count = max(int(turns * samples_per_turn), 48)
    points = []
    direction = 1 if length >= 0 else -1

    for i in range(sample_count + 1):
        t = i / sample_count
        y = y_start + length * t
        angle = 2.0 * pi * turns * t * direction
        x = x_center + radius * cos(angle)
        z = z_center + radius * sin(angle)
        points.append(App.Vector(x, y, z))

    return Part.Wire(Part.makePolygon(points).Edges)


def make_pipe_on_y_helix(radius, y_start, y_end, x_center, z_center, pitch, profile_radius):
    path = make_helical_path_y(radius, y_start, y_end, x_center, z_center, pitch)
    first = path.Vertexes[0].Point
    profile = Part.Wire(Part.Circle(first, App.Vector(0, 1, 0), profile_radius).toShape())
    return path.makePipeShell([profile], True, True)


def make_knurled_knob_y(outer_radius, inner_radius, thickness, teeth, y_front):
    points = []
    for i in range(teeth * 2):
        radius = outer_radius if i % 2 == 0 else inner_radius
        angle = 2.0 * pi * i / (teeth * 2)
        points.append(App.Vector(radius * cos(angle), 0, radius * sin(angle)))
    points.append(points[0])
    face = Part.Face(Part.Wire(Part.makePolygon(points).Edges))
    return face.extrude(App.Vector(0, thickness, 0)).translate(App.Vector(0, y_front, 0))


def build_block():
    p = PARAMS
    doc = new_doc("threaded_clamp_block_body")
    body = doc.addObject("PartDesign::Body", "Body_ClampBlock")

    base_sketch = body.newObject("Sketcher::SketchObject", "Sketch_01_Base_X30_Y30")
    add_closed_polyline(base_sketch, [(0, 0), (p["block_x"], 0), (p["block_x"], p["block_y"]), (0, p["block_y"])])
    pad = body.newObject("PartDesign::Pad", "Pad_02_Base_Block_Z50")
    pad.Profile = base_sketch
    pad.Length = p["block_z"]
    doc.recompute()

    base_feature = doc.addObject("Part::Feature", "03_Base_Block_30x30x50")
    base_feature.Shape = pad.Shape

    slot_tool = doc.addObject("Part::Feature", "04_Tool_Side_Rectangular_Slot_Through_XZ")
    slot_tool.Shape = Part.makeBox(
        p["block_x"] + 2.0,
        p["slot_y_end"] - p["slot_y_start"],
        p["block_z"] - p["slot_z_start"] + 1.0,
        App.Vector(-1.0, p["slot_y_start"], p["slot_z_start"]),
    )
    slot_cut = doc.addObject("Part::Cut", "05_Cut_Side_Rectangular_Slot_Through_XZ")
    slot_cut.Base = base_feature
    slot_cut.Tool = slot_tool
    doc.recompute()

    hole_x = p["block_x"] / 2.0
    hole_z = p["block_z"] / 2.0
    hole_tool = doc.addObject("Part::Feature", "06_Tool_Y_Axis_Hole_D10_Depth28")
    hole_tool.Shape = cylinder_y(p["hole_diameter"] / 2.0, p["hole_depth_y"], hole_x, 0.0, hole_z)
    hole_cut = doc.addObject("Part::Cut", "07_Cut_Blind_Hole_Not_Through_Back")
    hole_cut.Base = slot_cut
    hole_cut.Tool = hole_tool
    doc.recompute()

    thread_tool = doc.addObject("Part::Feature", "08_Tool_Internal_Thread_Groove")
    thread_tool.Shape = make_pipe_on_y_helix(
        p["hole_diameter"] / 2.0 - p["thread_groove_radius"] * 0.40,
        p["slot_y_end"] + 0.35,
        p["hole_depth_y"] - 0.35,
        hole_x,
        hole_z,
        p["thread_pitch"],
        p["thread_groove_radius"],
    )
    final = doc.addObject("Part::Cut", "09_Cut_Internal_Thread_Groove")
    final.Base = hole_cut
    final.Tool = thread_tool
    final.Label = "Final_ThreadedClampBlock"
    doc.recompute()
    hide_intermediates(doc, [final.Name])

    fcstd = os.path.join(OUT_DIR, "threaded_clamp_block_body.FCStd")
    step = os.path.join(OUT_DIR, "threaded_clamp_block_body.step")
    stl = os.path.join(OUT_DIR, "threaded_clamp_block_body.stl")
    doc.saveAs(fcstd)
    final.Shape.exportStep(step)
    Mesh.export([final], stl)
    return doc, final, fcstd, step, stl


def build_bolt():
    p = PARAMS
    doc = new_doc("threaded_clamp_block_bolt")

    shaft = doc.addObject("Part::Feature", "01_Bolt_Shaft_D9p2_L18")
    shaft.Shape = cylinder_y(p["bolt_shaft_diameter"] / 2.0, p["bolt_shaft_length"], 0, 0, 0)

    thread = doc.addObject("Part::Feature", "02_External_Thread_Ridge")
    thread.Shape = make_pipe_on_y_helix(
        p["bolt_thread_radius"],
        0.5,
        p["bolt_shaft_length"] - 0.5,
        0,
        0,
        p["thread_pitch"],
        p["thread_groove_radius"],
    )

    knob = doc.addObject("Part::Feature", "03_Knurled_Hand_Knob")
    knob.Shape = make_knurled_knob_y(
        p["bolt_knob_diameter"] / 2.0,
        p["bolt_knob_diameter"] / 2.0 - 1.8,
        p["bolt_knob_thickness"],
        p["bolt_knob_teeth"],
        -p["bolt_knob_thickness"],
    )

    fused_1 = doc.addObject("Part::Fuse", "04_Fuse_Shaft_Thread")
    fused_1.Base = shaft
    fused_1.Tool = thread
    fused_2 = doc.addObject("Part::Fuse", "05_Final_Threaded_Bolt_With_Knob")
    fused_2.Base = fused_1
    fused_2.Tool = knob
    doc.recompute()
    hide_intermediates(doc, [fused_2.Name])

    fcstd = os.path.join(OUT_DIR, "threaded_clamp_block_bolt.FCStd")
    step = os.path.join(OUT_DIR, "threaded_clamp_block_bolt.step")
    stl = os.path.join(OUT_DIR, "threaded_clamp_block_bolt.stl")
    doc.saveAs(fcstd)
    fused_2.Shape.exportStep(step)
    Mesh.export([fused_2], stl)
    return doc, fused_2, fcstd, step, stl


def build_assembly(block_obj, bolt_obj):
    p = PARAMS
    doc = new_doc("threaded_clamp_block_assembly")

    block = doc.addObject("Part::Feature", "ClampBlock_With_BlindThreadedHole")
    block.Shape = block_obj.Shape

    bolt = doc.addObject("Part::Feature", "ThreadedBolt_Partially_Inserted")
    bolt.Shape = bolt_obj.Shape
    bolt.Placement = App.Placement(
        App.Vector(p["block_x"] / 2.0, -8.0, p["block_z"] / 2.0),
        App.Rotation(),
    )

    doc.recompute()
    fcstd = os.path.join(OUT_DIR, "threaded_clamp_block_assembly.FCStd")
    step = os.path.join(OUT_DIR, "threaded_clamp_block_assembly.step")
    doc.saveAs(fcstd)
    Part.export([block, bolt], step)
    return doc, fcstd, step


def main():
    block_doc, block_obj, block_fcstd, block_step, block_stl = build_block()
    bolt_doc, bolt_obj, bolt_fcstd, bolt_step, bolt_stl = build_bolt()
    assembly_doc, assembly_fcstd, assembly_step = build_assembly(block_obj, bolt_obj)
    print("Generated threaded clamp block files:")
    for path in [
        block_fcstd,
        block_step,
        block_stl,
        bolt_fcstd,
        bolt_step,
        bolt_stl,
        assembly_fcstd,
        assembly_step,
    ]:
        print(path)


if __name__ == "__main__":
    main()
