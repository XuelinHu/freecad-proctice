# ESP32 四轮舵机车底盘

这是一个可导入 Fusion 360 的小型四轮转向车初版。模型由 FreeCAD 脚本生成，尺寸单位为 mm。

## 初版假设

- 车轮：沿用仓库中的 64 mm x 12 mm 车轮，使用原装舵机臂和 4 颗小螺钉连接。
- 舵机：SG90/MG90S 尺寸级别，每个车轮一个舵机安装位。
- 主控：55 x 28 mm ESP32 DevKit 外形包络，托盘带 4 个 M2.5 级安装柱。
- 底盘：140 x 110 mm，底部 4 mm，侧壁 24 mm；上盖可拆并预留 USB、排线和散热槽。

## 生成

```powershell
& 'D:\Program Files (x86)\FreeCAD_weekly-2025.12.31-Windows-x86_64-py311\bin\python.exe' `
  'D:\workspace\things\freecad-proctice\esp32_servo_rover\make_esp32_servo_rover.py'
```

输出位于 `output/`：

- `esp32_servo_rover_assembly.FCStd`：可编辑总成。
- `esp32_servo_rover_assembly.step`：导入 Fusion 360 的总成。
- `chassis_lower_body.step`、`chassis_lid.step`、`esp32_mounting_tray.step`：主要可打印件。
- `wheel_01.step` 到 `wheel_04.step`、`servo_bracket_01.step` 到 `servo_bracket_04.step`：四组重复零件。

## Fusion 360 导入

在 Fusion 360 中选择 `File > Open > Open from my computer`，导入 `output/esp32_servo_rover_assembly.step`。导入后建议把 `SG90 servo envelope` 替换为你手上的实际舵机 CAD，并用实际 ESP32 板测量 USB 口、排针和安装孔位置。

## 需要实物确认的尺寸

1. 舵机具体型号及外壳尺寸、耳朵孔距、输出轴高度。
2. ESP32 型号（普通 DevKit、ESP32-S3、带屏或带扩展板）及安装孔距。
3. 电池、电机驱动板和电源开关的位置；当前模型只预留 ESP32 和走线空间。
