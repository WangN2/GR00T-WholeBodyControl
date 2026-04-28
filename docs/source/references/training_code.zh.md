# 训练代码结构

本页描述 `gear_sonic/` 下的 Python 训练代码库，涵盖目录布局、训练管线、配置系统、关键模块和评估脚本。

---

## 目录布局

```
gear_sonic/
├── train_agent_trl.py          # 主训练入口
├── eval_agent_trl.py           # 单检查点评估
├── eval_exp.py                 # 检查点监控（连续评估）
├── config/                     # Hydra 配置层级
│   ├── base.yaml               # 全局默认值（种子、环境数、路径）
│   ├── base_eval.yaml          # 评估专用全局默认值
│   ├── eval_exp.yaml           # 检查点监控配置
│   ├── base/                   # Hydra 管道（输出目录、解析器）
│   ├── algo/                   # PPO 超参数
│   ├── actor_critic/           # 演员-评论家架构配置
│   │   ├── encoders/           # 各编码器 MLP 配置（g1、smpl、teleop）
│   │   ├── decoders/           # 解码器 MLP 配置（g1_kin、g1_dyn）
│   │   ├── critics/            # 评论家骨干网络配置
│   │   ├── quantizers/         # FSQ 量化器配置
│   │   └── universal_token/    # 组装的编码器+解码器+量化器预设
│   ├── aux_losses/             # 辅助损失定义
│   ├── callbacks/              # 训练回调配置
│   ├── exp/                    # 实验预设（组装所有组件）
│   ├── manager_env/            # 环境 MDP 组件配置
│   ├── opt/                    # 日志选项（wandb）
│   └── trainer/                # 训练器类选择
├── envs/                       # IsaacLab 环境包装器
│   ├── manager_env/
│   │   ├── modular_tracking_env_cfg.py   # 场景、传感器、机器人关节
│   │   ├── robots/             # 各机器人配置（g1.py、h2.py）
│   │   └── mdp/                # MDP 组件（见下文）
│   ├── wrapper/
│   │   └── manager_env_wrapper.py  # 面向 RL 的环境包装器
│   └── env_utils/              # 关节顺序工具
├── trl/                        # 训练模块（PPO、演员-评论家、损失）
│   ├── trainer/
│   │   ├── ppo_trainer.py          # 基础 PPO 训练器
│   │   └── ppo_trainer_aux_loss.py # PPO + 辅助损失（SONIC）
│   ├── modules/
│   │   ├── actor_critic_modules.py     # 演员、评论家类
│   │   ├── universal_token_modules.py  # UniversalTokenModule（SONIC ATM）
│   │   ├── base_module.py              # 共享 MLP 构建块
│   │   └── data_utils.py              # 批次/数据辅助工具
│   ├── losses/
│   │   └── token_losses.py     # 重建与潜在辅助损失
│   ├── callbacks/              # 运行时回调
│   │   ├── im_eval_callback.py     # 模仿评估指标
│   │   ├── im_resample_callback.py # 自适应动作重采样
│   │   ├── model_save_callback.py  # 检查点保存
│   │   ├── wandb_callback.py       # W&B 日志
│   │   └── read_eval_callback.py   # 从磁盘读取评估结果
│   └── utils/                  # 数学、旋转、调度工具
├── utils/                      # 共享工具
│   ├── motion_lib/             # 动作库加载（PKL 格式）
│   ├── mujoco_sim/             # MuJoCo 仿真到仿真桥接
│   └── teleop/                 # VR 遥操作辅助工具
├── data/                       # 机器人模型、URDF/USD 资源
├── data_process/               # 动作数据转换脚本
└── scripts/                    # MuJoCo 仿真循环、杂项工具
```

---

## 训练管线

运行 `python gear_sonic/train_agent_trl.py +exp=manager/universal_token/all_modes/sonic_release` 会执行以下步骤：

### 1. 配置加载

入口点使用 `@hydra.main(config_path="config", config_name="base")`。`+exp=...` 参数选择一个实验预设，组装所有子配置：

```
base.yaml                          # 全局默认值
  └── +exp=manager/universal_token/all_modes/sonic_release
        ├── /algo: ppo_im_phc      # PPO 超参数
        ├── /actor_critic: universal_token/all_mlp_v1
        │     ├── encoders/g1_mf_mlp, smpl_mlp, teleop_mlp
        │     ├── decoders/g1_kin_mf_mlp, g1_dyn_mlp
        │     ├── quantizers/fsq
        │     └── critics/mlp
        ├── /manager_env: base_env  # 环境配置
        │     ├── observations/{tokenizer, policy, critic}
        │     ├── rewards/tracking/base_5point_local_feet_acc
        │     ├── terminations/tracking/base_adaptive_strict_ori_foot_xyz
        │     └── events/tracking/level0_4
        ├── /aux_losses: universal_token/g1_recon_and_all_latent
        ├── /trainer: trl_ppo_aux
        └── /callbacks: model_save, wandb, read_eval, im_resample
```

### 2. 仿真器和加速器初始化

配置解析后，脚本：
1. 从配置字典解析 TRL `PPOConfig` / `ScriptArguments` / `ModelConfig`。
2. 创建 HuggingFace `Accelerator` 以支持多 GPU（DDP）。
3. 启动 IsaacLab `AppLauncher` 以启动 Isaac Sim 运行时。
4. 将 `config.yaml` 和 `meta.yaml` 保存到实验目录。

### 3. 环境创建

`create_manager_env()` 从组装的环境配置实例化 IsaacLab `ManagerBasedRLEnv`，然后用 `ManagerEnvWrapper` 包装它：

```
ManagerBasedRLEnv (IsaacLab)
  └── ManagerEnvWrapper
        ├── 观测空间（策略、评论家、分词器组）
        ├── 动作命令管理器（motion_lib）
        ├── 动作转换模块（可选，用于预训练 ATM）
        └── 键盘/可视化钩子
```

### 4. 策略和价值模型创建

演员和评论家从算法配置实例化。对于 SONIC 训练，演员骨干网络是 `UniversalTokenModule`：

```python
# 简化自 train_agent_trl.py
policy = custom_instantiate(config.algo.config.actor, env_config=env.config, ...)
value_model = custom_instantiate(config.algo.config.critic, env_config=env.config, ...)
```

`Actor` 将 `UniversalTokenModule` 包装为其骨干网络，并添加对角高斯分布用于探索。`Critic` 包装一个单独的 MLP 骨干网络。

### 5. PPO 训练循环

`TRLAuxLossPPOTrainer.train()` 方法运行主循环：

```
for iteration in range(num_learning_iterations):
    # 1.  rollout：收集 num_steps_per_env 个转移
    for step in range(num_steps_per_env):
        actions = policy.rollout(obs_dict)
        obs_dict, rewards, dones, infos = env.step(actions)
        store(obs, actions, rewards, values, log_probs)

    # 2. GAE：计算优势和回报
    advantages = generalized_advantage_estimation(rewards, values, dones)

    # 3. PPO 更新：在 mini-batch 上运行 num_ppo_epochs 轮
    for epoch in range(num_ppo_epochs):
        for mini_batch in shuffle_and_split(rollout_data):
            policy_loss = clipped_surrogate_objective(...)
            value_loss  = clipped_value_loss(...)
            aux_loss    = sum(coef_i * aux_loss_i)  # 编码器重建等
            total_loss  = policy_loss + value_loss_coef * value_loss
                        + aux_loss_scale * aux_loss
            optimizer.step(total_loss)

    # 4. 更新后：同步运行统计、自适应采样、回调
    update_scheduled_params(...)     # 学习率、域随机化
    callbacks.on_step_end(...)       # 检查点、评估、日志
```

---

## 配置系统

配置系统使用 [Hydra](https://hydra.cc/)，具有配置组和组合功能。

### 层级

| 层级 | 路径 | 用途 |
|---|---|---|
| **全局** | `config/base.yaml` | 种子、环境数、路径、wandb 开关 |
| **算法** | `config/algo/ppo_im_phc.yaml` | PPO 超参数、学习率、轮数 |
| **演员-评论家** | `config/actor_critic/` | 网络架构（编码器、解码器、评论家） |
| **环境** | `config/manager_env/` | 观测、奖励、终止条件、事件 |
| **辅助损失** | `config/aux_losses/` | 重建和潜在对齐损失 |
| **训练器** | `config/trainer/` | 训练器类选择（PPO 或 PPO+AuxLoss） |
| **回调** | `config/callbacks/` | 检查点、评估、W&B 日志 |
| **实验** | `config/exp/` | 组装上述所有内容的预设 |

### 实验预设

实验配置位于 `config/exp/` 下，使用 `@package _global_` 指令在根级别设置值。它们通过 `defaults` 组装所有组件配置：

```yaml
# config/exp/manager/universal_token/all_modes/sonic_release.yaml
defaults:
  - /algo: ppo_im_phc
  - /manager_env: base_env
  - override /actor_critic: universal_token/all_mlp_v1
  - override /manager_env/observations/tokenizer: unitoken_all_noz
  - override /manager_env/observations/policy: local_dir_hist
  - override /manager_env/rewards: tracking/base_5point_local_feet_acc
  - override /manager_env/terminations: tracking/base_adaptive_strict_ori_foot_xyz
  - override /manager_env/events: tracking/level0_4
  # ...
```

### 关键配置参数

| 参数 | 默认值 | 描述 |
|---|---|---|
| `num_envs` | 4096 | 并行仿真环境数量 |
| `algo.config.num_learning_iterations` | 100000 | 总训练迭代次数 |
| `algo.config.num_steps_per_env` | 32 | 每次迭代的 rollout 范围 |
| `algo.config.num_learning_epochs` | 5 | 每次迭代的 PPO 轮数 |
| `algo.config.num_mini_batches` | 4 | 每轮 PPO 的 mini-batch 数 |
| `algo.config.actor_learning_rate` | 2e-5 | 演员学习率 |
| `algo.config.critic_learning_rate` | 1e-3 | 评论家学习率 |
| `algo.config.clip_param` | 0.2 | PPO 裁剪参数 |
| `algo.config.init_noise_std` | 0.05 | 初始探索噪声标准差 |
| `algo.config.save_interval` | 500 | 检查点保存频率（迭代次数） |

---

## 通用 Token 模块

`UniversalTokenModule` 实现了 SONIC 的动作转换模块（ATM）—— 将多种动作输入映射到共享 Token 空间的核心架构。

### 架构

```
                  ┌─────────────┐
  G1 观测   ───►  │  G1 编码器  │──┐
                  └─────────────┘  │
                  ┌─────────────┐  │    ┌─────────┐     ┌─────────────┐
  遥操作观测───►  │遥操作编码器 │──┼──► │   FSQ   │──►  │ G1 动态     │──► 关节动作
                  └─────────────┘  │    │量化器   │     │   解码器    │
                  ┌─────────────┐  │    └─────────┘     └─────────────┘
  SMPL 观测 ───►  │SMPL 编码器  │──┘          │
                  └─────────────┘             │         ┌─────────────┐
                                              └───────► │G1 运动学   │──► （仅辅助损失）
                                                        │   解码器    │
                                                        └─────────────┘
```

**编码器**将不同的观测模态映射到共享潜在空间。每个编码器是一个 MLP，接收模态特定的分词器观测并输出固定大小的潜在向量。训练期间，根据 `encoder_sample_probs` 为每个环境采样一个编码器。

**FSQ 量化器**使用有限标量量化将连续潜在离散化为有限 Token 集。每个潜在维度被独立量化到 `fsq_level_list` 离散级别之一。这产生紧凑的离散 Token 表示。

**解码器**从量化 Token 加上本体感受重建输出：
- **G1 动态解码器**（`g1_dyn`）：产生发送到执行器的关节空间动作。这是部署时唯一使用的解码器。
- **G1 运动学解码器**（`g1_kin`）：从 Token 重建未来动作帧。仅在训练期间用于计算重建辅助损失。

### 潜在残差模式

对于下游任务（例如物体操作），外部策略可以在不重新训练基础 ATM 的情况下将修正注入 Token 空间：

| 模式 | 行为 |
|---|---|
| `post_quantization`（默认） | 残差在 FSQ 量化后添加 |
| `pre_quantization` | 残差在 FSQ 之前添加；总和被量化 |
| `pre_quantization_replace` | 潜在向量完全被残差替换 |

### 编码器采样

训练期间，每个环境根据 `encoder_sample_probs` 随机分配一个编码器。`encoder_index` 观测告诉模块哪个编码器产生了当前 Token。部署时，只有一个编码器处于活动状态（由观测配置选择）。

---

## 环境结构

训练环境基于 IsaacLab 的 `ManagerBasedRLEnv`，使用模块化 MDP 设计，每个组件通过 YAML 独立配置。

### MDP 组件

所有 MDP 组件位于 `gear_sonic/envs/manager_env/mdp/`：

| 模块 | 配置路径 | 描述 |
|---|---|---|
| `observations.py` | `config/manager_env/observations/` | 策略、评论家和分词器组的观测项 |
| `actions.py` | `config/manager_env/actions/` | 关节位置动作空间 |
| `rewards.py` | `config/manager_env/rewards/` | 奖励项（跟踪、正则化） |
| `terminations.py` | `config/manager_env/terminations/` | 回合终止条件 |
| `events.py` | `config/manager_env/events/` | 域随机化事件 |
| `commands.py` | `config/manager_env/commands/` | 动作命令生成（动作库） |
| `curriculum.py` | `config/manager_env/curriculum/` | 课程调度 |
| `terrain.py` | （内联） | 地形生成 |
| `recorders.py` | `config/manager_env/recorders/` | 视频录制 |

### 观测组

观测被拆分为组，每组有自己的配置文件：

| 组 | 用途 | 示例项 |
|---|---|---|
| **policy** | 策略 MLP 的直接输入 | joint_pos、joint_vel、base_ang_vel、gravity_dir、last_actions |
| **critic** | 价值函数的特权观测 | 所有策略观测 + base_lin_vel、body_pos、body_ori |
| **tokenizer** | UniversalTokenModule 编码器的输入 | 多未来关节命令、SMPL 关节、VR 目标、锚点方向 |

### 奖励项

奖励配置从 `config/manager_env/rewards/terms/` 组装单个项。关键跟踪奖励：

| 项 | 描述 |
|---|---|
| `tracking_relative_body_pos` | 跟踪参考身体位置（5 点：根、手腕、脚） |
| `tracking_relative_body_ori` | 跟踪参考身体方向 |
| `tracking_anchor_pos` | 跟踪根锚点位置 |
| `tracking_anchor_ori` | 跟踪根锚点方向 |
| `tracking_body_linvel` | 跟踪参考身体线速度 |
| `tracking_body_angvel` | 跟踪参考身体角速度 |
| `action_rate_l2` | 惩罚动作抖动 |
| `feet_acc` | 惩罚脚部加速度（平滑性） |

### ManagerEnvWrapper

`ManagerEnvWrapper` 桥接 IsaacLab 环境和 RL 训练循环。它处理：
- 为策略展平观测字典
- 应用可选的预训练动作转换模块
- 动作重放模式
- 调试可视化和键盘控制

---

## 评估脚本

### eval_agent_trl.py -- 单检查点

加载单个检查点并在 Isaac Sim 中运行评估。自动从检查点目录读取训练用的 `config.yaml` 以重建完整配置。

```bash
# 交互式可视化
python gear_sonic/eval_agent_trl.py +checkpoint=path/to/model.pt +headless=False ++num_envs=1

# 无头模式并渲染视频
python gear_sonic/eval_agent_trl.py +checkpoint=path/to/model.pt +headless=True \
    ++num_envs=16 +run_once=True \
    ++manager_env.config.save_rendering_dir=path/to/output \
    ++manager_env.config.render_results=True \
    +manager_env/recorders=render
```

关键特性：
- 合并训练配置与评估覆盖（配置中的 `eval_overrides`）
- 自动移除仅限训练的事件和终止条件
- 支持 `+run_once=True` 以在所有环境完成一个回合后退出
- 处理 `+metrics_file` 以从先前评估中渲染表现最差的动作

### eval_exp.py -- 检查点监控器

`CheckpointEvaluator` 持续监控实验目录中的新检查点并依次评估它们。它作为伴随进程与训练并行运行。

```bash
python gear_sonic/eval_exp.py ++experiment_dir=path/to/experiment
```

对于每个新检查点，它会：
1. 运行指标评估（通过子进程启动 `eval_agent_trl.py`）
2. 为最难的动作渲染视频
3. 将结果和视频记录到 W&B（恢复训练运行）
4. 标记每个检查点为已评估以避免重复工作

配置（`config/eval_exp.yaml`）：

| 参数 | 描述 |
|---|---|
| `experiment_dir` | 训练实验目录的路径 |
| `scan_interval` | 检查点扫描间隔秒数（默认：60） |
| `num_eval_envs` | 指标评估的环境数量 |
| `num_render_videos` | 每个检查点渲染的视频数量 |
| `eval_frequency` | 仅每 N 个检查点评估一次（默认：全部） |
| `single_pass` | 评估待处理检查点一次后退出 |

---

## 关键类参考

| 类 | 模块 | 描述 |
|---|---|---|
| `Actor` | `trl/modules/actor_critic_modules.py` | 策略网络：骨干网络 + 对角高斯分布。为时间模型维护观测缓冲区。 |
| `Critic` | `trl/modules/actor_critic_modules.py` | 价值函数网络：骨干网络 + 标量输出。支持运行均值/标准差归一化。 |
| `UniversalTokenModule` | `trl/modules/universal_token_modules.py` | SONIC ATM：多编码器、FSQ 量化器、多解码器。计算辅助重建损失。 |
| `TRLPPOTrainer` | `trl/trainer/ppo_trainer.py` | 基于 HuggingFace TRL 的基础 PPO 训练器。处理 rollout 收集、GAE 和梯度更新。 |
| `TRLAuxLossPPOTrainer` | `trl/trainer/ppo_trainer_aux_loss.py` | 扩展 `TRLPPOTrainer` 以支持辅助损失（重建、潜在对齐）。 |
| `PolicyAndValueWrapper` | `trl/trainer/ppo_trainer.py` | 将策略 + 价值模型包装为单个 `nn.Module`，用于 DDP 安全的前向传播。 |
| `ManagerEnvWrapper` | `envs/wrapper/manager_env_wrapper.py` | 桥接 IsaacLab `ManagerBasedRLEnv` 与训练循环。处理观测展平、动作转换、重放。 |
| `CheckpointEvaluator` | `eval_exp.py` | 监控实验目录、评估新检查点、记录到 W&B。 |
