# SONIC 数据集梳理与汇总

> 文档基于 GR00T-WholeBodyControl 仓库（2026.04 release）整理，涵盖训练数据集、数据采集（VLA）格式、数据后处理及配套工具。

---

## 一、数据集总览

SONIC 项目涉及两类核心数据集：

| 类型 | 名称 | 用途 | 规模 |
|------|------|------|------|
| **训练数据集** | BONES-SEED | 仿真环境中 PPO + 辅助损失训练 | 142,220 条运动片段，~288 小时 |
| **采集数据集** | LeRobot VLA Dataset | 真机/仿真遥操作演示数据，用于 Isaac-GR00T 后训练 | 按会话录制，逐条 episode |

---

## 二、训练数据集：BONES-SEED

### 2.1 数据集简介

BONES-SEED（Skeletal Everyday Embodiment Dataset）是由 [Bones Studio](https://bones.studio/datasets) 开源的大规模人体运动数据集，也是 SONIC 训练数据的核心来源。

| 属性 | 数值 |
|------|------|
| **总运动数** | 142,220（71,132 原始 + 71,088 镜像） |
| **总时长** | ~288 小时（@ 120 fps） |
| **演员数** | 522 名（253 女 / 269 男） |
| **年龄范围** | 17 – 71 岁 |
| **身高范围** | 145 – 199 cm |
| **体重范围** | 38 – 145 kg |
| **标注** | 每条运动最多 6 条自然语言描述 + 时序分段标签 + 骨骼元数据 |

### 2.2 运动类别分布

| 类别 | 数量 | 说明 |
|------|------|------|
| Locomotion | 74,488 | 行走、慢跑、跳跃、攀爬、爬行、转向及过渡动作 |
| Communication | 21,493 | 手势、指向、注视、交流性肢体语言 |
| Interactions | 14,643 | 物体操作、抓取放置、搬运、工具使用 |
| Dances | 11,006 | 多风格全身舞蹈表演 |
| Gaming | 8,700 | 受游戏启发的动作和动态运动 |
| Everyday | 5,816 | 家务任务、进食、坐卧、阅读等日常活动 |
| Sport | 3,993 | 体育运动和专项竞技动作 |
| Other | 2,081 | 特技、武术等边缘动作 |

### 2.3 数据格式

每条运动提供三种格式：

1. **SOMA Proportional (BVH)** — 保留原始演员身体比例的骨骼数据
2. **SOMA Uniform (BVH)** — 标准化骨骼，便于批量处理
3. **Unitree G1 (CSV)** — 已重定向到 Unitree G1 人形机器人的关节角度轨迹

### 2.4 与 SONIC 训练的关系

BONES-SEED 是 SONIC 训练数据的**主要子集**：

- **Unitree G1 关节轨迹** — 已重定向为 MuJoCo 兼容格式，可直接用于运动跟踪训练
- **广泛的运动覆盖** — 涵盖 8 大类、20 子类的全身运动
- **丰富的语言标注** — 支持语言条件策略学习
- **时序分段标签** — 支持结构化技能分解
- **表演者多样性** — 522 名演员覆盖多种体型、年龄和动作风格

### 2.5 下载方式

```bash
# 使用 Hugging Face CLI
pip install huggingface_hub
huggingface-cli download bones-studio/seed --repo-type dataset --local-dir ./bones-seed

# 或使用 Python
from huggingface_hub import snapshot_download
snapshot_download(repo_id="bones-studio/seed", repo_type="dataset", local_dir="./bones-seed")
```

### 2.6 过滤后规模

SONIC 训练前会对 BONES-SEED 进行可执行性过滤：

- **原始规模**：142,220 条
- **过滤后**：~130,000 条（约 **8.7%** 的不可执行动作被剔除）
- **过滤后时长**：~288 小时（有效数据）

---

## 三、VLA 数据采集数据集

### 3.1 采集架构

数据采集基于 **LeRobot v2.1** 格式，通过 ZMQ 从三个数据源同步获取数据：

```text
    Workstation (offboard)                           Robot (onboard)
┌──────────────────────┐  ┌──────────────────────┐  ┌───────────────┐
│  C++ deploy          │  │  pico_manager        │  │  Camera       │
│  (zmq_output_handler)│  │  _thread_server.py   │  │  server       │
│                      │  │                      │  │  (OAK cameras)│
│  port 5557           │  │  port 5556           │  │  port 5555    │
│  topics: g1_debug    │  │  topic: pose         │  │  (JPEG/ZMQ)   │
│          robot_config│  │  (SMPL body params)  │  │               │
└──────────┬───────────┘  └──────────┬────────────┘  └──────┬────────┘
           │                         │                       │
           └────────────┬────────────┘───────────────────────┘
                        │              (network)
               ┌────────▼────────┐
               │  run_data_      │
               │  exporter.py    │
               │  (workstation)  │
               │                 │
               │  LeRobot dataset│
               │  (parquet + mp4)│
               └─────────────────┘
```

| 数据源 | 运行位置 | ZMQ Topic / 端口 | 提供内容 |
|--------|----------|------------------|----------|
| C++ deployment | Workstation | `g1_debug` @ 5557 | 关节位置、速度、IMU 四元数 |
| C++ deployment | Workstation | `robot_config` @ 5557 | 启动时一次性机器人配置 |
| PICO teleop streamer | Workstation | `pose` @ 5556 | SMPL 人体参数（遥操作目标姿态） |
| Camera server | Robot (Jetson) | TCP @ 5555 | JPEG 压缩图像（ego view + 可选手腕相机） |

### 3.2 采集参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 采集频率 | **50 Hz** | 数据导出器主循环频率 |
| 图像分辨率 | **480 × 640** | ego view 和 wrist view 统一尺寸 |
| 视频编码 | **H.264** | MP4 容器存储 |
| 语言任务提示 | `"demo"` | 每条 episode 绑定一条自然语言描述 |
| 输出根目录 | `outputs/` | 数据集保存路径 |

### 3.3 存储格式（LeRobot v2.1）

数据集保存在 `outputs/<dataset-name>/` 下：

```text
outputs/2026-04-03-14-30-00/
├── data/
│   └── chunk-000/
│       ├── episode_000000.parquet    # 表格数据（关节状态、动作、标注等）
│       ├── episode_000001.parquet
│       └── ...
├── videos/
│   ├── observation.images.ego_view/
│   │   ├── episode_000000.mp4        # H264 编码的 ego 相机视频
│   │   └── ...
│   ├── observation.images.left_wrist/   # （仅启用 --record-wrist-cameras）
│   └── observation.images.right_wrist/  # （同上）
└── meta/
    ├── info.json                     # 数据集元数据（fps, features, sizes）
    ├── modality.json                 # GR00T 模态配置
    ├── episodes.jsonl                # 逐 episode 元数据
    └── tasks.jsonl                   # 任务提示定义
```

### 3.4 核心代码与入口

| 文件 | 作用 |
|------|------|
| `gear_sonic/scripts/run_data_exporter.py` | 数据导出器主程序（无 ROS2 依赖） |
| `gear_sonic/scripts/launch_data_collection.py` | 一体化 tmux 启动器（推荐） |
| `gear_sonic/data/exporter.py` | `Gr00tDataExporter` — LeRobot 格式导出核心类 |
| `gear_sonic/data/features_sonic_vla.py` | Sonic VLA 数据集特征与模态配置定义 |
| `gear_sonic/data/video_writer.py` | 视频写入器 |

### 3.5 快速采集命令

```bash
# 真机采集（推荐 tmux 一键启动）
python gear_sonic/scripts/launch_data_collection.py \
    --camera-host 192.168.123.164 \
    --task-prompt "pick up the cup"

# 仿真采集
python gear_sonic/scripts/launch_data_collection.py --sim

# 带手腕相机
python gear_sonic/scripts/launch_data_collection.py \
    --camera-host 192.168.123.164 \
    --task-prompt "pick up the cup" \
    --record-wrist-cameras

# 手动启动数据导出器（已有其他组件在运行时）
python gear_sonic/scripts/run_data_exporter.py \
    --task-prompt "walk forward" \
    --dataset-name my_session \
    --camera-host 192.168.123.164
```

---

## 四、数据集特征与模态配置

### 4.1 观测（Observation）特征

| 特征键 | 数据类型 | 形状 | 说明 |
|--------|----------|------|------|
| `observation.images.ego_view` | video | (480, 640, 3) | ego 视角 RGB 图像 |
| `observation.images.left_wrist` | video | (480, 640, 3) | 左手腕相机（可选） |
| `observation.images.right_wrist` | video | (480, 640, 3) | 右手腕相机（可选） |
| `observation.state` | float64 | (N,) | 机器人全身关节位置（N = 机器人 DOF 数） |
| `observation.eef_state` | float64 | (14,) | 左右手腕位姿 [pos(3), quat(4)] × 2 |
| `observation.root_orientation` | float64 | (4,) | 底盘朝向四元数 (qw, qx, qy, qz) |
| `observation.projected_gravity` | float64 | (3,) | 体坐标系下的重力向量 |
| `observation.cpp_rotation_offset` | float64 | (4,) | C++ 推理栈的旋转偏移四元数 |
| `observation.init_base_quat` | float64 | (4,) | 初始底盘朝向四元数 |

### 4.2 动作/遥操作（Action / Teleop）特征

| 特征键 | 数据类型 | 形状 | 说明 |
|--------|----------|------|------|
| `action.wbc` | float64 | (N,) | 全身控制策略输出的关节目标位置 |
| `action.motion_token` | float64 | (64,) | SONIC 运动 token（来自 C++ 部署） |
| `teleop.delta_heading` | float64 | (1,) | 航向角增量 |
| `teleop.smpl_joints` | float32 | (72,) | SMPL 人体关节位置（24 joints × 3） |
| `teleop.smpl_pose` | float32 | (63,) | SMPL 姿态参数（轴角形式，21 joints × 3） |
| `teleop.body_quat_w` | float32 | (4,) | SMPL 根节点朝向四元数 |
| `teleop.target_body_orientation` | float32 | (6,) | 目标身体朝向（6D 旋转表示） |
| `teleop.left_hand_joints` | float32 | (7,) | 左手手指关节目标 |
| `teleop.right_hand_joints` | float32 | (7,) | 右手手指关节目标 |
| `teleop.left_wrist_joints` | float32 | (3,) | 左手腕 Roll/Pitch/Yaw |
| `teleop.right_wrist_joints` | float32 | (3,) | 右手腕 Roll/Pitch/Yaw |
| `teleop.smpl_frame_index` | int64 | (1,) | 当前 SMPL 帧索引 |
| `teleop.stream_mode` | int32 | (1,) | 数据流模式标识 |
| `teleop.planner_mode` | int32 | (1,) | 运动规划器模式（locomotion mode） |
| `teleop.planner_movement` | float32 | (3,) | 规划器移动指令 (x, y, z) |
| `teleop.planner_facing` | float32 | (3,) | 规划器朝向指令 (x, y, z) |
| `teleop.planner_speed` | float32 | (1,) | 规划器速度指令 |
| `teleop.planner_height` | float32 | (1,) | 规划器高度指令 |
| `teleop.vr_3pt_position` | float32 | (9,) | VR 3 点跟踪位置 [左腕(3), 右腕(3), 颈部(3)] |
| `teleop.vr_3pt_orientation` | float32 | (18,) | VR 3 点跟踪朝向（6D 旋转 × 3） |

### 4.3 模态配置（modality.json）

`gear_sonic/data/features_sonic_vla.py` 中的 `get_modality_config_sonic_vla()` 定义了四类模态：

- **state**：机器人本体状态（关节组、手腕位姿、根朝向、重力投影、旋转偏移等）
- **action**：遥操作/动作指令（SMPL 参数、规划器指令、VR 3 点跟踪、运动 token 等）
- **video**：视频流（ego view，可选手腕相机）
- **annotation**：标注（自然语言任务描述）

### 4.4 关节分组（State）

状态按以下 7 个肢体组切片，索引由 `RobotModel` 动态推导：

1. `left_leg` — 左腿
2. `right_leg` — 右腿
3. `waist` — 腰部
4. `left_arm` — 左臂
5. `left_hand` — 左手
6. `right_arm` — 右臂
7. `right_hand` — 右手

---

## 五、数据处理与转换工具

### 5.1 数据处理脚本（`gear_sonic/data_process/`）

| 脚本 | 功能 |
|------|------|
| `convert_soma_csv_to_motion_lib.py` | 将 SOMA retargeter 的 CSV/PKL 转换为 SONIC 训练所需的 `motion_lib` PKL 格式 |
| `filter_and_copy_bones_data.py` | 过滤 BONES-SEED 中不可执行的动作片段 |
| `extract_soma_joints_from_bvh.py` | 从 BVH 文件提取 SOMA 骨骼关节数据 |
| `split_pkl_files.py` | 拆分大型 PKL 运动库文件 |

### 5.2 数据集后处理（`gear_sonic/scripts/process_dataset.py`）

该脚本直接操作 LeRobot v2.1 磁盘格式（parquet + mp4），无需训练框架依赖。

**主要功能：**

1. **去除 Stale SMPL 帧**
   - 检测 `teleop.smpl_pose` 全零行（遥操作暂停或 ZMQ 丢帧）
   - 同时去除紧接全零块之前的连续 frozen（与下一帧相同）前导帧
   - 保留未通向全零块的自然 frozen 帧（SMPL 流本身发布率略低的情况）

2. **多数据集合并**
   - 验证所有数据集的 `script_config`（机器人配置）一致后才合并
   - 自动去重任务定义
   - 支持从文本文件批量读取数据集路径

**常用命令：**

```bash
# 单数据集清洗（原地）
python gear_sonic/scripts/process_dataset.py \
    --dataset-path outputs/my_dataset

# 清洗并输出到新目录
python gear_sonic/scripts/process_dataset.py \
    --dataset-path outputs/my_dataset \
    --output-path outputs/my_dataset_cleaned

# 合并多个数据集
python gear_sonic/scripts/process_dataset.py \
    --dataset-path outputs/session1 outputs/session2 outputs/session3 \
    --output-path outputs/merged_dataset

# 跳过 SMPL 清洗，仅合并
python gear_sonic/scripts/process_dataset.py \
    --dataset-path outputs/session1 outputs/session2 \
    --output-path outputs/merged \
    --no-remove-stale-smpl
```

---

## 六、训练配置中的数据路径

SONIC 发布版训练预设（`sonic_release.yaml`）引用以下数据路径：

```yaml
manager_env:
  commands:
    motion:
      motion_lib_cfg:
        motion_file: data/motion_lib_bones_seed/robot_filtered      # G1 关节轨迹
        smpl_motion_file: data/bones_seed_smpl                       # SMPL 参数
        smpl_y_up: true
        adaptive_sampling:
          adp_samp_failure_rate_max_over_mean: 200
        upper_body_augment_prefixes:
          - "2025"
          - "sonic_mixed_walking_running"
          - "sonic_squating_different_height_switching"
          - "sonic_running"
          - "sonic_walking"
          - "sonic_squating_different_height_hold"
          - "sonic_walking_other_style"
          - "balance"
```

**历史帧与未来帧配置：**

| 组件 | 历史帧数 | 未来帧数 | 时间间隔 |
|------|----------|----------|----------|
| Actor / Critic | 10 帧 | — | — |
| G1 / Teleop 未来参考 | — | 10 帧 | 0.1 s |
| SMPL 未来参考 | — | 10 帧 | 0.02 s |

---

## 七、与 Isaac-GR00T 后训练的衔接

采集的 LeRobot 格式数据集可直接用于 [Isaac-GR00T](https://github.com/NVIDIA/Isaac-GR00T) 的后训练流水线：

```bash
# 在 Isaac-GR00T 仓库中
python scripts/gr00t_finetune.py \
    --dataset-path /path/to/outputs/2026-04-03-14-30-00-G1-robot01 \
    ...
```

兼容性要点：

- 输出格式为 **LeRobot v2.1**（parquet + mp4），与 Isaac-GR00T 原生兼容
- `meta/modality.json` 包含 GR00T 特定的模态配置，供后训练时解析
- `meta/info.json` 中的 `script_config` 记录了采集时的机器人配置

---

## 八、关键文件索引

| 路径 | 内容 |
|------|------|
| `gear_sonic/data/exporter.py` | `Gr00tDataExporter` / `Gr00tDatasetMetadata` — LeRobot 格式导出核心 |
| `gear_sonic/data/features_sonic_vla.py` | Sonic VLA 特征定义与模态配置生成 |
| `gear_sonic/data/video_writer.py` | H.264 视频写入器 |
| `gear_sonic/scripts/run_data_exporter.py` | 无 ROS2 依赖的数据采集主程序 |
| `gear_sonic/scripts/launch_data_collection.py` | tmux 一体化采集启动器 |
| `gear_sonic/scripts/process_dataset.py` | 数据集清洗、合并、SMPL 去Stale |
| `gear_sonic/data_process/convert_soma_csv_to_motion_lib.py` | SOMA CSV → motion_lib PKL |
| `gear_sonic/data_process/filter_and_copy_bones_data.py` | BONES-SEED 动作过滤 |
| `gear_sonic/utils/motion_lib/` | 运动库加载与管理（`motion_lib_base.py`, `motion_lib_robot.py`） |
| `docs/source/user_guide/training_data.md` | BONES-SEED 官方文档 |
| `docs/source/tutorials/data_collection.md` | VLA 数据采集完整指南 |
| `docs/GR00T-SONIC 训练与模型发布整理.md` | SONIC 训练与发布总览 |

---

## 九、数据统计速查

| 指标 | BONES-SEED（训练） | VLA 采集（后训练） |
|------|-------------------|-------------------|
| 数据条数 | 142,220 原始 / ~130K 过滤后 | 按 episode 计数 |
| 总时长 | ~288 小时 | 取决于采集会话 |
| 帧率 | 120 fps（源数据） | **50 Hz**（采集） |
| 图像分辨率 | — | 480 × 640 |
| 视频编码 | — | H.264 MP4 |
| 表格格式 | CSV / PKL | Parquet |
| 演员/场景多样性 | 522 人，8 大类 | 取决于操作员 |
| 语言标注 | 最多 6 条/运动 | 1 条/episode（task prompt） |
| 时序分段 | 有 | 无 |

---

*文档生成时间：2026-04-27*
