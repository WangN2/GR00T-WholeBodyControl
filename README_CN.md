<div align="center">

  <img src="media/groot_wbc.png" width="800" alt="GEAR SONIC Header">

  <!-- --- -->
  
  
</div>

<div align="center">

[![License](https://img.shields.io/badge/License-Apache%202.0-76B900.svg)](LICENSE)
[![IsaacLab](https://img.shields.io/badge/IsaacLab-2.3.0-orange.svg)](https://github.com/isaac-sim/IsaacLab/releases/tag/v2.3.0)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-76B900.svg)](https://nvlabs.github.io/GR00T-WholeBodyControl/)

</div>

---




# GR00T-WholeBodyControl

本仓库是 **GR00T 全身控制（Whole-Body Control, WBC）** 项目的代码库。它托管了模型检查点以及用于训练、评估和部署先进人形机器人全身控制器的脚本。目前支持：

- **Decoupled WBC**：NVIDIA GR00T [N1.5](https://research.nvidia.com/labs/gear/gr00t-n1_5/) 和 [N1.6](https://research.nvidia.com/labs/gear/gr00t-n1_6/) 模型中使用的解耦控制器（下半身使用 RL，上半身使用 IK）；
- **GEAR-SONIC 系列**：我们最新一代的通用型人形全身控制器（详见[白皮书](https://nvlabs.github.io/GEAR-SONIC/)）。

## 新闻

- **[2026-03-24]** 更新 C++ 推理栈：新增电机错误监控和温度上报（支持 TTS 语音告警与 MuJoCo 热力图可视化）；支持通过 ZMQ 协议 v4 进行流式 token 输入；空闲模式下基于错误的自适应重调；TRT 引擎输出现在与 ONNX 模型共存；**ZMQ 头大小已更改为 1280 字节**
- **[2026-03-16]** [BONES-SEED](https://huggingface.co/datasets/bones-studio/seed) 现已开源！一个大规模人体动作数据集（14.2万+ 动作，约 288 小时），包含与 Unitree G1 MuJoCo 兼容的轨迹（SONIC 训练数据的一大子集！）。
- **[2026-02-19]** 发布 GEAR-SONIC，包含预训练策略检查点、C++ 推理栈、VR 遥操作栈及相关文档。
- **[2025-11-12]** 首次发布 GR00T-WholeBodyControl，提供适用于 GR00T N1.5 和 N1.6 的 Decoupled WBC。

## 目录

- [新闻](#新闻)
- [GEAR-SONIC](#gear-sonic)
- [VR 全身遥操作](#vr-全身遥操作)
- [运动学规划器](#运动学规划器)
- [待办事项](#待办事项)
- [包含内容](#包含内容)
  - [环境配置](#环境配置)
- [文档](#文档)
- [引用](#引用)
- [许可证](#许可证)
- [支持](#支持)
- [Decoupled WBC](#decoupled-wbc)


## GEAR-SONIC

<p style="font-size: 1.2em;">
    <a href="https://nvlabs.github.io/GEAR-SONIC/"><strong>官方网站</strong></a> | 
    <a href="https://huggingface.co/nvidia/GEAR-SONIC"><strong>模型</strong></a> | 
    <a href="https://arxiv.org/abs/2511.07820"><strong>论文</strong></a> | 
    <a href="https://nvlabs.github.io/GR00T-WholeBodyControl/"><strong>文档</strong></a>
  </p>

<div align="center">
  <img src="docs/source/_static/sonic-preview-gif-480P.gif" width="800" >
  
</div>

SONIC 是一款人形行为基础模型，它赋予机器人一套从大规模人体动作数据中学到的核心运动技能。SONIC 无需为预定义动作分别构建控制器，而是将动作追踪作为一种可扩展的训练任务，使单一统一策略能够生成自然的全身运动，并支持从行走、爬行到遥操作和多模态控制的广泛行为。它旨在泛化到训练期间未见过的动作，并作为更高层规划与交互的基础。

在本仓库中，我们将发布 SONIC 的训练代码、部署框架、模型检查点以及用于数据采集的遥操作栈。


## VR 全身遥操作

SONIC 支持通过 PICO VR 头盔进行实时全身遥操作，实现自然的人到机器人动作迁移，用于数据采集和交互控制。

<div align="center">
<table>
<tr>
<td align="center"><b>行走</b></td>
<td align="center"><b>奔跑</b></td>
</tr>
<tr>
<td align="center"><img src="media/teleop_walking.gif" width="400"></td>
<td align="center"><img src="media/teleop_running.gif" width="400"></td>
</tr>
<tr>
<td align="center"><b>侧向移动</b></td>
<td align="center"><b>跪姿</b></td>
</tr>
<tr>
<td align="center"><img src="media/teleop_sideways.gif" width="400"></td>
<td align="center"><img src="media/teleop_kneeling.gif" width="400"></td>
</tr>
<tr>
<td align="center"><b>起身</b></td>
<td align="center"><b>跳跃</b></td>
</tr>
<tr>
<td align="center"><img src="media/teleop_getup.gif" width="400"></td>
<td align="center"><img src="media/teleop_jumping.gif" width="400"></td>
</tr>
<tr>
<td align="center"><b>双手操作</b></td>
<td align="center"><b>物体传递</b></td>
</tr>
<tr>
<td align="center"><img src="media/teleop_bimanual.gif" width="400"></td>
<td align="center"><img src="media/teleop_switch_hands.gif" width="400"></td>
</tr>
</table>
</div>

## 运动学规划器

SONIC 包含一个用于实时步态生成的运动学规划器——选择移动风格，使用键盘/手柄进行转向，并实时调整速度和高度。

<div align="center">
<table>
<tr>
<td align="center" colspan="2"><b>野外导航</b></td>
</tr>
<tr>
<td align="center" colspan="2"><img src="media/planner/planner_in_the_wild_navigation.gif" width="800"></td>
</tr>
<tr>
<td align="center"><b>奔跑</b></td>
<td align="center"><b>开心</b></td>
</tr>
<tr>
<td align="center"><img src="media/planner/planner_run.gif" width="400"></td>
<td align="center"><img src="media/planner/planner_happy.gif" width="400"></td>
</tr>
<tr>
<td align="center"><b>潜行</b></td>
<td align="center"><b>受伤</b></td>
</tr>
<tr>
<td align="center"><img src="media/planner/planner_stealth.gif" width="400"></td>
<td align="center"><img src="media/planner/planner_injured.gif" width="400"></td>
</tr>
<tr>
<td align="center"><b>跪姿</b></td>
<td align="center"><b>手膝爬行</b></td>
</tr>
<tr>
<td align="center"><img src="media/planner/planner_kneeling.gif" width="400"></td>
<td align="center"><img src="media/planner/planner_hand_crawling.gif" width="400"></td>
</tr>
<tr>
<td align="center"><b>肘膝爬行</b></td>
<td align="center"><b>拳击</b></td>
</tr>
<tr>
<td align="center"><img src="media/planner/planner_elbow_crawling.gif" width="400"></td>
<td align="center"><img src="media/planner/planner_boxing.gif" width="400"></td>
</tr>
</table>
</div>

## 待办事项

- [x] 发布 SONIC 预训练策略检查点
- [x] 开源 C++ 推理栈
- [x] 搭建文档
- [x] 开源遥操作栈和演示脚本
- [ ] 发布动作模仿与微调的训练脚本和配方
- [ ] 开源大规模数据采集工作流和 VLA 微调脚本
- [ ] 发布更多预处理过的大规模人体动作数据集



## 包含内容

本次发布包含：

- **`gear_sonic_deploy`**：用于在真实硬件上部署 SONIC 策略的 C++ 推理栈
- **`gear_sonic`**：用于采集演示数据的遥操作栈（训练代码暂未开源。）

### 环境配置

使用 Git LFS 克隆仓库：
```bash
git clone https://github.com/NVlabs/GR00T-WholeBodyControl.git
cd GR00T-WholeBodyControl
git lfs pull
```

## 文档

📚 **[完整文档](https://nvlabs.github.io/GR00T-WholeBodyControl/)**

### 快速开始
- [安装指南](https://nvlabs.github.io/GR00T-WholeBodyControl/getting_started/installation_deploy.html)
- [快速上手](https://nvlabs.github.io/GR00T-WholeBodyControl/getting_started/quickstart.html)
- [VR 遥操作设置](https://nvlabs.github.io/GR00T-WholeBodyControl/getting_started/vr_teleop_setup.html)

### 教程
- [键盘控制](https://nvlabs.github.io/GR00T-WholeBodyControl/tutorials/keyboard.html)
- [手柄控制](https://nvlabs.github.io/GR00T-WholeBodyControl/tutorials/gamepad.html)
- [ZMQ 通信](https://nvlabs.github.io/GR00T-WholeBodyControl/tutorials/zmq.html)
- [ZMQ 管理器 / PICO VR](https://nvlabs.github.io/GR00T-WholeBodyControl/tutorials/vr_wholebody_teleop.html)

### 最佳实践
- [遥操作](https://nvlabs.github.io/GR00T-WholeBodyControl/user_guide/teleoperation.html)





---

## 引用

如果您在研究中使用了 GEAR-SONIC，请引用：

```bibtex
@article{luo2025sonic,
    title={SONIC: Supersizing Motion Tracking for Natural Humanoid Whole-Body Control},
    author={Luo, Zhengyi and Yuan, Ye and Wang, Tingwu and Li, Chenran and Chen, Sirui and Casta\~neda, Fernando and Cao, Zi-Ang and Li, Jiefeng and Minor, David and Ben, Qingwei and Da, Xingye and Ding, Runyu and Hogg, Cyrus and Song, Lina and Lim, Edy and Jeong, Eugene and He, Tairan and Xue, Haoru and Xiao, Wenli and Wang, Zi and Yuen, Simon and Kautz, Jan and Chang, Yan and Iqbal, Umar and Fan, Linxi and Zhu, Yuke},
    journal={arXiv preprint arXiv:2511.07820},
    year={2025}
}
```

---

## 许可证

本项目采用双重许可证：

- **源代码**：采用 Apache License 2.0——适用于本仓库中的所有代码、脚本和软件组件
- **模型权重**：采用 NVIDIA Open Model License——适用于所有训练好的模型检查点和权重

完整的双重许可证文本请参见 [LICENSE](LICENSE)。

在使用本项目之前，请仔细阅读两份许可证。NVIDIA Open Model License 允许商业使用并需注明出处，同时要求遵守 NVIDIA 的可信 AI 条款。

所有必需的法律文件，包括 Apache 2.0 许可证、第三方归属声明和 DCO 条款，均已汇总在本仓库的 /legal 文件夹中。

---

## 支持

如有问题和反馈，请联系 GEAR WBC 团队：[gear-wbc@nvidia.com](gear-wbc@nvidia.com)！

## Decoupled WBC

关于 GR00T N1.5 和 N1.6 模型中使用的 Decoupled WBC，请参阅 [Decoupled WBC 文档](docs/source/references/decoupled_wbc.md)。


## 致谢

我们衷心感谢以下项目，本仓库中的部分代码源自它们：
- [Beyond Mimic](https://github.com/HybridRobotics/whole_body_tracking)
- [Isaac Lab](https://github.com/isaac-sim/IsaacLab)
