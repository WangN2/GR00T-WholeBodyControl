# 解耦 WBC

面向多台人形平台的运控操作实验软件栈，主要支持宇树 G1。本仓库提供全身控制策略、遥操作栈和数据导出器。

---

## 系统安装

### 前置条件
- Ubuntu 22.04
- 安装了较新驱动的 NVIDIA GPU
- Docker 和 NVIDIA Container Toolkit（容器内 GPU 访问所需）

### 仓库设置

安装 Git 和 Git LFS：

```bash
sudo apt update
sudo apt install git git-lfs
git lfs install
```

克隆仓库：

```bash
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/NVlabs/GR00T-WholeBodyControl.git
cd decoupled_wbc
```

### Docker 环境

我们提供了预装所有依赖的 Docker 镜像。

安装新镜像并启动容器：

```bash
./docker/run_docker.sh --install --root
```

这会从 `docker.io/nvgear` 拉取最新的 `decoupled_wbc` 镜像。

启动或重新进入容器：

```bash
./docker/run_docker.sh --root
```

使用 `--root` 以 `root` 用户身份运行。要以普通用户运行，请在本地构建镜像：

```bash
./docker/run_docker.sh --build
```

---

## 运行控制栈

进入容器后，可以直接启动控制策略。

- 仿真：

```bash
python decoupled_wbc/control/main/teleop/run_g1_control_loop.py
```

- 真实机器人：确保主机网络按照 [G1 SDK 开发指南](https://support.unitree.com/home/en/G1_developer) 进行配置，并在 `192.168.123.222` 设置静态 IP，子网掩码 `255.255.255.0`：

```bash
python decoupled_wbc/control/main/teleop/run_g1_control_loop.py --interface real
```

键盘快捷键（终端窗口）：
- `]`：激活策略
- `o`：停用策略
- `9`：释放/固定机器人
- `w` / `s`：前进/后退
- `a` / `d`：左/右平移
- `q` / `e`：左/右旋转
- `z`：导航命令归零
- `1` / `2`：提高/降低基座高度
- `backspace`（查看器）：在可视化工具中重置机器人

---

## 运行遥操作栈

遥操作策略主要使用 Pico 控制器进行手部与身体的协调控制。它还支持其他遥操作设备，包括 LeapMotion 和带有任天堂 Switch Joy-Con 控制器的 HTC Vive。

保持 `run_g1_control_loop.py` 运行，在另一个终端运行：

```bash
python decoupled_wbc/control/main/teleop/run_teleop_policy_loop.py --hand_control_device=pico --body_control_device=pico
```

### Pico 设置与控制

按照 [XR Robotics 指南](https://github.com/XR-Robotics) 在 Pico 头显上配置遥操作应用。

所需的 PC 软件已预装在 Docker 容器中。只需要 [XRoboToolkit-PC-Service](https://github.com/XR-Robotics/XRoboToolkit-PC-Service) 组件。

前置条件：将 Pico 连接到与主机相同的网络。

控制器绑定：
- `menu + left trigger`：切换下半身策略
- `menu + right trigger`：切换上半身策略
- `左摇杆`：X/Y 平移
- `右摇杆`：偏航旋转
- `L/R 扳机`：控制手部夹爪

Pico 单元测试：

```bash
python decoupled_wbc/control/teleop/streamers/pico_streamer.py
```

---

## 运行数据收集栈

通过部署助手运行完整栈（控制循环、遥操作策略和相机转发器）：

```bash
python decoupled_wbc/scripts/deploy_g1.py \
    --interface sim \
    --camera_host localhost \
    --sim_in_single_process \
    --simulator robocasa \
    --image-publish \
    --enable-offscreen \
    --env_name PnPBottle \
    --hand_control_device=pico \
    --body_control_device=pico
```

会创建 `tmux` 会话 `g1_deployment`，包含以下窗格：
- `control_data_teleop`：主控制循环、数据收集和遥操作策略
- `camera`：相机转发器
- `camera_viewer`：可选实时相机画面

在 `controller` 窗口（`control_data_teleop` 窗格，左侧）的操作：
- `]`：激活策略
- `o`：停用策略
- `k`：重置仿真和策略
- `` ` ``：终止 tmux 会话
- `ctrl + d`：退出窗格中的 shell

在 `data exporter` 窗口（`control_data_teleop` 窗格，右上）的操作：
- 输入任务提示

Pico 控制器操作：
- `A`：开始/停止录制
- `B`：丢弃轨迹
