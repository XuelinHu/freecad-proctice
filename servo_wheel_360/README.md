# 360 Degree Servo Wheel

This folder contains a parametric FreeCAD model for a 3D-printable wheel that
mounts to a common continuous-rotation hobby servo.

## Files

- `make_servo_wheel.py`: FreeCAD Python generation script.
- `make_servo_wheel_history.py`: FreeCAD Python script that keeps visible modeling steps in the object tree.
- `make_servo_wheel_partdesign.py`: PartDesign/Sketcher script with editable sketches, pads, and pockets.
- `output/servo_wheel_360.FCStd`: editable FreeCAD model.
- `output/servo_wheel_360.step`: CAD exchange file.
- `output/servo_wheel_360.stl`: slicer-ready mesh.
- `output/servo_wheel_360_history.FCStd`: FreeCAD model with construction history objects.
- `output/servo_wheel_360_history.step`: CAD exchange file from the history model.
- `output/servo_wheel_360_history.stl`: slicer-ready mesh from the history model.
- `output/servo_wheel_360_partdesign.FCStd`: FreeCAD model with `Body`, `Sketch`, `Pad`, and `Pocket` features.
- `output/servo_wheel_360_partdesign.step`: CAD exchange file from the PartDesign model.
- `output/servo_wheel_360_partdesign.stl`: slicer-ready mesh from the PartDesign model.

## Default Dimensions

- Wheel diameter: 64 mm
- Wheel width: 12 mm
- Front hub diameter: 27 mm
- Front hub height: 4 mm
- Servo horn pocket diameter: 20.8 mm
- Servo horn pocket depth: 2.6 mm
- Center screw clearance hole: 2.4 mm
- Four horn screw holes: 2.2 mm diameter, 15 mm bolt circle

## Recommended Mounting

Use the original plastic or metal servo horn that came with the servo. Insert
the horn into the round front pocket, then fasten the horn to the printed wheel
through the four small holes. The servo horn keeps the factory spline fit, which
is usually stronger and more accurate than printing the spline directly.

If your horn hole pattern is different, change these parameters near the top of
`make_servo_wheel.py`:

```python
"servo_horn_pocket_diameter": 20.8,
"servo_horn_pocket_depth": 2.6,
"horn_screw_hole_diameter": 2.2,
"horn_screw_bolt_circle_diameter": 15.0,
```

## Regenerate

```powershell
& 'D:\Program Files (x86)\FreeCAD_weekly-2025.12.31-Windows-x86_64-py311\bin\python.exe' `
  'D:\workspace\things\freecad-proctice\servo_wheel_360\make_servo_wheel.py'
```

## Printing Notes

- Print flat on the wheel side face.
- PLA or PETG is fine for a first test; TPU can be added later as a tire ring.
- Use 4 or more walls and at least 35 percent infill for a small robot wheel.
- Test-fit the servo horn before final assembly. If the pocket is too tight,
  increase `servo_horn_pocket_diameter` by 0.2 to 0.4 mm.
