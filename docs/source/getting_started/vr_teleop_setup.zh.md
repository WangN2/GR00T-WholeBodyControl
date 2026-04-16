# VR 遥操作设置（PICO）

本页介绍 PICO VR 全身遥操作的一次性硬件和软件设置。完成这些步骤后，请前往 [ZMQ Manager 教程](../tutorials/vr_wholebody_teleop.md) 在仿真或真实硬件上运行遥操作。

---

## 所需硬件

- [PICO 4 / PICO 4 Pro 头显](https://www.picoxr.com/global/products/pico4)
- [2x PICO 手柄](https://www.picoxr.com/global/products/pico4)
- [2x PICO 动作追踪器](https://www.picoxr.com/global/products/pico-motion-tracker)（绑在脚踝上）
- 高速、低延迟的 Wi-Fi 连接；遥操作性能严重依赖网络质量。

---

## 步骤 1：安装 XRoboToolkit

XRoboToolkit 包含 PC 服务端（运行在你的工作站上）和 PICO 应用端（运行在头显上），用于流式传输身体追踪数据。

### PC 服务端

1. 访问 [https://github.com/XR-Robotics](https://github.com/XR-Robotics)。
2. 按照 **"Install XRoboToolkit-PC-Service"** 的说明在工作站上安装 PC 服务端。
3. 对于机载部署，运行 `sudo dpkg -i gear_sonic_deploy/thirdparty/roboticsservice_1.0.0.0_arm64.deb`

### PICO 应用

1. 戴上 PICO 头显，开始设置和安装过程。
2. 在 PICO 上完成快速设置。
3. 确保 PICO 已连接到 Wi-Fi。
4. 在 PICO 中打开浏览器应用。
5. 在搜索栏中输入 **"xrobotoolkit"** 并选择 GitHub 页面 [https://github.com/XR-Robotics](https://github.com/XR-Robotics)。

```{image} ../_static/pico_setup/google_search_screenshot.png
:width: 600px
:align: center
```

6. 确保已启用 **开发者模式**（设置 → 开发者）。
7. **【在 PICO 内】** 在 GitHub 页面向下滚动，直到看到 APK 下载选项，然后用 PICO 扳机键点击下载。

```{tip}
在 PICO 浏览器中下载 [XRoboToolkit-PICO-1.1.1.apk](https://github.com/XR-Robotics/XRoboToolkit-Unity-Client/releases/download/v1.1.1/XRoboToolkit-PICO-1.1.1.apk)。（[其他版本](https://github.com/XR-Robotics/XRoboToolkit-Unity-Client/releases)）
```

8. **【在 PICO 内】** 打开浏览器页面右上角的下载管理选项，点击打开 `XRoboToolkit-PICO-1.1.1.apk` 下载。
9. **【在 PICO 内】** 选择 **安装** —— 应用将出现在你库中的 **未知** 分类下。

---

## 步骤 2：动作追踪器设置

```{image} ../_static/pico_setup/pico_setup_screenshot.png
:width: 600px
:align: center
```

1. 将一个 PICO 动作追踪器绑在左脚踝，另一个绑在右脚踝。**把宽松的裤腿塞紧**，确保追踪器可见。确保带指示灯的一面朝上。
2. 进入 PICO 设置。在左侧菜单中，向下滚动到最后一项：**"开发者"**。确保 **"安全边界"** 已关闭。
   - 如果开发者选项未激活，连续点击 "软件" 直到它出现。
3. 点击 PICO 菜单中的 **Wi-Fi 图标**。会出现一个头显的图片。在头显上方，有一个动作追踪器的小圆形图标。如果没有图标，直接打开 **"动作追踪器"** 应用本身。
   - 头显和 2 个手柄会显示 —— 选择 **动作追踪器**（小圆圈）。
4. 每个追踪器旁边有一个 **"i"** 图标。点击它并**取消配对所有追踪器**。
5. 所有追踪器清除后，点击右上角的 **"配对"** 按钮。
6. 按住每个动作追踪器顶部的按钮 **6 秒钟**。进入配对模式后，指示灯将闪烁红蓝两色。

### 动作追踪器校准

1. 戴上 PICO 头显。
2. 按下蓝色的 **"校准"** 按钮，并按照两个校准序列操作：
   - **序列 1：** 站直，双手持手柄自然垂放在身体两侧。
   - **序列 2：** 低头看着脚上的动作追踪器，直到头显摄像头识别到它们。
3. 校准完成后，将 PICO 头显戴在额头上（确保 PICO 朝前，以继续检测动作追踪器）。

---

## 步骤 3：安装 PICO 遥操作环境

从**仓库根目录**运行：

```bash
bash install_scripts/install_pico.sh
```

这会创建一个 `.venv_teleop` 虚拟环境（Python 3.10），包含：
- `teleop` 额外依赖（ZMQ、Pinocchio、PyVista）
- `sim` 额外依赖（MuJoCo、tyro）
- XRoboToolkit SDK
- Unitree SDK2 Python 绑定

激活环境：

```bash
source .venv_teleop/bin/activate   # 提示符变为：(gear_sonic_teleop)
```

---

## 步骤 4：将 PICO 连接到你的工作站

1. 打开笔记本电脑/PC 和 PICO 的 Wi-Fi 设置，确保它们处于**同一 Wi-Fi 网络**。记下 Wi-Fi 的 IPv4 地址。
   - 要查找 PICO 的 Wi-Fi，选择菜单右下角的控制中心。

```{image} ../_static/pico_setup/internet.png
:width: 600px
:align: center
```

```{image} ../_static/pico_setup/pico_vr_screenshot.png
:width: 600px
:align: center
```

2. 打开 **XRoboToolKit** 应用。点击 **"Enter"** 输入笔记本电脑的 IP 地址，位于 "PC Service:" 旁边。如果 "Status:" 旁边显示 **WORKING**，则表示连接成功。
   - 如果 IP 地址已经输入，在 "Status:" 所在的位置选择 **"Reconnect"**。

3. 确保按照下图所示勾选以下选项：
   - "Tracking" 下方的 **"Head"** 和 **"Controller"**。
   - 对于 Data/Control，确保选择 **"Send"** 按钮。
   - 对于 "Pico Motion Tracker"，确保选择 **"Full body"**。

```{image} ../_static/pico_setup/xrrobot_setup.png
:width: 600px
:align: center
```

---

## 下一步

你的 PICO 硬件和软件已准备就绪。请继续阅读 [ZMQ Manager (`zmq_manager`) 教程](../tutorials/vr_wholebody_teleop.md)，在仿真或真实机器人上运行全身遥操作。
