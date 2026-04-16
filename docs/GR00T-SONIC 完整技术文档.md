# GR00T-SONIC 完整技术文档

> 基于 2026.04 release 全面梳理  
> 涵盖：数据集 → 预训练 → 训练 → 微调 → 强化学习 → 评估 → ONNX 导出 → 部署 → 数据采集

---

## 一、项目概述

**GR00T-SONIC**（Single Unified Policy for Humanoid Whole-Body Control）是 NVIDIA GEAR Lab 开源的人形机器人全身控制基础模型。SONIC 通过**运动跟踪（Motion Tracking）**在超大规模人体运动数据上训练，支持多模态输入，产出自然的全身运动。

### 核心特性

| 特性 | 说明 |
|------|------|
| **统一策略** | 单一模型处理 walking、crawling、teleoperation、boxing 等多种行为 |
| **多模态编码** | 支持 G1 关节轨迹、SMPL 人体模型、VR 遥操作、SOMA 骨架等输入 |
| **离散潜空间** | 通过 **Finite Scalar Quantization (FSQ)** 将多模态运动编码到共享离散 token 空间 |
| **端到端训练** | 基于 Isaac Lab 仿真 + PPO + 辅助损失 |
| **训推一体** | 训练产出的 checkpoint 可直接导出 ONNX，供 C++ 推理栈部署 |

### 仓库结构

```
GR00T-WholeBodyControl/
├── decoupled_wbc/              # Python: 解耦 WBC 控制器 (RL 下肢 + IK 上肢)
├── gear_sonic/                 # Python: SONIC 训练/评估/数据处理
│   ├── train_agent_trl.py      # 主训练入口
│   ├── eval_agent_trl.py       # 评估入口
│   ├── config/                 # Hydra YAML 配置体系 (100+ 文件)
│   ├── trl/                    # 训练库核心 (PPO, 网络, 损失)
│   ├── envs/                   # Isaac Lab 环境包装
│   ├── data_process/           # 运动数据处理
│   └── scripts/                # 运行时脚本
├── gear_sonic_deploy/          # C++20: 真实机器人部署推理栈
├── external_dependencies/      # Git submodules
├── install_scripts/            # 安装辅助脚本
└── docs/                       # Sphinx 文档
```

---

## 二、数据集：BONES-SEED

### 2.1 数据集概述

[BONES-SEED](https://huggingface.co/datasets/bones-studio/seed)（Skeletal Everyday Embodiment Dataset）是由 Bones Studio 创建的大规模人体运动数据集，是 SONIC 预训练的核心数据来源。

| 属性 | 数值 |
|------|------|
| **总运动片段** | 142,220（71,132 原始 + 71,088 镜像） |
| **总时长** | ~288 小时（@ 120 fps） |
| **表演者** | 522 名演员（253 女 / 269 男） |
| **年龄范围** | 17–71 岁 |
| **身高范围** | 145–199 cm |
| **体重范围** | 38–145 kg |
| **输出格式** | SOMA Proportional / SOMA Uniform / Unitree G1 |
| **标注** | 每条运动最多 6 条自然语言描述 + 时间分段 + 骨骼元数据 |

### 2.2 运动类别分布

| 类别 | 数量 | 描述 |
|------|------|------|
| Locomotion | 74,488 | 行走、慢跑、跳跃、攀爬、爬行、转向 |
| Communication | 21,493 | 手势、指向、注视、交流性肢体语言 |
| Interactions | 14,643 | 物体操作、拾取放置、搬运、工具使用 |
| Dances | 11,006 | 多风格全身舞蹈 |
| Gaming | 8,700 | 游戏灵感动作 |
| Everyday | 5,816 | 家务、坐着、阅读等日常活动 |
| Sport | 3,993 | 体育运动 |
| Other | 2,081 | 特技、武术等 |

### 2.3 数据格式

每条运动提供三种格式：

- **SOMA Proportional (BVH)** — 保留原始演员身体比例的骨架
- **SOMA Uniform (BVH)** — 标准化骨架，便于批处理
- **Unitree G1 (CSV)** — 重定向到 Unitree G1 人形机器人的关节角轨迹

### 2.4 数据下载

```bash
pip install huggingface_hub

# 使用 Hugging Face CLI
huggingface-cli download bones-studio/seed --repo-type dataset --local-dir ./bones-seed

# 或使用 Python API
from huggingface_hub import snapshot_download
snapshot_download(repo_id="bones-studio/seed", repo_type="dataset", local_dir="./bones-seed")
```

---

## 三、数据预处理

### 3.1 数据预处理管线

SONIC 训练需要运动数据转换为 **motion_lib PKL 格式**。

```
BONES-SEED CSV (120 fps, 29 DOF)
    ↓
convert_soma_csv_to_motion_lib.py
    ↓
motion_lib PKL (30 fps) — 142K  motions
    ↓
filter_and_copy_bones_data.py
    ↓
robot_filtered — ~130K motions (过滤掉 8.7%)
```

### 3.2 详细步骤

**Step 1: CSV → motion_lib PKL**

```bash
python gear_sonic/data_process/convert_soma_csv_to_motion_lib.py \
    --input /path/to/bones_seed/g1/csv/ \
    --output data/motion_lib_bones_seed/robot \
    --fps 30 \
    --fps_source 120 \
    --individual \
    --num_workers 16
```

参数说明：
- `--fps 30`: 目标帧率（仿真步长）
- `--fps_source 120`: 源数据帧率
- `--individual`: 每条运动单独存储一个 PKL 文件
- `--num_workers 16`: 并行处理 worker 数

**Step 2: 过滤不可执行动作**

```bash
python gear_sonic/data_process/filter_and_copy_bones_data.py \
    --source data/motion_lib_bones_seed/robot \
    --dest data/motion_lib_bones_seed/robot_filtered \
    --workers 16
```

过滤规则（自动移除）：
- 家具交互（爬桌子、坐椅子）
- 车辆相关（开车、骑车）
- 杂技动作（后空翻、侧手翻）
- 高处表面（爬墙、跳楼）

最终数据目录结构：

```
data/
├── motion_lib_bones_seed/
│   ├── robot/              # 原始 142K PKLs
│   └── robot_filtered/     # 过滤后 ~130K PKLs
└── smpl_filtered/          # SMPL 运动数据 (~30GB, 从 HuggingFace 下载)
```

### 3.3 SMPL 数据下载（ HuggingFace）

```bash
# 下载训练 checkpoint + SMPL 数据 (~30GB)
python download_from_hf.py --training

# 或只下载 checkpoint（跳过 SMPL）
python download_from_hf.py --training --no-smpl
```

---

## 四、模型架构：Universal Token Module

### 4.1 核心设计理念

SONIC 的核心是 **Universal Token Module (ATM)**，它将不同模态的运动输入编码到一个**共享的离散 token 空间**，再由统一的解码器生成机器人动作。

```
                  ┌─────────────┐
  G1 obs    ───►  │  G1 Encoder │──┐
                  └─────────────┘  │
                  ┌─────────────┐  │    ┌─────────┐     ┌─────────────┐
  Teleop obs───►  │Teleop Encdr │──┼──► │   FSQ   │──►  │ G1 Dynamic  │──► joint actions
                  └─────────────┘  │    │Quantizer│     │   Decoder   │
                  ┌─────────────┐  │    └─────────┘     └─────────────┘
  SMPL obs  ───►  │ SMPL Encoder│──┘          │
                  └─────────────┘             │         ┌─────────────┐
                                              └───────► │G1 Kinematic │──► (aux loss only)
                                                        │   Decoder   │
                                                        └─────────────┘
```

### 4.2 三大组件

| 组件 | 说明 | 核心代码 |
|------|------|---------|
| **多编码器（Multi-Encoders）** | 3~4 个并行 MLP 编码器，将不同模态运动信息编码为统一 latent 向量 | `trl/modules/universal_token_modules.py` |
| **FSQ 量化器** | Finite Scalar Quantization，将连续 latent 压缩为离散 token | `config/actor_critic/quantizers/fsq.yaml` |
| **多解码器（Multi-Decoders）** | 从量化后的 token 解码到目标机器人动作空间 | `trl/modules/universal_token_modules.py` |

### 4.3 支持的编码器类型

| 编码器配置 | 输入 | 用途 |
|-----------|------|------|
| `g1_mf_mlp` | G1 机器人关节轨迹 | 机器人本体运动跟踪 |
| `smpl_mlp` | SMPL 人体模型参数 | 人体动作重定向到机器人 |
| `teleop_mlp` | VR 3 点遥操作信号 | VR 全身遥操作 |
| `soma_mlp` | SOMA 骨架数据 | 可选第 4 编码器（BONES-SEED 数据集） |

### 4.4 解码器类型

| 解码器 | 输出 | 使用阶段 |
|--------|------|---------|
| `g1_dyn_mlp` | 关节动作（位置/速度） | **运行时推理**（核心） |
| `g1_kin_mf_mlp` | 未来运动重建 | **辅助损失训练时**（仅用于 loss） |

### 4.5 关键超参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `encoder_sample_probs` | `[0.4, 0.3, 0.3]` | G1 / SMPL / Teleop 采样概率 |
| `fsq_level_list` | `[8, 8, 8, 5, 5, 5]` | FSQ 每维量化级别 |
| `latent_residual_mode` | `post_quantization` | 下游任务残差注入模式 |
| `num_hist_frames` | `10` | Actor/Critic 历史帧数 |
| `num_future_frames` | `10` | 未来帧预测数 |

---

## 五、预训练与训练

### 5.1 训练方法概述

SONIC 采用 **PPO（Proximal Policy Optimization）** 作为基础 RL 算法，结合 **辅助损失（Auxiliary Losses）** 进行训练：

- **策略损失（Policy Loss）**：PPO clipped surrogate objective
- **价值损失（Value Loss）**：Clipped value loss
- **辅助损失（Aux Loss）**：
  - 编码器重建损失（G1 kinematic decoder 重建未来运动）
  - 潜变量对齐损失（所有编码器的 latent 在 FSQ 前后保持一致）

### 5.2 PPO 训练循环

```
for iteration in range(num_learning_iterations):
    # 1. Rollout: 收集 num_steps_per_env 个时间步的转移
    for step in range(num_steps_per_env):
        actions = policy.rollout(obs_dict)
        obs_dict, rewards, dones, infos = env.step(actions)
        store(obs, actions, rewards, values, log_probs)

    # 2. GAE: 计算优势函数和回报
    advantages = generalized_advantage_estimation(rewards, values, dones)

    # 3. PPO Update: num_ppo_epochs 轮 mini-batch 更新
    for epoch in range(num_ppo_epochs):
        for mini_batch in shuffle_and_split(rollout_data):
            policy_loss = clipped_surrogate_objective(...)
            value_loss  = clipped_value_loss(...)
            aux_loss    = sum(coef_i * aux_loss_i)  # 重建 + latent 对齐
            total_loss  = policy_loss + value_loss_coef * value_loss
                        + aux_loss_scale * aux_loss
            optimizer.step(total_loss)

    # 4. 回调：保存 checkpoint、评估、日志
    callbacks.on_step_end(...)
```

### 5.3 配置系统（Hydra）

SONIC 使用 Hydra 配置系统，约 **100+ YAML 文件** 组合形成完整训练配方。

#### 关键配置文件

| 文件 | 作用 |
|------|------|
| `config/base.yaml` | 全局默认：seed=0, num_envs=4096 |
| `config/algo/ppo_im_phc.yaml` | PPO 超参：5 epochs, 4 mini-batches, clip=0.2, actor_lr=2e-5, critic_lr=1e-3 |
| `config/trainer/trl_ppo_aux.yaml` | 选择 PPO + 辅助损失 trainer |
| `config/actor_critic/universal_token/all_mlp_v1.yaml` | 组装好的 SONIC ATM 预设 |
| `config/aux_losses/universal_token/g1_recon_and_all_latent.yaml` | 辅助损失组合 |
| `config/manager_env/rewards/tracking/base_5point_local_feet_acc.yaml` | 奖励函数 |
| `config/manager_env/events/tracking/level0_4.yaml` | 域随机化 |

#### 训练预设（Experiment Presets）

| 预设 | 编码器 | 说明 |
|------|--------|------|
| `sonic_release` | G1 + teleop + SMPL | **默认** — 匹配发布的 checkpoint |
| `sonic_bones_seed` | G1 + teleop + SMPL + SOMA | 4 编码器，用于 BONES-SEED |
| `sonic_h2` | - | H2 机器人变体 |

### 5.4 关键 PPO 超参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `num_envs` | 4096 | 并行仿真环境数 |
| `num_learning_iterations` | 100,000 | 总训练迭代数 |
| `num_steps_per_env` | 32 | 每轮 rollout 时间步数 |
| `num_learning_epochs` | 5 | PPO epochs / iteration |
| `num_mini_batches` | 4 | Mini-batches / epoch |
| `actor_learning_rate` | 2e-5 | Actor 学习率 |
| `critic_learning_rate` | 1e-3 | Critic 学习率 |
| `clip_param` | 0.2 | PPO 裁剪参数 |
| `init_noise_std` | 0.05 | 初始探索噪声标准差 |
| `save_interval` | 500 | Checkpoint 保存间隔（iterations） |

### 5.5 奖励函数

核心跟踪奖励：

| 奖励项 | 描述 |
|--------|------|
| `tracking_relative_body_pos` | 跟踪参考身体位置（5 点：root, 手腕, 脚） |
| `tracking_relative_body_ori` | 跟踪参考身体朝向 |
| `tracking_anchor_pos` | 跟踪根锚点位置 |
| `tracking_anchor_ori` | 跟踪根锚点朝向 |
| `tracking_body_linvel` | 跟踪参考身体线速度 |
| `tracking_body_angvel` | 跟踪参考身体角速度 |
| `action_rate_l2` | 惩罚动作抖动 |
| `feet_acc` | 惩罚脚部加速度（平滑性） |

---

## 六、训练命令

### 6.1 环境准备

```bash
# 1. 安装 Isaac Lab（单独安装，不在 pip 依赖中）
# https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/index.html
# 推荐 conda 环境，Python 3.11

# 2. 安装 gear_sonic 训练依赖
pip install -e "gear_sonic[training]"

# 3. 下载预训练 checkpoint 和 SMPL 数据
python download_from_hf.py --training

# 4. 准备 BONES-SEED 运动数据（见第三节）
```

### 6.2 从头训练

```bash
# 单机单卡调试（16 env，可视化）
python gear_sonic/train_agent_trl.py \
    +exp=manager/universal_token/all_modes/sonic_release \
    num_envs=16 headless=False

# 单机 8 卡训练（推荐配置）
accelerate launch --num_processes=8 gear_sonic/train_agent_trl.py \
    +exp=manager/universal_token/all_modes/sonic_release \
    num_envs=4096 headless=True

# 多节点训练（64+ GPUs 推荐）
accelerate launch \
    --multi_gpu --num_machines=8 --num_processes=64 \
    --machine_rank=$MACHINE_RANK \
    --main_process_ip=$MASTER_ADDR \
    --main_process_port=$MASTER_PORT \
    gear_sonic/train_agent_trl.py \
    +exp=manager/universal_token/all_modes/sonic_release \
    num_envs=4096 headless=True
```

### 6.3 从预训练模型微调（推荐）

```bash
accelerate launch --num_processes=8 gear_sonic/train_agent_trl.py \
    +exp=manager/universal_token/all_modes/sonic_release \
    +checkpoint=sonic_release/last.pt \
    num_envs=4096 headless=True \
    ++manager_env.commands.motion.motion_lib_cfg.motion_file=data/motion_lib_bones_seed/robot_filtered \
    ++manager_env.commands.motion.motion_lib_cfg.smpl_motion_file=data/smpl_filtered
```

### 6.4 使用 Sample Data 快速测试

无需下载完整 BONES-SEED，使用 HuggingFace 上的 sample data：

```bash
python gear_sonic/train_agent_trl.py \
    +exp=manager/universal_token/all_modes/sonic_release \
    num_envs=16 headless=True \
    ++manager_env.commands.motion.motion_lib_cfg.motion_file=sample_data/robot_filtered \
    ++manager_env.commands.motion.motion_lib_cfg.smpl_motion_file=sample_data/smpl_filtered
```

### 6.5 训练监控

**W&B 日志**（默认开启）：

```bash
WANDB_MODE=offline python gear_sonic/train_agent_trl.py ...   # 离线模式
wandb.wandb_project=my_project wandb.wandb_entity=my_team      # 自定义项目
use_wandb=false                                                # 完全关闭
```

**关键指标**：

| 指标 | 良好范围 | 描述 |
|------|---------|------|
| `rewards/total` | 3.0+ | 总奖励 |
| `rewards/anchor_pos_err` | < 0.15 | 根位置跟踪误差（米） |
| `rewards/body_pos_err` | < 0.10 | 身体位置跟踪误差（米） |
| `throughput/fps` | ~4000+ | 训练吞吐量 |

### 6.6 预期训练时间

| 硬件 | 100K iterations 耗时 |
|------|---------------------|
| 8x L40 | ~5-7 天 |
| 8x A100 | ~3-5 天 |
| 8x H100 | ~2-3 天 |

---

## 七、评估

### 7.1 单 Checkpoint 评估

```bash
# 交互式可视化
python gear_sonic/eval_agent_trl.py \
    +checkpoint=sonic_release/last.pt \
    +headless=False ++num_envs=1

# Headless 评估（指标模式）
python gear_sonic/eval_agent_trl.py \
    +checkpoint=sonic_release/last.pt \
    +headless=True \
    ++eval_callbacks=im_eval \
    ++run_eval_loop=False \
    ++num_envs=128

# 渲染视频
python gear_sonic/eval_agent_trl.py \
    +checkpoint=sonic_release/last.pt \
    +headless=True \
    ++eval_callbacks=im_eval \
    ++num_envs=8 \
    ++manager_env.config.render_results=True \
    "++manager_env.config.save_rendering_dir=/tmp/renders" \
    "~manager_env/recorders=empty" "+manager_env/recorders=render"
```

### 7.2 持续评估（Checkpoint Monitor）

```bash
python gear_sonic/eval_exp.py \
    +exp=manager/universal_token/all_modes/sonic_release
```

自动监控训练目录，评估新产生的 checkpoint 并记录到 W&B。

### 7.3 评估指标

**训练奖励**（W&B `Episode_Reward/`）：

| 指标 | 收敛值 | 描述 |
|------|--------|------|
| `tracking_vr_5point_local` | > 0.80 | 5 点跟踪质量 |
| `tracking_relative_body_pos` | > 0.44 | 上半身位置跟踪 |
| `tracking_anchor_pos` | > 0.14 | 根位置跟踪 |
| `time_out` | > 0.90 | 片段完成率 |

**评估指标**（`eval_agent_trl.py`）：

| 指标 | 收敛值 | 描述 |
|------|--------|------|
| `success_rate` | > 0.97 | 无提前终止的跟踪成功率 |
| `mpjpe_l` | < 30 mm | 局部关节位置误差 |
| `mpjpe_g` | < 200 mm | 全局关节位置误差 |

收敛良好的策略在 100K iterations 后可达 >0.98 success rate 和 <29 mm mpjpe_l。

---

## 八、ONNX 导出与部署

### 8.1 ONNX 导出

训练产出的 `.pt` checkpoint 可导出为 ONNX，供 C++ 推理栈部署：

```bash
python gear_sonic/eval_agent_trl.py \
    +checkpoint=<path_to_checkpoint.pt> \
    +headless=True ++num_envs=1 \
    +export_onnx_only=true
```

输出（在 `exported/` 目录下）：

| 文件 | 描述 |
|------|------|
| `*_smpl.onnx` | SMPL 编码器 + 解码器 |
| `*_g1.onnx` | G1 编码器 + 解码器 |
| `*_teleop.onnx` | Teleop 编码器 + 解码器 |
| `*_encoder.onnx` | 所有编码器组合 |
| `*_decoder.onnx` | 解码器单独 |

### 8.2 运动规划器（Kinematic Planner）

SONIC 部署时搭配一个**运动规划器**，负责生成未来全身姿态序列：

```
高层指令（mode, target_vel, direction, height）
    ↓
Kinematic Planner (ONNX, TensorRT 加速)
    ↓
未来 MuJoCo qpos 序列 (30 Hz)
    ↓
重采样到 50 Hz
    ↓
SONIC Policy (ONNX) 跟踪该序列
    ↓
机器人关节动作
```

规划器支持的 27 种运动模式：

| 类别 | 模式 |
|------|------|
| 移动 | idle, slowWalk, walk, run |
| 下蹲/地面 | squat, kneelTwoLeg, kneelOneLeg, lyingFacedown, handCrawling, elbowCrawling |
| 拳击 | idleBoxing, walkBoxing, leftJab, rightJab, randomPunches, leftHook, rightHook |
| 风格行走 | happy, stealth, injured, careful, objectCarrying, crouch, happyDance, zombie, point, scared |

### 8.3 C++ 部署栈

```bash
cd gear_sonic_deploy

# Docker 方式（推荐）
./docker/run-ros2-dev.sh
# 容器内
source scripts/setup_env.sh
just build

# 原生构建
./scripts/install_deps.sh
source scripts/setup_env.sh
just build
```

部署运行：

```bash
# Sim2Sim（MuJoCo 仿真）
bash deploy.sh sim

# 真机部署
bash deploy.sh real
```

### 8.4 训推衔接

```
┌─────────────────────────────────────────────┐
│              训练端 (gear_sonic)             │
│  train_agent_trl.py → PPO + Aux Loss        │
│       ↓                                     │
│  eval_agent_trl.py +export_onnx_only=true   │
│       ↓                                     │
│  ONNX 模型 (encoder + decoder)              │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│          部署端 (gear_sonic_deploy)          │
│  ONNX Runtime / TensorRT → ROS2 → Unitree G1 │
│                                              │
│  规划器线程 (10 Hz): 生成未来运动序列         │
│  控制线程 (50 Hz): 策略推理 + 电机控制        │
│  输入线程 (100 Hz): 键盘/手柄/ZMQ 接收        │
└─────────────────────────────────────────────┘
```

---

## 九、数据采集（VLA 数据收集）

### 9.1 概述

SONIC 支持通过 VR 遥操作采集数据，输出为 [LeRobot](https://github.com/huggingface/lerobot) 格式数据集，用于后续的 VLA（Vision-Language-Action）post-training。

### 9.2 系统架构

```text
    Workstation (offboard)                    Robot (onboard)
┌──────────────────────┐  ┌───────────────┐  ┌───────────────┐
│  C++ deploy          │  │ PICO teleop   │  │ Camera server │
│  (zmq, port 5557)    │  │ (zmq, port    │  │ (OAK cameras, │
│                      │  │  5556)        │  │  port 5555)   │
└──────────┬───────────┘  └───────┬───────┘  └───────┬───────┘
           │                      │                  │
           └────────────┬─────────┘──────────────────┘
                        │
               ┌────────▼────────┐
               │ Data Exporter   │
               │ (LeRobot format)│
               │ parquet + mp4   │
               └─────────────────┘
```

### 9.3 数据收集启动

```bash
# 安装数据收集环境
bash install_scripts/install_data_collection.sh

# 一键启动（tmux，4 个 pane）
python gear_sonic/scripts/launch_data_collection.py \
    --camera-host 192.168.123.164 \
    --task-prompt "pick up the cup"

# 或手动多终端运行
source .venv_data_collection/bin/activate
python gear_sonic/scripts/run_data_exporter.py \
    --task-prompt "pick up the cup" \
    --camera-host 192.168.123.164
```

### 9.4 输出格式

LeRobot v2.1 格式：

```
outputs/2026-04-03-14-30-00-G1-robot01/
├── data/
│   ├── train-00000.parquet      # 表格数据（关节状态、动作、标注）
│   └── ...
├── videos/
│   ├── observation.images.ego_view/
│   │   ├── episode_000000.mp4
│   │   └── ...
│   └── observation.images.left_wrist/
└── meta/
    ├── info.json
    ├── modality.json
    ├── episodes.jsonl
    └── tasks.jsonl
```

每条帧包含：
- `observation.state.joint_position` — 关节位置
- `observation.state.joint_velocity` — 关节速度
- `observation.images.ego_view` —  ego 视角图像
- `action.joint_position` — 遥操作目标关节位置
- `annotation.human.action.task_description` — 语言任务描述

### 9.5 后处理

```bash
# 清理 stale SMPL 帧
python gear_sonic/scripts/process_dataset.py \
    --dataset-path outputs/my_dataset

# 合并多个数据集
python gear_sonic/scripts/process_dataset.py \
    --dataset-path outputs/session1 outputs/session2 \
    --output-path outputs/merged_dataset
```

---

## 十、环境安装速查

### 10.1 各用途环境对照

| 用途 | 环境 | 安装方式 |
|------|------|---------|
| **训练 / 微调** | Isaac Lab conda env | 先装 Isaac Lab，再 `pip install -e "gear_sonic[training]"` |
| **MuJoCo 仿真** | `.venv_sim` | `bash install_scripts/install_mujoco_sim.sh` |
| **VR 遥操作** | `.venv_teleop` | `bash install_scripts/install_pico.sh` |
| **数据采集** | `.venv_data_collection` | `bash install_scripts/install_data_collection.sh` |
| **真机部署** | C++ build / Docker | `gear_sonic_deploy/docker/run-ros2-dev.sh` |

### 10.2 Docker 部署环境（推荐）

```bash
# 宿主机只需：NVIDIA 驱动 + Docker + TensorRT TAR 包
cd gear_sonic_deploy/docker
./run-ros2-dev.sh

# 容器内已包含：ROS2 Humble, CUDA 12.4.1, CMake, Clang, just, ONNX Runtime
source scripts/setup_env.sh
just build
```

### 10.3 验证环境

```bash
python check_environment.py              # 全量检查
python check_environment.py --training   # 仅训练
python check_environment.py --deploy     # 仅部署
```

---

## 十一、关键入口速查表

| 目标 | 命令 / 文件 |
|------|------------|
| **主训练** | `gear_sonic/train_agent_trl.py` |
| **单点评估** | `gear_sonic/eval_agent_trl.py` |
| **持续评估** | `gear_sonic/eval_exp.py` |
| **ONNX 导出** | `eval_agent_trl.py +export_onnx_only=true` |
| **核心模型** | `gear_sonic/trl/modules/universal_token_modules.py` |
| **PPO 训练器** | `gear_sonic/trl/trainer/ppo_trainer_aux_loss.py` |
| **默认训练预设** | `config/exp/manager/universal_token/all_modes/sonic_release.yaml` |
| **PPO 超参** | `config/algo/ppo_im_phc.yaml` |
| **辅助损失** | `config/aux_losses/universal_token/g1_recon_and_all_latent.yaml` |
| **数据下载** | `python download_from_hf.py` |
| **Sim2Sim** | `deploy.sh sim` + `run_sim_loop.py` |
| **数据采集** | `launch_data_collection.py` |
| **数据处理** | `gear_sonic/scripts/process_dataset.py` |

---

## 十二、参考文档索引

| 文档路径 | 内容 |
|---------|------|
| `docs/source/user_guide/training.md` | 完整训练指南 |
| `docs/source/user_guide/training_data.md` | BONES-SEED 数据集说明 |
| `docs/source/references/training_code.md` | 代码深度参考 |
| `docs/source/references/planner_onnx.md` | 运动规划器 ONNX 导出 |
| `docs/source/getting_started/installation_training.md` | 训练环境安装 |
| `docs/source/getting_started/installation_deploy.md` | 部署环境安装 |
| `docs/source/user_guide/new_embodiments.md` | 添加新机器人本体 |
| `docs/source/user_guide/teleoperation.md` | 遥操作最佳实践 |
| `docs/source/getting_started/vr_teleop_setup.md` | PICO VR 设置 |
| `docs/source/tutorials/data_collection.md` | 数据采集管线 |
