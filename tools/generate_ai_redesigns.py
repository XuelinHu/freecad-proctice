#!/usr/bin/env python3
"""Generate separate sketch and partial-design variants of FreeCAD models.

Run this script with the Python executable bundled with FreeCAD. Source files
are never modified; generated files are written to sibling directories with
an AI_ prefix.
"""

from __future__ import annotations

import FreeCAD as App
import Part
import Sketcher

import argparse
import json
import math
import re
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="FreeCAD repository root")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional centralized output directory; default is sibling AI_ directories",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace generated files with the same names",
    )
    return parser.parse_args()


def slug(value):
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return value.strip("_.") or "model"


def source_files(root, output_dir):
    output_dir = output_dir.resolve() if output_dir else None
    files = []
    for path in root.rglob("*.FCStd"):
        resolved = path.resolve()
        if output_dir and (output_dir == resolved or output_dir in resolved.parents):
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if any(part.startswith("AI_") or part.lower() == "ai_generated" for part in path.parts):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.as_posix().lower())


def output_model_dir(root, source_path, output_dir):
    if output_dir:
        relative = source_path.relative_to(root).with_suffix("")
        model_id = slug("__".join(relative.parts))
        return output_dir / model_id, model_id

    source_parent = source_path.parent
    if source_path.stem.casefold() == source_parent.name.casefold():
        target = source_parent.parent / ("AI_" + source_parent.name)
    else:
        target = source_parent / ("AI_" + source_path.stem)
    return target, target.name


def shape_from_document(document):
    candidates = []
    for obj in document.Objects:
        shape = getattr(obj, "Shape", None)
        if shape is None or shape.isNull() or not shape.Faces:
            continue
        try:
            volume = float(shape.Volume)
        except Exception:
            volume = 0.0
        try:
            area = float(shape.Area)
        except Exception:
            area = 0.0
        candidates.append((volume, area, obj, shape))
    if not candidates:
        return None, None
    _, _, obj, shape = max(candidates, key=lambda item: (item[0], item[1]))
    return obj, shape


def edge_points(edge):
    try:
        points = list(edge.discretize(Number=16))
    except Exception:
        points = []
    if len(points) < 2:
        vertices = edge.Vertexes
        points = [vertex.Point for vertex in vertices]
    return points


def normal_for_face(face):
    try:
        u1, u2, v1, v2 = face.ParameterRange
        normal = face.normalAt((u1 + u2) / 2.0, (v1 + v2) / 2.0)
        if normal.Length > 1e-9:
            return normal.normalize()
    except Exception:
        pass
    return App.Vector(0, 0, 1)


def basis_for_face(face, normal):
    origin = face.CenterOfMass
    direction = None
    for edge in face.OuterWire.Edges:
        points = edge_points(edge)
        if len(points) >= 2:
            candidate = points[-1].sub(points[0])
            projection = candidate.dot(normal)
            candidate = candidate.sub(App.Vector(
                normal.x * projection, normal.y * projection, normal.z * projection
            ))
            if candidate.Length > 1e-7:
                direction = candidate.normalize()
                break
    if direction is None:
        direction = App.Vector(1, 0, 0)
        if abs(direction.dot(normal)) > 0.95:
            direction = App.Vector(0, 1, 0)
        projection = direction.dot(normal)
        direction = direction.sub(App.Vector(
            normal.x * projection, normal.y * projection, normal.z * projection
        )).normalize()
    second = normal.cross(direction).normalize()
    return origin, direction, second


def outline_points(shape):
    faces = list(shape.Faces)
    if not faces:
        return [], "bounding_box"
    face = max(faces, key=lambda item: float(item.Area))
    normal = normal_for_face(face)
    origin, axis_x, axis_y = basis_for_face(face, normal)
    points = []
    for edge in face.OuterWire.Edges:
        for point in edge_points(edge):
            delta = point.sub(origin)
            local = App.Vector(delta.dot(axis_x), delta.dot(axis_y), 0)
            if not points or (local.sub(points[-1])).Length > 1e-6:
                points.append(local)
    if len(points) >= 2 and (points[0].sub(points[-1])).Length < 1e-6:
        points.pop()
    if len(points) < 3:
        box = shape.BoundBox
        width = box.XLength if math.isfinite(box.XLength) and 1e-6 < box.XLength < 1e6 else 20.0
        height = box.YLength if math.isfinite(box.YLength) and 1e-6 < box.YLength < 1e6 else 20.0
        points = [
            App.Vector(0, 0, 0),
            App.Vector(width, 0, 0),
            App.Vector(width, height, 0),
            App.Vector(0, height, 0),
        ]
        return points, "bounding_box"
    if any(
        not all(math.isfinite(value) and abs(value) < 1e6 for value in (point.x, point.y))
        for point in points
    ):
        points = [
            App.Vector(0, 0, 0),
            App.Vector(20, 0, 0),
            App.Vector(20, 20, 0),
            App.Vector(0, 20, 0),
        ]
        return points, "bounding_box"
    return points, "largest_face_outline"


def add_outline(sketch, points):
    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        if (end.sub(start)).Length > 1e-7:
            sketch.addGeometry(Part.LineSegment(start, end), False)


def add_metadata(obj, source_path, mode, source_object, outline_mode):
    obj.addProperty("App::PropertyString", "SourceModel", "AI Redesign")
    obj.SourceModel = str(source_path)
    obj.addProperty("App::PropertyString", "RedrawMode", "AI Redesign")
    obj.RedrawMode = mode
    obj.addProperty("App::PropertyString", "SourceObject", "AI Redesign")
    obj.SourceObject = source_object
    obj.addProperty("App::PropertyString", "OutlineMethod", "AI Redesign")
    obj.OutlineMethod = outline_mode


def make_sketch_file(path, source_path, points, source_object, outline_mode, overwrite):
    if path.exists() and not overwrite:
        return False
    document = App.newDocument("AISketch")
    sketch = document.addObject("Sketcher::SketchObject", "RedrawSketch")
    sketch.Label = "AI redraw sketch"
    add_outline(sketch, points)
    add_metadata(sketch, source_path, "sketch", source_object, outline_mode)
    document.recompute()
    document.saveAs(str(path))
    App.closeDocument(document.Name)
    return True


def make_partial_file(path, stl_path, step_path, source_path, points,
                      source_object, outline_mode, source_bbox, overwrite):
    if path.exists() and not overwrite:
        return False
    document = App.newDocument("AIPartialDesign")
    body = document.addObject("PartDesign::Body", "PartialDesignBody")
    body.Label = "AI partial design"
    sketch = body.newObject("Sketcher::SketchObject", "RedrawSketch")
    sketch.Label = "AI redraw base sketch"
    add_outline(sketch, points)
    add_metadata(sketch, source_path, "partial_design_sketch", source_object, outline_mode)

    wire_points = list(points) + [points[0]]
    try:
        wire = Part.makePolygon(wire_points)
        face = Part.Face(wire)
        size = max(max(point.x for point in points) - min(point.x for point in points),
                   max(point.y for point in points) - min(point.y for point in points))
        depth = max(1.0, min(size * 0.18, 20.0))
        partial_shape = face.extrude(App.Vector(0, 0, depth))
    except Exception:
        raw_width = source_bbox[0] if source_bbox else 20.0
        raw_height = source_bbox[1] if source_bbox else 20.0
        width = raw_width if math.isfinite(raw_width) and 1e-6 < raw_width < 1e6 else 20.0
        height = raw_height if math.isfinite(raw_height) and 1e-6 < raw_height < 1e6 else 20.0
        width = max(1.0, width)
        height = max(1.0, height)
        depth = max(1.0, min(max(width, height) * 0.18, 20.0))
        partial_shape = Part.makeBox(width, height, depth)

    feature = body.newObject("PartDesign::Feature", "PartialDesign")
    feature.Label = "AI partial design feature"
    feature.Shape = partial_shape
    add_metadata(feature, source_path, "partial_design", source_object, outline_mode)
    feature.addProperty("App::PropertyLength", "DesignDepth", "AI Redesign")
    feature.DesignDepth = partial_shape.BoundBox.ZLength
    sketch.Visibility = False
    document.recompute()
    document.saveAs(str(path))
    try:
        import Mesh
        Mesh.export([feature], str(stl_path))
    except Exception as exc:
        print("WARN STL", path, str(exc))
    try:
        Part.export([feature], str(step_path))
    except Exception as exc:
        print("WARN STEP", path, str(exc))
    App.closeDocument(document.Name)
    return True


def process_model(root, output_dir, source_path, overwrite):
    model_dir, model_id = output_model_dir(root, source_path, output_dir)
    sketch_dir = model_dir / "sketch"
    partial_dir = model_dir / "partial_design"
    sketch_dir.mkdir(parents=True, exist_ok=True)
    partial_dir.mkdir(parents=True, exist_ok=True)

    document = None
    source_object = "none"
    source_shape = None
    source_bbox = None
    try:
        document = App.openDocument(str(source_path))
        obj, source_shape = shape_from_document(document)
        if obj is not None:
            source_object = obj.Name
        if source_shape is not None:
            box = source_shape.BoundBox
            source_bbox = (float(box.XLength), float(box.YLength), float(box.ZLength))
        points, outline_mode = outline_points(source_shape) if source_shape else ([], "bounding_box")
        if len(points) < 3:
            return {"source": str(source_path), "status": "skipped", "reason": "no usable shape"}
    except Exception as exc:
        return {"source": str(source_path), "status": "error", "reason": str(exc)}
    finally:
        if document is not None:
            App.closeDocument(document.Name)

    sketch_path = sketch_dir / (source_path.stem + "_sketch.FCStd")
    partial_path = partial_dir / (source_path.stem + "_partial.FCStd")
    stl_path = partial_dir / (source_path.stem + "_partial.stl")
    step_path = partial_dir / (source_path.stem + "_partial.step")
    make_sketch_file(sketch_path, source_path, points, source_object, outline_mode, overwrite)
    make_partial_file(
        partial_path, stl_path, step_path, source_path, points, source_object,
        outline_mode, source_bbox, overwrite
    )
    return {
        "source": str(source_path),
        "status": "generated",
        "model_id": model_id,
        "sketch": str(sketch_path),
        "partial_design": str(partial_path),
        "stl": str(stl_path),
        "step": str(step_path),
        "outline_method": outline_mode,
    }


def main():
    args = parse_args()
    root = args.root.resolve()
    output_dir = args.output_dir.resolve() if args.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for source_path in source_files(root, output_dir):
        result = process_model(root, output_dir, source_path, args.overwrite)
        results.append(result)
        print(result["status"].upper(), source_path, result.get("reason", ""))
    manifest = (output_dir / "manifest.json") if output_dir else root / "AI_redraw_manifest.json"
    manifest.write_text(json.dumps(results, ensure_ascii=True, indent=2), encoding="utf-8")
    generated = sum(item["status"] == "generated" for item in results)
    print("SUMMARY", "sources=", len(results), "generated=", generated, "manifest=", manifest)
    return 0 if generated == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
