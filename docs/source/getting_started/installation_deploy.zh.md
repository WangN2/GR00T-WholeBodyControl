# 安装（部署）

## 前置条件

**所有设置都需要：**
- **Ubuntu 20.04/22.04/24.04** 或其他基于 Debian 的 Linux 发行版
- **CUDA Toolkit**（用于 GPU 加速）
- **TensorRT**（用于推理优化）—— **请先安装这个！**
- **Jetpack 6**（用于机载部署）
- Python 3.8+
- 支持 LFS 的 Git

**从 [NVIDIA Developer](https://developer.nvidia.com/tensorrt/download/10x) 下载 TensorRT：**

| 平台 | TensorRT 版本 |
|---|---|
| x86_64 (桌面) | **10.13**（必需） |
| Jetson / G1 机载 Orin | **10.7**（必需；需要 JetPack 6 —— [刷机指南](../references/jetpack6.md)） |

```{tip}
下载 **TAR** 包（而不是 DEB 包），这样你可以将 TensorRT 解压到任意位置。压缩包约 10 GB；建议使用 `pv` 监控进度：
```

```{danger}
**必须**使用上述列出的确切 TensorRT 版本。使用不同版本已知会导致错误的推理结果 —— 规划器将输出错误的动作，从而引发危险的机器人行为。
```

```sh
sudo apt-get install -y pv
pv TensorRT-*.tar.gz | tar -xz -f -
```

将解压后的 TensorRT 移动到 `~/TensorRT`（或类似位置），并添加到 `~/.bashrc`：

```sh
export TensorRT_ROOT=$HOME/TensorRT
```

## 克隆仓库

```bash
git clone https://github.com/NVlabs/GR00T-WholeBodyControl.git
cd GR00T-WholeBodyControl
git lfs pull          # 确保所有大文件都已拉取
```

## 环境设置

### 原生开发（推荐）

**优点：** 直接安装到系统中，构建更快，可用于生产。

```{warning}
对于 G1 机载部署，我们要求机载 Orin 升级到 Jetpack 6 以支持 TensorRT。请按照[刷机指南](../references/jetpack6.md)进行升级！
```

**前置条件：**
- 基本开发工具（cmake、git 等）
- （可选）如果你计划使用基于 ROS2 的输入/输出，需要 ROS2

**设置步骤：**

1. **安装系统依赖：**

```sh
cd gear_sonic_deploy
chmod +x scripts/install_deps.sh
./scripts/install_deps.sh
```

2. **设置环境：**

```sh
source scripts/setup_env.sh
```

设置脚本会自动：
- 配置 TensorRT 环境
- 设置所有必要的路径

为方便起见，你可以将环境设置添加到 shell 配置文件中：

```sh
echo "source $(pwd)/scripts/setup_env.sh" >> ~/.bashrc
```

3. **构建项目：**

```sh
just build
```

### Docker（ROS2 开发环境）

我们提供了一个统一的 Docker 环境，内置 ROS2 Humble，支持 x86_64 和 Jetson 平台。

**前置条件：**
- 已安装 Docker，且用户已加入 docker 组
- 宿主机已设置 `TensorRT_ROOT` 环境变量
- Jetson 平台：JetPack 6.1+（CUDA 12.6）

**快速设置：**

```sh
# 1. 将用户加入 docker 组（一次性设置）
sudo usermod -aG docker $USER
newgrp docker

# 2. 设置 TensorRT 路径（添加到 ~/.bashrc 以持久化）
export TensorRT_ROOT=/path/to/TensorRT

# 3. 启动容器
cd gear_sonic_deploy
./docker/run-ros2-dev.sh
```

**选项：**

```sh
./docker/run-ros2-dev.sh               # 标准构建（快）
./docker/run-ros2-dev.sh --rebuild     # 强制重建
./docker/run-ros2-dev.sh --with-opengl # 包含 OpenGL 以支持可视化（RViz、Gazebo）
```

**架构支持：**
- **x86_64**：CUDA 12.4.1（需要 NVIDIA 驱动 550+）
- **Jetson**：CUDA 12.4.1 容器运行在 CUDA 12.6 宿主机上（前向兼容）

**容器内部：**

```sh
source scripts/setup_env.sh # 设置依赖
just build                  # 构建
just --list                 # 显示所有命令
```

**故障排除：**
- 如果遇到 "permission denied"，请确保你已在 docker 组中
- 启动容器前，**宿主机**必须已设置 TensorRT
- Jetson 平台：先在宿主机上运行 `source scripts/setup_env.sh`（设置 jetson_clocks）
