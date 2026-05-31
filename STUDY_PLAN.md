# GR00T-WholeBodyControl 精通学习计划

> 目标：将具备基础机器学习背景的研发人员，系统培养为能独立开发、调试、部署此项目的核心研发。
> 预计周期：**12 周**（每日 2-3h，周末 4-5h）

---

## 0. 先认清你脚下的土地 —— 项目技术地图

GR00T-WholeBodyControl 不是单一项目，而是**三套系统共存**的一个大型研发仓库：

```
┌─────────────────────────────────────────────────────────────┐
│                  GR00T-WholeBodyControl                     │
├─────────────────┬───────────────────┬───────────────────────┤
│  decoupled_wbc/ │   gear_sonic/     │  gear_sonic_deploy/   │
│  (Python)       │   (Python)        │  (C++20)              │
├─────────────────┼───────────────────┼───────────────────────┤
│ 解耦全身控制     │ 通用全身控制器      │ 实机部署推理栈        │
│ RL下半身 +       │ 大规模运动跟踪      │ TensorRT / ONNX      │
│ IK上半身         │ 多模态Token架构     │ 4线程实时控制        │
│ ROS2 IPC         │ IsaacLab训练        │ Unitree SDK2 DDS     │
└─────────────────┴───────────────────┴───────────────────────┘
```

**你目前完成的那次训练**（`scripts/reinforcement_learning/rsl_rl/train.py`）属于 **Isaac Lab 官方示例**，用的是 **RSL-RL**。但 `gear_sonic/` 自己的训练系统（`train_agent_trl.py`）**并未使用 RSL-RL**，而是基于 HuggingFace TRL 自研了一套 PPO 训练器。

**一句话区分**：
- **RSL-RL** = ETH 苏黎世的 PPO 库（简单、高效、你刚跑过）
- **gear_sonic.trl** = 本项目自研的 PPO + Auxiliary Losses（支持 FSQ 量化、多编码器、动作分块等复杂功能）

---

## 第一阶段：地基建设（第 1-2 周）

> **目标**：补齐机器人控制 + RL + 运动学的前置知识，建立共同语言。

### 必读论文

| 优先级 | 论文 | 为什么读 |
|--------|------|---------|
| ⭐⭐⭐ | [PPO: Proximal Policy Optimization](https://arxiv.org/abs/1707.06347) (Schulman 2017) | 项目所有 RL 训练的根基 |
| ⭐⭐⭐ | [GAE: Generalized Advantage Estimation](https://arxiv.org/abs/1506.02438) (Schulman 2016) | 理解 `gae_lambda` 和优势函数怎么算 |
| ⭐⭐ | [SMPL](https://smpl.is.tue.mpg.de/) (Loper et al. 2015) | 人体参数化模型，理解 `smpl_mlp` 编码器的输入 |
| ⭐ | [6D Rotation Representation](https://arxiv.org/abs/1812.07035) (Zhou CVPR 2019) | 理解为什么代码里不用欧拉角，而用 6D/四元数 |

### 必读代码/文档

| 文件/目录 | 读什么 |
|-----------|--------|
| `docs/算法解析/逆运动学(IK)初学者指南.md` | Pink 库做 QP-IK 的基本原理 |
| `docs/GR00T-WholeBodyControl 安装与复现手册.md` | 先把所有环境装通 |
| `docs/GR00T-WholeBodyControl 项目文件结构详解.md` | 建立文件导航感 |
| `gear_sonic/trl/trainer/ppo_trainer.py` 前 200 行 | 先不读细节，只看 `_rollout_step()` 和 `train()` 的宏观流程 |

### 动手任务

1. **跑通一个非 Isaac Lab 的 PPO 小实验**
   ```bash
   pip install stable-baselines3 gymnasium
   python -c "import gymnasium as gym; from stable_baselines3 import PPO; env = gym.make('Humanoid-v4'); model = PPO('MlpPolicy', env, verbose=1); model.learn(total_timesteps=10000)"
   ```
   > 目的：理解 PPO 需要什么输入（obs）、输出什么（action distribution）、loss 由哪几部分组成。

2. **用 Pinocchio 算一次 G1 的前向运动学**
   ```python
   import pinocchio as pin
   # 加载 decoupled_wbc 里的 G1 URDF，算一下 FK
   ```
   > 目的：理解 `joint angles → body position` 的映射关系。

### 阶段产出

- [ ] 能手绘 PPO 的训练循环图（Rollout → Compute GAE → Update Policy → Repeat）
- [ ] 能解释 SMPL 的 `beta`（形状）和 `pose`（姿态）参数
- [ ] 能解释为什么 ReLU 不适合机器人控制（Dying ReLU）而 ELU 更适合

---

## 第二阶段：Isaac Lab 环境系统（第 3-4 周）

> **目标**：彻底理解 Isaac Lab 的环境配置体系，能独立修改奖励、观察、终止条件。

### 核心概念

Isaac Lab 的 `ManagerBasedRLEnv` 由 6 个 Manager 组成：

```
Observation Manager  → 策略看什么
Reward Manager       → 做什么给奖励
Termination Manager  → 什么时候结束
Command Manager      → 给什么指令（如目标速度）
Event Manager        → 域随机化、物理参数扰动
Curriculum Manager   → 难度自动调整（如地形升级）
```

### 精读文件

| 文件 | 读什么 |
|------|--------|
| `gear_sonic/envs/manager_env/modular_tracking_env_cfg.py` | 环境配置类怎么组装 6 个 Manager |
| `gear_sonic/config/manager_env/base_env.yaml` | 基础环境参数（viewer_eye, terrain, num_envs） |
| `gear_sonic/config/manager_env/rewards/tracking/*.yaml` | 跟踪类奖励的权重和公式 |
| `gear_sonic/config/manager_env/observations/policy/*.yaml` | Policy 观察空间的组成 |
| `gear_sonic/config/manager_env/terminations/tracking/*.yaml` | 终止条件（摔倒、超时、出界） |
| `gear_sonic/config/exp/manager/universal_token/all_modes/sonic_release.yaml` | **实验预设文件**，看 Hydra 如何组合所有配置 |

### 动手任务

1. **修改奖励权重并重训**
   - 把 `track_lin_vel_xy_exp` 的权重从默认改成 2.0 倍
   - 在 `gear_sonic/config/manager_env/rewards/` 下创建自己的 `my_rewards.yaml`
   - 跑一次短训练（100 iter），对比 TensorBoard 曲线差异

2. **可视化观察空间**
   ```bash
   # 在训练脚本里加一行打印，看 observation 的 shape 和 key
   print(env.observation_space)
   ```

3. **读通 G1 Rough Terrain 的奖励函数**
   - 逐项解释 `feet_air_time`、`feet_slide`、`termination_penalty` 的物理含义
   - 参考之前你训练日志里的最终数值（如 `feet_air_time=0.0085`）判断训练好坏

### 阶段产出

- [ ] 能独立写一个新的 `RewardTerm`（如"惩罚膝盖内扣"）并注册到配置中
- [ ] 能解释 Curriculum 怎么让地形从简单变难（看 `terrain_levels` 从 0→5.8）
- [ ] 能解释 `num_steps_per_env=24` 和 `max_iterations=3000` 的乘积关系

---

## 第三阶段：SONIC 核心架构 — Universal Token Module（第 5-6 周）

> **目标**：理解项目的"灵魂"——多编码器 + FSQ 量化 + 多解码器的 Action Transform Module。

### 必读论文

| 论文 | 核心收获 |
|------|---------|
| **SONIC** (arXiv:2511.07820) | ATM 架构、BONES-SEED 数据集、大规模运动跟踪训练范式 |
| **FSQ** (Mentzer et al. 2023) | 为什么用 `fsq_level_list: [8,8,8,5,5,5]` 而不是 VQ-VAE |

### 精读代码

| 文件 | 读什么 |
|------|--------|
| `gear_sonic/trl/modules/universal_token_modules.py` | **整个 ATM 的前向流程**：obs → encoders → latent → FSQ → decoder → action |
| `gear_sonic/trl/modules/actor_critic_modules.py` | Actor 怎么包 ATM、Critic 怎么独立做价值估计 |
| `gear_sonic/trl/trainer/ppo_trainer_aux_loss.py` | `ppo_loss + aux_loss` 的加权组合逻辑 |
| `gear_sonic/trl/losses/token_losses.py` | `G1ReconLoss`、`G1SmplLatentLoss` 等辅助 loss 的数学实现 |
| `gear_sonic/envs/wrapper/manager_env_wrapper.py` | `residual` / `direct_latent` / `mixed` 三种动作模式的区别 |

### 关键理解点

```
输入侧（多种模态，选一个）          共享空间                输出侧
┌─────────┐                        ┌──────────┐          ┌─────────────┐
│ G1 关节  │──► G1 Encoder ──►     │          │          │ G1 Dynamic  │──► 机器人动作
├─────────┤                        │  Latent  │   FSQ    │  Decoder    │
│ SMPL  pose│──► SMPL Encoder ──►  │  Space   │──► Quant │  (runtime)  │
├─────────┤                        │          │          ├─────────────┤
│ Teleop   │──► Teleop Encoder ──► │          │          │ G1 Kinematic│──► 辅助Loss
├─────────┤                        │          │          │  Decoder    │
│ SOMA     │──► SOMA Encoder ──►   │          │          └─────────────┘
└─────────┘                        └──────────┘
```

- **Encoder**：把不同模态的输入映射到同一个 latent space
- **FSQ**：把连续 latent 离散化成 compact tokens（比 VQ-VAE 简单，不需要 codebook）
- **Decoder**：把 tokens 解码成 G1 的关节动作
- **Latent Residual**：外部策略可以在 latent 层注入修正，不用重新训练 ATM

### 动手任务

1. **打印 ATM 的模型结构**
   ```python
   from gear_sonic.trl.modules.universal_token_modules import UniversalTokenModule
   # 加载 config，实例化模型，print(model)
   ```

2. **导出 ONNX 并可视化**
   ```bash
   cd gear_sonic
   python eval_agent_trl.py \
     +checkpoint=/path/to/checkpoint \
     export_onnx_only=true \
     num_envs=1
   ```
   > 查看生成的 `*_encoder.onnx` 和 `*_decoder.onnx`，用 Netron 打开看结构。

3. **对比实验**
   - 用 `sonic_release.yaml`（3 encoders）vs `sonic_bones_seed.yaml`（4 encoders + SOMA）
   - 观察训练速度和最终 reward 的差异

### 阶段产出

- [ ] 能手绘 ATM 的完整数据流图（从 obs 到 action，标出 FSQ 位置）
- [ ] 能解释 `residual` 模式 vs `direct_latent` 模式的区别
- [ ] 能解释辅助 loss 为什么能提升泛化性（跨模态对齐）

---

## 第四阶段：数据流与运动跟踪（第 7-8 周）

> **目标**：理解 BONES-SEED 数据从下载到变成训练数据的完整链路。

### 必读文档

| 文档 | 核心内容 |
|------|---------|
| `docs/算法解析/人体到G1重定向的数学原理.md` | **T-Pose Delta 重定向的 6 步推导**（必读！） |
| `docs/数据集讲解/SONIC 数据集梳理与汇总.md` | BONES-SEED 数据结构、过滤规则、LeRobot 格式 |
| `docs/数据集讲解/SMPL与BONES-SEED数据集对比.md` | SMPL 参数空间 vs G1 关节空间的映射关系 |

### 精读代码

| 文件 | 读什么 |
|------|--------|
| `gear_sonic/data_process/convert_soma_csv_to_motion_lib.py` | CSV → motion_lib PKL 的转换逻辑 |
| `gear_sonic/utils/motion_lib/motion_lib_base.py` | 运动库采样、自适应采样（Auto PMCP） |
| `gear_sonic/utils/motion_lib/skeleton.py` | 骨骼树、SLERP 插值、FK |
| `decoupled_wbc/data/exporter.py` | LeRobot VLA 数据导出格式 |

### 关键理解点

**重定向 6 步法**：
1. T-Pose 参考对齐（找到 root-relative rotation）
2. 全局旋转差计算
3. 缩放归一化（SMPL 和 G1 身高不同）
4. 父关节继承链
5. 1-DOF axis-angle 投影
6. IsaacLab ↔ MuJoCo 关节索引重排

### 动手任务

1. **下载并可视化 BONES-SEED 数据**
   ```bash
   python download_from_hf.py --training
   ```
   > 用 `matplotlib` 或 `polyscope` 可视化一段重定向后的 G1 动作。

2. **跑通 motion_lib 生成**
   ```bash
   python gear_sonic/data_process/convert_soma_csv_to_motion_lib.py \
     --input_dir data/bones_seed_smpl \
     --output_dir data/motion_lib_bones_seed
   ```

3. **修改过滤规则**
   - 在 `filter_and_copy_bones_data.py` 里加一条自己的过滤规则
   - 观察过滤前后 motion 数量的变化

### 阶段产出

- [ ] 能解释为什么 BONES-SEED 有 14.2 万条 motion，过滤后剩 13 万（8.7% 被滤掉）
- [ ] 能解释 `motion_lib` 的 PKL 文件里存了哪些字段（qpos, qvel, body_pos, etc.）
- [ ] 能独立把一段 SMPL 动画重定向到 G1 上（跑通脚本）

---

## 第五阶段：Decoupled WBC 与部署（第 9-10 周）

> **目标**：理解从训练好的模型到实机运行的完整部署链路。

### 必读文档

| 文档 | 核心内容 |
|------|---------|
| `docs/source/references/decoupled_wbc.md` | 解耦控制架构详解 |
| `docs/改装G1实机部署工作清单.md` | 改装机器人后的部署注意事项 |
| `gear_sonic_deploy/README.md` | C++ 部署栈编译和运行指南 |

### 精读代码

| 文件 | 读什么 |
|------|--------|
| `decoupled_wbc/control/policy/g1_gear_wbc_policy.py` | ONNX 策略加载、86-D 观察向量构建、历史缓冲 |
| `decoupled_wbc/control/policy/g1_decoupled_whole_body_policy.py` | 上下身策略融合、安全超时机制 |
| `decoupled_wbc/control/robot_model/robot_model.py` | Pinocchio FK、重力补偿、Joint Groups |
| `gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/src/g1_deploy_onnx_ref.cpp` | **4 线程实时循环**（Input/Control/Planner/Writer） |
| `gear_sonic_deploy/include/control_policy.hpp` | TensorRT 推理引擎封装 |
| `gear_sonic_deploy/include/observation_config.hpp` | 154-D 观察向量的 YAML 配置解析 |

### 关键理解点

**Decoupled WBC 架构**：
```
Teleop / Keyboard / Planner
        ↓
[Upper Body Policy]  ←  IK (Pink)  →  target_upper_body_pose
        ↓                                                    ↓
[G1DecoupledWholeBodyPolicy]  ←  combine  →  full q (29 DOF)
        ↑                                                    ↑
[Lower Body Policy]  ←  RL ONNX (gear_wbc)  →  body_action
        ↑
   Observations (86-D)
```

**C++ 部署 4 线程**：
| 线程 | 频率 | 职责 |
|------|------|------|
| Input | 100 Hz | 读取输入（键盘/ZMQ/ROS2） |
| Control | 50 Hz | 观察 → TensorRT 推理 → 电机目标 |
| Planner | 10 Hz | 27 模式轨迹规划，30→50 Hz SLERP 插值 |
| Command Writer | 500 Hz | 通过 Unitree SDK2 DDS 发 `LowCmd_` |

### 动手任务

1. **在 MuJoCo 里跑 Decoupled WBC**
   ```bash
   python decoupled_wbc/sim2mujoco/scripts/run_mujoco_gear_wbc.py
   ```

2. **编译 C++ 部署栈**
   ```bash
   cd gear_sonic_deploy
   source scripts/setup_env.sh
   just build
   ```

3. **做一次 ONNX → TensorRT 转换**
   - 用 `gear_sonic_deploy/src/TRTInference/` 的代码加载 `model_2999.pt` 导出的 ONNX
   - 观察 `.trt` 引擎缓存文件的生成

### 阶段产出

- [ ] 能解释 86-D 观察向量里每一项的来源（joint pos, IMU, cmd, history...）
- [ ] 能解释 Decoupled WBC 的安全超时机制（1 秒无 teleop 指令时注入默认导航命令）
- [ ] 能解释为什么 C++ 部署需要 `policy_fp16_` 前缀的 TensorRT 引擎（FP16 加速）

---

## 第六阶段：综合实战（第 11-12 周）

> **目标**：独立提出改进，完成端到端实验，形成可交付的产出。

### 实战选题（选一个方向深入）

#### 方向 A：改进 Universal Token Module
- **想法**：在 encoder 里加一层 Transformer 做时序建模（目前是纯 MLP）
- **验证**：在 `gear_sonic/trl/modules/base_module.py` 里加 `TransformerEncoder` 类型
- **评估**：对比 MLP vs Transformer 的 `mean_reward` 和 `episode_length`

#### 方向 B：改进运动跟踪数据流
- **想法**：设计一个新的 reward shaping（如"惩罚膝盖过度伸展"）
- **验证**：修改 `gear_sonic/config/manager_env/rewards/`，重训 500 iter
- **评估**：对比训练曲线和 Policy 的关节极限分布

#### 方向 C：C++ 部署优化
- **想法**：把 C++ 部署的推理线程从 50Hz 优化到 100Hz
- **验证**：调整 `control_thread` 的 sleep 间隔，测试 CPU/GPU 占用
- **评估**：测量端到端延迟（从 observation 到 motor command）

#### 方向 D：数据收集与 VLA
- **想法**：用 PICO VR 采集一段自己的动作，导出为 LeRobot 格式
- **验证**：跑 `gear_sonic/scripts/launch_data_collection.py`
- **评估**：检查导出数据的 parquet 结构和视频质量

### 产出要求

1. **技术报告**（Markdown，≥3000 字）
   - 背景、方法、实验设计、结果、结论
   - 附 TensorBoard 截图和关键代码 diff

2. **代码提交**
   - 一个可复现的实验分支
   - 包含修改后的 config 和启动脚本

3. **内部分享**
   - 15 分钟的技术分享 PPT/文档
   - 讲清楚：改了什么、为什么改、效果怎么样

---

## 附录 A：前置知识速查表

如果你发现自己卡住了，先回到这里补基础：

| 概念 | 不懂会卡在哪 | 推荐资源 |
|------|------------|---------|
| **梯度下降 / 反向传播** | 看不懂 loss 怎么更新网络 | 吴恩达 DL Course 1 |
| **概率分布采样** | 看不懂 `mean + std * noise` | PyTorch `torch.distributions.Normal` |
| **四元数 / 旋转矩阵** | 看不懂姿态表示 | 3Blue1Brown 系列 + `scipy.spatial.transform` |
| **Docker / Conda** | 环境装不上 | Docker 官方文档 + Conda cheat sheet |
| **CMake / C++ 基础** | 编译不过部署栈 | CMake 官方教程（前 10 章） |

## 附录 B：常见问题速答

**Q：为什么训练用 Isaac Lab，部署用 MuJoCo？**
> Isaac Lab 基于 USD/Omniverse，渲染和物理都在 GPU 上，适合大规模并行训练。MuJoCo 轻量、确定性强、CPU 也能跑，适合部署侧的快速仿真验证。

**Q：RSL-RL 和 gear_sonic.trl 到底用哪个？**
> RSL-RL 只用于 Isaac Lab 官方示例（如你刚跑的 `rsl_rl/train.py`）。`gear_sonic` 真正的训练入口是 `train_agent_trl.py`，用的是自研 TRL。

**Q：Decoupled WBC 和 SONIC 是什么关系？**
> 两套独立系统。Decoupled WBC 是 N1.5/N1.6 的控制器（下半身 RL + 上半身 IK）。SONIC 是统一策略（一个网络管全身），基于运动跟踪预训练。

**Q：为什么 `gear_sonic_deploy` 用 C++ 而不是 Python？**
> 实时控制要求确定性延迟（< 20ms）。Python 的 GIL 和 GC 不可控，C++ 20 可以做到 500Hz 的命令写入。

## 附录 C：关键文件索引（按学习阶段）

```
阶段 1（地基）:
  docs/算法解析/逆运动学(IK)初学者指南.md
  docs/GR00T-WholeBodyControl 安装与复现手册.md

阶段 2（环境）:
  gear_sonic/envs/manager_env/modular_tracking_env_cfg.py
  gear_sonic/config/exp/manager/universal_token/all_modes/sonic_release.yaml
  gear_sonic/config/manager_env/rewards/tracking/*.yaml

阶段 3（架构）:
  gear_sonic/trl/modules/universal_token_modules.py
  gear_sonic/trl/modules/actor_critic_modules.py
  gear_sonic/trl/trainer/ppo_trainer_aux_loss.py

阶段 4（数据）:
  docs/算法解析/人体到G1重定向的数学原理.md
  gear_sonic/data_process/convert_soma_csv_to_motion_lib.py
  gear_sonic/utils/motion_lib/motion_lib_base.py

阶段 5（部署）:
  decoupled_wbc/control/policy/g1_gear_wbc_policy.py
  decoupled_wbc/control/robot_model/robot_model.py
  gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/src/g1_deploy_onnx_ref.cpp
  gear_sonic_deploy/include/control_policy.hpp

阶段 6（实战）:
  gear_sonic/train_agent_trl.py
  gear_sonic/eval_agent_trl.py
  你自己的实验分支
```

---

**最后一句建议**：不要试图在两周内读完所有代码。这个项目的精髓在于**"先跑通，再读透，最后改对"**。每读完一个模块，就动手改一行配置、加一个 print、跑一次训练——Debug 模式下的学习速度是纯阅读的 10 倍。
