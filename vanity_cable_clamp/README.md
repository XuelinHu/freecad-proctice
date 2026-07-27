# 化妆台布线夹具

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
D:\workspace\things\freecad-proctice\vanity_cable_clamp\output\vanity_cable_clamp_body.FCStd
D:\workspace\things\freecad-proctice\vanity_cable_clamp\output\vanity_cable_clamp_body.step
D:\workspace\things\freecad-proctice\vanity_cable_clamp\output\vanity_cable_clamp_body.stl
```

旋钮螺杆：

```text
D:\workspace\things\freecad-proctice\vanity_cable_clamp\output\vanity_cable_clamp_knob_screw.FCStd
D:\workspace\things\freecad-proctice\vanity_cable_clamp\output\vanity_cable_clamp_knob_screw.step
D:\workspace\things\freecad-proctice\vanity_cable_clamp\output\vanity_cable_clamp_knob_screw.stl
```

装配体：

```text
D:\workspace\things\freecad-proctice\vanity_cable_clamp\output\vanity_cable_clamp_assembly.FCStd
D:\workspace\things\freecad-proctice\vanity_cable_clamp\output\vanity_cable_clamp_assembly.step
```

## 重新生成

```powershell
& 'D:\Program Files (x86)\FreeCAD_weekly-2025.12.31-Windows-x86_64-py311\bin\python.exe' `
  'D:\workspace\things\freecad-proctice\vanity_cable_clamp\make_vanity_cable_clamp.py'
```

## 打印建议

- 夹具主体建议侧躺打印，让 C 型侧面贴近打印平台。
- 旋钮螺杆当前是打印演示结构；如果需要更强夹紧力，建议后续改为嵌入 M6/M8 金属螺丝。
- 压盘与桌板接触面可以后续贴一片软胶垫，减少压痕和打滑。
