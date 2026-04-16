# 使用键盘进行动作追踪与运动学规划

<figure style="margin: 1em 0;">
<video width="100%" autoplay loop muted playsinline style="border-radius: 8px;">
  <source src="../_static/kinematic_planner/Navigation.mp4" type="video/mp4">
</video>
<figcaption style="text-align: center; font-style: italic; margin-top: 0.5em;">野外导航演示：使用键盘控制运动学规划器。</figcaption>
</figure>

```{video} ../_static/Keyboard_Guidance.mp4
:width: 100%
```
*视频：键盘控制 walkthrough —— 启动控制系统、播放参考动作、以及使用规划器模式进行实时 locomotion。*

使用键盘命令控制机器人播放参考动作并运行基于规划器的 locomotion（使用 `--input-type keyboard`）。

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
bash deploy.sh --input-type keyboard sim
```

**真实机器人：**

```bash
# 在 gear_sonic_deploy/ 目录下
bash deploy.sh --input-type keyboard real
```

## 分步指南：普通模式（参考动作追踪）

普通模式播放预加载的参考动作。这是程序启动时的默认模式。

1. 在终端 2 中，按 **`]`** 启动控制系统。
2. 在 MuJoCo 窗口中，按 **`9`** 将机器人放到地面。
3. 回到终端 2，按 **`T`** 播放当前参考动作 —— 机器人将执行到完成。
4. 按 **`N`** 切换到下一个动作序列，或按 **`P`** 切换到上一个。
5. 再次按 **`T`** 播放新动作。
6. 要重播同一动作，在它完成后再次按 **`T`**。要在动作中途停止并返回第一帧，按 **`R`** —— 机器人在第一帧暂停且不终止策略。
7. 使用 **`Q`** / **`E`** 微调左右朝向（每次 ±π/12 rad）。
8. 按 **`I`** 重新初始化基座四元数并将朝向重置为零，即机器人会将当前朝向视为参考动作第一帧的朝向。
9. 完成后，按 **`O`** 停止控制并退出。

## 分步指南：规划器模式（实时动作生成）

规划器模式让你可以实时控制机器人 —— 选择 locomotion 风格，用 WASD 控制方向，并动态调整速度和高度。

1. 在普通模式下，按 **`ENTER`** 切换到规划器模式。终端将打印 `Planner enabled`。
2. 机器人默认进入 **Locomotion** 动作集。按 **`1`** 为慢走，**`2`** 为行走，**`3`** 为奔跑。
3. 按 **`W`** 向前走。机器人使用动量系统 —— 按住方向键会将动量设为满值；松开后机器人会逐渐减速并返回 idle。
4. 用 **`A`** / **`D`** 控制方向（同时调整朝向和移动方向），或用 **`Q`** / **`E`** 原地转向（每次 ±π/6 rad，仅调整朝向）。
5. 按 **`,`** / **`.`** 进行左右平移。
6. 按 **`S`** 向后移动。
7. 用 **`9`**（减小）/ **`0`**（增大）调整速度。速度范围取决于当前模式（见下表）。
8. 按 **`N`** 切换到下一个动作集（Locomotion → Squat → Boxing → Styled Walking → …）。用 **`P`** 返回上一个。
9. 在一个动作集中，按 **`1`**–**`8`** 选择特定模式（见下方的动作集部分）。
10. 对于下蹲类模式，用 **`-`**（降低）/ **`=`**（升高）调整身体高度，限制在 0.2–0.8 m。
11. 如果需要立即 halt，按 **`R`**、**`` ` ``** 或 **`~`** —— 这会立即将移动动量重置为零。
12. 再次按 **`ENTER`** 返回普通模式，或按 **`O`** 停止并退出。

## 控制参考

### 系统控制（两种模式通用）

| 按键 | 动作 |
|-----|--------|
| **]** | 启动控制系统 |
| **O** | 停止控制并退出（紧急停止） |
| **ENTER** | 在普通 / 规划器模式间切换 |
| **I** | 重新初始化基座四元数并重置朝向 |
| **Z** | 切换编码器模式（在模式 0 和模式 1 之间切换，如果编码器已加载） |
| **F** | 报告电机温度（TTS 语音播报） |

### 普通模式按键

| 按键 | 动作 |
|-----|--------|
| **T** | 播放当前动作到完成 |
| **R** | 从开头重启当前动作（暂停在第 0 帧） |
| **P** / **N** | 上一个 / 下一个动作序列 |
| **Q** / **E** | 在策略层面调整 delta 朝向 左 / 右（±π/12 rad） |

### 规划器模式按键

**移动：**

| 按键 | 动作 |
|-----|--------|
| **W** / **S** | 向前 / 向后移动 |
| **A** / **D** | 轻微调整朝向并向前移动（左 / 右） |
| **,** / **.** | 左右平移 |

**朝向：**

| 按键 | 动作 |
|-----|--------|
| **Q** / **E** | 在规划器层面调整朝向 左 / 右（±π/6 rad） |
| **J** / **L** | 在策略层面调整 delta 朝向 左 / 右（±π/12 rad） |

**模式与速度：**

| 按键 | 动作 |
|-----|--------|
| **N** / **P** | 下一个 / 上一个动作集 |
| **1**–**8** | 选择当前动作集内的模式 |
| **9** / **0** | 减小 / 增加移动速度 |
| **-** / **=** | 减小 / 增加高度（非站立动作集，0.2–0.8 m） |
| **T** | 播放动作 |

**紧急：**

| 按键 | 动作 |
|-----|--------|
| **R** / **`** / **~** | 紧急停止（立即重置动量） |

## 动作集

**动作集（motion set）**是一组相关的移动风格（例如 locomotion、手势或蹲伏）。选择动作集内的模式会让机器人以该风格行动。每个动作集最多包含八个可选模式。

用 **`N`**（下一个）/ **`P`**（上一个）在动作集间循环。在每个动作集中，按 **`1`**–**`8`** 选择模式。有关底层规划器模型、模式索引和输入/输出规范的更多细节，请参阅[运动学规划器 ONNX 模型参考](../references/planner_onnx.md)。

### 动作集 0 — Locomotion（站立）

| 按键 | 模式 | 速度范围 |
|-----|------|-------------|
| **1** | Slow Walk | 0.2–0.8 m/s |
| **2** | Walk | — |
| **3** | Run | 1.5–3.0 m/s |
| **4** | Happy | — |
| **5** | Stealth | — |
| **6** | Injured | — |

```{tip}
使用 **`,`** / **`.`** 进行横向（侧步）移动时，建议将目标速度保持在约 **0.4 m/s**。侧步时速度过高可能导致机器人双脚碰撞，因为横向步态需要交叉摆腿。
```

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1em; margin: 1em 0;">
<figure style="margin: 0;">
<video width="100%" autoplay loop muted playsinline style="border-radius: 8px;">
  <source src="../_static/kinematic_planner/planner_happy.mp4" type="video/mp4">
</video>
<figcaption style="text-align: center; font-style: italic; margin-top: 0.5em;">Happy 风格行走。</figcaption>
</figure>
<figure style="margin: 0;">
<video width="100%" autoplay loop muted playsinline style="border-radius: 8px;">
  <source src="../_static/kinematic_planner/planner_stealth.mp4" type="video/mp4">
</video>
<figcaption style="text-align: center; font-style: italic; margin-top: 0.5em;">Stealth 风格行走。</figcaption>
</figure>
<figure style="margin: 0;">
<video width="100%" autoplay loop muted playsinline style="border-radius: 8px;">
  <source src="../_static/kinematic_planner/planner_injured.mp4" type="video/mp4">
</video>
<figcaption style="text-align: center; font-style: italic; margin-top: 0.5em;">Injured 风格行走。</figcaption>
</figure>
<figure style="margin: 0;">
<video width="100%" autoplay loop muted playsinline style="border-radius: 8px;">
  <source src="../_static/kinematic_planner/planner_run.mp4" type="video/mp4">
</video>
<figcaption style="text-align: center; font-style: italic; margin-top: 0.5em;">Running locomotion 模式。</figcaption>
</figure>
</div>

### 动作集 1 — Squat / Ground

高度可用 **`-`** / **`=`** 调整（0.2–0.8 m）。进入此动作集时默认高度为 0.8 m。

| 按键 | 模式 | 速度范围 |
|-----|------|-------------|
| **1** | Squat | static |
| **2** | Kneel (Two Legs) | static |
| **3** | Kneel (One Leg) | static |
| **4** | Hand Crawling | 0.4–1.0 m/s |
| **5** | Elbow Crawling | 0.7–1.0 m/s |

<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1em; margin: 1em 0;">
<figure style="margin: 0;">
<video width="100%" autoplay loop muted playsinline style="border-radius: 8px;">
  <source src="../_static/kinematic_planner/planner_kneeling.mp4" type="video/mp4">
</video>
<figcaption style="text-align: center; font-style: italic; margin-top: 0.5em;">Kneeling 模式，支持可变高度控制。</figcaption>
</figure>
<figure style="margin: 0;">
<video width="100%" autoplay loop muted playsinline style="border-radius: 8px;">
  <source src="../_static/kinematic_planner/hand_crawling.mp4" type="video/mp4">
</video>
<figcaption style="text-align: center; font-style: italic; margin-top: 0.5em;">Hand crawling locomotion。</figcaption>
</figure>
<figure style="margin: 0;">
<video width="100%" autoplay loop muted playsinline style="border-radius: 8px;">
  <source src="../_static/kinematic_planner/planner_elbow_crawling.mp4" type="video/mp4">
</video>
<figcaption style="text-align: center; font-style: italic; margin-top: 0.5em;">Elbow crawling locomotion。</figcaption>
</figure>
</div>

### 动作集 2 — Boxing

| 按键 | 模式 | 速度范围 |
|-----|------|-------------|
| **1** | Idle Boxing | static |
| **2** | Walk Boxing | 0.7–1.5 m/s |
| **3** | Left Jab | 0.7–1.5 m/s |
| **4** | Right Jab | 0.7–1.5 m/s |
| **5** | Random Punches | 0.7–1.5 m/s |
| **6** | Left Hook | 0.7–1.5 m/s |
| **7** | Right Hook | 0.7–1.5 m/s |

<figure style="margin: 1em 0;">
<video width="100%" autoplay loop muted playsinline style="border-radius: 8px;">
  <source src="../_static/kinematic_planner/planner_boxing.mp4" type="video/mp4">
</video>
<figcaption style="text-align: center; font-style: italic; margin-top: 0.5em;">Boxing 模式演示。</figcaption>
</figure>

### 动作集 3 — 其他风格行走

| 按键 | 模式 |
|-----|------|
| **1** | Careful |
| **2** | Object Carrying |
| **3** | Crouch |
| **4** | Happy Dance |
| **5** | Zombie |
| **6** | Point |
| **7** | Scared |

## 移动动量系统

键盘模式中的规划器使用基于动量的移动系统：
- 按下方向键（**W/S/A/D/,/.**）会将动量设为 **1.0**（全速）。
- 每帧没有方向键按下时，动量会乘性衰减（×0.999）。
- 当动量降至 **0.1** 以下时，机器人会过渡到 idle（Locomotion 动作集）或保持当前的静态姿势（Squat 和 Boxing 动作集）。
- 紧急停止（**R/`/~**）会立即将动量重置为零。

这意味着你不需要一直按住键 —— 单次按压即可开始移动，机器人会自然滑行停止。
