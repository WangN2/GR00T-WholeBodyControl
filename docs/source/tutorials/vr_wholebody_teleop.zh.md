# PICO VR 全身遥操作

使用 PICO VR 头显和手柄进行完整的全身遥操作。部署时使用 `--input-type zmq_manager` 选项。`zmq_manager` 输入类型可在**规划器模式**（通过 ZMQ 发送 locomotion 指令）和**流式动作模式**（来自 PICO 的全身 SMPL 姿势）之间切换。

```{admonition} 安全警告
:class: danger
全身遥操作涉及快速、敏捷的动作。**始终**保持清晰的安全区域，并让安全操作员在键盘前随时准备触发紧急停止（C++ 终端中按 **`O`**，或 PICO 手柄上按 **A+B+X+Y**）。

**你必须穿着紧身裤或打底裤**，以保证脚部追踪器的视线 —— 宽松或肥大的衣物可能导致追踪不可预测地失效，从而引发危险动作。
```

```{video} ../_static/teleop/teleop_session_overview.mp4
:width: 100%
```
*视频：端到端遥操作 walkthrough —— PICO 校准、启动策略、以及机器人独立平衡。详细的操作最佳实践请参阅[遥操作指南](../user_guide/teleoperation.md)。*

## 前置条件

1. **已完成[快速开始](../getting_started/quickstart.md)** —— 你能够运行 sim2sim 循环。
2. **已完成[VR 遥操作设置](../getting_started/vr_teleop_setup.md)** —— PICO 硬件已安装、校准、连接，且 `.venv_teleop` 已准备就绪。

---

## 分步指南：在仿真中遥操作

运行**三个终端**来遥操作仿真机器人。

### 终端 1 — 在 MuJoCo 仿真器中启动虚拟机器人

从**仓库根目录**：

```bash
# bash install_scripts/install_pico.sh

source .venv_teleop/bin/activate
python gear_sonic/scripts/run_sim_loop.py
```

### 终端 2 — C++ 部署

从 `gear_sonic_deploy/`：

```bash
cd gear_sonic_deploy
source scripts/setup_env.sh
./deploy.sh --input-type zmq_manager sim
# 等待出现 "Init done"
```

```{note}
`--zmq-host` 参数默认为 `localhost`，当 C++ 部署脚本和遥操作脚本（终端 3）在同一台机器上运行时这是正确的。如果遥操作脚本运行在另一台机器上，请传递 `--zmq-host <teleop-machine-ip>`。
```

### 终端 3 — PICO 遥操作串流端

从**仓库根目录**：

```bash
source .venv_teleop/bin/activate

# 带完整可视化（首次运行推荐）：
python gear_sonic/scripts/pico_manager_thread_server.py --manager \
    --vis_vr3pt --vis_smpl

# 无可视化（无头/机载练习）：
# python gear_sonic/scripts/pico_manager_thread_server.py --manager
```

开启可视化后，等待弹出一个窗口，显示一个所有关节处于默认角度的 Unitree G1 网格。如果没有窗口弹出，请仔细检查[VR 遥操作设置](../getting_started/vr_teleop_setup.md)中 PICO 的 XRoboToolKit IP 配置。

### 你的第一次遥操作会话

1. **摆出校准姿势** —— 站直，双脚并拢，上臂贴紧身体两侧，前臂向前弯曲 90°（每个肘部呈 L 形），手掌朝内。详情请参见[校准姿势](#calibration-pose)。
2. 同时按 **A + B + X + Y** 启动控制策略并运行初始完整校准（`CALIB_FULL`）。
3. 将你的手臂与机器人当前的姿势对齐，然后按 **A + X** 进入全身 SMPL 遥操作（**POSE** 模式）。移动你的手臂和腿部 —— 机器人会跟随。
4. 再次按 **A + X** 回退到 **PLANNER**（idle）模式。
5. 再次按 **A + B + X + Y** 停止机器人。

<figure style="margin: 1em 0;">
<video width="100%" autoplay loop muted playsinline style="border-radius: 8px;">
  <source src="../_static/teleop_calib/basic_flow_web.mp4" type="video/mp4">
</video>
<figcaption style="text-align: center; font-style: italic; margin-top: 0.5em;">基本全身遥操作流程：校准姿势 → 启动 → POSE 模式 → PLANNER idle → 停止。</figcaption>
</figure>

---

(pico-controls)=

## 完整的 PICO 控制说明

### 模式与校准

系统有**4 种运行模式**和**2 种校准类型**。

**模式：**

| 模式 | 编码器 | 说明 |
|---|---|---|
| **OFF** | -- | 策略未运行。摆出[校准姿势](#calibration-pose)，然后按 **A+B+X+Y** 启动策略。 |
| **POSE** | SMPL | 全身遥操作 —— 将 PICO 的 SMPL 姿势串流到 C++ 部署端。你的动作会直接映射到机器人。 |
| **PLANNER** | G1 | 运动学规划器激活；上半身由规划器控制。摇杆控制行走和奔跑模式下的方向和朝向。 |
| **PLANNER_FROZEN_UPPER** | G1 | 规划器 locomotion；上半身冻结在最后一次 POSE 快照。 |
| **VR_3PT** | TELEOP | 规划器 locomotion；上半身跟随 VR 3 点追踪（头 + 双手）。依赖非 IK 的 VR 3 点校准。 |

**校准类型**（非 IK 工作流，用于最小延迟）：

| 类型 | 校准内容 | 触发时机 |
|---|---|---|
| **CALIB_FULL** | 头部 + 双手腕 对齐 **全零**参考姿势。 | 首次 **A+B+X+Y**（启动时）。 |
| **CALIB** | 仅双手腕 对齐 **当前机器人姿势**。 | 每次通过 **左摇杆按下** 进入 VR_3PT 时。 |

### 状态机

共有 4 种模式和 2 条控制链。每条链形成一个三角形：**A+X**（或 **B+Y**）可从规划器节点及其 VR_3PT 子模式返回 POSE。

```text
  ┌──────────────────────────────────────┐
  │  A+B+X+Y (任意模式) ──► OFF          │
  └──────────────────────────────────────┘

  启动：
    OFF ──(A+B+X+Y)──► PLANNER ──(A+X)──► POSE
          CALIB_FULL

  链 1 — G1 编码器监听规划器生成的全身动作：PLANNER

    PLANNER ─── L-Stick (+CALIB) ──► VR_3PT
     ▲    │ ◄─────── L-Stick ─────────  │
     │    │                             │
     │A+X │A+X                    A+X   │
     │    ▼                             ▼
     └─ POSE ◄──────────────────────────┘

  链 2 — G1 编码器监听规划器生成的下半身动作：PLANNER_FROZEN_UPPER

    PLANNER_FROZEN_UPPER ── L-Stick (+CALIB) ──► VR_3PT
         ▲     │ ◄──────── L-Stick ──────────     │
         │     │                                  │
         │B+Y  │B+Y                          B+Y  │
         │     ▼                                  ▼
         └── POSE ◄───────────────────────────────┘
```

```{admonition} 危险 —— 模式切换安全
:class: danger
**在切换到 POSE 或 VR_3PT 之前，务必先将你的身体与机器人当前的姿势对齐！！**

- **POSE：** 机器人会立即跳到你当前的物理姿势。如果差异很大，会导致突然的剧烈动作。
- **VR_3PT：** 校准错位会导致一旦你移动手臂，机器人就产生不稳定且危险的动作。更多信息请参见 [per-switch-calib](#per-switch-calib) 部分。
```

(calibration-pose)=

### VR_3PT 校准提示

`VR_3PT` 模式依赖于精确的校准。会发生两次校准事件：

#### 一次性 `CALIB_FULL`（头 + 手腕）

在首次按 **A + B + X + Y** 之前，你**必须**摆出机器人的**全零参考姿势**。系统会将你的 PICO 身体追踪帧捕获为所有后续动作映射的零参考。

**参考姿势：**
1. **站直**，双脚并拢，正视前方。
2. **上臂**自然下垂，贴近躯干。
3. **前臂**向前弯曲 90°（每个肘部呈 L 形），手掌朝内。

```{tip}
启动遥操作脚本时带上 `--vis_vr3pt`，可以在可视化窗口中看到机器人的参考姿势。在按下启动组合键之前，让你的身体与它匹配。
```

(per-switch-calib)=
#### 每次切换的 `CALIB`（仅手腕）

每次你通过 **左摇杆按下** 进入 `VR_3PT` 时，系统会根据机器人的**当前**姿势重新校准双手腕。在点击前务必将你的手臂与机器人对齐。

下面是一个**错误校准实践**的示例 —— 在未将手臂与机器人当前姿势对齐的情况下切换到 VR_3PT。机器人可能不会立即跳动，但你一旦移动就会产生不稳定且危险的动作。

<figure style="margin: 1em 0;">
<video width="100%" autoplay loop muted playsinline style="border-radius: 8px;">
  <source src="../_static/teleop_calib/BAD_Calib_VR3PT_web.mp4" type="video/mp4">
</video>
<figcaption style="text-align: center; font-style: italic; margin-top: 0.5em;">错误实践：未对齐手臂就进入 VR_3PT 会导致不稳定、不安全的动作。</figcaption>
</figure>

```{admonition} 危险 —— 模式切换安全
:class: danger
**在切换到 POSE 或 VR_3PT 之前，务必将你的身体与机器人当前的姿势对齐。**

**从错误 VR_3PT 校准中恢复：**
1. 冻结上半身 —— 再次按 **左摇杆按下** 返回。
2. 重新将你的手臂与机器人当前（可能已经变形的）姿势对齐。
3. 切换到 **POSE** 模式（**A+X**）以重置。
```

如果你不小心进入了错误校准的 VR_3PT 状态，下面是**恢复流程** —— 冻结上半身（左摇杆按下返回），然后切换到 POSE 模式（A+X）以安全重置。

<figure style="margin: 1em 0;">
<video width="100%" autoplay loop muted playsinline style="border-radius: 8px;">
  <source src="../_static/teleop_calib/BAD_Calib_VR3PT_recover_web.mp4" type="video/mp4">
</video>
<figcaption style="text-align: center; font-style: italic; margin-top: 0.5em;">从错误 VR_3PT 校准中恢复：冻结上半身 → 重新对齐 → 切换到 POSE 模式。</figcaption>
</figure>

### 快速入门备忘单

| 动作 | 按键 | 说明 |
|---|---|---|
| **启动 / 停止策略** | **A+B+X+Y** | 首次按下：启动 + CALIB_FULL。再次按下：紧急停止 → OFF。 |
| **切换 POSE** | **A+X** | 在 PLANNER ↔ POSE 之间切换。或从 VR_3PT（通过 PLANNER 进入）→ POSE。 |
| **切换 PLANNER_FROZEN_UPPER** | **B+Y** | 在 POSE ↔ PLANNER_FROZEN_UPPER 之间切换。或从 VR_3PT（通过 PLANNER_FROZEN_UPPER 进入）→ POSE。 |
| **切换 VR_3PT** | **左摇杆按下** | 从任意 Planner 模式 → VR_3PT（触发 CALIB）。再次按下返回。 |
| **手部抓取** | **扳机键**（每只手） | 控制对应手的抓取。 |

### 摇杆控制（规划器模式）

在 **PLANNER**、**PLANNER_FROZEN_UPPER** 和 **VR_3PT** 中生效：

| 输入 | 功能 |
|---|---|
| **左摇杆** | 移动方向（前 / 后 / 平移） |
| **右摇杆（水平方向）** | Yaw / 朝向（连续累积） |
| **A + B** | 下一个 locomotion 模式 |
| **X + Y** | 上一个 locomotion 模式 |

**Locomotion 模式**（通过 A+B / X+Y 循环）：

| ID | 模式 |
|---|---|
| 0 | Idle [默认] |
| 1 | Slow Walk |
| 2 | Walk |
| 3 | Run |
| 4 | Squat |
| 5 | Kneel (two legs) |
| 6 | Kneel |
| 7 | Lying face-down |
| 8 | Crawling |
| 9–16 | Boxing 变体（idle、walk、punches、hooks） |
| 17 | Forward Jump |
| 18 | Stealth Walk |
| 19 | Injured Walk |

---

## 紧急停止

| 方法 | 动作 |
|---|---|
| **PICO 手柄** | 同时按 **A+B+X+Y** → OFF |
| **键盘**（C++ 终端） | 按 **`O`** 立即停止 |

---

## 分步指南：在真实机器人上遥操作

```{admonition} 安全警告
:class: danger
只有在能够流畅控制仿真中的机器人并熟悉紧急停止后，才能继续。**请先终止所有正在运行的 `run_sim_loop.py` 进程** —— 同时运行仿真和真实实例会产生冲突。
```

真实机器人的工作流程使用**两个终端**（无需 MuJoCo 仿真器）。

### 终端 1 — C++ 部署（真实机器人）

从 `gear_sonic_deploy/`：

```bash
cd gear_sonic_deploy
source scripts/setup_env.sh

# 'real' 会自动检测机器人网络接口（192.168.123.x）。
# 如果自动检测失败，直接传递 G1 的 IP：
#   ./deploy.sh --input-type zmq_manager <G1-IP>
./deploy.sh --input-type zmq_manager real

# 等待出现 "Init done"
```

```{note}
如果遥操作脚本（终端 2）运行在另一台机器上，请添加 `--zmq-host <IP-of-teleop-machine>`，以便 C++ 端知道 ZMQ 发布者的位置。
```

### 终端 2 — PICO 遥操作串流端

从**仓库根目录**：

```bash
source .venv_teleop/bin/activate
python gear_sonic/scripts/pico_manager_thread_server.py --manager

# 如果在带显示器的外接机上运行，可添加可视化：
#   --vis_vr3pt --vis_smpl
```

```{note}
启动前，请在 PICO 的 XRoboToolKit 应用中更新 IP，使其与当前机器匹配。
```

启动序列与仿真相同：校准姿势 → **A+B+X+Y** → **A+X** 进入 POSE 模式。所有可用命令请参见[完整的 PICO 控制说明](#pico-controls)。
