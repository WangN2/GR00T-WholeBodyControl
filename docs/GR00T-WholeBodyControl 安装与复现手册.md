# GR00T-WholeBodyControl 安装与复现手册

> 目标：在单台 x86_64 Ubuntu 工作站上完成训练环境、部署环境、仿真环境的配置，使后续 agent 可按本手册逐步执行。
>
> 机器信息：Ubuntu 24.04, x86_64, NVIDIA Driver 580.142 (CUDA 13.0), 代码已克隆到 `/home/nio/wangbin/GR00T-WholeBodyControl`
>
> 项目文档根目录：`/home/nio/wangbin/GR00T-WholeBodyControl/docs/source/getting_started/`

---

## 1. 项目结构总览

```
GR00T-WholeBodyControl/
├── decoupled_wbc/              # Python: 解耦 WBC 控制器 (RL 下肢 + IK 上肢)
│   ├── pyproject.toml
│   └── tests/
├── gear_sonic/                 # Python: SONIC 训练/遥操作/仿真
│   ├── pyproject.toml          # extras: [training], [sim], [teleop], [camera], [data_collection]
│   ├── data_process/           # 数据预处理脚本
│   ├── scripts/                # run_sim_loop.py 等
│   └── trl/                    # RL 训练代码
├── gear_sonic_deploy/          # C++20: 真实机器人部署推理栈
│   ├── CMakeLists.txt
│   ├── docker/run-ros2-dev.sh  # Docker 开发环境
│   ├── scripts/
│   │   ├── install_deps.sh     # 系统依赖安装
│   │   ├── setup_env.sh        # 环境变量配置
│   │   └── repack_tensorrt_from_deb.sh  # DEB→自包含目录脚本
│   ├── deploy.sh               # 部署入口 (sim|real)
│   └── .justfile               # just build / just run
├── external_dependencies/      # Git submodules: unitree_sdk2_python, XRoboToolkit...
├── install_scripts/            # install_mujoco_sim.sh, install_pico.sh, install_ros.sh...
├── docs/                       # Sphinx 文档
├── download_from_hf.py         # HuggingFace 模型/数据下载
└── check_environment.py        # 环境预检脚本
```

**三大环境**：
1. **训练环境** (`gear_sonic` + Isaac Lab) — 用于 RL 训练、评估、ONNX 导出
2. **部署环境** (`gear_sonic_deploy`) — C++ 推理栈，依赖 TensorRT + ONNXRuntime
3. **仿真/遥操作环境** (MuJoCo + PICO VR 可选) — Sim2Sim 测试与数据收集

---

## 2. 系统级依赖

> **重要**：本手册假设使用 **Docker 开发模式**（推荐，适合多人共享宿主机）。
> 容器镜像构建时已自动执行 `install_deps.sh` 和 `install_ros2_humble.sh`，因此**宿主机不需要运行这些脚本**。
> 宿主机只需保留 NVIDIA 驱动、Docker、TensorRT TAR 包和代码仓库即可。

### 2.1 宿主机最小依赖（Docker 模式）

宿主机**不需要**执行 `install_deps.sh`（该脚本在 Docker 镜像构建时已运行）。只需确保：

| 组件 | 说明 | 验证命令 |
|------|------|---------|
| NVIDIA Driver | ≥550 (CUDA 12.4 兼容) | `nvidia-smi` |
| Docker + nvidia-container-toolkit | GPU 容器支持 | `docker info \| grep nvidia` |
| Git LFS | 拉取大文件 | `git lfs version` |
| TensorRT TAR 包 | `~/TensorRT` 供容器挂载 | `ls ~/TensorRT/lib/libnvinfer.so` |

宿主机**禁止**安装的系统级包（应留在容器内）：
- ROS2、CMake、Clang、just、ONNX Runtime、CUDA toolkit 开发包 —— 这些全部在 Docker 镜像内

### 2.2 Docker 镜像包含的内容（无需宿主机重复安装）

`Dockerfile.ros2` 构建时已自动完成：
- `install_deps.sh` → build-essential, clang, cmake, just, libyaml-cpp-dev, libeigen3-dev, libzmq3-dev, nlohmann-json3-dev, ONNX Runtime 1.16.3
- `install_ros2_humble.sh` → ROS2 Humble Desktop
- CUDA 12.4.1 开发环境
- 自动 Jetson 检测支持

容器启动时 `run-ros2-dev.sh` 还会自动：
- 挂载宿主机的 `~/TensorRT` → `/opt/TensorRT`
- 挂载代码目录 → `/workspace/g1_deploy`
- source `scripts/setup_env.sh` 配置环境变量

### 2.2 TensorRT（TAR 包安装，文档推荐）

**关键要求**：必须使用 **TAR 包**（非 DEB），解压到 `~/TensorRT`，因为 Docker 挂载需要自包含目录。

| 平台 | 版本 | 说明 |
|------|------|------|
| x86_64 | **10.13** (文档要求) 或 **10.16** (已验证兼容) | CUDA 12.x 绑定 |
| Jetson | 10.7 + JetPack 6 | 仅 Orin 真机部署 |

**安装步骤**：
```bash
# 1. 下载 TAR 包（需 NVIDIA 开发者账号）
# https://developer.nvidia.com/tensorrt/download/10x
# 选择：Linux x86_64 → TAR Package → CUDA 12.x

# 2. 解压到 ~/TensorRT
cd ~
tar -xzf ~/Downloads/TensorRT-10.*.Linux.x86_64-gnu.cuda-*.tar.gz
mv TensorRT-10.* TensorRT

# 3. 设置环境变量
export TensorRT_ROOT=$HOME/TensorRT
echo 'export TensorRT_ROOT=$HOME/TensorRT' >> ~/.bashrc

# 4. 验证
ls $TensorRT_ROOT/include/NvInfer.h    # 必须是实际文件，不是软链接
ls $TensorRT_ROOT/lib/libnvinfer.so
ls $TensorRT_ROOT/bin/trtexec
```

> ⚠️ **常见坑**：如果之前用 `setup_tensorrt_for_docker.sh` 创建过 `~/TensorRT`，里面全是软链接，挂载到 Docker 后会断裂。必须先 `rm -rf ~/TensorRT` 再用 TAR 包重建。

### 2.3 Git LFS 拉取大文件

```bash
cd /home/nio/wangbin/GR00T-WholeBodyControl
git lfs install
git lfs pull
```

验证：`ls -la gear_sonic/data/assets/robot_description/urdf/g1/main.urdf` 应为 ~60KB+，不是 130 字节的指针文件。

---

## 3. 训练环境（Training）

### 3.1 前置：Isaac Lab 安装

```bash
# Isaac Lab 需要单独安装，不在 pip 依赖中
# 参考：https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/index.html

# 推荐：conda 环境，Python 3.11
conda create -n env_isaaclab python=3.11
conda activate env_isaaclab

# 按官方指引安装 Isaac Lab 2.3+
# 验证
python -c "import isaaclab; print(isaaclab.__version__)"
```

### 3.2 安装 gear_sonic[training]

```bash
cd /home/nio/wangbin/GR00T-WholeBodyControl

# 在 Isaac Lab 的 conda 环境中
pip install -e "gear_sonic[training]"
```

依赖：`hydra-core==1.3.2`, `wandb`, `trl==0.28.0`, `transformers>=4.56.2`, `accelerate>=1.3.0`

### 3.3 下载训练模型与数据

```bash
# 安装 huggingface_hub
pip install huggingface_hub

# 下载训练 checkpoint + SMPL 数据 (~30GB)
python download_from_hf.py --training

# 或只下载 checkpoint（跳过 SMPL）
python download_from_hf.py --training --no-smpl

# 或只下载部署用的 ONNX 模型
python download_from_hf.py
```

下载后目录结构：
```
<repo_root>/
├── sonic_release/
│   ├── last.pt                 # 训练 checkpoint
│   └── config.yaml
├── data/smpl_filtered/         # SMPL 运动数据 (~30GB)
└── gear_sonic_deploy/          # ONNX 部署模型
    ├── policy/release/
    │   ├── model_encoder.onnx
    │   ├── model_decoder.onnx
    │   └── observation_config.yaml
    └── planner/target_vel/V2/
        └── planner_sonic.onnx
```

### 3.4 准备运动数据（Bones-SEED）

**来源**：https://bones-studio.ai/seed 下载 G1 retargeted CSVs (29 DOF, 120 FPS)

```bash
# Step 1: CSV → motion_lib PKL
cd /home/nio/wangbin/GR00T-WholeBodyControl
python gear_sonic/data_process/convert_soma_csv_to_motion_lib.py \
    --input /path/to/bones_seed/g1/csv/ \
    --output data/motion_lib_bones_seed/robot \
    --fps 30 --fps_source 120 --individual --num_workers 16

# Step 2: 过滤 G1 无法完成的动作（去除 ~8.7%）
python gear_sonic/data_process/filter_and_copy_bones_data.py \
    --source data/motion_lib_bones_seed/robot \
    --dest data/motion_lib_bones_seed/robot_filtered \
    --workers 16
```

### 3.5 验证训练环境

```bash
python check_environment.py --training

# 快速冒烟测试（16 env，5 个学习迭代）
python gear_sonic/train_agent_trl.py \
    +exp=manager/universal_token/all_modes/sonic_release \
    num_envs=16 headless=False \
    ++algo.config.num_learning_iterations=5
```

---

## 4. 部署环境（Deployment）

### 4.1 方式 A：Docker 容器（推荐，ROS2 开发）

```bash
cd /home/nio/wangbin/GR00T-WholeBodyControl/gear_sonic_deploy/docker

# 启动容器（会自动挂载 TensorRT、代码目录）
./run-ros2-dev.sh

# 容器内执行
source scripts/setup_env.sh
just build
just --list
```

**容器特性**：
- 基于 `nvidia/cuda:12.4.1-devel-ubuntu22.04`
- 内置 ROS2 Humble
- 自动挂载 `$TensorRT_ROOT` → `/opt/TensorRT`
- 自动 source `setup_env.sh`

### 4.2 方式 B：宿主机原生构建

```bash
cd /home/nio/wangbin/GR00T-WholeBodyControl/gear_sonic_deploy

# 1. 安装系统依赖（如未执行）
./scripts/install_deps.sh

# 2. 配置环境
source scripts/setup_env.sh

# 3. 构建
just build
```

### 4.3 部署运行

```bash
# Sim2Sim（MuJoCo 仿真）
bash deploy.sh sim

# 真机部署
bash deploy.sh real
```

---

## 5. 仿真/遥操作环境（Sim & Teleop）

### 5.1 MuJoCo 仿真环境（用于 Sim2Sim）

```bash
cd /home/nio/wangbin/GR00T-WholeBodyControl
bash install_scripts/install_mujoco_sim.sh
```

该脚本：
- 安装 `uv` 包管理器（如果缺失）
- 创建 `.venv_sim` (Python 3.10)
- 安装 `gear_sonic[sim]` + `unitree_sdk2_python`

运行：
```bash
source .venv_sim/bin/activate
python gear_sonic/scripts/run_sim_loop.py
```

### 5.2 PICO VR 遥操作（可选）

```bash
# 硬件：PICO 4 + 2 控制器 + 2 脚踝追踪器
# 软件：
bash install_scripts/install_pico.sh
source .venv_teleop/bin/activate
```

XRoboToolkit PC Service 安装：
```bash
wget https://github.com/XR-Robotics/XRoboToolkit-PC-Service/releases/download/v1.0.0/XRoboToolkit_PC_Service_1.0.0_ubuntu_24.04_amd64.deb
sudo dpkg -i XRoboToolkit_PC_Service_1.0.0_ubuntu_24.04_amd64.deb
```

---

## 6. 环境验证清单

运行综合检查：
```bash
cd /home/nio/wangbin/GR00T-WholeBodyControl

# 全量检查
python check_environment.py

# 仅训练
python check_environment.py --training

# 仅部署
python check_environment.py --deploy
```

### 预期通过项

| 检查项 | 训练 | 部署 | 说明 |
|--------|------|------|------|
| Python 3.11 | ✅ | - | Isaac Lab 要求 |
| Python 3.10+ | - | ✅ | 部署/仿真最低要求 |
| Git LFS | ✅ | ✅ | 网格文件 >1KB |
| CUDA GPU | ✅ | ✅ | torch.cuda.is_available() |
| Isaac Lab | ✅ | - | `import isaaclab` |
| TensorRT | - | ✅ | `$TensorRT_ROOT` 存在且文件完整 |
| ONNX Runtime | - | ✅ | `/opt/onnxruntime` |
| ROS2 Humble | - | △ | Docker 内已含；宿主机可选 |
| CMake ≥3.14 | - | ✅ | `cmake --version` |
| just | - | ✅ | `just --version` |

---

## 7. 关键命令速查

### 训练
```bash
# 单机单卡调试
python gear_sonic/train_agent_trl.py \
    +exp=manager/universal_token/all_modes/sonic_release \
    num_envs=16 headless=False

# 单机 8 卡训练
accelerate launch --num_processes=8 gear_sonic/train_agent_trl.py \
    +exp=manager/universal_token/all_modes/sonic_release \
    num_envs=4096 headless=True

# 从 released checkpoint 微调
python gear_sonic/train_agent_trl.py \
    +exp=manager/universal_token/all_modes/sonic_release \
    +checkpoint=sonic_release/last.pt \
    num_envs=4096 headless=True
```

### 评估
```bash
# 评估指标
python gear_sonic/eval_agent_trl.py \
    +checkpoint=<path_to_checkpoint.pt> \
    +headless=True ++eval_callbacks=im_eval

# 导出 ONNX（用于 C++ 部署）
python gear_sonic/eval_agent_trl.py \
    +checkpoint=<path_to_checkpoint.pt> \
    +headless=True ++num_envs=1 +export_onnx_only=true
```

### 部署
```bash
# Sim2Sim（宿主机 Terminal 1：MuJoCo sim，Terminal 2：部署）
source .venv_sim/bin/activate
python gear_sonic/scripts/run_sim_loop.py        # Terminal 1
bash deploy.sh sim                                # Terminal 2

# 真机
bash deploy.sh real
```

---

## 8. 已知问题与排查

| 问题 | 原因 | 解决 |
|------|------|------|
| CMake 找不到 TensorRT | `TensorRT_ROOT` 未设置或软链接断裂 | 确认 `~/TensorRT` 内为实际文件；`export TensorRT_ROOT=$HOME/TensorRT` |
| `ModuleNotFoundError: isaaclab` | Isaac Lab 未安装或环境错误 | 按官方指南安装；激活正确的 conda env |
| 网格文件只有 130 字节 | Git LFS 未拉取 | `git lfs pull` |
| `size mismatch` 加载 checkpoint | 实验配置与 checkpoint 架构不匹配 | 使用 `sonic_release` 配置；检查 `hidden_dims` |
| `trl/transformers` 冲突 | 版本不兼容 | `pip install -e "gear_sonic[training]" --upgrade` |
| 机器人仿真中爆炸/摔倒 | init height / KP/KD / action_scale 错误 | 调参；见 `new_embodiments.md` |
| MuJoCo Docker 黑屏 | Intel iGPU 与 NVIDIA dGPU 冲突 | `export __NV_PRIME_RENDER_OFFLOAD=1` |
| Sim 中 `ChannelFactory` 错误 | CycloneDDS 域冲突 | 注释掉 SimulatorFactory 中重复 channel init |

---

## 9. 安装阶段拆分（供 Agent 执行）

### Phase 1：系统底座
- [ ] 执行 `install_deps.sh`（基础工具链 + ONNX Runtime + Git LFS）
- [ ] 安装 TensorRT TAR 包到 `~/TensorRT`
- [ ] 拉取 Git LFS 大文件
- [ ] 运行 `check_environment.py --deploy`

### Phase 2：部署环境
- [ ] 构建 Docker 镜像 `./run-ros2-dev.sh`
- [ ] 或在宿主机执行 `source scripts/setup_env.sh && just build`
- [ ] 验证 `just build` 成功

### Phase 3：训练环境
- [ ] 安装 Isaac Lab（conda env，Python 3.11）
- [ ] `pip install -e "gear_sonic[training]"`
- [ ] `python download_from_hf.py --training`
- [ ] 准备 Bones-SEED 运动数据（可选，可先用 sample_data）
- [ ] 运行 `check_environment.py --training`
- [ ] 冒烟测试训练脚本

### Phase 4：仿真环境
- [ ] `bash install_scripts/install_mujoco_sim.sh`
- [ ] 验证 `run_sim_loop.py` 可启动
- [ ] Sim2Sim 联调（`deploy.sh sim` + `run_sim_loop.py`）

### Phase 5：遥操作环境（可选）
- [ ] `bash install_scripts/install_pico.sh`
- [ ] 安装 XRoboToolkit PC Service
- [ ] PICO 硬件配对与校准
