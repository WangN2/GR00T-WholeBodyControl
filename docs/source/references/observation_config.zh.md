# 观测配置

本页是部署系统中配置观测的完整参考。涵盖 YAML 配置格式、编码器系统、每种可用观测类型，以及如何创建自定义观测。

(obs-config-format)=
## 配置格式

观测通过 YAML 文件配置，使用 `--obs-config <path>` 传入。每个观测都有一个 `name`（必须匹配已注册的观测）和一个 `enabled` 标志。

### 基本结构

```yaml
observations:
  - name: "motion_joint_positions"
    enabled: true
  - name: "motion_joint_velocities"
    enabled: true
  - name: "motion_anchor_orientation"
    enabled: true
  - name: "base_angular_velocity"
    enabled: true
  - name: "body_joint_positions"
    enabled: true
  - name: "body_joint_velocities"
    enabled: true
  - name: "last_actions"
    enabled: true
```

**关键规则：**

- 观测按**列出的顺序拼接**，形成策略输入向量。
- 偏移量自动计算 —— 无需手动管理偏移。
- 所有启用观测的**总维度**必须与 ONNX 模型的输入大小匹配。
- 禁用的观测（`enabled: false`）会被完全跳过。
- 重新排序条目会改变输入张量的布局（偏移量会相应移动）。

(obs-config-encoder)=
### 使用编码器（基于 Token 的策略）

对于使用编码器将观测压缩为紧凑 Token 的策略，添加一个 `encoder:` 部分：

```yaml
observations:
  - name: "token_state"           # 编码器输出（维度在下面设置）
    enabled: true
  - name: "base_angular_velocity" # 直接观测
    enabled: true
  - name: "body_joint_positions"
    enabled: true
  - name: "body_joint_velocities"
    enabled: true
  - name: "last_actions"
    enabled: true

encoder:
  dimension: 64       # Token 输出维度
  use_fp16: false     # 编码器 TensorRT 精度（可选）
  encoder_observations:
    - name: "motion_joint_positions_10frame_step5"
      enabled: true
    - name: "motion_joint_velocities_10frame_step5"
      enabled: true
    - name: "motion_anchor_orientation_10frame_step5"
      enabled: true
    - name: "motion_root_z_position_10frame_step5"
      enabled: true
  encoder_modes:            # 可选：每种模式的观测要求
    - name: "g1"
      mode_id: 0
      required_observations:
        - motion_joint_positions_10frame_step5
        - motion_joint_velocities_10frame_step5
        - motion_anchor_orientation_10frame_step5
        - motion_root_z_position_10frame_step5
```

**编码器字段：**

| 字段 | 描述 |
|---|---|
| `dimension` | Token 输出维度（必须与编码器 ONNX 模型输出匹配）。设为 0 或省略以禁用编码器。 |
| `use_fp16` | 编码器 TensorRT 引擎使用 FP16 精度（默认：false）。 |
| `encoder_observations` | 输入编码器的观测（所有模式的超集）。格式与策略观测相同，使用 name/enabled。 |
| `encoder_modes` | *（可选）* 每种模式的观测要求。不在模式 `required_observations` 中的观测会被零填充，节省计算。 |

使用 `--encoder-file <path>` 加载编码器模型。如果省略，可以通过 ROS2/ZMQ 外部设置 `token_state`。

完整的注释示例请参阅 `policy/observation_config_example.yaml`。

### 命名约定

多帧观测遵循模式：`{base_name}_{N}frame_step{S}`

- **N** = 采集的帧数（时间窗口大小）
- **S** = 帧之间的步长（以 50 Hz 的控制节拍为单位，因此 step5 = 间隔 0.1 秒）
- 没有后缀 = 仅单当前帧

例如，`motion_joint_positions_10frame_step5` 采集 10 帧关节位置，每 5 个节拍采样一次（0.1 秒），提供 0.9 秒的前瞻窗口。如果未来帧超出动作长度，则重复最后一帧。

---

## 编码器与 Token 观测

这些观测与编码器（分词器）系统相关。YAML 格式请参阅上面的[使用编码器](obs-config-encoder)部分。

| 名称 | 维度 | 描述 |
|---|---|---|
| `token_state` | 配置决定 | 编码器输出 Token（维度由 YAML 中的 `encoder.dimension` 设置）。由本地编码器推理填充，或通过 ZMQ/ROS2 外部提供。 |
| `encoder_mode` | 3 | 当前编码器模式 ID + 2 个零填充值。 |
| `encoder_mode_4` | 4 | 当前编码器模式 ID + 3 个零填充值。 |

---

## 动作参考观测

从当前活动的动作序列（参考动作、规划器输出或 ZMQ 流）中采集。所有关节数据使用 **IsaacLab 关节顺序**（29 个关节）。

### 关节位置（来自动作）

| 名称 | 维度 | 帧数 | 步长 | 描述 |
|---|---|---|---|---|
| `motion_joint_positions` | 29 | 1 | — | 当前帧关节位置（rad） |
| `motion_joint_positions_3frame_step1` | 87 | 3 | 1 | 3 帧窗口，连续 |
| `motion_joint_positions_5frame_step5` | 145 | 5 | 5 | 5 帧窗口，间隔 0.1 秒 |
| `motion_joint_positions_10frame_step1` | 290 | 10 | 1 | 10 帧窗口，连续 |
| `motion_joint_positions_10frame_step5` | 290 | 10 | 5 | 10 帧窗口，间隔 0.1 秒 |
| `motion_joint_positions_lowerbody_10frame_step1` | 120 | 10 | 1 | 仅下肢关节（12 个关节），连续 |
| `motion_joint_positions_lowerbody_10frame_step5` | 120 | 10 | 5 | 仅下肢关节，间隔 0.1 秒 |
| `motion_joint_positions_wrists_10frame_step1` | 60 | 10 | 1 | 仅腕关节（6 个关节），连续 |
| `motion_joint_positions_wrists_2frame_step1` | 12 | 2 | 1 | 仅腕关节，2 个连续帧 |

```{note}
当上肢控制激活时（例如通过 ZMQ/ROS2 遥操作），这些观测中的上肢关节位置会被外部提供的目标替换。
```

### 关节速度（来自动作）

| 名称 | 维度 | 帧数 | 步长 | 描述 |
|---|---|---|---|---|
| `motion_joint_velocities` | 29 | 1 | — | 当前帧关节速度（rad/s）。未播放时为零。 |
| `motion_joint_velocities_3frame_step1` | 87 | 3 | 1 | 3 帧窗口，连续 |
| `motion_joint_velocities_5frame_step5` | 145 | 5 | 5 | 5 帧窗口，间隔 0.1 秒 |
| `motion_joint_velocities_10frame_step1` | 290 | 10 | 1 | 10 帧窗口，连续 |
| `motion_joint_velocities_10frame_step5` | 290 | 10 | 5 | 10 帧窗口，间隔 0.1 秒 |
| `motion_joint_velocities_lowerbody_10frame_step1` | 120 | 10 | 1 | 仅下肢关节，连续 |
| `motion_joint_velocities_lowerbody_10frame_step5` | 120 | 10 | 5 | 仅下肢关节，间隔 0.1 秒 |
| `motion_joint_velocities_wrists_10frame_step1` | 60 | 10 | 1 | 仅腕关节，连续 |

### 锚点方向（来自动作）

经过航向校正的从机器人当前基座方向到参考动作方向的相对旋转。输出是 3×3 旋转矩阵的前两列（每帧 6 个值）。

| 名称 | 维度 | 帧数 | 步长 | 描述 |
|---|---|---|---|---|
| `motion_anchor_orientation` | 6 | 1 | — | 当前帧锚点方向（完整基座四元数） |
| `motion_anchor_orientation_10frame_step1` | 60 | 10 | 1 | 10 帧窗口，连续 |
| `motion_anchor_orientation_10frame_step5` | 60 | 10 | 5 | 10 帧窗口，间隔 0.1 秒 |
| `motion_anchor_orientation_heading` | 6 | 1 | — | 当前帧，仅航向四元数（偏航从机器人基座提取） |
| `motion_anchor_orientation_heading_10frame_step1` | 60 | 10 | 1 | 仅航向，10 帧窗口，连续 |
| `motion_anchor_orientation_heading_10frame_step5` | 60 | 10 | 5 | 仅航向，10 帧窗口，间隔 0.1 秒 |
| `motion_anchor_orientation_refheading` | 6 | 1 | — | 当前帧，参考航向四元数（偏航从第一帧未来参考帧提取） |
| `motion_anchor_orientation_refheading_10frame_step1` | 60 | 10 | 1 | 参考航向，10 帧窗口，连续 |
| `motion_anchor_orientation_refheading_10frame_step5` | 60 | 10 | 5 | 参考航向，10 帧窗口，间隔 0.1 秒 |

### 根 Z 位置（来自动作）

| 名称 | 维度 | 帧数 | 步长 | 描述 |
|---|---|---|---|---|
| `motion_root_z_position` | 1 | 1 | — | 当前帧根高度（m） |
| `motion_root_z_position_3frame_step1` | 3 | 3 | 1 | 3 帧窗口，连续 |
| `motion_root_z_position_10frame_step1` | 10 | 10 | 1 | 10 帧窗口，连续 |
| `motion_root_z_position_10frame_step5` | 10 | 10 | 5 | 10 帧窗口，间隔 0.1 秒 |

---

## SMPL 观测

从动作序列中的 SMPL 数据采集（可选 —— 需要包含 `smpl_joint.csv` / `smpl_pose.csv` 的动作）。

### SMPL 关节位置

每个 SMPL 关节的 3D 位置（24 个关节 × 3 = 每帧 72）。

| 名称 | 维度 | 帧数 | 步长 | 描述 |
|---|---|---|---|---|
| `smpl_joints` | 72 | 1 | — | 当前帧，全部 24 个 SMPL 关节 |
| `smpl_joints_2frame_step1` | 144 | 2 | 1 | 2 个连续帧 |
| `smpl_joints_5frame_step5` | 360 | 5 | 5 | 5 帧窗口，间隔 0.1 秒 |
| `smpl_joints_10frame_step1` | 720 | 10 | 1 | 10 帧窗口，连续 |
| `smpl_joints_10frame_step5` | 720 | 10 | 5 | 10 帧窗口，间隔 0.1 秒 |
| `smpl_joints_lower_10frame_step1` | 270 | 10 | 1 | 仅下肢 SMPL 关节（9 个关节），连续 |

### SMPL 姿态（轴角）

每个 SMPL 身体部位的 3D 轴角（21 个姿态 × 3 = 每帧 63）。

| 名称 | 维度 | 帧数 | 步长 | 描述 |
|---|---|---|---|---|
| `smpl_pose` | 63 | 1 | — | 当前帧，全部 21 个 SMPL 姿态 |
| `smpl_pose_5frame_step5` | 315 | 5 | 5 | 5 帧窗口，间隔 0.1 秒 |
| `smpl_pose_10frame_step1` | 630 | 10 | 1 | 10 帧窗口，连续 |
| `smpl_pose_10frame_step5` | 630 | 10 | 5 | 10 帧窗口，间隔 0.1 秒 |
| `smpl_elbow_wrist_poses_10frame_step1` | 120 | 10 | 1 | 仅肘部 + 腕部姿态（4 个部位），连续 |

### SMPL 别名

这些使用与动作观测相同的采集器，但用于基于 SMPL 的策略：

| 名称 | 维度 | 帧数 | 步长 | 描述 |
|---|---|---|---|---|
| `smpl_root_z_10frame_step1` | 10 | 10 | 1 | 根高度，10 个连续帧 |
| `smpl_anchor_orientation_10frame_step1` | 60 | 10 | 1 | 锚点方向，10 个连续帧 |
| `smpl_anchor_orientation_2frame_step1` | 12 | 2 | 1 | 锚点方向，2 个连续帧 |

---

## VR 跟踪观测

VR 3 点和 5 点跟踪数据。当外部源（ZMQ/ROS2）提供 VR 数据时，直接使用缓冲值。否则，从动作序列的身体数据计算位置和方向，并归一化到根身体坐标系。

### VR 3 点

| 名称 | 维度 | 描述 |
|---|---|---|
| `vr_3point_local_target` | 9 | 根坐标系中的 3 点位置：`[left_wrist xyz, right_wrist xyz, head xyz]` |
| `vr_3point_local_target_compliant` | 9 | 与上述相同（遥操作期间相同） |
| `vr_3point_local_orn_target` | 12 | 根坐标系中的 3 点方向：`[left quat wxyz, right quat wxyz, head quat wxyz]` |
| `vr_3point_compliance` | 3 | 柔顺值：`[left_arm, right_arm, head]`。键盘控制（g/h/b/v 键），范围 [0.0, 0.5]。 |

### VR 5 点

| 名称 | 维度 | 描述 |
|---|---|---|
| `vr_5point_local_target` | 15 | 根坐标系中的 5 点位置：`[left_wrist, right_wrist, head, left_ankle, right_ankle]` × xyz |
| `vr_5point_local_orn_target` | 20 | 根坐标系中的 5 点方向：5 个四元数 × wxyz |

---

## 机器人状态历史观测

从 StateLogger 环形缓冲区采集（来自真实机器人的测量传感器数据）。通过采样过去的状态提供时间上下文。

### 单帧（当前状态）

| 名称 | 维度 | 描述 |
|---|---|---|
| `base_angular_velocity` | 3 | IMU 角速度（rad/s）：`[roll_rate, pitch_rate, yaw_rate]` |
| `body_joint_positions` | 29 | 当前编码器关节位置（rad，IsaacLab 顺序） |
| `body_joint_velocities` | 29 | 当前编码器关节速度（rad/s，IsaacLab 顺序） |
| `last_actions` | 29 | 上一策略输出（归一化动作值） |
| `gravity_dir` | 3 | 身体坐标系中的重力方向（从基座 IMU 四元数计算） |

### 多帧历史（4 帧，步长 1）

| 名称 | 维度 | 描述 |
|---|---|---|
| `his_body_joint_positions_4frame_step1` | 116 | 关节位置：4 个连续节拍（29 × 4） |
| `his_body_joint_velocities_4frame_step1` | 116 | 关节速度：4 个连续节拍 |
| `his_last_actions_4frame_step1` | 116 | 过去动作：4 个连续节拍 |
| `his_base_angular_velocity_4frame_step1` | 12 | 角速度：4 个连续节拍（3 × 4） |
| `his_gravity_dir_4frame_step1` | 12 | 重力方向：4 个连续节拍 |

### 多帧历史（10 帧，步长 1）

| 名称 | 维度 | 描述 |
|---|---|---|
| `his_body_joint_positions_10frame_step1` | 290 | 关节位置：10 个连续节拍（29 × 10） |
| `his_body_joint_velocities_10frame_step1` | 290 | 关节速度：10 个连续节拍 |
| `his_last_actions_10frame_step1` | 290 | 过去动作：10 个连续节拍 |
| `his_base_angular_velocity_10frame_step1` | 30 | 角速度：10 个连续节拍（3 × 10） |
| `his_gravity_dir_10frame_step1` | 30 | 重力方向：10 个连续节拍 |

---

## 创建自定义观测

你可以通过修改 C++ 源代码来添加自己的观测类型。观测系统围绕**注册表模式**构建 —— 你编写一个采集函数，用名称和维度注册它，然后在 YAML 配置中使用该名称。

所有观测代码位于 `gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/src/g1_deploy_onnx_ref.cpp` 中的 `G1Deploy` 类内。

### 步骤 1：编写采集函数

采集函数从内部状态（传感器数据、动作数据等）读取，并将输出写入给定偏移量的目标缓冲区。函数签名为：

```cpp
bool MyObservation(std::vector<double>& target_buffer, size_t offset) {
    // 将观测值写入 target_buffer，从 offset 开始。
    // 成功返回 true，失败返回 false（将停止控制循环）。
}
```

**G1Deploy 内部可用的数据源**（完整列表请参阅 `g1_deploy_onnx_ref.cpp` 中的成员变量）：

| 源 | 描述 |
|---|---|
| `state_logger_` | 过去机器人状态的环形缓冲区 —— IMU、关节、速度、动作、手部状态、Token 状态 |
| `current_motion_` / `current_frame_` | 当前活动的动作序列和播放游标 |
| `operator_state` | 操作员控制标志（`.play`、`.start`、`.stop`） |
| `vr_*_buffer_`、`left_hand_joint_buffer_` 等 | 缓冲的输入接口数据 —— VR 跟踪、手部关节、柔顺性、上肢目标 |
| `heading_state_buffer_`、`movement_state_buffer_` | 航向和规划器运动命令的线程安全缓冲区 |

**示例** —— 一个输出躯干 IMU 角速度（3 个值）的自定义观测：

```cpp
bool GatherTorsoAngularVelocity(std::vector<double>& target_buffer, size_t offset) {
    if (!state_logger_) { return false; }

    auto hist = state_logger_->GetLatest(1);
    if (hist.empty()) { return false; }

    const auto& entry = hist[0];
    target_buffer[offset + 0] = entry.body_torso_ang_vel[0];
    target_buffer[offset + 1] = entry.body_torso_ang_vel[1];
    target_buffer[offset + 2] = entry.body_torso_ang_vel[2];
    return true;
}
```

### 步骤 2：在观测注册表中注册

将你的观测添加到 `g1_deploy_onnx_ref.cpp` 中的 `GetObservationRegistry()` 方法。每个条目是一个 `{name, dimension, gatherer_lambda}` 元组：

```cpp
std::vector<ObservationRegistry> GetObservationRegistry() {
    return {
        // ... 现有观测 ...

        // 你的自定义观测：
        {"torso_angular_velocity", 3,
         [this](std::vector<double>& buf, size_t offset) {
             return GatherTorsoAngularVelocity(buf, offset);
         }},
    };
}
```

**名称**是你在 YAML 配置中使用的字符串。**维度**必须精确 —— 系统会验证所有启用观测的总和是否与 ONNX 模型输入大小匹配。

### 步骤 3：在 YAML 配置中使用

注册后，你的观测可以像内置观测一样使用：

```yaml
observations:
  - name: "torso_angular_velocity"
    enabled: true
  # ... 其他观测 ...
```

### 提示

- **维度必须固定。** 观测维度在注册时设置，运行时不能更改。如果需要可变大小数据，填充到固定最大值。
- **不要在热路径中分配内存。** 采集函数在控制循环中以 50 Hz 运行。避免 `new`、`malloc` 或调整向量大小。在构造函数中预分配缓冲区或使用栈数组。
- **谨慎返回 `false`。** 从采集器返回 `false` 会停止整个控制循环。仅在不可恢复的错误时返回 `false`。对于缺失的可选数据，写零并返回 `true`。
- **线程安全。** 采集器在控制线程上运行。从 `state_logger_` 和 `DataBuffer` 对象读取是线程安全的。访问 `current_motion_` 和 `current_frame_` 受 `current_motion_mutex_` 保护（调用 `GatherObservations()` 时已持有）。
- **多帧模式。** 如果你的观测需要时间窗口，请遵循现有的 `GatherHis*` 或 `GatherMotion*MultiFrame` 模式 —— 它们接受 `num_frames` 和 `step_size` 参数并注册多个变体（例如，`my_obs`、`my_obs_4frame_step1`、`my_obs_10frame_step5`）。
- **编码器观测。** 自定义观测也可以用作编码器输入。在同一个注册表中注册它们 —— 它们将可用于 YAML 配置中的 `observations:` 和 `encoder_observations:`。
- **修改后重新构建。** 修改 C++ 源代码后，从 `gear_sonic_deploy/` 目录使用 `just build` 重新构建。

---

## 示例配置

### 最小配置（154D —— 默认策略）

```yaml
observations:
  - name: "motion_joint_positions"       # 29D
    enabled: true
  - name: "motion_joint_velocities"      # 29D
    enabled: true
  - name: "motion_anchor_orientation"    # 6D
    enabled: true
  - name: "base_angular_velocity"        # 3D
    enabled: true
  - name: "body_joint_positions"         # 29D
    enabled: true
  - name: "body_joint_velocities"        # 29D
    enabled: true
  - name: "last_actions"                 # 29D
    enabled: true
# 总计：154D
```

### 使用编码器的基于 Token 的策略

```yaml
observations:
  - name: "token_state"                  # 64D（来自编码器）
    enabled: true
  - name: "base_angular_velocity"        # 3D
    enabled: true
  - name: "body_joint_positions"         # 29D
    enabled: true
  - name: "body_joint_velocities"        # 29D
    enabled: true
  - name: "last_actions"                 # 29D
    enabled: true

encoder:
  dimension: 64
  use_fp16: false
  encoder_observations:
    - name: "motion_joint_positions_10frame_step5"   # 290D
      enabled: true
    - name: "motion_joint_velocities_10frame_step5"  # 290D
      enabled: true
    - name: "motion_anchor_orientation_10frame_step5" # 60D
      enabled: true
    - name: "motion_root_z_position_10frame_step5"   # 10D
      enabled: true
```

### VR 遥操作策略

```yaml
observations:
  - name: "token_state"                         # 64D
    enabled: true
  - name: "vr_3point_local_target"              # 9D
    enabled: true
  - name: "vr_3point_local_orn_target"          # 12D
    enabled: true
  - name: "vr_3point_compliance"                # 3D
    enabled: true
  - name: "base_angular_velocity"               # 3D
    enabled: true
  - name: "body_joint_positions"                # 29D
    enabled: true
  - name: "body_joint_velocities"               # 29D
    enabled: true
  - name: "last_actions"                        # 29D
    enabled: true
```

YAML 语法详情请参阅上面的[配置格式](obs-config-format)部分。
