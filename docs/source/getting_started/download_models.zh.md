# 下载模型检查点

预训练的 GEAR-SONIC 检查点（ONNX 格式）托管在 Hugging Face 上：

**[nvidia/GEAR-SONIC](https://huggingface.co/nvidia/GEAR-SONIC)**

## 快速下载

### 安装依赖

```bash
pip install huggingface_hub
```

### 运行下载脚本

在仓库根目录下运行：

```bash
python download_from_hf.py
```

这会下载**最新**的策略编码器（encoder）+ 解码器（decoder）+ 运动学规划器（kinematic planner）到 `gear_sonic_deploy/`，并保持部署二进制文件期望的目录结构。

---

## 选项

| 参数 | 说明 |
|------|-------------|
| `--no-planner` | 跳过运动学规划器下载 |
| `--output-dir PATH` | 覆盖目标目录 |
| `--token TOKEN` | HF token（替代 `huggingface-cli login`） |

### 示例

```bash
# 策略 + 规划器（默认）
python download_from_hf.py

# 仅策略
python download_from_hf.py --no-planner

# 下载到自定义目录
python download_from_hf.py --output-dir /data/gear-sonic
```

---

## 通过 CLI 手动下载

如果你更喜欢使用 Hugging Face CLI：

```bash
pip install huggingface_hub[cli]

# 仅策略
huggingface-cli download nvidia/GEAR-SONIC \
    model_encoder.onnx \
    model_decoder.onnx \
    observation_config.yaml \
    --local-dir gear_sonic_deploy

# 全部（策略 + 规划器）
huggingface-cli download nvidia/GEAR-SONIC --local-dir gear_sonic_deploy
```

---

## 通过 Python 手动下载

```python
from huggingface_hub import hf_hub_download

REPO_ID = "nvidia/GEAR-SONIC"

encoder = hf_hub_download(repo_id=REPO_ID, filename="model_encoder.onnx")
decoder = hf_hub_download(repo_id=REPO_ID, filename="model_decoder.onnx")
config  = hf_hub_download(repo_id=REPO_ID, filename="observation_config.yaml")
planner = hf_hub_download(repo_id=REPO_ID, filename="planner_sonic.onnx")

print("Policy encoder :", encoder)
print("Policy decoder :", decoder)
print("Obs config     :", config)
print("Planner        :", planner)
```

---

## 可用文件

```
nvidia/GEAR-SONIC/
├── model_encoder.onnx         # 策略编码器
├── model_decoder.onnx         # 策略解码器
├── observation_config.yaml    # 观测配置
└── planner_sonic.onnx         # 运动学规划器
```

下载脚本会将它们放置到部署二进制文件期望的结构中：

```
gear_sonic_deploy/
├── policy/release/
│   ├── model_encoder.onnx
│   ├── model_decoder.onnx
│   └── observation_config.yaml
└── planner/target_vel/V2/
    └── planner_sonic.onnx
```

---

## 认证

该仓库是**公开的** —— 下载时无需 token。

如果你遇到速率限制或需要访问私有分支：

```bash
# 选项 1：CLI 登录（推荐 —— token 只需保存一次）
huggingface-cli login

# 选项 2：环境变量
export HF_TOKEN="hf_..."
python download_from_hf.py

# 选项 3：直接传入 token
python download_from_hf.py --token hf_...
```

在 [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) 获取免费 token。

---

## 下一步

下载完成后，请跟随[快速开始](quickstart.md)指南，在 MuJoCo 仿真或真实硬件上运行部署栈。
