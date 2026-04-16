# 快速开始

在几分钟内上手 SONIC！

首先，请确保你已经完成了[安装指南](installation_deploy)。

```{admonition} 安全警告
:class: danger
机器人可能具有危险性。请确保周围有清晰的安全区域，让安全操作员随时准备在键盘前触发紧急停止，并自行承担使用本软件的风险。作者和贡献者对因使用或误用本项目造成的任何损坏、伤害或损失不承担责任。
```

## IsaacLab 评估

敬请期待！

## MuJoCo 中的 Sim2Sim

<video width="100%" autoplay loop muted playsinline style="border-radius: 8px; margin: 1em 0;">
  <source src="../_static/sim2sim.mp4" type="video/mp4">
</video>

要在 MuJoCo 仿真器中测试，请在不同的终端中运行仿真循环和部署脚本。

```{note}
MuJoCo 仿真器（终端 1）在宿主机上的 Python 虚拟环境中运行 —— **不在** Docker 容器内。部署二进制文件（终端 2）可以在宿主机上原生运行，也可以在 Docker 容器内运行。如果你使用 Docker，请在宿主机上运行终端 1，在容器内运行终端 2。
```

### 一次性设置：安装 MuJoCo 仿真环境

在**宿主机**（Docker 外部）上，从**仓库根目录**（`GR00T-WholeBodyControl/`）运行：

```sh
bash install_scripts/install_mujoco_sim.sh
```

这会创建一个轻量级的 `.venv_sim` 虚拟环境，仅包含仿真器所需的包（MuJoCo、Pinocchio、Unitree SDK2 等）。

### 运行 sim2sim 循环

我们强烈建议在真实硬件上部署之前，先在仿真中运行此流程并熟悉控制方式。

**终端 1 — MuJoCo 仿真器**（宿主机，从仓库根目录）：

```sh
source .venv_sim/bin/activate
python gear_sonic/scripts/run_sim_loop.py
```

**终端 2 — 部署**（宿主机或 Docker，从 `gear_sonic_deploy/`）：

```sh
bash deploy.sh sim
```

**开始控制：**

1. 在终端 2（deploy.sh）中，按 **`]`** 启动策略。
2. 点击 MuJoCo 查看器窗口，按 **`9`** 将机器人放到地面。
3. 回到终端 2。按 **`T`** 播放当前参考动作 —— 机器人将执行到完成。
4. 按 **`N`** 或 **`P`** 切换到下一个或上一个动作序列。
5. 再次按 **`T`** 播放新动作。
6. 动作完成后，你可以再次按 **`T`** 重播同一动作。如果你想停止并回到当前动作的第一帧，按 **`R`** 从头开始重启。这可用于在不终止策略的情况下停止动作。
7. 完成或需要**紧急停止**时，按 **`O`** 停止控制并退出。

更多控制方式，请参阅 [键盘](../tutorials/keyboard.md)、[手柄](../tutorials/gamepad.md)、[ZMQ 串流](../tutorials/zmq.md) 和 [接口管理器](../tutorials/manager.md) 教程。

## 真实机器人

要在真实的 G1 机器人上部署，请运行：

```sh
./deploy.sh real
```

## 在线可视化

启动可视化工具并连接到正在运行的 `g1_deploy` 可执行文件：

```sh
python visualize_motion.py --realtime_debug_url tcp://localhost:5557
```

注意：
- 默认端口：5557（使用 `--zmq-out-port <port>` 更改）
- 默认主题：`g1_debug`（在可执行文件上使用 `--zmq-out-topic <topic>` 更改，在可视化工具上使用 `--realtime_debug_topic <topic>` 更改）
- 对于物理机器人，将 `localhost` 替换为机器人的 IP 地址

有关离线动作 CSV 可视化和日志记录的详细信息，请参阅[部署代码与程序流程](../references/deployment_code.md)。

更多高级用法，请参阅 [键盘](../tutorials/keyboard.md)、[手柄](../tutorials/gamepad.md)、[ZMQ 串流](../tutorials/zmq.md)、[VR 全身遥操作](../tutorials/vr_wholebody_teleop.md) 和 [接口管理器](../tutorials/manager.md) 教程。
