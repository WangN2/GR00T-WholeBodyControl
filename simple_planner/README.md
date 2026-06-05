# Simple Motion Planner — 简化版运动规划器训练框架

> 基于 PyTorch 的简化版运动规划器，用于学习从高层运动指令到全身关节轨迹的生成。

## 核心思想

参考 SONIC 部署栈中的 Kinematic Planner，本简化版实现一个**条件运动补全模型**：

```
输入: 4帧历史 context (root_pos + root_quat + 29 joints) + 运动条件 (mode, vel, dir)
      ↓
Transformer Encoder-Decoder
      ↓
输出: 未来 K 帧全身姿态 (K=24, 对应 6 tokens × 4 frames)
```

## 文件结构

```
simple_planner/
├── data/
│   └── motion_dataset.py      # 数据集加载与预处理
├── models/
│   └── planner.py             # Transformer Motion Completion 模型
├── scripts/
│   ├── train.py               # 训练脚本
│   ├── export_onnx.py         # ONNX 导出
│   └── inference.py           # 推理脚本
├── configs/
│   └── default.yaml           # 训练配置
└── README.md                  # 本文件
```

## 快速开始

```bash
cd simple_planner

# 1. 训练
python scripts/train.py --data-dir /data/wangbin/sample_data/robot_filtered

# 2. 导出 ONNX
python scripts/export_onnx.py --checkpoint checkpoints/planner_best.pt

# 3. 推理测试
python scripts/inference.py --onnx checkpoints/planner.onnx
```

## 与官方 Planner 的对比

| 特性 | 官方 Planner (NVIDIA) | 本简化版 |
|------|:---------------------:|:--------:|
| 根轨迹生成 | Spring Model（解析计算） | 神经网络端到端学习 |
| 目标姿态选择 | 从 Clip Library 采样 | 端到端生成 |
| 预测长度 | 可变 (6~16 tokens) | 固定 24 帧 |
| 模型架构 | 未开源（推测 Diffusion/Transformer） | Transformer Encoder-Decoder |
| 推理延迟 | ~1-2 ms (TensorRT + CUDA Graph) | ~5-10 ms (PyTorch CPU) |
| 运动模式 | 27 种 | 4 种 (idle/walk/run/squat) |

> 本简化版旨在帮助理解 Planner 的核心训练逻辑，不追求与官方模型完全一致。
