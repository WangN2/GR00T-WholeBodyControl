# 动作参考数据

本页介绍 C++ 部署栈所使用的动作参考数据格式、如何创建自定义参考动作，以及如何验证和部署它们。

部署栈会播放预加载的**参考动作**——即策略跟踪的关节位置、速度和全身运动学序列。这些动作以 CSV 文件形式存储在结构化文件夹层级中。你可以从任何来源生成它们（动作捕捉、仿真、重定向管线等），只要输出符合下面描述的格式即可。

---

## 文件夹结构

每个动作数据集是一个目录，包含每个动作片段一个子文件夹。C++ 读取器（`MotionDataReader`）在启动时自动发现所有子文件夹。

```
reference/my_motions/
├── motion_name_1/
│   ├── joint_pos.csv          # 关节位置
│   ├── joint_vel.csv          # 关节速度
│   ├── body_quat.csv          # 身体四元数
│   ├── body_pos.csv           # 身体位置
│   ├── metadata.txt           # 身体部位索引
│   ├── body_lin_vel.csv       # 身体线速度
│   ├── body_ang_vel.csv       # 身体角速度
│   ├── smpl_joint.csv         # SMPL 关节位置
│   ├── smpl_pose.csv          # SMPL 身体姿态
│   └── info.txt               # 详细动作信息
└── motion_name_2/
    └── ...
```

C++ 读取器扫描基础目录中的子文件夹，将每个子文件夹读取为一个动作，并验证该文件夹内所有文件的帧数一致性。

---

## 文件格式

C++ 读取器加载存在的文件，缺失的文件会被优雅地跳过。然而，**在实践中**，大多数策略需要：
- `joint_pos.csv`、`joint_vel.csv` —— 用于基于关节的动作跟踪
- `body_quat.csv` —— 用于锚点方向观测（如果采集观测时缺失此文件，控制循环将停止）
- `body_pos.csv` —— 用于航向计算和 VR 3 点观测
- `metadata.txt` —— 当存在身体数据时，用于身体部位索引对齐

一个动作必须**至少有一个有效的数据源**（关节、身体或 SMPL）才能在启动时加载。

### `joint_pos.csv`

**IsaacLab 顺序**的关节位置（29 个关节）。每行是一个 50 Hz 的时间步。第一行为表头。

| 列 | 描述 |
|--------|-------------|
| `joint_0` … `joint_28` | 关节角度，弧度（IsaacLab 顺序） |

形状：`(timesteps, 29)`

### `joint_vel.csv`

**IsaacLab 顺序**的关节速度（29 个关节）。每行是一个 50 Hz 的时间步。帧数必须与 `joint_pos.csv` 匹配。

| 列 | 描述 |
|--------|-------------|
| `joint_vel_0` … `joint_vel_28` | 关节角速度，rad/s（IsaacLab 顺序） |

形状：`(timesteps, 29)`

### `body_pos.csv`

**世界坐标系**中的身体部位位置。每个身体贡献 3 列（x, y, z）。身体数量因动作而异。用于航向计算和 VR 3 点观测。

| 列 | 描述 |
|--------|-------------|
| `body_0_x`, `body_0_y`, `body_0_z` | 身体 0（根/骨盆）的位置，单位：米 |
| `body_1_x`, `body_1_y`, `body_1_z` | 身体 1 的位置，单位：米 |
| … | … |

形状：`(timesteps, num_bodies * 3)`

**我们假设根/骨盆始终在列组 0**（前 3 列）。

### `body_quat.csv`

**世界坐标系**中的身体部位方向，以四元数表示。每个身体贡献 4 列。四元数顺序为 **(w, x, y, z)**。**大多数策略都需要** —— `motion_anchor_orientation` 观测（大多数策略使用）如果此文件缺失，将导致控制系统停止。

| 列 | 描述 |
|--------|-------------|
| `body_0_w`, `body_0_x`, `body_0_y`, `body_0_z` | 身体 0（根/骨盆）的四元数 |
| `body_1_w`, `body_1_x`, `body_1_y`, `body_1_z` | 身体 1 的四元数 |
| … | … |

形状：`(timesteps, num_bodies * 4)`

**我们假设根/骨盆始终在列组 0**（前 4 列）。

```{note}
`body_quat.csv` 中的身体数量可以与 `body_pos.csv` 不同。C++ 读取器独立跟踪它们（`num_bodies` 与 `num_body_quaternions`）。然而，根身体（第一个列组）必须存在，航向计算才能工作。如果不需要根位置，可以使用零值填充。
```

### `metadata.txt`

包含**身体部位索引**数组，将 `body_pos.csv` / `body_quat.csv` 中的每个列组映射到对应的 IsaacLab 身体索引。当存在身体数据时需要此文件。

```
Metadata for: motion_name
==============================

Body part indexes:
[ 0  4 10 18  5 11 19  9 16 22 28 17 23 29]

Total timesteps: 497
```

C++ 读取器解析 `Body part indexes:` 后跟一行括号内的空格分隔整数。例如，`[0, 4, 10, 18, ...]` 表示列组 0 → IsaacLab 身体 0（骨盆/根），列组 1 → 身体 4，依此类推。

对于**仅根**动作（仅 1 个身体），使用：

```
Body part indexes:
[0]
```

### `body_lin_vel.csv` / `body_ang_vel.csv`

世界坐标系中的身体部位线速度和角速度。布局与 `body_pos.csv` 相同（每个身体 3 列）。身体数量必须与 `body_pos.csv` 匹配。

### `smpl_joint.csv`

SMPL 关节位置（通常 24 个关节 × 3 个坐标）。每行是一个时间步。

形状：`(timesteps, num_smpl_joints * 3)`

### `smpl_pose.csv`

SMPL 身体姿态，以轴角表示（通常 21 个姿态 × 3 个坐标）。每行是一个时间步。

形状：`(timesteps, num_smpl_poses * 3)`

```{note}
**当前的参考动作跟踪管线仅使用基于关节的跟踪**（编码器模式 0）。要启用基于 SMPL 的参考跟踪（编码器模式 2），你需要修改代码以检测 SMPL 数据的存在并相应地切换编码器模式。
```

### `info.txt`

人类可读的摘要，包含形状、数据类型和数值范围。C++ 栈不读取此文件 —— 仅用于文档说明。

---

## 创建自定义参考动作

你可以从任何来源生成参考动作 —— 唯一要求是生成上述格式的 CSV 文件。常见方法：

1. **动作捕捉重定向** —— 将人体动作捕捉重定向到 G1 模型，导出关节位置/速度和身体运动学。
2. **仿真录制** —— 以 50 Hz 从 IsaacLab 或 MuJoCo 仿真中录制关节状态。
3. **程序生成** —— 以编程方式创建关节轨迹。

### 所需最小文件

为 SONIC 策略创建可用动作的**最小**文件集：

1. **`joint_pos.csv`** —— 29 个关节位置（IsaacLab 顺序），表头 + 每时间步一行
2. **`joint_vel.csv`** —— 29 个关节速度（IsaacLab 顺序），表头 + 每时间步一行
3. **`body_quat.csv`** —— 根四元数（w, x, y, z），表头 + 每时间步一行
4. **`body_pos.csv`** —— 根位置（x, y, z），表头 + 每时间步一行。如果不需要位置跟踪，可以全部填零。
5. **`metadata.txt`** —— 身体部位索引（仅根动作为 `[0]`）

**示例文件：**

`joint_pos.csv`：
```
joint_0,joint_1,joint_2,...,joint_28
0.128441,0.102713,0.020116,...,0.045231
0.130124,0.104532,0.021045,...,0.046112
...
```

`joint_vel.csv`：
```
joint_vel_0,joint_vel_1,...,joint_vel_28
0.143671,0.143864,...,0.012345
...
```

`body_quat.csv`（仅根四元数）：
```
body_0_w,body_0_x,body_0_y,body_0_z
0.999123,0.000456,0.001234,0.040567
...
```

`body_pos.csv`（根位置，可以全部为零）：
```
body_0_x,body_0_y,body_0_z
0.000000,0.000000,0.000000
...
```

`metadata.txt`：
```
Metadata for: my_motion
==============================

Body part indexes:
[0]

Total timesteps: 100
```

这给你一个**仅根**动作（1 个身体 = 骨盆/根），大多数策略都可以跟踪。


### 提供的转换脚本

包含一个便捷的脚本 `reference/convert_motions.py`，用于将 **joblib pickle**（`.pkl`）文件转换为此格式。这只是众多可能来源之一 —— 你可以使用任何能生成正确 CSV 输出的工具或管线。

```bash
cd gear_sonic_deploy
python reference/convert_motions.py <pkl_file> [output_dir]
```

pickle 应该是一个字典，其中每个键是动作名称，每个值包含 `joint_pos`、`joint_vel`、`body_pos_w`、`body_quat_w`、`body_lin_vel_w`、`body_ang_vel_w`、`_body_indexes` 和 `time_step_total`。

---

## 验证参考动作

### MuJoCo 可视化

使用包含的可视化工具检查动作在 G1 模型上是否正确：

```bash
cd gear_sonic_deploy
python visualize_motion.py --motion_dir reference/my_motions/motion_name_1/
```

**控制：**
- **空格键**：暂停/恢复播放
- **R**：重置到第 0 帧
- **,** / **.**：后退/前进一帧
- **-** / **=**：上一个/下一个动作（如果加载了多个）

验证内容：
- 机器人直立站立，不会穿入地面
- 关节角度看起来合理（没有极端姿态）
- 动作播放流畅，没有突然跳跃
- 身体位置跟踪预期轨迹

---

## 使用参考动作

### 使用 `deploy.sh`

通过 `--motion-data` 传入动作目录：

```bash
./deploy.sh --motion-data reference/my_motions/ sim
```

或使用默认动作（在 `deploy.sh` 中配置）：

```bash
./deploy.sh sim
```

### 运行时

部署后，使用键盘或游戏手柄浏览和播放动作：

- **T**：播放当前动作
- **N / P**：下一个/上一个动作
- **R**：从第 0 帧重新开始

完整控制参考请参阅[键盘教程](../tutorials/keyboard.md)。

---

## 验证规则

C++ 读取器在加载时执行以下验证：

- **帧数一致性**：动作文件夹内的所有 CSV 文件必须具有相同的行数（不包括表头）。不匹配会导致动作被跳过并报错。
- **关节数一致性**：`joint_pos.csv` 和 `joint_vel.csv` 必须具有相同的列数。
- **身体数一致性**：`body_lin_vel.csv` 和 `body_ang_vel.csv` 必须与 `body_pos.csv` 具有相同的身体列数。
- **至少一个数据源**：动作必须至少有一些有效数据（关节、身体或 SMPL）才能被加载。
- **元数据解析**：`metadata.txt` 文件必须包含 `Body part indexes:` 行，后跟一个括号内的整数列表，动作才能具有正确的身体部位对齐。

如果动作验证失败，它将被跳过并打印警告。部署将继续处理剩余的有效动作。

---

## 注意事项

- 所有数据频率为 **50 Hz**（每个时间步 0.02 秒），与控制循环频率匹配。
- 关节顺序遵循 **IsaacLab 约定**（不是 MuJoCo）。C++ 栈在发送电机命令时在内部处理转换。
- 身体四元数使用 **(w, x, y, z)** 顺序。
- 第一个身体（列组 0）必须对应根/骨盆，航向计算和锚点方向观测才能正确工作。
- 虽然 C++ 读取器可以在没有 `body_quat.csv` 的情况下加载动作，但如果策略观测 `motion_anchor_orientation`（大多数策略都会），控制循环在采集观测时会失败。
- CSV 文件的第一行必须有一个**表头行** —— C++ 读取器跳过每个 CSV 的第一行。
- 数值在内部以 `double` 精度解析。
