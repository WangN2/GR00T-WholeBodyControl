# GR00T-WholeBodyControl 项目文件结构详解

> 基于 2026.04 release 整理

```
GR00T-WholeBodyControl/
├── 根目录文件                ← 项目级配置与入口
├── decoupled_wbc/            ← Python 解耦 WBC 控制器
├── gear_sonic/               ← SONIC 训练栈（Python）
├── gear_sonic_deploy/        ← C++20 推理部署栈
├── docs/                     ← Sphinx 文档
├── external_dependencies/    ← 外部依赖子模块
├── install_scripts/          ← 安装辅助脚本
├── legal/                    ← 许可证与声明
├── media/                    ← README 媒体资源
└── systemd/                  ← systemd 服务配置
```

---

## 一、根目录文件

| 文件/目录 | 说明 |
|-----------|------|
| `README.md` / `README_CN.md` | 项目主 README（中英文） |
| `AGENTS.md` | 给 AI Agent 的开发指引（编码规范、构建流程） |
| `pyproject.toml` | 根级 Python 工具配置（black, ruff, isort, mypy） |
| `Makefile` | 快捷命令（`make run-checks`, `make format`） |
| `lint.sh` | 代码检查脚本（ruff + isort + black） |
| `download_from_hf.py` | ⭐ 从 HuggingFace 下载 checkpoint 和 SMPL 数据 |
| `check_environment.py` | 环境检查脚本 |
| `CITATION.cff` | 论文引用信息 |
| `LICENSE` | 双许可证：Apache 2.0（代码）+ NVIDIA Open Model（权重） |
| `CONTRIBUTING.md` | 贡献指南 |
| `SECURITY.md` | 安全策略 |

---

## 二、decoupled_wbc/ — 解耦 WBC 控制器

**功能**：GR00T N1.5 / N1.6 使用的解耦全身控制器（RL 控制下肢 + IK 控制上肢）。

```
decoupled_wbc/
├── __init__.py
├── version.py
├── pyproject.toml            ← 该包的独立安装配置
│
├── control/                  ← 控制器核心算法
│   ├── whole_body_controller.py
│   └── ...
│
├── data/                     ← 数据处理与加载
│
├── dexmg/                    ← Dexterous Manipulation 相关
│
├── docker/                   ← Docker 开发环境
│   ├── Dockerfile.deploy
│   ├── run_docker.sh         ← ⭐ 启动容器脚本（支持分支隔离）
│   └── entrypoint/
│
├── scripts/                  ← 工具脚本
│
├── sim2mujoco/               ← Sim 到 MuJoCo 的转换工具
│
└── tests/                    ← pytest 测试用例
```

### 安装方式
```bash
pip install -e decoupled_wbc/          # 最小安装
pip install -e "decoupled_wbc[full]"   # 含仿真+可视化+数据采集
pip install -e "decoupled_wbc[dev]"    # 含 pytest, black, ruff
```

---

## 三、gear_sonic/ — SONIC 训练栈（Python）

**功能**：SONIC 人形行为基础模型的完整训练、评估和数据处理管线。

```
gear_sonic/
│
├── train_agent_trl.py        ← ⭐ 主训练入口（PPO + 辅助损失）
├── eval_agent_trl.py         ← 单 checkpoint 评估
├── eval_exp.py               ← 持续监控并评估新 checkpoint
│
├── camera/                   ← 摄像头驱动
│   ├── realsense.py          # Intel RealSense
│   ├── oak.py                # OAK 相机
│   ├── usb_camera.py         # USB 摄像头
│   └── dummy_camera.py       # 虚拟摄像头（测试用）
│
├── config/                   ← ⭐ Hydra YAML 配置体系（100+ 文件）
│   ├── base.yaml             # 全局默认配置
│   ├── base_eval.yaml        # 评估默认配置
│   ├── algo/                 # 算法超参（PPO 等）
│   ├── trainer/              # Trainer 配置
│   ├── actor_critic/         # 网络架构配置
│   │   ├── encoders/         # 编码器：g1, smpl, teleop, soma
│   │   ├── decoders/         # 解码器：dyn, kin
│   │   └── quantizers/       # 量化器：FSQ
│   ├── aux_losses/           # 辅助损失配置
│   ├── manager_env/          # 环境 MDP 配置
│   │   ├── actions/          # 动作空间
│   │   ├── observations/     # 观测空间（policy/critic）
│   │   ├── rewards/          # 奖励函数
│   │   ├── terminations/     # 终止条件
│   │   ├── events/           # 域随机化事件
│   │   └── commands/         # 运动指令
│   ├── callbacks/            # 回调配置（保存、评估、W&B）
│   └── exp/                  # 实验预设
│       └── manager/universal_token/all_modes/
│           ├── sonic_release.yaml      # ⭐ 默认 3 编码器
│           ├── sonic_bones_seed.yaml   # 4 编码器（+SOMA）
│           └── sonic_h2.yaml           # H2 机器人
│
├── data/                     ← 机器人模型与资产
│   ├── robot_model/          # 机器人模型抽象
│   │   ├── instantiation/
│   │   │   └── g1.py         # G1 模型构建器
│   │   └── model_data/
│   │       └── g1/           # G1 URDF/USD/MJCF/meshes
│   ├── robots/               # 更多机器人资产
│   ├── assets/               # 额外资产（H2 等）
│   └── human/                # 人体骨骼元数据
│
├── data_process/             ← 运动数据处理脚本
│   ├── convert_soma_csv_to_motion_lib.py
│   ├── filter_and_copy_bones_data.py
│   └── extract_soma_joints_from_bvh.py
│
├── envs/                     ← Isaac Lab 环境包装 & MDP
│
├── isaac_utils/              ← Isaac Sim 工具函数
│
├── scripts/                  ← 运行时脚本
│   ├── run_sim_loop.py       # MuJoCo 仿真循环
│   └── pico_manager_thread_server.py  # PICO VR 遥操作服务端
│
├── trl/                      ← ⭐ 训练库核心
│   ├── trainer/
│   │   ├── ppo_trainer.py           # 基础 PPO
│   │   └── ppo_trainer_aux_loss.py  # PPO + 辅助损失
│   ├── modules/
│   │   ├── universal_token_modules.py   # ⭐ SONIC 核心架构
│   │   ├── actor_critic_modules.py      # Actor/Critic 网络
│   │   └── base_module.py               # MLP 基础模块
│   ├── losses/
│   │   └── token_losses.py         # 重建 + 潜变量对齐损失
│   └── callbacks/
│       ├── model_save_callback.py
│       ├── im_eval_callback.py
│       ├── im_resample_callback.py
│       └── wandb_callback.py
│
└── utils/                    ← 共享工具
    ├── motion_lib/           # 运动库（加载、采样、插值）
    ├── mujoco_sim/           # MuJoCo 仿真桥接
    └── data_collection/      # 数据采集（telemetry, video, zmq）
```

### 安装方式
```bash
pip install -e "gear_sonic[full]"    # 含训练+仿真+可视化
pip install -e "gear_sonic[teleop]"  # 仅遥操作
pip install -e "gear_sonic[sim]"     # 仅 MuJoCo 仿真
```

---

## 四、gear_sonic_deploy/ — C++20 推理部署栈

**功能**：在真机（Unitree G1）上部署 SONIC 策略的 C++ 推理管道，支持 TensorRT 和 ONNXRuntime。

```
gear_sonic_deploy/
│
├── CMakeLists.txt            ← CMake 构建配置
├── deploy.sh                 ← ⭐ 一键部署脚本
│
├── cmake/                    ← CMake 模块和工具链
│
├── docker/                   ← Docker 环境
│   ├── Dockerfile.ros2
│   └── run-ros2-dev.sh       ← ⭐ ROS2 开发容器启动脚本
│
├── g1/                       ← G1 机器人相关
│
├── policy/                   ← 策略推理相关
│
├── reference/                ← 参考实现
│
├── scripts/                  ← 辅助脚本
│   └── setup_env.sh          # 环境设置
│
├── src/                      ← ⭐ C++ 源码
│   └── g1/
│       └── g1_deploy_onnx_ref.cpp   # ONNX 推理参考实现
│
└── thirdparty/               ← 第三方 C++ 依赖
```

### 构建方式
```bash
cd gear_sonic_deploy
./deploy.sh        # 或直接用 cmake
```

---

## 五、docs/ — Sphinx 文档

```
docs/
└── source/
    ├── conf.py                       # Sphinx 配置
    ├── index.rst                     # 文档首页
    │
    ├── getting_started/              ← 快速入门
    │   ├── quickstart.md             # 快速开始
    │   ├── installation_training.md  # 训练环境安装
    │   ├── download_models.md        # 模型下载
    │   └── vr_teleop_setup.md        # VR 遥操作设置
    │
    ├── user_guide/                   ← 用户指南
    │   ├── training.md               # ⭐ 完整训练指南
    │   ├── training_data.md          # BONES-SEED 数据说明
    │   ├── configuration.md          # 配置系统说明
    │   ├── teleoperation.md          # 遥操作最佳实践
    │   ├── new_embodiments.md        # 添加新机器人本体
    │   └── troubleshooting.md        # 故障排查
    │
    ├── references/                   ← 参考文档
    │   ├── training_code.md          # ⭐ 训练代码深度参考
    │   ├── deployment_code.md        # 部署代码参考
    │   ├── planner_onnx.md           # ONNX 导出说明
    │   └── conventions.md            # 命名规范
    │
    ├── tutorials/                    ← 教程
    │   ├── keyboard.md               # 键盘控制
    │   ├── gamepad.md                # 手柄控制
    │   └── data_collection.md        # 数据采集管线
    │
    ├── resources/                    # 附加资源
    │
    └── _static/                      # 静态文件（CSS, 图片）
```

### 构建文档
```bash
cd docs
make html
```

---

## 六、其他目录

### external_dependencies/ — 外部依赖
```
external_dependencies/
├── XRoboToolkit-PC-Service-Pybind_X86_and_ARM64/   # XRobo 工具包
└── unitree_sdk2_python/                             # Unitree SDK2 Python
```

### install_scripts/ — 安装辅助脚本
包含 Leap SDK、MuJoCo、PICO VR、ROS 等安装脚本。

### legal/ — 许可证文件
包含 Apache 2.0、NVIDIA Open Model License 等完整许可证文本。

### media/ — 媒体资源
README 中使用的 GIF、视频等媒体文件。

### systemd/ — 系统服务配置
真机部署时使用的 systemd 服务文件（如 camera server 等）。

---

## 七、模块关系总览

```
┌─────────────────────────────────────────────────────────────────┐
│                         训练阶段                                  │
│  gear_sonic/                                                    │
│  ├── train_agent_trl.py → PPO + Aux Loss → checkpoint (.pt)    │
│  └── eval_agent_trl.py / eval_exp.py                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ ONNX Export
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                         部署阶段                                  │
│  gear_sonic_deploy/                                             │
│  ├── src/g1/g1_deploy_onnx_ref.cpp                              │
│  └── TensorRT / ONNXRuntime → ROS2 → Unitree G1 真机           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         控制阶段                                  │
│  decoupled_wbc/                                                 │
│  └── RL 下肢 + IK 上肢 → 全身控制（仿真或真机）                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 八、速查：我该去哪个目录？

| 想做什么 | 去哪个目录/文件 |
|---------|----------------|
| **训练 SONIC 模型** | `gear_sonic/train_agent_trl.py` |
| **评估 checkpoint** | `gear_sonic/eval_agent_trl.py` |
| **修改训练配置** | `gear_sonic/config/` |
| **添加新机器人本体** | `gear_sonic/data/robots/` + `docs/source/user_guide/new_embodiments.md` |
| **处理 BONES-SEED 数据** | `gear_sonic/data_process/` |
| **真机 C++ 部署** | `gear_sonic_deploy/src/` |
| **构建部署环境** | `gear_sonic_deploy/deploy.sh` |
| **启动 ROS2 Docker** | `gear_sonic_deploy/docker/run-ros2-dev.sh` |
| **解耦 WBC 控制** | `decoupled_wbc/control/` |
| **运行测试** | `pytest decoupled_wbc/tests/` |
| **下载模型/数据** | `python download_from_hf.py` |
| **看训练文档** | `docs/source/user_guide/training.md` |
| **看代码参考** | `docs/source/references/training_code.md` |
