import os

import FreeCAD as App
import Mesh
import Part
import Sketcher


# Unit: millimeter.
PARAMS = {
    "length": 48.0,
    "width": 45.0,
    "height": 20.0,
    "slot_zone_width": 10.0,
    "hole_zone_width": 5.0,
    "slot_count": 4,
    "slot_start_margin": 2.0,
    "slot_end_margin": 4.0,
    "slot_width": 8.0,
    "slot_start_z": 2.0,
    "slot_end_z": 6.0,
    "angled_slot_width": 3.5,
    "angled_slot_length": 7.0,
    "angled_slot_horizontal_run": 12.0,
    "angled_slot_vertical_drop": 12.0,
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


def add_body_sketch(body, name, z=0):
    sketch = body.newObject("Sketcher::SketchObject", name)
    sketch.Placement = App.Placement(App.Vector(0, 0, z), App.Rotation())
    return sketch


def hide_intermediates(doc, visible_names):
    for obj in doc.Objects:
        if obj.ViewObject is None:
            continue
        obj.ViewObject.Visibility = obj.Name in visible_names


def make_sloped_recess_tool(x0, x1, y0, y1, top_z, start_z, end_z):
    vertices = [
        App.Vector(x0, y0, top_z + 1),
        App.Vector(x1, y0, top_z + 1),
        App.Vector(x1, y1, top_z + 1),
        App.Vector(x0, y1, top_z + 1),
        App.Vector(x0, y0, start_z),
        App.Vector(x1, y0, end_z),
        App.Vector(x1, y1, end_z),
        App.Vector(x0, y1, start_z),
    ]
    faces = [
        Part.Face(Part.makePolygon([vertices[i] for i in [0, 1, 2, 3, 0]])),
        Part.Face(Part.makePolygon([vertices[i] for i in [4, 7, 6, 5, 4]])),
        Part.Face(Part.makePolygon([vertices[i] for i in [0, 4, 5, 1, 0]])),
        Part.Face(Part.makePolygon([vertices[i] for i in [1, 5, 6, 2, 1]])),
        Part.Face(Part.makePolygon([vertices[i] for i in [2, 6, 7, 3, 2]])),
        Part.Face(Part.makePolygon([vertices[i] for i in [3, 7, 4, 0, 3]])),
    ]
    shell = Part.makeShell(faces)
    return Part.makeSolid(shell)


def make_rounded_slot_2d(width, length):
    radius = width / 2.0
    half_straight = (length - width) / 2.0
    left = App.Vector(-half_straight, 0, 0)
    right = App.Vector(half_straight, 0, 0)

    edge1 = Part.LineSegment(App.Vector(-half_straight, -radius, 0), App.Vector(half_straight, -radius, 0)).toShape()
    arc1 = Part.Arc(
        App.Vector(half_straight, -radius, 0),
        App.Vector(half_straight + radius, 0, 0),
        App.Vector(half_straight, radius, 0),
    ).toShape()
    edge2 = Part.LineSegment(App.Vector(half_straight, radius, 0), App.Vector(-half_straight, radius, 0)).toShape()
    arc2 = Part.Arc(
        App.Vector(-half_straight, radius, 0),
        App.Vector(-half_straight - radius, 0, 0),
        App.Vector(-half_straight, -radius, 0),
    ).toShape()
    wire = Part.Wire([edge1, arc1, edge2, arc2])
    return Part.Face(wire)


def make_angled_slot_tool(x_center, y_center, top_z, width, length, horizontal_run, vertical_drop):
    face = make_rounded_slot_2d(width, length)
    tool = face.extrude(App.Vector(horizontal_run, 0, -vertical_drop))
    # Front view X-Z direction is -45 degrees: +X run equals -Z drop.
    tool.translate(App.Vector(x_center, y_center, top_z))
    return tool


def build_model():
    p = PARAMS
    doc = new_doc("sloped_tray_insert_48x45x20")
    body = doc.addObject("PartDesign::Body", "Body_SlopedTrayInsert")
    doc.recompute()

    base_sketch = add_body_sketch(body, "Sketch_01_Base_48x45")
    add_closed_polyline(base_sketch, [(0, 0), (p["length"], 0), (p["length"], p["width"]), (0, p["width"])])
    base = body.newObject("PartDesign::Pad", "Pad_02_Base_Block_20")
    base.Profile = base_sketch
    base.Length = p["height"]
    doc.recompute()

    final = doc.addObject("Part::Feature", "03_Base_For_Sloped_Cuts")
    final.Shape = base.Shape

    x0 = p["slot_start_margin"]
    x1 = p["length"] - p["slot_end_margin"]
    y_margin = (p["slot_zone_width"] - p["slot_width"]) / 2.0

    for i in range(p["slot_count"]):
        y0 = i * p["slot_zone_width"] + y_margin
        y1 = y0 + p["slot_width"]
        tool = doc.addObject("Part::Feature", f"04_Tool_Sloped_Recess_{i + 1}_6to12mm")
        tool.Shape = make_sloped_recess_tool(
            x0,
            x1,
            y0,
            y1,
            p["height"],
            p["slot_start_z"],
            p["slot_end_z"],
        )
        cut = doc.addObject("Part::Cut", f"05_Cut_Sloped_Recess_{i + 1}")
        cut.Base = final
        cut.Tool = tool
        final = cut
        doc.recompute()

    hole_y_center = p["slot_count"] * p["slot_zone_width"] + p["hole_zone_width"] / 2.0
    hole_x_center = p["length"] / 2.0
    angled_tool = doc.addObject("Part::Feature", "06_Tool_Angled_3p5x7mm_Slot")
    angled_tool.Shape = make_angled_slot_tool(
        hole_x_center,
        hole_y_center,
        p["height"],
        p["angled_slot_width"],
        p["angled_slot_length"],
        p["angled_slot_horizontal_run"],
        p["angled_slot_vertical_drop"],
    )
    final_cut = doc.addObject("Part::Cut", "07_Cut_Angled_3p5x7mm_Slot")
    final_cut.Base = final
    final_cut.Tool = angled_tool
    final = final_cut
    final.Label = "Final_SlopedTrayInsert_48x45x20"
    doc.recompute()

    hide_intermediates(doc, [final.Name])

    fcstd = os.path.join(OUT_DIR, "sloped_tray_insert_48x45x20.FCStd")
    step = os.path.join(OUT_DIR, "sloped_tray_insert_48x45x20.step")
    stl = os.path.join(OUT_DIR, "sloped_tray_insert_48x45x20.stl")
    doc.saveAs(fcstd)
    final.Shape.exportStep(step)
    Mesh.export([final], stl)
    return doc, final, fcstd, step, stl


def write_readme(fcstd, step, stl):
    readme = os.path.join(SCRIPT_DIR, "README_sloped_tray_insert.md")
    text = f"""# 48x45x20 斜坡凹槽件

## 结构理解

- 整体外形：48 x 45 x 20 mm。
- 45mm 宽度方向分成：10 + 10 + 10 + 10 + 5 mm。
- 前 4 个 10mm 区域各有一条长条凹槽。
- 每条凹槽沿 48mm 长度方向延伸，一端留 2mm，另一端留 4mm，凹槽长度 42mm。
- 凹槽底面沿 48mm 方向倾斜，一端深 6mm，另一端深 12mm。
- 最后 5mm 区域中间有一个 3.5 x 7mm 的斜向长圆孔。
- 斜孔方向也沿 48mm 长度方向，相对竖直方向倾斜 75 度。

## 输出文件

```text
{fcstd}
{step}
{stl}
```

## 重新生成

```powershell
& 'D:\\Program Files (x86)\\FreeCAD_weekly-2025.12.31-Windows-x86_64-py311\\bin\\python.exe' `
  'D:\\workspace\\things\\freecad-proctice\\vanity_cable_clamp\\make_sloped_tray_insert.py'
```
"""
    with open(readme, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    doc, final, fcstd, step, stl = build_model()
    write_readme(fcstd, step, stl)
    print("Generated sloped tray insert:")
    print(fcstd)
    print(step)
    print(stl)


if __name__ == "__main__":
    main()
