# 串流动作追踪

通过 ZMQ 将动作数据串流到机器人，用于参考动作追踪。该接口支持串流 **SMPL 姿势**（例如来自 PICO）或来自任何外部源的 **G1 全身关节位置**（qpos）（`--input-type zmq`）。

```{admonition} 前置条件
:class: note
请先完成[快速开始](../getting_started/quickstart.md)，确保 sim2sim 循环已运行。
```

```{admonition} 紧急停止
:class: danger
随时按 **`O`** 即可立即停止控制并退出。请始终保持一只手在键盘附近准备按 **`O`**。
```

## 启动

**Sim2Sim（MuJoCo）：**

```bash
# 终端 1 — MuJoCo 仿真器（从仓库根目录）
source .venv_sim/bin/activate
python gear_sonic/scripts/run_sim_loop.py

# 终端 2 — C++ 部署（从 gear_sonic_deploy/）
bash deploy.sh --input-type zmq \
  --zmq-host <publisher-ip> \
  --zmq-port 5556 \
  --zmq-topic pose \
  sim
```

**真实机器人：**

```bash
# 在 gear_sonic_deploy/ 目录下
bash deploy.sh --input-type zmq \
  --zmq-host <publisher-ip> \
  --zmq-port 5556 \
  --zmq-topic pose \
  real
```

## 分步指南

1. 按 **`]`** 启动控制系统。
2. 默认情况下你处于**参考动作模式** —— 使用 **`T`** 播放动作，**`N`** / **`P`** 切换，**`R`** 重启（与[键盘接口](keyboard.md)相同）。
3. 按 **`ENTER`** 切换到 **ZMQ 串流模式**。终端将打印 `ZMQ STREAMING MODE: ENABLED`。
4. 策略现在会实时追踪从 ZMQ 发布者到达的动作帧。播放会自动开始。
5. 再次按 **`ENTER`** 切换回参考动作。终端将打印 `ZMQ STREAMING MODE: DISABLED`，编码模式重置为 `0`（基于关节）。
6. 在任意模式下使用 **`Q`** / **`E`** 调整朝向（每次 ±0.1 rad）。
7. 按 **`I`** 重新初始化基座四元数并将朝向重置为零。
8. 完成后，按 **`O`** 停止控制并退出。

```{note}
**不支持规划器** —— 此接口仅使用预加载和 ZMQ 串流的参考动作。对于规划器 + ZMQ 控制（例如 PICO VR 遥操作），请改用 `--input-type zmq_manager`。参见 [VR 全身遥操作教程](vr_wholebody_teleop.md)。
```

```{tip}
**构建你自己的串流源。** 下面记录的 ZMQ 串流协议是自包含的 —— 任何以该格式发送消息的发布者都可以驱动机器人。你可以编写自己的动作捕捉重定向管道、仿真器桥接，或任何其他产生所需字段的源。无需 PICO 硬件。
```

## 与 PICO VR 遥操作配合使用

你可以将 `--input-type zmq` 与 PICO 遥操作串流端一起使用，构建一个简单的纯串流全身遥操作设置。在此模式下，PICO 通过 ZMQ 串流全身 SMPL 姿势，部署端直接追踪它们 —— 没有 locomotion 规划器，没有 PICO 按键模式切换。所有控制都通过键盘完成。

### 前置条件

1. **已完成[快速开始](../getting_started/quickstart.md)** —— 你能够运行 sim2sim 循环。
2. **PICO VR 硬件已设置** —— 头显和手柄已连接，身体追踪正常工作，且 `.venv_teleop` 已安装。安装和校准请参见 [VR 遥操作设置](../getting_started/vr_teleop_setup.md)。

### 启动（Sim2Sim）

运行三个终端：

**终端 1 — MuJoCo 仿真器**（从仓库根目录）：

```bash
source .venv_sim/bin/activate
python gear_sonic/scripts/run_sim_loop.py
```

**终端 2 — C++ 部署**（从 `gear_sonic_deploy/`）：

```bash
bash deploy.sh --input-type zmq \
  --zmq-host localhost \
  --zmq-port 5556 \
  --zmq-topic pose \
  sim
```

**终端 3 — PICO 遥操作串流端**（从仓库根目录）：

```bash
source .venv_teleop/bin/activate

# 带可视化（首次运行推荐）：
python gear_sonic/scripts/pico_manager_thread_server.py \
    --manager --vis_smpl --vis_vr3pt

# 无可视化（headless）：
# python gear_sonic/scripts/pico_manager_thread_server.py --manager
```

### 启动（真实机器人）

运行两个终端（无需 MuJoCo）：

**终端 1 — C++ 部署**（从 `gear_sonic_deploy/`）：

```bash
bash deploy.sh --input-type zmq \
  --zmq-host <teleop-machine-ip> \
  --zmq-port 5556 \
  --zmq-topic pose \
  real
```

将 `<teleop-machine-ip>` 替换为 `localhost`（如果 PICO 串流端运行在同一台机器上）或运行终端 2 的机器 IP。

**终端 2 — PICO 遥操作串流端**（从仓库根目录）：

```bash
source .venv_teleop/bin/activate
python gear_sonic/scripts/pico_manager_thread_server.py --manager
```

### 分步指南

1. **校准姿势**：站直，双脚并拢，上臂贴紧身体两侧，前臂向前弯曲 90°（每个肘部呈 L 形），手掌朝内。
2. 在 PICO 手柄上，同时按 **A + B + X + Y** 初始化并校准身体追踪。
3. 在 PICO 手柄上按 **A + X** 开始串流姿势。
4. 在终端 2（C++ 部署）中，按 **`]`** 启动控制系统。
5. 在 MuJoCo 窗口中（仅仿真），按 **`9`** 将机器人放到地面。
6. 回到终端 2，按 **`ENTER`** 启用 ZMQ 串流。终端打印 `ZMQ STREAMING MODE: ENABLED`。机器人开始实时追踪你的 PICO 姿势。
7. 移动你的身体 —— 机器人会镜像你的动作。使用每只 PICO 手柄上的 **扳机键（Trigger）** 闭合对应的机器人手部。
8. 要**暂停**串流（例如重新调整站位），再次按 **`ENTER`**。终端打印 `ZMQ STREAMING MODE: DISABLED`。机器人保持最后姿势并停止追踪。你可以自由移动而不影响机器人。
9. 要**恢复**，再按一次 **`ENTER`**。机器人会跳到你当前的姿势 —— **在恢复前请回到接近机器人当前姿势的位置**，以避免突然跳动。
10. 完成后，按 **`O`** 停止控制并退出。

```{admonition} 危险 —— 从暂停中恢复
:class: danger
当你按 **`ENTER`** 从暂停中恢复串流时，机器人会立即尝试到达你当前的物理姿势。如果你的身体与机器人姿势相差很大，机器人可能会做出突然的剧烈动作。**在按 `ENTER` 恢复前，务必回到接近机器人当前姿势的位置。**
```

### ZMQ 模式下的 PICO 按键

在 `--input-type zmq` 模式下，C++ 部署端**不会**直接处理 PICO 手柄的按键组合。然而，按键仍然会影响 **Python 串流端**，而后者控制什么数据被发布到 `pose` ZMQ 主题上。由于部署端追踪到达（或未到达）该主题的任何内容，因此某些按键仍会间接影响机器人。

| PICO 按键 | 效果 |
|-------------|--------|
| **A + B + X + Y** | 在串流端校准身体追踪。按一次初始化；再次按停止串流（串流端紧急停止）。 |
| **A + X** | 在串流端切换姿势模式 —— 开始或停止发布姿势数据。停止时，机器人保持最后姿势。**可作为暂停/恢复。** |
| **Menu（按住）** | 按住时暂停姿势串流。机器人保持最后姿势直到松开。**可作为暂停。** 松开后请回到接近机器人当前姿势的位置。 |
| **Trigger** | 手部抓取 —— 由串流端处理，并作为 `left_hand_joints` / `right_hand_joints` 发送到串流中。 |
| **B + Y** | 在串流端切换姿势模式（与 A+X 效果相同）—— 开始或停止发布姿势数据。**可作为暂停/恢复。** |

部署端的所有模式控制都通过键盘完成：

| 按键 | 动作 |
|-----|--------|
| **`]`** | 启动控制系统 |
| **`ENTER`** | 切换串流开/关（暂停/恢复） |
| **`O`** | 紧急停止 —— 停止控制并退出 |
| **`I`** | 重新初始化基座四元数并重置朝向 |
| **`Q`** / **`E`** | 调整朝向（±0.1 rad） |
| **`F`** | 报告电机温度（TTS 语音播报） |

```{note}
要获得完整的 PICO VR 体验，包括规划器支持、locomotion 模式以及基于 PICO 手柄的模式切换，请改用 `--input-type zmq_manager`。参见 [VR 全身遥操作教程](vr_wholebody_teleop.md)。
```

## 控制说明

| 按键 | 动作 |
|-----|--------|
| **]** | 启动控制系统 |
| **O** | 停止控制并退出（紧急停止） |
| **ENTER** | 在参考动作和 ZMQ 串流之间切换 |
| **I** | 重新初始化基座四元数并重置朝向 |
| **Q** / **E** | 调整 delta 朝向 左 / 右（±0.1 rad） |
| **F** | 报告电机温度（TTS 语音播报） |

*仅参考动作模式（串流关闭）：*

| 按键 | 动作 |
|-----|--------|
| **T** | 播放当前动作到完成 |
| **R** | 从开头重启当前动作（暂停在第 0 帧） |
| **P** / **N** | 上一个 / 下一个动作序列 |

## 串流协议版本

编码模式由 ZMQ 串流协议版本自动决定。**SONIC 使用协议 v1、v3 和 v4。** 协议 v2 可用于自定义应用。

### 编码模式逻辑

编码模式仅在策略模型配置了**编码器**并已加载时生效。启动时，每个动作的编码模式根据编码器可用性初始化：

| `encode_mode` | 含义 |
|----------------|---------|
| `-2` | 模型中未配置编码器 / token state —— 编码模式无效果 |
| `-1` | 存在编码器配置（token state 维度 > 0），但未提供编码器模型文件 |
| `0` | 编码器已加载，基于关节的模式（默认） |
| `1` | 编码器已加载，遥操作 / 3 点上半身模式 |
| `2` | 编码器已加载，基于 SMPL 的模式 |

当 ZMQ 串流激活时，协议版本决定串流动作的编码模式：v1 → `0`，v2/v3 → `2`。协议 v4 完全绕过编码器 —— 它将预计算的 token 直接串流到策略解码器的 `token_state` 观测槽中。这仅在模型实际拥有编码器（`encode_mode >= 0`）时才会影响推理。如果未配置编码器（`-2`），值会被设置但不会影响推理管道。

切换回参考动作（按 **ENTER** 禁用串流）时，编码模式重置为 `0`（如果该动作有编码器，即 `encode_mode >= 0`）。

### 公共字段（所有版本）

所有版本都需要两个公共字段：

| 字段 | 形状 | 数据类型 | 说明 |
|-------|-------|-------|-------------|
| `body_quat` | `[N, 4]` 或 `[N, num_bodies, 4]` | `f32` / `f64` | 每帧的身体四元数（w, x, y, z） |
| `frame_index` | `[N]` | `i32` / `i64` | 用于对齐的单调递增帧索引 |

```{warning}
会话中途不允许更改协议版本。如果发布者在串流过程中切换了协议版本，接口会自动禁用 ZMQ 模式并返回参考动作以确保安全。

错误信息：`Protocol version changed from X to Y during active ZMQ session!`
```

### 协议 v1 — 基于关节（编码模式 0）

串流原始 G1 关节位置和速度。当你的源直接提供 qpos/qvel 数据时使用（例如来自另一个仿真器或动作捕捉重定向管道）。

**必需字段：**

| 字段 | 形状 | 数据类型 | 说明 |
|-------|-------|-------|-------------|
| `joint_pos` | `[N, 29]` | `f32` / `f64` | IsaacLab 顺序的关节位置（全部 29 个关节） |
| `joint_vel` | `[N, 29]` | `f32` / `f64` | IsaacLab 顺序的关节速度（全部 29 个关节） |

- `N` = 每条消息的帧数（batch size）。
- 必须提供全部 29 个关节值，且有意义。
- `joint_pos` 和 `joint_vel` 的帧数必须匹配。

**常见错误：**
- `Version 1 missing required fields (joint_pos, joint_vel)` —— 一个或两个字段缺失。
- `Frame count mismatch between joint_pos and joint_vel` —— `N` 维度不一致。

### 协议 v2 — 基于 SMPL（编码模式 2）

串流 SMPL 人体模型数据。此协议**不被 SONIC 的内置管道使用** —— 它可供你自己的生成 SMPL 表示的自定义应用使用，例如一个只观测 SMPL 的策略。

**必需字段：**

| 字段 | 形状 | 数据类型 | 说明 |
|-------|-------|-------|-------------|
| `smpl_joints` | `[N, 24, 3]` | `f32` / `f64` | SMPL 关节位置（24 个关节 × xyz） |
| `smpl_pose` | `[N, 21, 3]` | `f32` / `f64` | SMPL 关节旋转，轴角格式（21 个身体姿势 × xyz） |

- `joint_pos` 和 `joint_vel` 在 v2 中为**可选**。

**常见错误：**
- `Version 2 missing required field 'smpl_joints'` 或 `'smpl_pose'` —— 必需的 SMPL 字段缺失。

### 协议 v3 — 关节 + SMPL 组合（编码模式 2）

同时包含关节级和 SMPL 数据。SONIC 的全身遥操作（例如 PICO VR）使用此协议。

**必需字段：**

| 字段 | 形状 | 数据类型 | 说明 |
|-------|-------|-------|-------------|
| `joint_pos` | `[N, 29]` | `f32` / `f64` | IsaacLab 顺序的关节位置 |
| `joint_vel` | `[N, 29]` | `f32` / `f64` | IsaacLab 顺序的关节速度 |
| `smpl_joints` | `[N, 24, 3]` | `f32` / `f64` | SMPL 关节位置（24 个关节 × xyz） |
| `smpl_pose` | `[N, 21, 3]` | `f32` / `f64` | SMPL 关节旋转，轴角格式（21 个身体姿势 × xyz） |

```{important}
在协议 v3 中，`joint_pos` 中**只有 6 个手腕关节需要有意义的值** —— 其余 23 个关节可以为零。手腕关节索引（IsaacLab 顺序）为：**[23, 24, 25, 26, 27, 28]**（每只手腕 3 个关节 × 2）。非手腕关节的 `joint_vel` 也可以为零。

SMPL 字段（`smpl_joints`、`smpl_pose`）在 v3 中承载主要动作数据；`joint_pos` 中的手腕关节提供了 SMPL  alone 无法捕捉的精细手腕控制。
```

- 所有四个字段的帧数必须一致。

**常见错误：**
- `Version 3 missing required field 'joint_pos'` 或 `'joint_vel'` —— 关节字段缺失（与 v2 不同，它们在 v3 中是必需的）。
- `Version 3 frame count mismatch between smpl_joints (X) and joint_pos (Y)` —— 各字段的 `N` 维度不一致。

### 协议 v4 — 仅 Token 串流（直接潜在动作）

串流预计算的动作 token 直接到策略，完全绕过编码器。当你的源产生已编码的潜在动作时使用（例如运行在另一台机器上的独立编码器，或输出 token 的生成模型）。

与 v1–v3 不同，协议 v4 **不携带动作帧** —— 机器人端的参考动作保持不变。token 直接注入到解码器策略的 `token_state` 观测槽中。

**必需字段：**

| 字段 | 形状 | 数据类型 | 说明 |
|-------|-------|-------|-------------|
| `token_state` | `[D]` | `f32` / `f64` | 动作 token 数组（维度必须与观测配置中的编码器 `dimension` 匹配） |

**可选字段：**

| 字段 | 形状 | 数据类型 | 说明 |
|-------|-------|-------|-------------|
| `frame_index` | `[1]` | `i32` / `i64` | 帧索引（仅用于日志记录，不影响播放） |
| `left_hand_joints` | `[7]` 或 `[1, 7]` | `f32` / `f64` | 左手 7-DOF Dex3 关节位置 |
| `right_hand_joints` | `[7]` 或 `[1, 7]` | `f32` / `f64` | 右手 7-DOF Dex3 关节位置 |
| `body_quat_w` | `[4]` 或 `[1, 4]` | `f32` / `f64` | 用于更新朝向的身体四元数（w,x,y,z） |

- `token_state` 的维度会与编码器配置进行校验。不匹配时会记录为警告。
- 提供手部关节时，会直接应用到机器人（与 v1–v3 的可选手部字段相同）。
- `body_quat_w` 可用于在 token 串流期间更新朝向参考。

**常见错误：**
- `Version 4 missing required field 'token_state'` —— 消息中缺少 `token_state` 字段。
- `Protocol version 4 with motion data is impossible!` —— v4 消息产生了动作序列（不应发生；表明解码器有 bug）。
- `Protocol version 4 with empty token data!` —— `token_state` 字段存在但无数据。

```{warning}
协议 v4 要求策略的观测配置中包含带有 `token_state` 的编码器配置。如果模型没有编码器（`encode_mode == -2`），token 会被接收但不会产生效果。
```

### 协议总结

| 协议 | 编码模式 | SONIC 使用 | 必需字段 |
|----------|-------------|---------------|-----------------|
| v1 | `0`（基于关节） | ✅ 是 | `joint_pos`, `joint_vel` |
| v2 | `2`（基于 SMPL） | ❌ 仅自定义 | `smpl_joints`, `smpl_pose` |
| v3 | `2`（基于 SMPL） | ✅ 是 | `joint_pos`, `joint_vel`, `smpl_joints`, `smpl_pose` |
| v4 | N/A（绕过编码器） | ✅ 是 | `token_state` |

## 可选串流字段

以下可选字段可包含在任何协议版本中：

| 字段 | 形状 | 数据类型 | 说明 |
|-------|-------|-------|-------------|
| `left_hand_joints` | `[7]` 或 `[1, 7]` | `f32` / `f64` | 左手 7-DOF Dex3 关节位置 |
| `right_hand_joints` | `[7]` 或 `[1, 7]` | `f32` / `f64` | 右手 7-DOF Dex3 关节位置 |
| `vr_position` | `[9]` 或 `[3, 3]` | `f32` / `f64` | VR 3 点追踪位置：左手腕、右手腕、头部（xyz × 3） |
| `vr_orientation` | `[12]` 或 `[3, 4]` | `f32` / `f64` | VR 3 点朝向：左、右、头部四元数（wxyz × 3） |
| `catch_up` | 标量 | `bool` / `u8` / `i32` | 如果为 `true`（默认），检测到较大帧间隙时重置播放 |
| `heading_increment` | 标量 | `f32` / `f64` | 每条消息应用的增量朝向调整 |

## 配置

| 参数 | 默认值 | 说明 |
|------|---------|-------------|
| `--zmq-host` | `localhost` | ZMQ 发布者主机 |
| `--zmq-port` | `5556` | ZMQ 发布者端口 |
| `--zmq-topic` | `pose` | ZMQ 主题前缀 |
| `--zmq-conflate` | off | 仅保留最新消息（丢弃过时帧） |
