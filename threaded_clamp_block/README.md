# 30x30x50 threaded clamp block

## Geometry

- Main block: X=30 mm, Y=30 mm, Z=50 mm.
- Rectangular slot opens from the Y-Z side face and cuts along the X axis.
- Slot spans the full X width.
- Slot Y range: 5-25 mm, width 20 mm.
- Slot Z range: 15-50 mm.
- The lower side near the X-Y plane keeps a 15 mm solid connection.
- The slot is fully open through X, but not through the full Z height.
- Screw hole starts from the X-Z front face and cuts along the Y axis.
- Blind screw hole diameter: 10 mm.
- Blind screw hole Y range: 0-28 mm.
- Rear face is not pierced; 2 mm material remains.
- Internal thread groove is added mainly in the rear support section.
- A matching hand knob bolt with external thread is also generated.

## Output

```text
D:\workspace\things\freecad-proctice\threaded_clamp_block\output\threaded_clamp_block_body.FCStd
D:\workspace\things\freecad-proctice\threaded_clamp_block\output\threaded_clamp_block_body.step
D:\workspace\things\freecad-proctice\threaded_clamp_block\output\threaded_clamp_block_body.stl
D:\workspace\things\freecad-proctice\threaded_clamp_block\output\threaded_clamp_block_bolt.FCStd
D:\workspace\things\freecad-proctice\threaded_clamp_block\output\threaded_clamp_block_bolt.step
D:\workspace\things\freecad-proctice\threaded_clamp_block\output\threaded_clamp_block_bolt.stl
D:\workspace\things\freecad-proctice\threaded_clamp_block\output\threaded_clamp_block_assembly.FCStd
D:\workspace\things\freecad-proctice\threaded_clamp_block\output\threaded_clamp_block_assembly.step
```

## Regenerate

```powershell
& 'D:\Program Files (x86)\FreeCAD_weekly-2025.12.31-Windows-x86_64-py311\bin\python.exe' `
  'D:\workspace\things\freecad-proctice\threaded_clamp_block\make_threaded_clamp_block.py'
```
