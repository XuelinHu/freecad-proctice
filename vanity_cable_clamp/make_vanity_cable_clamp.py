import os
from math import cos, pi, radians, sin

import FreeCAD as App
import Mesh
import Part
import Sketcher


# Unit: millimeter.
PARAMS = {
    "clamp_depth": 86.0,
    "clamp_height": 58.0,
    "clamp_width": 34.0,
    "spine_thickness": 18.0,
    "jaw_thickness": 14.0,
    "jaw_gap": 30.0,
    "corner_radius": 2.0,
    "cable_channel_radius": 5.0,
    "cable_channel_count": 3,
    "knob_outer_radius": 24.0,
    "knob_inner_radius": 20.5,
    "knob_teeth": 24,
    "knob_thickness": 12.0,
    "screw_radius": 3.8,
    "screw_length": 38.0,
    "pressure_pad_radius": 12.0,
    "pressure_pad_thickness": 4.0,
    "clearance_hole_radius": 4.4,
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
    indices = []
    for i, point in enumerate(points):
        nxt = points[(i + 1) % len(points)]
        indices.append(add_line(sketch, point, nxt))
    for i in range(len(indices)):
        sketch.addConstraint(Sketcher.Constraint("Coincident", indices[i], 2, indices[(i + 1) % len(indices)], 1))
    return indices


def add_circle(sketch, x, y, radius):
    geo_index = sketch.addGeometry(
        Part.Circle(App.Vector(x, y, 0), App.Vector(0, 0, 1), radius),
        False,
    )
    sketch.addConstraint(Sketcher.Constraint("Radius", geo_index, radius))
    return geo_index


def add_body_sketch(body, name, z=0):
    sketch = body.newObject("Sketcher::SketchObject", name)
    sketch.Placement = App.Placement(App.Vector(0, 0, z), App.Rotation())
    return sketch


def add_pad(body, name, sketch, length):
    pad = body.newObject("PartDesign::Pad", name)
    pad.Profile = sketch
    pad.Length = length
    return pad


def make_knob_outline(outer_radius, inner_radius, teeth):
    points = []
    for i in range(teeth * 2):
        radius = outer_radius if i % 2 == 0 else inner_radius
        angle = 2.0 * pi * i / (teeth * 2)
        points.append((radius * cos(angle), radius * sin(angle)))
    return points


def cylinder_along_y(radius, length, x, y, z):
    cyl = Part.makeCylinder(radius, length, App.Vector(x, y, z), App.Vector(0, 1, 0))
    return cyl


def hide_intermediates(doc, final_names):
    for obj in doc.Objects:
        if obj.ViewObject is None:
            continue
        obj.ViewObject.Visibility = obj.Name in final_names


def build_clamp_body():
    p = PARAMS
    doc = new_doc("vanity_cable_clamp_body")
    body = doc.addObject("PartDesign::Body", "Body_CClampCableGuide")
    doc.recompute()

    depth = p["clamp_depth"]
    height = p["clamp_height"]
    spine = p["spine_thickness"]
    jaw = p["jaw_thickness"]

    profile = add_body_sketch(body, "Sketch_01_CClamp_Side_Profile")
    # XY sketch, padded along Z. X is table depth, Y is clamp height.
    c_points = [
        (0, 0),
        (depth, 0),
        (depth, jaw),
        (spine, jaw),
        (spine, height - jaw),
        (depth, height - jaw),
        (depth, height),
        (0, height),
    ]
    add_closed_polyline(profile, c_points)
    base_pad = add_pad(body, "Pad_02_CClamp_Body", profile, p["clamp_width"])
    doc.recompute()

    boss_sketch = add_body_sketch(body, "Sketch_03_Knob_Hole_Boss", 0)
    boss_x = p["spine_thickness"] + 18.0
    boss_y = p["jaw_thickness"] / 2.0
    add_circle(boss_sketch, boss_x, boss_y, 9.0)
    boss_pad = add_pad(body, "Pad_04_Knob_Hole_Boss", boss_sketch, p["clamp_width"])
    doc.recompute()

    # Boolean cuts are kept as named construction steps because the screw axis is vertical.
    fused_shape = base_pad.Shape.fuse(boss_pad.Shape).removeSplitter()
    fused = doc.addObject("Part::Feature", "05_Fused_Clamp_And_Boss")
    fused.Shape = fused_shape

    hole_tool = doc.addObject("Part::Feature", "06_Tool_Vertical_Knob_Clearance_Hole")
    hole_tool.Shape = cylinder_along_y(
        p["clearance_hole_radius"],
        jaw + 4.0,
        boss_x,
        -2.0,
        p["clamp_width"] / 2.0,
    )
    cut_hole = doc.addObject("Part::Cut", "07_Cut_Knob_Clearance_Hole")
    cut_hole.Base = fused
    cut_hole.Tool = hole_tool
    doc.recompute()

    channel_tools = []
    start_x = 34.0
    spacing = 14.0
    for i in range(p["cable_channel_count"]):
        x = start_x + i * spacing
        tool = doc.addObject("Part::Feature", f"08_Tool_Cable_Channel_{i + 1}")
        # Half-depth cylinder cut across the width. It makes an open cradle on the top jaw.
        tool.Shape = cylinder_along_y(
            p["cable_channel_radius"],
            p["clamp_width"] + 4.0,
            x,
            height + 1.0,
            -2.0,
        ).rotate(App.Vector(x, height + 1.0, -2.0), App.Vector(1, 0, 0), 90)
        channel_tools.append(tool)

    final = cut_hole
    for i, tool in enumerate(channel_tools):
        cut = doc.addObject("Part::Cut", f"09_Cut_Cable_Channel_{i + 1}")
        cut.Base = final
        cut.Tool = tool
        final = cut
        doc.recompute()

    final.Label = "Final_ClampBody_With_CableGuide"
    hide_intermediates(doc, [final.Name])
    body.Tip = boss_pad
    doc.recompute()

    fcstd = os.path.join(OUT_DIR, "vanity_cable_clamp_body.FCStd")
    step = os.path.join(OUT_DIR, "vanity_cable_clamp_body.step")
    stl = os.path.join(OUT_DIR, "vanity_cable_clamp_body.stl")
    doc.saveAs(fcstd)
    final.Shape.exportStep(step)
    Mesh.export([final], stl)
    return doc, final, fcstd, step, stl


def build_knob_screw():
    p = PARAMS
    doc = new_doc("vanity_cable_clamp_knob_screw")
    body = doc.addObject("PartDesign::Body", "Body_KnurledKnobScrew")
    doc.recompute()

    knob_sketch = add_body_sketch(body, "Sketch_01_GearLike_Knob_Profile")
    add_closed_polyline(knob_sketch, make_knob_outline(p["knob_outer_radius"], p["knob_inner_radius"], p["knob_teeth"]))
    knob_pad = add_pad(body, "Pad_02_GearLike_Knob", knob_sketch, p["knob_thickness"])
    doc.recompute()

    screw_sketch = add_body_sketch(body, "Sketch_03_Screw_Shaft_Profile", p["knob_thickness"])
    add_circle(screw_sketch, 0, 0, p["screw_radius"])
    screw_pad = add_pad(body, "Pad_04_Screw_Shaft", screw_sketch, p["screw_length"])
    doc.recompute()

    pad_sketch = add_body_sketch(body, "Sketch_05_Pressure_Pad_Profile", p["knob_thickness"] + p["screw_length"])
    add_circle(pad_sketch, 0, 0, p["pressure_pad_radius"])
    pressure_pad = add_pad(body, "Pad_06_Pressure_Pad", pad_sketch, p["pressure_pad_thickness"])
    doc.recompute()

    final = pressure_pad
    body.Tip = final
    hide_intermediates(doc, [final.Name])

    fcstd = os.path.join(OUT_DIR, "vanity_cable_clamp_knob_screw.FCStd")
    step = os.path.join(OUT_DIR, "vanity_cable_clamp_knob_screw.step")
    stl = os.path.join(OUT_DIR, "vanity_cable_clamp_knob_screw.stl")
    doc.saveAs(fcstd)
    final.Shape.exportStep(step)
    Mesh.export([final], stl)
    return doc, final, fcstd, step, stl


def build_assembly(clamp_obj, knob_obj):
    p = PARAMS
    doc = new_doc("vanity_cable_clamp_assembly")

    clamp = doc.addObject("Part::Feature", "ClampBody")
    clamp.Shape = clamp_obj.Shape
    clamp.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

    knob = doc.addObject("Part::Feature", "KnobScrew_Inserted")
    knob.Shape = knob_obj.Shape
    boss_x = p["spine_thickness"] + 18.0
    z_center = p["clamp_width"] / 2.0
    # Knob model axis is local Z. Rotate it to clamp vertical Y, then place it in the lower jaw hole.
    knob.Placement = App.Placement(
        App.Vector(boss_x, -p["knob_thickness"] - 1.5, z_center),
        App.Rotation(App.Vector(1, 0, 0), -90),
    )

    tabletop = doc.addObject("Part::Feature", "Reference_Tabletop_25mm_Not_For_Print")
    tabletop.Shape = Part.makeBox(
        p["clamp_depth"] - p["spine_thickness"] - 8.0,
        25.0,
        p["clamp_width"] + 8.0,
        App.Vector(p["spine_thickness"] + 4.0, p["jaw_thickness"] + 2.5, -4.0),
    )

    doc.recompute()
    fcstd = os.path.join(OUT_DIR, "vanity_cable_clamp_assembly.FCStd")
    step = os.path.join(OUT_DIR, "vanity_cable_clamp_assembly.step")
    doc.saveAs(fcstd)
    Part.export([clamp, knob, tabletop], step)
    return doc, fcstd, step


def write_readme(paths):
    readme = os.path.join(SCRIPT_DIR, "README.md")
    text = f"""# 化妆台布线夹具

这是一个用于化妆台、桌面边缘或薄板边缘的布线夹具模型。结构由两部分组成：

- 夹具主体：C 型夹口，上方带 3 个线缆导向槽。
- 旋钮螺杆：齿形手拧旋钮、压紧杆、圆形压盘。

另有一个装配文件，把旋钮螺杆插入夹具下方孔位，并放入 25mm 厚桌板参考块。

## 本机 Gear 插件

已确认本机可导入：

```text
freecad.gears 1.3.0
```

本模型的旋钮没有直接使用 Gear 插件生成齿轮对象，而是用 `Sketch_01_GearLike_Knob_Profile` 画了粗齿形草图后 `Pad` 拉伸。这样更符合“草图可编辑”的需求，也更适合 3D 打印手拧旋钮。

## 默认尺寸

- 夹具外深：86 mm
- 夹具外高：58 mm
- 夹具宽度：34 mm
- 夹口基础开口：30 mm
- 线缆槽数量：3 个
- 单个线缆槽半径：5 mm
- 旋钮外半径：24 mm
- 旋钮齿数：24
- 压紧杆半径：3.8 mm
- 压盘半径：12 mm

## Output Files

夹具主体：

```text
{paths["body_fcstd"]}
{paths["body_step"]}
{paths["body_stl"]}
```

旋钮螺杆：

```text
{paths["knob_fcstd"]}
{paths["knob_step"]}
{paths["knob_stl"]}
```

装配体：

```text
{paths["assembly_fcstd"]}
{paths["assembly_step"]}
```

## 重新生成

```powershell
& 'D:\\Program Files (x86)\\FreeCAD_weekly-2025.12.31-Windows-x86_64-py311\\bin\\python.exe' `
  'D:\\workspace\\things\\freecad-proctice\\vanity_cable_clamp\\make_vanity_cable_clamp.py'
```

## 打印建议

- 夹具主体建议侧躺打印，让 C 型侧面贴近打印平台。
- 旋钮螺杆当前是打印演示结构；如果需要更强夹紧力，建议后续改为嵌入 M6/M8 金属螺丝。
- 压盘与桌板接触面可以后续贴一片软胶垫，减少压痕和打滑。
"""
    with open(readme, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    clamp_doc, clamp_obj, body_fcstd, body_step, body_stl = build_clamp_body()
    knob_doc, knob_obj, knob_fcstd, knob_step, knob_stl = build_knob_screw()
    assembly_doc, assembly_fcstd, assembly_step = build_assembly(clamp_obj, knob_obj)
    paths = {
        "body_fcstd": body_fcstd,
        "body_step": body_step,
        "body_stl": body_stl,
        "knob_fcstd": knob_fcstd,
        "knob_step": knob_step,
        "knob_stl": knob_stl,
        "assembly_fcstd": assembly_fcstd,
        "assembly_step": assembly_step,
    }
    write_readme(paths)
    print("Generated vanity cable clamp files:")
    for value in paths.values():
        print(value)


if __name__ == "__main__":
    main()
