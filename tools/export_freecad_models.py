#!/usr/bin/env python
"""Batch-export FreeCAD documents to mesh/CAD exchange formats.

Run with FreeCADCmd, for example:
  FreeCADCmd.exe tools/export_freecad_models.py . --formats stl step
"""

from __future__ import annotations

try:
    import FreeCAD as App  # type: ignore
    import Import  # type: ignore
    import Mesh  # type: ignore
except ImportError as exc:  # pragma: no cover - requires FreeCAD runtime
    raise SystemExit(
        "This script must be run with FreeCADCmd or a Python runtime that can "
        "import FreeCAD modules."
    ) from exc


SUPPORTED_FORMATS = {"stl", "step", "stp", "iges", "igs"}


def iter_documents(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.FCStd")
        if ".git" not in path.parts and "__pycache__" not in path.parts
    )


def exportable_objects(doc):
    objects = []
    for obj in doc.Objects:
        shape = getattr(obj, "Shape", None)
        if shape is None:
            continue
        if getattr(shape, "isNull", lambda: True)():
            continue
        objects.append(obj)
    return objects


def output_path(source: Path, fmt: str) -> Path:
    suffix = ".step" if fmt == "stp" else ".iges" if fmt == "igs" else f".{fmt}"
    return source.with_suffix(suffix)


def export_document(source: Path, formats: list[str], overwrite: bool) -> list[Path]:
    doc = App.openDocument(str(source))
    exported: list[Path] = []
    try:
        doc.recompute()
        objects = exportable_objects(doc)
        if not objects:
            print(f"SKIP no exportable shapes: {source}")
            return exported

        for fmt in formats:
            target = output_path(source, fmt)
            if target.exists() and not overwrite:
                print(f"SKIP exists: {target}")
                continue
            if fmt == "stl":
                Mesh.export(objects, str(target))
            elif fmt in {"step", "stp", "iges", "igs"}:
                Import.export(objects, str(target))
            else:
                raise ValueError(f"Unsupported format: {fmt}")
            exported.append(target)
            print(f"EXPORTED {target}")
    finally:
        App.closeDocument(doc.Name)
    return exported


def main() -> int:
    import argparse
    from pathlib import Path
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", help="Repository/model root")
    parser.add_argument(
        "--formats",
        nargs="+",
        default=["stl", "step"],
        help="Any of: stl step stp iges igs",
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    formats = [fmt.lower().lstrip(".") for fmt in args.formats]
    unsupported = sorted(set(formats) - SUPPORTED_FORMATS)
    if unsupported:
        raise SystemExit(f"Unsupported formats: {', '.join(unsupported)}")

    root = Path(args.root).resolve()
    docs = iter_documents(root)
    if not docs:
        print(f"No .FCStd files found under {root}")
        return 0

    failures = 0
    for source in docs:
        try:
            export_document(source, formats, args.overwrite)
        except Exception as exc:  # pragma: no cover - reports per-file failures
            failures += 1
            print(f"FAILED {source}: {exc}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
