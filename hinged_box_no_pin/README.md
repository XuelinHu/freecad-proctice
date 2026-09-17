# 双合页免插销收纳盒

这是一个可直接用于 FDM 3D 打印的掏空盒体与上盖。盒体后侧带两个一体成型转轴，盖子带两个 C 形弹性扣环；打印完成后把盖子扣到转轴上即可，不需要购买或手工插入销轴、螺丝等零件。

## 默认尺寸

- 盒体外尺寸：120 × 80 × 45 mm
- 盒体壁厚：2.4 mm
- 盒体底厚：2.4 mm
- 盖板厚度：2.4 mm
- 盖子配合间隙：0.35 mm
- 合页数量：2
- 一体转轴直径：4.4 mm
- 扣环转动间隙：0.35 mm

所有尺寸集中在 `make_hinged_box.py` 顶部的 `PARAMS` 中，可以按打印机精度调整。

## 打印文件

- `output/hinged_box_print_plate.stl`：推荐使用，盒体和盖子已在同一打印平台上摆好。
- `output/hinged_box_body.stl`：仅打印盒体，底面已贴平台。
- `output/hinged_box_lid.stl`：仅打印盖子，盖子外表面已贴平台。
- `output/hinged_box_assembly.FCStd`：FreeCAD 闭合装配预览。
- 同名 `STEP` 文件可用于继续修改。

## 打印和装配

建议使用 0.4 mm 喷嘴、0.2 mm 层高、3 道壁、15% 至 25% 填充。盒体和盖子均按无需支撑的方向输出；合页转轴与盒体是一体结构。

打印完成并冷却后，将盖子的两个 C 形扣环分别对准盒体后侧的两个转轴，从后侧均匀按压扣入。首次转动可能略紧，往复开合几次即可。不要沿合页轴线横向硬推，以免折断扣环。

如果打印机尺寸误差较大，可将 `hinge_clearance` 从 `0.35` 调到 `0.45`，或将 `clip_mouth` 从 `4.05` 调到 `4.15` 后重新生成。

## 重新生成

```powershell
& 'D:\Program Files (x86)\FreeCAD_weekly-2025.12.31-Windows-x86_64-py311\bin\python.exe' `
  'D:\workspace\things\freecad-proctice\hinged_box_no_pin\make_hinged_box.py'
```
