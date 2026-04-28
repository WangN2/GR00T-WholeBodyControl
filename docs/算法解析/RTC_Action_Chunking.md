# Real-Time Execution of Action Chunking (RTC) 技术详解

> **知识储备文档** | 整理日期: 2026-04-28  
> 应用领域: 机器人模仿学习、遥操作、人形机器人全身控制 (GR00T/SONIC)  
> 关联技术: ACT, Diffusion Policy, Transformer-based Policy

---

## 目录

1. [背景：为什么需要 Action Chunking](#一背景为什么需要-action-chunking)
2. [核心问题：重叠预测如何融合](#二核心问题重叠预测如何融合)
3. [三种 RTC 执行策略](#三三种-rtc-执行策略)
4. [Temporal Ensemble 数学原理](#四temporal-ensemble-数学原理)
5. [完整执行流程图解](#五完整执行流程图解)
6. [Python 参考实现](#六python-参考实现)
7. [关键超参数调优指南](#七关键超参数调优指南)
8. [在 GR00T/SONIC 中的关联与应用](#八在-gr00tsonic-中的关联与应用)
9. [参考论文与资源](#九参考论文与资源)
10. [关键术语表](#十关键术语表)

---

## 一、背景：为什么需要 Action Chunking

### 1.1 原始单步推理的问题

在机器人遥操作中，最朴素的做法是**每步观察、每步推理、每步执行**：

```
t=0: 观察 o_0 → 推理模型 → 动作 a_0 → 执行
t=1: 观察 o_1 → 推理模型 → 动作 a_1 → 执行
t=2: 观察 o_2 → 推理模型 → 动作 a_2 → 执行
```

**痛点**：

| 问题 | 说明 |
|------|------|
| **推理延迟高** | Transformer / Diffusion Policy 推理需 50-200ms |
| **控制频率受限** | 若推理占 100ms，最高仅 10Hz，机器人运动抖动明显 |
| **时间连续性差** | 单步预测忽略动作之间的时间相关性，输出不平滑 |
| **计算资源浪费** | 高频推理导致 GPU 持续高负载 |

### 1.2 Action Chunking 的核心思想

一次推理预测未来 **k 步** 的动作序列（称为一个 **chunk**）：

```
t=0: 观察 o_0 → 推理 → 预测 chunk_0 = [a_0, a_1, ..., a_k]
       ↓ 执行 a_0  (t=0)
       ↓ 执行 a_1  (t=1, 无需推理)
       ↓ ...
       ↓ 执行 a_k  (t=k, 无需推理)
t=k+1: 观察 o_{k+1} → 再次推理 → 预测 chunk_1 = [a_{k+1}, ...]
```

**收益**：

- **推理频率降低 k 倍** → 可用更重的模型
- **动作更平滑** → 模型天然考虑了未来时间上下文
- **更容易达到高控制频率** → 如 50Hz 甚至 100Hz
- **减少抖动** → 序列级预测比单步预测稳定

### 1.3 术语定义

| 术语 | 符号 | 含义 |
|------|------|------|
| **Chunk Size** | `k` | 每次推理预测的动作步数 |
| **Action Chunk** | `C_t` | 时刻 t 推理出的动作序列 `[a_t, a_{t+1}, ..., a_{t+k-1}]` |
| **Execution Horizon** | `h` | 实际执行多少步后才做下一次推理（`h ≤ k`） |
| **Inference Frequency** | `f_inf` | 模型推理的频率（通常 `f_inf = f_ctrl / h`） |
| **Control Frequency** | `f_ctrl` | 机器人实际控制频率（如 50Hz） |

---

## 二、核心问题：重叠预测如何融合

Action Chunking 引入了一个关键问题：**同一时刻可能对应多个不同 chunk 的预测**。

### 2.1 问题示例

假设 `chunk_size = 4`：

```
t=0: 推理 chunk_0 = [a_0^(0), a_1^(0), a_2^(0), a_3^(0)]
t=1: 推理 chunk_1 = [a_1^(1), a_2^(1), a_3^(1), a_4^(1)]
t=2: 推理 chunk_2 = [a_2^(2), a_3^(2), a_4^(2), a_5^(2)]
```

对于 **t=2** 时刻的动作 `a_2`：

- `chunk_0[2] = a_2^(0)` —— t=0 时的"旧"预测
- `chunk_1[1] = a_2^(1)` —— t=1 时的"较新"预测
- `chunk_2[0] = a_2^(2)` —— t=2 时的"最新"预测

**矛盾**：

| 预测来源 | 优势 | 劣势 |
|---------|------|------|
| `a_2^(0)` (旧) | 已验证更久，可能更稳定 | 信息过时，未利用最新观察 |
| `a_2^(2)` (新) | 基于最新观察 o_2 | 推理刚完成，可能不稳定/有噪声 |

**如果直接用新 chunk 完全覆盖旧 chunk** → 导致**动作抖动（jittering）**，机器人运动不平滑。

### 2.2 核心挑战总结

> **如何在利用最新观察信息的同时，保持动作的时序一致性和平滑性？**

这就是 **RTC (Real-Time Control / Receding Horizon Control)** 要解决的核心问题。

---

## 三、三种 RTC 执行策略

### 策略 1: Open-Loop Execution（开环执行）

**思想**：推理一次，严格执行预测的整个 chunk，不做任何修正或融合。

```python
def open_loop_execute(observations, policy, chunk_size):
    for t in range(0, len(observations), chunk_size):
        chunk = policy(observations[t])  # 推理一次
        for i in range(chunk_size):
            if t + i < len(observations):
                robot.execute(chunk[i])
```

**时间线**（`chunk_size=4`）：

```
t=0: 推理 [a0, a1, a2, a3] → 执行 a0
t=1: 直接执行 a1
t=2: 直接执行 a2
t=3: 直接执行 a3
t=4: 推理 [a4, a5, a6, a7] → 执行 a4
```

**优点**：
- 实现最简单
- 推理频率最低（`f_inf = f_ctrl / k`）
- 无融合计算开销

**缺点**：
- **反应迟钝**：若 t=1 时环境突变，必须等到 t=4 才能响应
- **无纠错能力**：一旦推理错误，整个 chunk 都会错
- **不适合动态环境**

**适用场景**：
- 完全静态或极低速任务
- 作为 baseline 对比

---

### 策略 2: Closed-Loop with Chunk Replacement（闭环覆盖）

**思想**：每步都重新推理，但**直接用新 chunk 的第一个动作**，丢弃旧 chunk 的剩余预测。

```python
def closed_loop_replace(observations, policy):
    for t in range(len(observations)):
        chunk = policy(observations[t])  # 每步都推理
        robot.execute(chunk[0])          # 只用新 chunk 的第 0 个动作
```

**时间线**（`chunk_size=4`）：

```
t=0: 推理 chunk_0=[a0^(0), a1^(0), a2^(0), a3^(0)] → 执行 a0^(0)
t=1: 推理 chunk_1=[a1^(1), a2^(1), a3^(1), a4^(1)] → 执行 a1^(1)  ← 丢弃 a1^(0)
t=2: 推理 chunk_2=[a2^(2), a3^(2), a4^(2), a5^(2)] → 执行 a2^(2)  ← 丢弃 a2^(0), a2^(1)
```

**优点**：
- 反应最快，每步都利用最新观察
- 纠错能力最强

**缺点**：
- **严重抖动**：相邻时刻的动作来自完全不同的推理，时间连续性被破坏
- 推理频率最高（每步都推理），计算开销大
- **违背了 chunking 的初衷**（平滑性）

**适用场景**：
- 几乎不用，除非对反应速度有极端要求

---

### 策略 3: Temporal Ensemble（时间集合，推荐）

**思想**：每步重新推理，但对**重叠时刻的多个预测做加权平均**，越新的预测权重越高。

这是 **ACT 论文**中提出的标准做法，也是目前最广泛采用的 RTC 策略。

**核心操作**：

```
t=0: 推理 chunk_0 = [a0^(0), a1^(0), a2^(0), a3^(0)]
     → 执行 a0 = a0^(0)

t=1: 推理 chunk_1 = [a1^(1), a2^(1), a3^(1), a4^(1)]
     对于 a1，有两个候选：a1^(0) 和 a1^(1)
     → 执行 a1 = w0*a1^(0) + w1*a1^(1)  (加权平均)

t=2: 推理 chunk_2 = [a2^(2), a3^(2), a4^(2), a5^(2)]
     对于 a2，有三个候选：a2^(0), a2^(1), a2^(2)
     → 执行 a2 = w0*a2^(0) + w1*a2^(1) + w2*a2^(2)
```

**优点**：
- **平滑性好**：融合多个预测的共识，减少单步噪声
- **反应性适中**：每步都有最新信息参与
- **可解释性强**：权重反映了对"新旧信息"的权衡

**缺点**：
- 需要维护历史 chunk 缓存
- 融合计算有轻微开销（可忽略）

**适用场景**：
- **通用推荐**，绝大多数模仿学习任务

---

## 四、Temporal Ensemble 数学原理

### 4.1 加权平均公式

对于时刻 `t` 的动作，收集所有包含该时刻预测的 chunk：

$$a_t = \frac{\sum_{i \in \mathcal{I}_t} w(t, i) \cdot a_t^{(i)}}{\sum_{i \in \mathcal{I}_t} w(t, i)}$$

其中：
- $\mathcal{I}_t$ = 所有在时刻 `i` 推理且包含时刻 `t` 的 chunk 的集合
- $a_t^{(i)}$ = 时刻 `i` 推理的 chunk 中对应时刻 `t` 的动作
- $w(t, i)$ = 该预测的权重

### 4.2 权重设计

#### 方案 A: 指数衰减权重（最常用）

$$w(t, i) = \exp(-\lambda \cdot (t - i))$$

| 参数 | 说明 |
|------|------|
| $\lambda$ | 衰减系数，控制"遗忘速度" |
| $t - i$ | 预测距今的步数（offset），**越小越新** |

**示例**（`λ = 0.01`）：

| offset | 权重 |
|--------|------|
| 0 (最新) | `exp(0) = 1.00` |
| 1 | `exp(-0.01) ≈ 0.99` |
| 4 | `exp(-0.04) ≈ 0.96` |
| 8 | `exp(-0.08) ≈ 0.92` |

**特点**：衰减缓慢，新旧预测权重差异小，**更平滑**。

#### 方案 B: 线性衰减权重

$$w(t, i) = 1 - \alpha \cdot (t - i)$$

**特点**：简单直观，但 offset 大时可能变负数，需截断。

#### 方案 C: 只取最近 N 个预测

$$w(t, i) = \begin{cases} 1 & \text{if } t - i < N \\ 0 & \text{otherwise} \end{cases}$$

然后对非零权重做平均。

**特点**：只考虑最近的 N 个预测，内存开销固定。

### 4.3 归一化

无论采用哪种权重，最终都要做**归一化**：

$$\tilde{w}_i = \frac{w_i}{\sum_j w_j}$$

确保权重之和为 1。

---

## 五、完整执行流程图解

### 5.1 时间-预测矩阵

假设 `chunk_size = 4`，执行 8 步：

```
       t=0    t=1    t=2    t=3    t=4    t=5    t=6    t=7
      ┌──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┐
chunk │      │      │      │      │      │      │      │      │
──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┤
C_0   │ a0^0 │ a1^0 │ a2^0 │ a3^0 │      │      │      │      │  (t=0推理)
C_1   │      │ a1^1 │ a2^1 │ a3^1 │ a4^1 │      │      │      │  (t=1推理)
C_2   │      │      │ a2^2 │ a3^2 │ a4^2 │ a5^2 │      │      │  (t=2推理)
C_3   │      │      │      │ a3^3 │ a4^3 │ a5^3 │ a6^3 │      │  (t=3推理)
C_4   │      │      │      │      │ a4^4 │ a5^4 │ a6^4 │ a7^4 │  (t=4推理)
──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┤
执行   │ a0   │ a1   │ a2   │ a3   │ a4   │ a5   │ a6   │ a7   │
      └──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┘

其中:
  a0 = a0^0                          (唯一预测，直接执行)
  a1 = ensemble(a1^0, a1^1)          (2个预测融合)
  a2 = ensemble(a2^0, a2^1, a2^2)    (3个预测融合)
  a3 = ensemble(a3^0, a3^1, a3^2, a3^3) (4个预测融合)
  a4 = ensemble(a4^1, a4^2, a4^3, a4^4) (4个预测融合)
  ...
```

### 5.2 不同阶段的特点

| 阶段 | 时刻 | 参与融合的预测数 | 特点 |
|------|------|-----------------|------|
| **启动期** | t < k | 1, 2, 3, ..., k | 预测数递增，动作逐渐稳定 |
| **稳态期** | t ≥ k | k | 固定 k 个预测融合，最稳定 |
| **终止期** | 接近结束 | k, ..., 2, 1 | 预测数递减 |

> **注意**：实际应用中，"启动期"的不稳定可以通过**预填充（warm-up）**来缓解，即开始前先做几次虚拟推理。

---

## 六、Python 参考实现

### 6.1 核心 RTC 执行器

```python
"""
Action Chunking with Temporal Ensemble (RTC)
参考实现，可直接用于机器人控制循环
"""

import numpy as np
from collections import deque
from typing import Callable, Optional


class ActionChunkingRTC:
    """
    Real-Time Controller for Action Chunking with Temporal Ensemble.

    Args:
        chunk_size: 每次推理预测的动作步数
        action_dim: 动作维度
        ensemble_lambda: 指数衰减系数 (默认 0.01)
        max_cache_size: 缓存的最大 chunk 数量 (默认等于 chunk_size)
        warmup_steps: 启动前预填充的步数 (默认 0)
    """

    def __init__(
        self,
        chunk_size: int = 16,
        action_dim: int = 7,
        ensemble_lambda: float = 0.01,
        max_cache_size: Optional[int] = None,
        warmup_steps: int = 0,
    ):
        self.chunk_size = chunk_size
        self.action_dim = action_dim
        self.ensemble_lambda = ensemble_lambda
        self.max_cache_size = max_cache_size or chunk_size
        self.warmup_steps = warmup_steps

        # 缓存结构: deque of (prediction_time, chunk)
        # chunk shape: (chunk_size, action_dim)
        self.chunk_cache = deque(maxlen=self.max_cache_size)
        self.current_time = 0

    def reset(self):
        """重置缓存，用于新 episode"""
        self.chunk_cache.clear()
        self.current_time = 0

    def predict_and_execute(
        self,
        observation: np.ndarray,
        policy_fn: Callable[[np.ndarray], np.ndarray],
    ) -> np.ndarray:
        """
        单步入口: 观察 -> 推理 -> 融合 -> 返回动作

        Args:
            observation: 当前观察
            policy_fn: 策略模型，输入观察，输出 chunk (chunk_size, action_dim)

        Returns:
            action: 融合后的动作 (action_dim,)
        """
        # 1. 推理新 chunk
        chunk = policy_fn(observation)
        assert chunk.shape[0] == self.chunk_size, \
            f"Expected chunk shape[0]={self.chunk_size}, got {chunk.shape[0]}"

        # 2. 存入缓存
        self.chunk_cache.append((self.current_time, chunk))

        # 3. 计算当前时刻的融合动作
        action = self._temporal_ensemble(self.current_time)

        # 4. 时间推进
        self.current_time += 1

        return action

    def _temporal_ensemble(self, target_time: int) -> np.ndarray:
        """
        对 target_time 时刻的所有候选预测做加权平均
        """
        candidates = []
        weights = []

        for pred_time, chunk in self.chunk_cache:
            offset = target_time - pred_time

            # 检查该 chunk 是否包含 target_time
            if 0 <= offset < self.chunk_size:
                action_candidate = chunk[offset]
                candidates.append(action_candidate)

                # 指数衰减权重: 越新的预测权重越高
                weight = np.exp(-self.ensemble_lambda * offset)
                weights.append(weight)

        if not candidates:
            # 无候选时返回零动作（或上一动作）
            return np.zeros(self.action_dim)

        # 归一化权重
        weights = np.array(weights, dtype=np.float64)
        weights /= weights.sum()

        # 加权平均
        candidates = np.array(candidates)
        action = np.average(candidates, axis=0, weights=weights)

        return action

    def get_cache_info(self) -> dict:
        """返回缓存状态信息，用于调试"""
        return {
            "current_time": self.current_time,
            "cached_chunks": len(self.chunk_cache),
            "cache_times": [t for t, _ in self.chunk_cache],
        }


# ============================================================
# 使用示例
# ============================================================

def dummy_policy(obs: np.ndarray) -> np.ndarray:
    """模拟策略模型：输出随机 chunk"""
    chunk_size, action_dim = 8, 7
    return np.random.randn(chunk_size, action_dim)


def demo():
    """完整演示"""
    rtc = ActionChunkingRTC(
        chunk_size=8,
        action_dim=7,
        ensemble_lambda=0.05,  # 衰减稍快，更信任新预测
    )

    print("=" * 60)
    print("Action Chunking RTC Demo")
    print("=" * 60)

    for step in range(20):
        obs = np.random.randn(100)  # 模拟观察
        action = rtc.predict_and_execute(obs, dummy_policy)

        info = rtc.get_cache_info()
        print(f"Step {step:02d}: action_mean={action.mean():+.3f}, "
              f"cache_size={info['cached_chunks']}")

    print("=" * 60)


if __name__ == "__main__":
    demo()
```

### 6.2 变体：带执行步长限制的 RTC

有时不需要每步都推理，可以每 `execution_horizon` 步推理一次：

```python
class ActionChunkingRTCWithHorizon(ActionChunkingRTC):
    """
    带执行步长限制的 RTC：每 execution_horizon 步才做一次推理
    """

    def __init__(self, execution_horizon: int = 4, **kwargs):
        super().__init__(**kwargs)
        self.execution_horizon = execution_horizon
        self.steps_since_inference = 0
        self.last_chunk = None
        self.last_pred_time = 0

    def predict_and_execute(self, observation, policy_fn):
        # 只在需要时推理
        if self.steps_since_inference >= self.execution_horizon or self.last_chunk is None:
            self.last_chunk = policy_fn(observation)
            self.last_pred_time = self.current_time
            self.steps_since_inference = 0

            # 存入缓存（这里仍每步都缓存，只是推理频率降低）
            self.chunk_cache.append((self.last_pred_time, self.last_chunk))

        # 计算融合动作
        action = self._temporal_ensemble(self.current_time)

        self.current_time += 1
        self.steps_since_inference += 1

        return action
```

---

## 七、关键超参数调优指南

### 7.1 Chunk Size (`k`)

| `k` 值 | 效果 | 适用场景 |
|--------|------|---------|
| 4-8 | 反应快，但平滑性一般 | 需要快速响应的动态任务 |
| 16-32 | 平衡反应和平滑 | **通用推荐** |
| 64+ | 极平滑，但反应迟钝 | 非常缓慢、确定性的任务 |

**经验法则**：
- 控制频率 50Hz → `chunk_size=16` 对应 320ms 的预测窗口
- 若任务需要 <200ms 的反应时间，`k` 不应超过 10

### 7.2 Ensemble Lambda (`λ`)

| `λ` 值 | 效果 | 适用场景 |
|--------|------|---------|
| 0.0 | 所有预测等权重平均 | 极高噪声环境，需要强平滑 |
| 0.01-0.05 | 缓慢衰减，旧预测仍有显著权重 | **通用推荐** |
| 0.1-0.3 | 快速衰减，更信任最新预测 | 动态环境，需要较好反应性 |
| 1.0+ | 几乎只取最新预测 | 接近闭环覆盖，抖动风险高 |

**调优方法**：
1. 先用 `λ=0.01` 作为 baseline
2. 若动作**反应迟钝** → 增大 `λ`
3. 若动作**抖动明显** → 减小 `λ`

### 7.3 Execution Horizon (`h`)

| 策略 | `h` 值 | 推理频率 | 适用场景 |
|------|--------|---------|---------|
| 纯闭环 | `h=1` | 每步推理 | 计算资源充足，追求最佳性能 |
| 折中 | `h=k/2` | 每 k/2 步推理 | **平衡推荐** |
| 纯开环 | `h=k` | 每 k 步推理 | 计算资源受限，任务简单 |

---

## 八、在 GR00T/SONIC 中的关联与应用

### 8.1 当前 SONIC 训练中的潜在应用

SONIC 目前使用 **PPO + 辅助损失** 进行 RL 训练，策略输出单步动作。但 RTC / Action Chunking 思想可以迁移到以下场景：

| 场景 | 应用方式 |
|------|---------|
| **模仿学习微调** | 用 ACT / Diffusion Policy 在遥操作数据上微调 SONIC 策略时，chunking 是标准做法 |
| **数据后处理** | 遥操作采集的数据常有抖动，chunking + ensemble 可作为离线平滑预处理 |
| **Sim2Real 部署** | `gear_sonic_deploy` 推理栈中，可用 chunking 降低 ONNX 推理频率，提高控制频率 |
| **VR 遥操作平滑** | PICO VR 采集的 SMPL/关节数据可用 temporal ensemble 去噪 |

### 8.2 部署侧的 RTC 适配

在 `gear_sonic_deploy` (C++ 推理栈) 中：

```cpp
// 概念性伪代码
class RTCActionExecutor {
    std::deque<std::pair<int, ActionChunk>> cache_;
    int current_step_ = 0;
    
public:
    Action Execute(const Observation& obs, PolicyModel* model) {
        // 推理新 chunk
        ActionChunk chunk = model->Infer(obs);
        cache_.push_back({current_step_, chunk});
        
        // Temporal ensemble
        Action action = TemporalEnsemble(current_step_);
        
        current_step_++;
        return action;
    }
    
private:
    Action TemporalEnsemble(int target_step) {
        std::vector<Action> candidates;
        std::vector<float> weights;
        
        for (auto& [pred_step, chunk] : cache_) {
            int offset = target_step - pred_step;
            if (offset >= 0 && offset < chunk.size()) {
                candidates.push_back(chunk[offset]);
                weights.push_back(exp(-lambda_ * offset));
            }
        }
        
        return WeightedAverage(candidates, weights);
    }
};
```

### 8.3 与 SOMA/BONES-SEED 数据处理的结合

BONES-SEED 提供的 120FPS 运动数据在转换为 30/50Hz 时：

1. **下采样前**：对高帧率数据做 temporal ensemble 去噪
2. **训练时**：将 SOMA/G1 运动序列作为 chunk 输入，训练策略预测未来动作
3. **评估时**：用 RTC 执行策略输出，保证平滑跟踪

---

## 九、参考论文与资源

### 核心论文

| 论文 | 作者 | 贡献 |
|------|------|------|
| **Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware** (ACT) | Zhao et al., 2023 | 首次系统提出 Action Chunking + Temporal Ensemble |
| **Diffusion Policy: Visuomotor Policy Learning via Action Diffusion** | Chi et al., 2023 | 将 Diffusion 模型用于动作 chunking 预测 |
| **Scaling Data-Driven Robotics with Reward Sketching and Reinforcement Learning** | Sharma et al., 2023 | 在大规模数据中使用 chunking 策略 |

### 代码参考

- **ACT 官方实现**: https://github.com/tonyzhaozh/act
- **Diffusion Policy**: https://github.com/real-stanford/diffusion_policy
- **LeRobot (HuggingFace)**: https://github.com/huggingface/lerobot （包含标准化的 action chunking 实现）

### 相关概念

- **MPC (Model Predictive Control)**：与 RTC 思想同源，都是"预测一段、执行一步、重新预测"
- **Receding Horizon Control**：控制理论中的标准术语，指滚动优化未来一段时域

---

## 十、关键术语表

| 术语 (英文) | 术语 (中文) | 定义 |
|------------|------------|------|
| **Action Chunking** | 动作分块 | 一次推理预测未来多步动作的序列 |
| **RTC** | 实时控制 / 滚动时域控制 | 在动作分块基础上，实时融合重叠预测的机制 |
| **Temporal Ensemble** | 时间集合 | 对同一时刻的多个历史预测做加权平均 |
| **Chunk Size** | 分块大小 | 每次推理预测的动作步数 |
| **Execution Horizon** | 执行步长 | 实际执行多少步后才进行下一次推理 |
| **Inference Frequency** | 推理频率 | 模型被调用的频率 |
| **Control Frequency** | 控制频率 | 机器人实际执行动作的频率 |
| **Open-Loop** | 开环 | 推理后不根据新观察修正，严格执行预测 |
| **Closed-Loop** | 闭环 | 每步都利用最新观察重新推理并修正 |
| **Jittering** | 抖动 | 动作在相邻时刻间突变，不平滑 |
| **Warm-up** | 预填充 | 正式开始前先做若干次虚拟推理，让缓存填满 |

---

## 附录：快速决策表

| 你的需求 | 推荐配置 |
|---------|---------|
| 最大化平滑性 | `chunk_size=32`, `λ=0.01`, `h=1` |
| 最大化反应速度 | `chunk_size=4`, `λ=0.2`, `h=1` |
| 计算资源受限 | `chunk_size=16`, `h=8` (每8步推理一次) |
| 动态环境 (物体移动) | `chunk_size=8`, `λ=0.1`, `h=2` |
| 静态环境 (固定轨迹) | `chunk_size=32`, `λ=0.0`, `h=16` |
| 真机部署 (Sim2Real) | `chunk_size=16`, `λ=0.05`, `h=4` |

---

> **维护说明**: 本文档作为 GR00T-WholeBodyControl 项目知识储备，后续可根据实际训练/部署经验补充具体参数和性能数据。
