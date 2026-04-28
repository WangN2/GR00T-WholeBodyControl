# C++ 部署程序流程

本文档描述主可执行文件的运行方式、参数以及日志/配置选项。

## 程序流水线

高层流程（与当前代码匹配）：
- 输入接口：`keyboard | gamepad | gamepad_manager | zmq | zmq_manager | ros2 | manager`
- 可选规划器（启用时）生成目标动画
- 运动读取器为非规划器模式提供参考动作
- 策略推理（TensorRT；可选 encoder → decoder）
- 通过 `--output-type <zmq|ros2|all>` 发布输出

## 可用命令

```sh
just build           # 构建主项目
just clean           # 清理构建产物
just --list          # 显示所有可用命令
```

## 运行

### 频率测试

加载 ONNX 模型并打印输入/输出信息。这是模型加载的健全性检查；报告的频率不是 TensorRT 推理速度。

```sh
# 基本用法，使用默认设置（1000 次迭代，随机数据）
just run freq_test policy/example/model_step_000000.onnx

# 自定义迭代次数和数据模式
just run freq_test policy/example/model_step_000000.onnx 5000 random
```

**用法：** `just run freq_test <model_file> [iterations] [data_mode]`
- `model_file`：ONNX 模型文件路径（必需）
- `iterations`：推理迭代次数（默认：1000）
- `data_mode`：输入数据类型 — `zeros|random|ones`（默认：random）

### 策略部署

在 G1 机器人上部署 ONNX 策略，使用动作参考控制：

```sh
# 示例命令（真实机器人）
just run g1_deploy_onnx_ref enP8p1s0 policy/release/model_decoder.onnx reference/example/ \
  --obs-config policy/release/observation_config.yaml \
  --encoder-file policy/release/model_encoder.onnx \
  --planner-file planner/target_vel/V2/planner_sonic.onnx \
  --input-type manager \
  --enable-motion-recording \
  --enable-csv-logs

# MuJoCo 仿真（禁用 CRC 校验）
python ../gear_sonic/scripts/run_sim_loop.py
just run g1_deploy_onnx_ref lo policy/release/model_decoder.onnx reference/example/ \
  --obs-config policy/release/observation_config.yaml \
  --encoder-file policy/release/model_encoder.onnx \
  --planner-file planner/target_vel/V2/planner_sonic.onnx \
  --input-type manager \
  --enable-motion-recording \
  --enable-csv-logs \
  --disable-crc-check
```

**用法：** `just run g1_deploy_onnx_ref <network_interface> <model_file> <motion_data_path> [options...]`

**必需参数：**
- `network_interface`：DDS 通信的网络接口（例如 `eth0`, `enp5s0`, `enP8p1s0`, `lo`）
- `model_file`：ONNX 策略模型文件路径
- `motion_data_path`：包含参考动作的动作数据目录路径

**可选参数：**

**模型配置：**
- `--obs-config <path>`：观测配置 YAML 文件路径
- `--encoder-file <path>`：ONNX 编码器模型文件路径（可选，用于基于 token 的策略）
- `--planner-file <path>`：ONNX 规划器模型文件路径（ROS2、`gamepad_manager` 和 `zmq_manager` 规划器模式所需）
- `--planner-precision <16|32>`：规划器的浮点精度（默认：32）
- `--policy-precision <16|32>`：策略的浮点精度（默认：32）

**输出模式：**
- `--output-type <type>`：发布控制结果的输出接口
  - `zmq` — 通过 ZMQ 发布（默认）
  - `ros2` — 通过 ROS2 发布（仅在构建时启用了 ROS2 支持时可用）
  - `all` — 同时创建所有可用的输出接口

**输入模式：**
- `--input-type <type>`：输入接口类型（默认：`keyboard`）
  - `keyboard` — 直接键盘输入
  - `gamepad` — 无线手柄
  - `gamepad_manager` — 手柄 + 快速切换到 ZMQ/ROS2
  - `zmq` — 网络动作流
  - `zmq_manager` — 规划器和网络动作流之间动态切换
  - `manager` — 键盘、手柄、ZMQ 和 ROS2 之间动态切换
  - `ros2` — ROS2 话题控制（需要规划器，仅在构建时启用了 ROS2 支持时可用）

**ZMQ 配置（在使用 `--input-type zmq`、`zmq_manager`、`demo_gamepad_manager` 或 `manager` 时）：**
- `--zmq-host <host>`：ZMQ 服务器主机（默认：`localhost`）
- `--zmq-port <port>`：ZMQ 服务器端口（默认：`5556`）
- `--zmq-topic <topic>`：ZMQ 话题/前缀（默认：`pose`）
- `--zmq-conflate`：启用 ZMQ CONFLATE 模式
- `--zmq-verbose`：启用详细 ZMQ 订阅者日志
- `--zmq-out-port`：使用 `--output-type zmq` 时发布控制结果的端口（默认：`5557`）
- `--zmq-out-topic`：使用 `--output-type zmq` 时发布控制结果的话题（默认：`g1_debug`）

**仿真：**
- `--disable-crc-check`：禁用 CRC 校验（MuJoCo 仿真所需）

**手部与柔顺控制：**
- `--set-compliance <value>`：设置初始 VR 3 点柔顺值（0.01 = 刚性，0.5 = 柔顺；默认：`0.5,0.5,0.0`）。可指定 1 个值（应用于双手）或 3 个逗号分隔值（`left_wrist,right_wrist,head`）。运行时键盘控制：`g/h` = 左手 ±0.1，`b/v` = 右手 ±0.1。
- `--max-close-ratio <value>`：设置初始手部最大闭合比例（0.2–1.0；默认：1.0 = 允许完全闭合）。运行时键盘控制：`x/c` = ±0.1。

**日志（CLI 标志）：**
- **调试/分析日志（写入单个 CSV 文件）**：
  - `--target-motion-logfile <path>`：记录控制器追踪的目标动作（使用 `visualize_motion.py` 可视化）
  - `--planner-motion-logfile <path>`：记录规划器生成的动画序列
  - `--policy-input-logfile <path>`：记录策略输入（观测）张量
  - `--record-input-file <path>`：将操作者控制输入记录到 CSV 以便后续回放
  - `--playback-input-file <path>`：从 CSV 回放先前记录的控制输入
- **状态 CSV 日志（写入带时间戳的目录）**：
  - `--logs-dir <path>`：状态 CSV 日志的基础目录（默认：`logs/dd-mm-yy/hh-mm-ss`）
  - `--enable-csv-logs`：启用机器人状态 CSV 日志（默认：关闭）
  - `--enable-motion-recording`：将活动动作流记录到 `reference/recorded_motion/...`（默认：关闭）

## 日志（详情）

系统提供多种日志功能用于调试、分析和回放。

### 动作日志

**目标动作 (`--target-motion-logfile <path>`)：**
- 记录控制器每个控制帧（~50 Hz）追踪的动作
- CSV 列：`pos_x, pos_y, pos_z, rot_qw, rot_qx, rot_qy, rot_qz, dof_0, dof_1, ... dof_28`
  - 全局位置 (xyz)
  - 全局旋转四元数 (w, x, y, z)
  - 29 个关节角度 (DoF)

**规划器动作 (`--planner-motion-logfile <path>`)：**
- 记录规划器生成的动画序列（~10 Hz 规划更新）
- 每次规划器更新产生一个短序列（例如 ~100 帧），追加到 CSV
- 与目标动作相同的 CSV 格式
- 包含动作混合和重新规划结果

**动作录制 (`--enable-motion-recording`)：**
- 自动将当前活动动作流记录到 `reference/recorded_motion/YYYYMMDD/` 下的带时间戳文件夹中
  - **流式动作**（ZMQ pose 话题）：保存为 `streamed_HHMMSS/`
  - **规划器动作**（规划器生成的序列）：保存为 `planner_motion_HHMMSS/`
- 每个录制文件夹包含 `joint_pos.csv`、`joint_vel.csv`、`body_pos.csv`、`body_quat.csv` 等
- 用于离线检查/回归比较闭环行为

### 可视化

所有动作 CSV 文件（记录的数据和参考动作）都可以使用 `visualize_motion.py` 脚本进行可视化：

```sh
# 可视化记录的动作数据（单个 CSV 文件）
python visualize_motion.py --csv_path target_motion.csv

# 可视化动作数据目录中的参考动作
python visualize_motion.py --motion_dir reference/example/high_jump_full_turn/
```

可视化脚本可以连接到正在运行的 `g1_deploy` 可执行文件，实时可视化目标/测量机器人动作：

```sh
python visualize_motion.py --realtime_debug_url tcp://localhost:5557
```

这显示四个 G1 机器人：目标动画（彩色）、零平移目标（绿色）、测量传感器数据（红色）和电机温度热力图（白色，带逐关节颜色指示：绿色 → 黄色 → 橙色 → 红色/闪烁，按温度）。

**配置：**
- 默认端口：5557（使用 `--zmq-out-port <port>` 更改）
- 默认话题：`g1_debug`（在可执行文件上使用 `--zmq-out-topic <topic>` 更改，在可视化工具上使用 `--realtime_debug_topic <topic>` 更改）
- 对于物理机器人，将 `localhost` 替换为机器人的 IP 地址

**回放控制：**
- **Space**：暂停/恢复回放
- **`.`**（句点）：前进一帧
- **`,`**（逗号）：后退一帧
- **`r`**：重置到第 0 帧

### 策略输入日志

**策略输入 (`--policy-input-logfile <path>`)：**
- 记录输入神经网络策略的原始观测张量
- 输出：单个 CSV 文件（每控制步一行，所有观测值）
- 用于调试观测配置和输入漂移

### 控制输入录制/回放

**录制 (`--record-input-file <path>`)：**
- 记录控制输入（动作索引、帧、操作者状态、规划器状态、移动命令）
- 控制系​​统激活时开始记录
- 提示：在从龙门架放下后等待几秒再开始控制，以便在回放时给自己设置时间

**回放 (`--playback-input-file <path>`)：**
- 回放记录的控制输入以进行可重复的实验
- 控制系​​统激活时开始回放
- 用于使用相同输入测试策略变更

### 机器人状态 CSV 记录器

使用 `--enable-csv-logs` 启用时，系统在每个控制步（50 Hz）记录详细的机器人状态。

**输出目录：**
- 默认：`logs/dd-mm-yy/hh-mm-ss`（自动生成时间戳）
- 自定义：使用 `--logs-dir <path>` 指定目录

**生成的文件（按信号类型拆分）：**
- `base_quat.csv` — 基座 IMU 四元数（4 个值：w, x, y, z）
- `base_ang_vel.csv` — 基座角速度（3 个值：x, y, z）
- `torso_quat.csv` — 躯干 IMU 四元数（4 个值）
- `torso_ang_vel.csv` — 躯干角速度（3 个值）
- `q.csv` — 关节位置（29 个关节）
- `dq.csv` — 关节速度（29 个关节）
- `action.csv` — 策略动作（29 个关节）

**CSV 格式：**
- 列：`index,time_ms,...`
- `time_ms`：自首次记录以来的毫秒数（开始时为 0.0，允许小数）
- 所有文件使用相同的索引/时间戳进行同步

**示例：**

```sh
just run g1_deploy_onnx_ref enp5s0 policy/model.onnx reference/motions/ \
  --obs-config policy/obs_config.yaml \
  --enable-csv-logs \
  --logs-dir logs/my_experiment
```

## 观测配置

系统使用 YAML 配置文件来定义哪些观测输入到策略。这允许在不修改代码的情况下灵活设计策略。

**基本结构 (`--obs-config <path>`)：**

```yaml
observations:
  - name: "body_joint_positions"
    enabled: true
  - name: "base_angular_velocity"
    enabled: true
  # ... 其他观测
```

**使用编码器（基于 Token 的策略）：**

对于使用编码 token 的策略，添加一个 `encoder:` 部分：

```yaml
observations:
  - name: "token_state"           # 编码器输出（64 维 token）
    enabled: true
  - name: "base_angular_velocity" # 直接观测
    enabled: true

encoder:
  dimension: 64       # Token 输出维度
  use_fp16: false     # TensorRT 精度（可选）
  encoder_observations:
    - name: "motion_joint_positions_10frame_step5"
      enabled: true
    # ... 输入到编码器的观测
```

然后使用 `--encoder-file <path>` 运行以加载编码器模型。如果省略，token 可以通过 ROS2/ZMQ 外部设置。

**完整观测参考：**

有关所有可用观测名称、维度和示例配置的完整列表，请参阅 [观测配置](observation_config.zh.md)。

**示例：**
- 参见 `policy/observation_config_example.yaml`
