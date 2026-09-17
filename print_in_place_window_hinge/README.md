# 一体打印窗式合页

这是一个“打印即装配”的活动合页。两片叶板、连续转轴和交错轴套包含在同一个 STL 中，打印时已经组合在一起，不需要打印后安装销轴、螺丝或扣合两个零件。

模型展开后平放打印。内部连续转轴属于左叶板，右叶板的四段轴套围绕转轴打印，并通过预留间隙保持可活动。

## 默认尺寸

- 合页长度：80 mm
- 展开总宽度：约 80 mm
- 叶板厚度：3.2 mm
- 轴套外径：9 mm
- 内部转轴直径：4 mm
- 径向活动间隙：0.45 mm
- 轴向活动间隙：0.50 mm
- 每片叶板安装孔：2 个，孔径 4.8 mm

## 推荐打印文件

- `output/print_in_place_window_hinge.stl`：单个完整合页，一次打印成型。
- `output/print_in_place_window_hinge_pair.stl`：两个完整合页排在同一平台上，一次打印两个。
- `output/print_in_place_window_hinge.FCStd`：FreeCAD 可编辑文件，能分别查看两个活动部分。
- 同名 STEP 文件可用于其他 CAD 软件继续修改。

## 打印建议

- 0.4 mm 喷嘴，0.2 mm 层高。
- 3 道或 4 道墙，20% 至 35% 填充。
- 按 STL 当前方向平放，不要旋转成竖直方向。
- 通常不需要支撑；切片软件中不要在转轴间隙里自动生成支撑。
- PLA、PETG 均可，PETG 打印温度过高时更容易把活动间隙粘住。

打印完成并完全冷却后，握住两片叶板轻轻反向扭动，使间隙中的少量拉丝断开，再逐步开合。不要使用锤子冲击转轴。

如果打印机尺寸偏差较大，可把脚本顶部的 `radial_clearance` 从 `0.45` 增大到 `0.50` 或 `0.55` 后重新生成。

## 重新生成

```powershell
& 'D:\Program Files (x86)\FreeCAD_weekly-2025.12.31-Windows-x86_64-py311\bin\python.exe' `
  'D:\workspace\things\freecad-proctice\print_in_place_window_hinge\make_window_hinge.py'
```
