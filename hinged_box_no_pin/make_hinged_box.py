import os

import FreeCAD as App
import Mesh
import Part


# Unit: millimeter. These parameters are intended for a 0.4 mm FDM nozzle.
PARAMS = {
    "length": 120.0,
    "width": 80.0,
    "height": 45.0,
    "wall": 2.4,
    "bottom": 2.4,
    "lid_thickness": 2.4,
    "lid_gap": 0.40,
    "lid_rear_overhang": 1.5,
    "rim_height": 3.5,
    "rim_thickness": 1.6,
    "rim_clearance": 0.35,
    "hinge_axis_offset": 4.3,
    "hinge_axis_drop": 2.2,
    "hinge_width": 26.0,
    "hinge_support_width": 3.0,
    "hinge_positions": (16.0, 78.0),
    "pin_radius": 2.2,
    "hinge_clearance": 0.35,
    "clip_outer_radius": 3.9,
    "clip_mouth": 4.05,
    "support_overlap": 0.8,
    "print_spacing": 10.0,
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


def export_object(doc, obj, stem, export_stl=True):
    doc.recompute()
    fcstd_path = os.path.join(OUT_DIR, stem + ".FCStd")
    step_path = os.path.join(OUT_DIR, stem + ".step")
    doc.saveAs(fcstd_path)
    obj.Shape.exportStep(step_path)
    paths = [fcstd_path, step_path]
    if export_stl:
        stl_path = os.path.join(OUT_DIR, stem + ".stl")
        Mesh.export([obj], stl_path)
        paths.append(stl_path)
    return paths


def add_parameters(obj):
    for name, value in PARAMS.items():
        if name == "hinge_positions":
            continue
        prop_name = "Param_" + name
        obj.addProperty("App::PropertyString", prop_name, "Print parameters")
        setattr(obj, prop_name, str(value))
    obj.addProperty("App::PropertyString", "Param_hinge_positions", "Print parameters")
    obj.Param_hinge_positions = ", ".join(str(value) for value in PARAMS["hinge_positions"])


def make_box_body():
    p = PARAMS
    outer = Part.makeBox(p["length"], p["width"], p["height"])
    cavity = Part.makeBox(
        p["length"] - 2.0 * p["wall"],
        p["width"] - 2.0 * p["wall"],
        p["height"] - p["bottom"] + 0.1,
        App.Vector(p["wall"], p["wall"], p["bottom"]),
    )
    shape = outer.cut(cavity)

    axis_y = p["width"] + p["hinge_axis_offset"]
    axis_z = p["height"] - p["hinge_axis_drop"]
    pin_r = p["pin_radius"]

    for hinge_x in p["hinge_positions"]:
        pin = Part.makeCylinder(
            pin_r,
            p["hinge_width"],
            App.Vector(hinge_x, axis_y, axis_z),
            App.Vector(1, 0, 0),
        )
        shape = shape.fuse(pin)

        for support_x in (
            hinge_x,
            hinge_x + p["hinge_width"] - p["hinge_support_width"],
        ):
            support = Part.makeBox(
                p["hinge_support_width"],
                axis_y - p["width"] + p["support_overlap"],
                2.0 * pin_r,
                App.Vector(
                    support_x,
                    p["width"] - p["support_overlap"],
                    axis_z - pin_r,
                ),
            )
            shape = shape.fuse(support)

    return shape.removeSplitter()


def make_lid_closed():
    p = PARAMS
    lid_z = p["height"] + p["lid_gap"]
    plate = Part.makeBox(
        p["length"],
        p["width"] + p["lid_rear_overhang"],
        p["lid_thickness"],
        App.Vector(0, 0, lid_z),
    )

    rim_inset = p["wall"] + p["rim_clearance"]
    rim_outer_length = p["length"] - 2.0 * rim_inset
    rim_outer_width = p["width"] - 2.0 * rim_inset
    rim_origin = App.Vector(rim_inset, rim_inset, lid_z - p["rim_height"])
    rim_outer = Part.makeBox(
        rim_outer_length,
        rim_outer_width,
        p["rim_height"],
        rim_origin,
    )
    rim_inner = Part.makeBox(
        rim_outer_length - 2.0 * p["rim_thickness"],
        rim_outer_width - 2.0 * p["rim_thickness"],
        p["rim_height"] + 0.2,
        App.Vector(
            rim_inset + p["rim_thickness"],
            rim_inset + p["rim_thickness"],
            lid_z - p["rim_height"] - 0.1,
        ),
    )
    shape = plate.fuse(rim_outer.cut(rim_inner))

    axis_y = p["width"] + p["hinge_axis_offset"]
    axis_z = p["height"] - p["hinge_axis_drop"]
    inner_r = p["pin_radius"] + p["hinge_clearance"]
    outer_r = p["clip_outer_radius"]
    clip_start_offset = p["hinge_support_width"] + 0.6
    clip_length = p["hinge_width"] - 2.0 * clip_start_offset

    for hinge_x in p["hinge_positions"]:
        clip_x = hinge_x + clip_start_offset
        outer = Part.makeCylinder(
            outer_r,
            clip_length,
            App.Vector(clip_x, axis_y, axis_z),
            App.Vector(1, 0, 0),
        )
        inner = Part.makeCylinder(
            inner_r,
            clip_length + 0.2,
            App.Vector(clip_x - 0.1, axis_y, axis_z),
            App.Vector(1, 0, 0),
        )
        clip = outer.cut(inner)

        mouth = Part.makeBox(
            clip_length + 0.4,
            outer_r + 0.3,
            p["clip_mouth"],
            App.Vector(
                clip_x - 0.2,
                axis_y - outer_r - 0.1,
                axis_z - p["clip_mouth"] / 2.0,
            ),
        )
        clip = clip.cut(mouth)

        connector = Part.makeBox(
            clip_length,
            axis_y - (p["width"] - 0.5),
            lid_z + p["lid_thickness"] - (p["height"] + 0.15),
            App.Vector(clip_x, p["width"] - 0.5, p["height"] + 0.15),
        )
        shape = shape.fuse(clip).fuse(connector)

    return shape.removeSplitter()


def orient_lid_for_print(lid_closed):
    print_shape = lid_closed.copy()
    print_shape.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 180.0)
    bounds = print_shape.BoundBox
    print_shape.translate(App.Vector(-bounds.XMin, -bounds.YMin, -bounds.ZMin))
    return print_shape


def make_feature(doc, name, label, shape, color):
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape
    add_parameters(obj)
    if obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color
    return obj


def build_all():
    body_shape = make_box_body()
    lid_closed_shape = make_lid_closed()
    lid_print_shape = orient_lid_for_print(lid_closed_shape)

    if not body_shape.isValid() or not lid_closed_shape.isValid() or not lid_print_shape.isValid():
        raise RuntimeError("Generated an invalid solid; check the model parameters.")

    body_doc = new_doc("hinged_box_body")
    body_obj = make_feature(
        body_doc,
        "BodyWithIntegralPins",
        "Box body with two integral hinge pins",
        body_shape,
        (0.82, 0.82, 0.86),
    )
    body_paths = export_object(body_doc, body_obj, "hinged_box_body")

    lid_doc = new_doc("hinged_box_lid")
    lid_obj = make_feature(
        lid_doc,
        "LidWithSnapClips_PrintOrientation",
        "Lid with two snap-fit hinge clips - print orientation",
        lid_print_shape,
        (0.93, 0.66, 0.18),
    )
    lid_paths = export_object(lid_doc, lid_obj, "hinged_box_lid")

    assembly_doc = new_doc("hinged_box_assembly")
    assembly_body = make_feature(
        assembly_doc,
        "BodyWithIntegralPins",
        "Box body",
        body_shape,
        (0.82, 0.82, 0.86),
    )
    assembly_lid = make_feature(
        assembly_doc,
        "LidWithSnapClips",
        "Closed lid",
        lid_closed_shape,
        (0.93, 0.66, 0.18),
    )
    if assembly_lid.ViewObject is not None:
        assembly_lid.ViewObject.Transparency = 10
    assembly_doc.recompute()
    assembly_compound = assembly_doc.addObject("Part::Feature", "AssemblyExport")
    assembly_compound.Label = "Body and lid assembly export"
    assembly_compound.Shape = Part.makeCompound([body_shape, lid_closed_shape])
    if assembly_compound.ViewObject is not None:
        assembly_compound.ViewObject.Visibility = False
    assembly_doc.recompute()
    assembly_step = os.path.join(OUT_DIR, "hinged_box_assembly.step")
    assembly_compound.Shape.exportStep(assembly_step)
    if assembly_body.ViewObject is not None:
        assembly_body.ViewObject.Visibility = True
    if assembly_lid.ViewObject is not None:
        assembly_lid.ViewObject.Visibility = True
    if assembly_compound.ViewObject is not None:
        assembly_compound.ViewObject.Visibility = False
    assembly_fcstd = os.path.join(OUT_DIR, "hinged_box_assembly.FCStd")
    assembly_doc.saveAs(assembly_fcstd)
    assembly_paths = [assembly_fcstd, assembly_step]

    plate_doc = new_doc("hinged_box_print_plate")
    lid_on_plate = lid_print_shape.copy()
    lid_on_plate.translate(
        App.Vector(0, body_shape.BoundBox.YMax + PARAMS["print_spacing"], 0)
    )
    plate_shape = Part.makeCompound([body_shape, lid_on_plate])
    plate_obj = make_feature(
        plate_doc,
        "PrintPlate",
        "Body and lid arranged for one print job",
        plate_shape,
        (0.72, 0.78, 0.86),
    )
    plate_paths = export_object(plate_doc, plate_obj, "hinged_box_print_plate")

    print("Generated pin-free hinged box:")
    for path in body_paths + lid_paths + assembly_paths + plate_paths:
        print(path)
    print("Body solids:", len(body_shape.Solids))
    print("Lid solids:", len(lid_print_shape.Solids))
    print("Print plate solids:", len(plate_shape.Solids))
    print("Body bounds:", body_shape.BoundBox.XLength, body_shape.BoundBox.YLength, body_shape.BoundBox.ZLength)
    print("Lid print bounds:", lid_print_shape.BoundBox.XLength, lid_print_shape.BoundBox.YLength, lid_print_shape.BoundBox.ZLength)


if __name__ == "__main__":
    build_all()
