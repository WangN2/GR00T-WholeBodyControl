# GR00T-SONIC 训练与模型发布整理

> 基于 2026.04 release 最新代码仓整理  
> SONIC（Single Unified Policy for Humanoid Whole-Body Control）是 GR00T 系列最新的人形行为基础模型。

---

## 一、整体架构概览

SONIC 的核心设计理念：**单一统一策略**，通过运动跟踪在超大规模人体运动数据上训练，支持多模态输入，产出自然的全身运动。

| 特性 | 说明 |
|------|------|
| **统一策略** | 单一模型处理 walking、crawling、teleoperation 等多种行为 |
| **多模态编码** | 支持 G1 关节、SMPL 人体模型、VR 遥操作、SOMA 骨架等输入 |
| **离散潜空间** | 通过 **Finite Scalar Quantization (FSQ)** 将多模态运动编码到共享离散 token 空间 |
| **端到端训练** | 基于 Isaac Lab 仿真 + PPO + 辅助损失 |
| **训推一体** | 训练产出的 checkpoint 可直接导出 ONNX，供 `gear_sonic_deploy` C++ 推理栈部署 |

---

## 二、训练代码结构（`gear_sonic/`）

```
gear_sonic/
├── train_agent_trl.py          ← 主训练入口（PPO + 辅助损失）
├── eval_agent_trl.py           ← 单 checkpoint 评估
├── eval_exp.py                 ← 持续监控新 checkpoint 并评估
│
├── trl/                        ← 训练库核心
│   ├── trainer/
│   │   ├── ppo_trainer.py              # 基础 PPO trainer（基于 HuggingFace TRL）
│   │   └── ppo_trainer_aux_loss.py     # PPO + 辅助重建/潜变量损失（SONIC 用）
│   ├── modules/
│   │   ├── universal_token_modules.py  # ⭐ SONIC 核心架构
│   │   ├── actor_critic_modules.py     # Actor（策略）和 Critic（价值）网络
│   │   └── base_module.py              # 共享 MLP 基础模块
│   ├── losses/
│   │   └── token_losses.py             # 重建损失 + 潜变量对齐辅助损失
│   └── callbacks/
│       ├── model_save_callback.py      # 每 N 步保存 checkpoint
│       ├── im_eval_callback.py         # 模仿评估指标
│       ├── im_resample_callback.py     # 自适应运动重采样
│       └── wandb_callback.py           # Weights & Biases 日志
│
├── envs/                       ← Isaac Lab 环境包装 & MDP 组件
├── data_process/               ← 运动数据处理与转换
│   ├── convert_soma_csv_to_motion_lib.py
│   ├── filter_and_copy_bones_data.py
│   └── extract_soma_joints_from_bvh.py
│
├── utils/                      ← 共享工具
│   ├── motion_lib/             # 运动库（motion_lib_base, motion_lib_robot, skeleton）
│   ├── mujoco_sim/             # MuJoCo 仿真桥接
│   └── data_collection/        # 数据采集（telemetry, video_writer, zmq）
│
└── scripts/                    ← 运行时脚本
    ├── run_sim_loop.py         # MuJoCo 仿真循环
    └── pico_manager_thread_server.py  # PICO VR 遥操作服务端
```

---

## 三、模型架构（Universal Token Module）

核心代码：`gear_sonic/trl/modules/universal_token_modules.py`

### 3.1 三大组件

| 组件 | 说明 |
|------|------|
| **多编码器（Multi-Encoders）** | 3~4 个并行运动编码器，将不同模态运动信息编码为统一表示 |
| **FSQ 量化器（Finite Scalar Quantization）** | 将连续潜向量压缩为离散 token，实现跨模态统一表示 |
| **多解码器（Multi-Decoders）** | 从量化后的潜空间解码到目标机器人动作空间 |

### 3.2 支持的编码器类型

| 编码器配置 | 输入 | 用途 |
|-----------|------|------|
| `g1_mf_mlp` | G1 机器人关节轨迹 | 机器人本体运动跟踪 |
| `smpl_mlp` | SMPL 人体模型参数 | 人体动作重定向到机器人 |
| `teleop_mlp` | VR 3 点遥操作信号 | VR 全身遥操作 |
| `soma_mlp` | SOMA 骨架数据 | 可选第 4 编码器（BONES-SEED 数据集） |

### 3.3 解码器类型

| 解码器配置 | 输出 | 使用阶段 |
|-----------|------|---------|
| `g1_dyn_mlp` | 关节动作（位置/速度） | **运行时推理**（核心） |
| `g1_kin_mf_mlp` | 未来运动重建 | **辅助损失训练时**（仅用于 loss） |

---

## 四、配置文件体系（Hydra）

SONIC 使用 **Hydra** 配置系统，约 **100+ 个 YAML 文件**通过组合形成完整训练配方。

### 4.1 关键配置文件

| 文件路径 | 作用 |
|---------|------|
| `config/base.yaml` | 全局默认：seed=0, num_envs=4096, sim_type=isaacsim |
| `config/algo/ppo_im_phc.yaml` | ⭐ PPO 超参：5 epochs, 4 mini-batches, clip=0.2, actor_lr=2e-5, critic_lr=1e-3, 100K iterations |
| `config/trainer/trl_ppo_aux.yaml` | 选择 PPO + 辅助损失 trainer |
| `config/actor_critic/universal_token/all_mlp_v1.yaml` | 组装好的 SONIC ATM 预设 |
| `config/aux_losses/universal_token/g1_recon_and_all_latent.yaml` | 辅助损失组合配置 |
| `config/manager_env/base_env.yaml` | MDP 环境基础配置 |
| `config/manager_env/rewards/tracking/base_5point_local_feet_acc.yaml` | 奖励函数组成 |
| `config/manager_env/terminations/tracking/base_adaptive_strict_ori_foot_xyz.yaml` | 终止条件 |
| `config/manager_env/events/tracking/level0_4.yaml` | 域随机化（Domain Randomization） |
| `config/callbacks/model_save.yaml` | Checkpoint 保存间隔（默认 500 iters） |
| `config/callbacks/wandb.yaml` | W&B 日志配置 |

### 4.2 训练预设（Experiment Presets）

| 预设文件 | 说明 |
|---------|------|
| `config/exp/manager/universal_token/all_modes/sonic_release.yaml` | ⭐ **默认 3 编码器**（G1 + teleop + SMPL） |
| `config/exp/manager/universal_token/all_modes/sonic_bones_seed.yaml` | 4 编码器（+ SOMA），用于 BONES-SEED 数据集 |
| `config/exp/manager/universal_token/all_modes/sonic_h2.yaml` | H2 机器人变体 |

### 4.3 `sonic_release.yaml` 关键参数

| 参数 | 配置 |
|------|------|
| 编码器 | G1 + teleop + SMPL（3 编码器，不含 SOMA） |
| 机器人类型 | `g1_model_12_dex`（G1 29 DOF 带手） |
| 历史帧 | Actor 和 Critic 各 **10 帧** |
| 未来帧 | G1/teleop: 10 帧 @ 0.1s；SMPL: 10 帧 @ 0.02s |
| 数据路径 | `data/motion_lib_bones_seed/robot_filtered` + `data/bones_seed_smpl` |
| 辅助损失 | G1 重建 + 所有潜变量对齐（latent alignment） |

---

## 五、数据与资产

### 5.1 训练数据集：BONES-SEED

| 属性 | 数值 |
|------|------|
| 原始规模 | 142K+ 个运动片段 |
| 过滤后 | ~130K（过滤掉约 8.7% 不可执行动作） |
| 时长 | ~288 小时 |
| 格式 | motion_lib PKL + SMPL 参数 |

### 5.2 机器人资产（`gear_sonic/data/robots/`）

| 机器人 | DOF 变体 | 说明 |
|--------|---------|------|
| **Unitree G1** | 12, 23, 27, 29, 43 DOF | 主要平台，含 URDF/USD/MJCF/meshes |
| **H2** | - | 次要人形机器人 |

---

## 六、快速启动命令

### 6.1 环境安装

```bash
# 安装 gear_sonic（含训练依赖）
pip install -e "gear_sonic[full]"

# 下载预训练 checkpoint 和 SMPL 数据
python download_from_hf.py
```

### 6.2 从预训练模型微调（推荐）

```bash
accelerate launch --num_processes=8 gear_sonic/train_agent_trl.py \
    +exp=manager/universal_token/all_modes/sonic_release \
    +checkpoint=sonic_release/last.pt \
    num_envs=4096 \
    headless=True
```

### 6.3 从头训练

```bash
accelerate launch --num_processes=8 gear_sonic/train_agent_trl.py \
    +exp=manager/universal_token/all_modes/sonic_release \
    num_envs=4096 \
    headless=True
```

### 6.4 评估

```bash
# 单 checkpoint 评估
python gear_sonic/eval_agent_trl.py \
    +exp=manager/universal_token/all_modes/sonic_release \
    +checkpoint=sonic_release/last.pt

# 持续监控评估（自动评估新产生的 checkpoint）
python gear_sonic/eval_exp.py \
    +exp=manager/universal_token/all_modes/sonic_release
```

> ⚠️ **硬件要求**：训练推荐 **64+ GPUs**；评估和微调可在更少 GPU 上运行。

---

## 七、与部署端的衔接

```
┌─────────────────────────────────────────────────────────────┐
│                    训练端 (gear_sonic)                       │
│  train_agent_trl.py → PPO + Aux Loss → checkpoint (.pt)     │
│                              ↓                              │
│                        ONNX Export                          │
│                              ↓                              │
│              gear_sonic_deploy (C++ 推理栈)                  │
│  ONNX Runtime / TensorRT → ROS2 → Unitree G1 真机           │
└─────────────────────────────────────────────────────────────┘
```

训练产出的 checkpoint 可通过以下方式导出 ONNX，供 `gear_sonic_deploy` 部署：

- 参考文档：`docs/source/references/planner_onnx.md`
- 或直接集成到 `gear_sonic_deploy` 的 C++ 推理管道中

---

## 八、关键文档索引

| 文档路径 | 内容 |
|---------|------|
| `docs/source/user_guide/training.md` | ⭐ 完整训练指南（数据处理、命令、多节点、评估、ONNX 导出） |
| `docs/source/user_guide/training_data.md` | BONES-SEED 数据集详细说明 |
| `docs/source/references/training_code.md` | ⭐ 代码深度参考（目录结构、训练流程、架构图、关键类） |
| `docs/source/getting_started/installation_training.md` | 训练环境安装指南 |
| `docs/source/user_guide/new_embodiments.md` | 如何添加新的机器人本体 |
| `docs/source/references/planner_onnx.md` | 运动规划器 ONNX 导出说明 |
| `docs/source/user_guide/teleoperation.md` | 遥操作最佳实践 |
| `docs/source/getting_started/vr_teleop_setup.md` | PICO VR 全身遥操作设置 |
| `docs/source/tutorials/data_collection.md` | 数据采集管线 |

---

## 九、训练关键入口速查表

| 目标 | 命令/文件 |
|------|----------|
| 主训练 | `gear_sonic/train_agent_trl.py` |
| 单点评估 | `gear_sonic/eval_agent_trl.py` |
| 持续评估 | `gear_sonic/eval_exp.py` |
| 核心模型 | `gear_sonic/trl/modules/universal_token_modules.py` |
| PPO 训练器 | `gear_sonic/trl/trainer/ppo_trainer_aux_loss.py` |
| 默认训练预设 | `config/exp/manager/universal_token/all_modes/sonic_release.yaml` |
| PPO 超参 | `config/algo/ppo_im_phc.yaml` |
| 辅助损失 | `config/aux_losses/universal_token/g1_recon_and_all_latent.yaml` |
| 数据下载 | `python download_from_hf.py` |
