# 坐标系与旋转约定

本文档记录 SONIC 代码库中使用的坐标系、四元数和旋转约定。如果弄错了这些，会导致隐蔽的 bug —— 机器人会动，但方向或朝向是错的。

## 坐标系

### Isaac Lab / MuJoCo（仿真）

- **Z 轴向上**：重力沿 -Z 方向。地面是 XY 平面。
- **右手系**：X 向前，Y 向左，Z 向上。
- 这是训练和评估时使用的约定。

### SMPL / BVH（人体动作数据）

- **Y 轴向上**：重力沿 -Y 方向。地面是 XZ 平面。
- 加载 SMPL 或 BVH 数据时，在运动库配置中设置 `smpl_y_up: true`。运动库会自动在内部将 Y-up 转换为 Z-up。

### 总结

| 系统 | 上轴 | 约定 |
|------|------|------|
| Isaac Lab | Z | Z-up, 右手系 |
| MuJoCo | Z | Z-up, 右手系 |
| SMPL 人体模型 | Y | Y-up |
| BVH 动作文件 | Y | Y-up |
| 重定向后的 PKL 数据 | Z | Z-up（已转换） |

## 四元数约定

### 标量在前 (wxyz) — SONIC 的默认约定

SONIC 代码库**在所有地方**都使用 **标量在前 (wxyz)** 的四元数：

```
q = [w, x, y, z]
```

这适用于：

- `gear_sonic/trl/utils/torch_transform.py` — 所有旋转工具函数
- `gear_sonic/isaac_utils/rotations.py` — Isaac Lab 旋转辅助函数（使用 `w_last=False`）
- Isaac Lab API（`body_quat_w`, `root_quat_w` 等）
- 运动库内部存储
- 重定向后的 PKL 数据（`root_rot` 字段）

### 标量在后 (xyzw) — 仅 scipy 使用

[SciPy 的 Rotation 类](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.html)
使用 **标量在后 (xyzw)** 约定：

```
q = [x, y, z, w]
```

这仅在 **数据处理脚本**（`data_process/`）中调用 `scipy.spatial.transform.Rotation` 时使用。这些脚本在保存前会转换为 wxyz：

```python
# 数据处理中（scipy xyzw → wxyz 用于存储）
root_quat_xyzw = Rotation.from_euler("xyz", euler_angles).as_quat()  # scipy: xyzw
root_quat_wxyz = root_quat_xyzw[:, [3, 0, 1, 2]]                    # 转换为 wxyz
```

### `w_last` 参数

`gear_sonic/isaac_utils/rotations.py` 中的函数接受一个 `w_last` 布尔参数：

```python
quat_rotate(q, v, w_last=False)   # q 是 wxyz（标量在前）— 默认值
quat_rotate(q, v, w_last=True)    # q 是 xyzw（标量在后）
```

**除非与 scipy 或明确使用 xyzw 的系统交互，否则始终使用 `w_last=False`。**

### 快速参考

| 系统 | 约定 | 顺序 | 单位元 |
|------|------|------|--------|
| SONIC (torch_transform.py) | wxyz | `[w, x, y, z]` | `[1, 0, 0, 0]` |
| Isaac Lab | wxyz | `[w, x, y, z]` | `[1, 0, 0, 0]` |
| SciPy | xyzw | `[x, y, z, w]` | `[0, 0, 0, 1]` |
| MuJoCo | wxyz | `[w, x, y, z]` | `[1, 0, 0, 0]` |
| ROS | xyzw | `[x, y, z, w]` | `[0, 0, 0, 1]` |

### 约定之间转换

```python
# wxyz → xyzw
q_xyzw = q_wxyz[..., [1, 2, 3, 0]]

# xyzw → wxyz
q_wxyz = q_xyzw[..., [3, 0, 1, 2]]
```

## 旋转表示法

代码库根据上下文使用多种旋转表示法：

| 表示法 | 形状 | 使用场景 |
|--------|------|----------|
| 四元数 (wxyz) | `(..., 4)` | 仿真、运动库、观测 |
| 轴角 | `(..., 3)` | 运动 PKL 中的 `pose_aa` 字段 |
| 旋转矩阵 | `(..., 3, 3)` | 正向运动学、6D 旋转编码 |
| 6D 旋转 | `(..., 6)` | 某些观测项（旋转矩阵的前两列） |
| 欧拉角 | `(..., 3)` | CSV 动作数据输入（立即转换） |

### 动作数据中的轴角

重定向后的 PKL 文件中的 `pose_aa` 字段以轴角向量的形式存储每个刚体的**局部**旋转。方向是旋转轴，模长是弧度为单位的角度：

```python
pose_aa  # (T, num_bodies, 3) — 每个刚体的轴角，MuJoCo 刚体顺序
```

## 关节顺序

Isaac Lab 和 MuJoCo 以不同的顺序遍历运动学树。代码库为每个机器人提供双向索引映射：

```python
from gear_sonic.envs.manager_env.robots.g1 import (
    G1_ISAACLAB_TO_MUJOCO_DOF,   # 重排自由度：IsaacLab → MuJoCo
    G1_MUJOCO_TO_ISAACLAB_DOF,   # 重排自由度：MuJoCo → IsaacLab
)

# 将关节位置从 IsaacLab 顺序转换为 MuJoCo 顺序：
mujoco_joints = isaaclab_joints[..., G1_ISAACLAB_TO_MUJOCO_DOF]
```

运动 PKL 数据（`dof`, `pose_aa`）以 **MuJoCo 顺序**存储。Isaac Lab 仿真使用 **IsaacLab 顺序**。训练流水线通过 `order_converter.py` 自动处理转换。

有关如何为新机器人定义这些映射，请参阅[在新机体上训练](../user_guide/new_embodiments.md)。
