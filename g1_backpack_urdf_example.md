# G1 加装后背箱子 — URDF / MJCF 修改示例

> 适用场景：在 Unitree G1 后背加装一个固定箱子（固定外设），并部署训练好的模型。

---

## 1. 坐标系说明

G1 URDF/MJCF 中采用的坐标系：
- **X 轴**：机器人前方（+X 向前，-X 向后）
- **Y 轴**：机器人左侧（+Y 向左，-Y 向右）
- **Z 轴**：垂直向上

左髋 `left_hip_pitch_joint` 的 origin 为 `0 0.064452 -0.1027`，说明左腿在 +Y 侧，从而确认上述坐标系方向。

---

## 2. 需要修改的文件

本项目训练和部署使用的模型格式不同：

| 阶段 | 使用的模型文件 | 路径 |
|------|--------------|------|
| Isaac Lab 训练 / MuJoCo 仿真 | **URDF** | `gear_sonic/data/robots/g1/g1_29dof.urdf` 等 |
| C++ 部署（`gear_sonic_deploy`） | **MJCF/XML** | `gear_sonic_deploy/g1/g1_29dof.xml` |

> **如果只改 URDF 不改 MJCF，部署时前向运动学（FK）不会感知到箱子的质量和碰撞，但箱子质量仍然会通过底层物理引擎影响机器人。**
>
> 对于固定外设（fixed joint），**运动学树结构不变**，但 **质量分布变了**。为了保持一致性，建议 **URDF 和 MJCF 都修改**，且参数保持一致。

---

## 3. URDF 修改示例

在 `g1_29dof.urdf` 中，找到 `torso_link` 的定义（约在 489~510 行），在其 **闭合标签 `</link>` 之后**，添加以下内容：

```xml
  <!-- ========== 后背箱子（Backpack Box）========== -->
  <link name="backpack_box_link">
    <inertial>
      <!-- 质心位置：相对于 backpack_box_link 自身坐标系 -->
      <!-- 假设箱子中心在其几何中心 -->
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <!-- 箱子总质量（单位：kg），请用电子秤实测 -->
      <mass value="5.0"/>
      <!-- 惯性张量（单位：kg*m^2），可用近似公式或 SolidWorks/Fusion360 导出 -->
      <!-- 以下示例为 0.3m x 0.15m x 0.4m 长方体，质量 5kg 的近似值 -->
      <inertia ixx="0.0708" ixy="0" ixz="0" iyy="0.0917" iyz="0" izz="0.0313"/>
    </inertial>
    <visual>
      <!-- 箱子几何中心相对于 torso_link 的位置 -->
      <origin xyz="-0.12 0 0.18" rpy="0 0 0"/>
      <geometry>
        <!-- 方式1：使用 mesh（推荐，如果你有 CAD 导出的 STL） -->
        <!-- <mesh filename="meshes/backpack_box.STL"/> -->
        <!-- 方式2：使用简单几何体（快速验证） -->
        <box size="0.30 0.15 0.40"/>
      </geometry>
      <material name="box_material">
        <color rgba="0.8 0.3 0.3 1"/>
      </material>
    </visual>
    <collision>
      <origin xyz="-0.12 0 0.18" rpy="0 0 0"/>
      <geometry>
        <box size="0.30 0.15 0.40"/>
      </geometry>
    </collision>
  </link>

  <joint name="backpack_box_joint" type="fixed">
    <!-- 箱子附着点：相对于 torso_link 的位置和姿态 -->
    <!-- -0.12 表示向后（后背方向），0.18 表示在 torso_link 上方约 18cm -->
    <origin xyz="-0.12 0 0.18" rpy="0 0 0"/>
    <parent link="torso_link"/>
    <child link="backpack_box_link"/>
  </joint>
```

### 插入位置示意

```xml
  </link>             <!-- torso_link 结束 -->
  <joint name="waist_pitch_joint" type="revolute">
    ...
  </joint>

  <!-- 在此处插入 backpack_box_link 和 backpack_box_joint -->

  <!-- LOGO -->
  <joint name="logo_joint" type="fixed">
```

---

## 4. MJCF（部署 XML）修改示例

**部署栈 `gear_sonic_deploy` 使用的是 MuJoCo MJCF 格式**，而不是 URDF。你也需要同步修改 `gear_sonic_deploy/g1/g1_29dof.xml`。

### 步骤 A：在 `<asset>` 中添加 mesh（如果使用自定义 mesh）

在 `<asset>` 区域的 `torso_link` 之后添加：

```xml
    <mesh name="backpack_box" file="backpack_box.STL"/>
```

如果使用简单几何体（box/cylinder），则 **不需要** 在 asset 中声明 mesh。

### 步骤 B：在 `torso_link` 的 `<body>` 内添加子 body

找到 `torso_link` 的 body 节点（约第 136 行），在其内部（例如在 `logo_link` 的 geom 之后，shoulders 之前）添加：

```xml
            <body name="backpack_box_link" pos="-0.12 0 0.18">
              <inertial pos="0 0 0" mass="5.0" diaginertia="0.0708 0.0917 0.0313"/>
              <!-- 视觉几何 -->
              <geom type="box" size="0.15 0.075 0.20" contype="0" conaffinity="0" group="1" density="0" rgba="0.8 0.3 0.3 1"/>
              <!-- 碰撞几何（尺寸是半边长 half-size） -->
              <geom type="box" size="0.15 0.075 0.20" rgba="0.8 0.3 0.3 1"/>
            </body>
```

> **注意 MuJoCo 的 `box size` 是半边长（half-size）**，而 URDF 的 `box size` 是全长。因此 URDF 中 `0.30 0.15 0.40` 对应 MJCF 中 `size="0.15 0.075 0.20"`。

### 插入位置示意

```xml
            <geom pos="0.0039635 0 -0.054" quat="1 0 0 0" type="mesh" rgba="0.7 0.7 0.7 1" mesh="waist_support_link"/>

            <!-- 在此处插入 backpack_box_link body -->

            <site name="imu" size="0.01" pos="-0.03959 -0.00224 0.13792"/>
            <body name="left_shoulder_pitch_link" pos="0.0039563 0.10022 0.23778" ...>
```

---

## 5. 关键参数：如何确定箱子的位置和惯性

### 5.1 附着位置 `xyz`

建议使用卷尺或游标卡尺，测量箱子几何中心到 G1 **torso_link 坐标原点**的相对位置：
- **X**：箱子在机器人前后方向的位置（负值 = 后背方向）
- **Y**：左右偏移（通常为 0，如果箱子居中）
- **Z**：上下高度

> `torso_link` 的坐标原点大约在腰部偏上位置（具体参考 `waist_pitch_joint` 的 origin）。如果你难以直接测量，可以：
> 1. 把 G1 站立在地面，测量箱子中心到地面的高度，再减去 torso_link 原点的高度（约 0.7~0.8m，可通过加载无箱子模型在 MuJoCo/Isaac Lab 中查看）。
> 2. 或者先给一个粗略估计，在仿真中观察箱子位置是否 visually 正确，再微调。

### 5.2 质量 `mass`

直接用电子秤测量箱子及其内部所有设备的总质量。

### 5.3 惯性张量 `inertia`

#### 方案 A：CAD 软件导出（最准确）
在 SolidWorks / Fusion 360 / Onshape 中：
1. 给箱子模型赋予材料密度
2. 导出为 URDF（使用 sw2urdf / fusion2urdf 插件）
3. 提取其中的 `<inertial>` 块

#### 方案 B：长方体近似公式
如果箱子近似为均匀长方体，尺寸为 `L x W x H`（长 x 宽 x 高），质量为 `m`：

```
ixx = m * (H^2 + W^2) / 12
iyy = m * (L^2 + H^2) / 12
izz = m * (L^2 + W^2) / 12
ixy = ixz = iyz = 0
```

例如 `L=0.30, W=0.15, H=0.40, m=5.0`：
```
ixx = 5.0 * (0.40^2 + 0.15^2) / 12 = 5.0 * 0.1825 / 12 ~= 0.0760
iyy = 5.0 * (0.30^2 + 0.40^2) / 12 = 5.0 * 0.25   / 12 ~= 0.1042
izz = 5.0 * (0.30^2 + 0.15^2) / 12 = 5.0 * 0.1125 / 12 ~= 0.0469
```

> 示例代码中的数值略有不同，是因为考虑了质心不在几何中心的情况。请根据你的实际箱子调整。

---

## 6. 重要注意事项

### 6.1 训练与部署的 URDF/MJCF 必须一致

如果你的 **训练时的 URDF 没有这个箱子**，但 **部署时的 MJCF 加上了箱子**：

| 影响项 | 说明 |
|--------|------|
| **质心位置** | 训练时 policy 感知的 COM 与实际 COM 不符，可能影响平衡 |
| **总质量** | 重力补偿项不匹配，尤其在 slow-speed tracking 时明显 |
| **角动量 / 转动惯量** | 躯干旋转时的动力学响应不同 |
| **碰撞检测** | 箱子可能与环境碰撞，但 policy 未在训练中见过这种接触 |

**建议做法**：
1. **最优**：用带箱子的 URDF 重新训练（或至少做 domain randomization，在训练时随机化躯干质量/质心）。
2. **次优**：如果箱子较轻（< 2kg）且 policy 鲁棒性较好，可以直接部署，但建议先在仿真中验证。
3. **权宜之计**：在部署代码中，手动调整 gravity compensation 和 feedforward torque 的质量参数（如果有的话）。

### 6.2 检查 mesh 文件路径

如果使用自定义 STL mesh：
- URDF：`meshes/backpack_box.STL` 路径是相对于 URDF 文件位置的
- MJCF：`file="backpack_box.STL"` 路径是相对于 `meshdir="meshes"` 的
- 请确保 `gear_sonic/data/robots/g1/meshes/` 和 `gear_sonic_deploy/g1/meshes/` 中都有该文件（或建立软链接）

### 6.3 关节名称不要冲突

确保 `backpack_box_joint` 和 `backpack_box_link` 的名称在文件中是唯一的，不要与现有名称重复。

### 6.4 如果使用 decoupled_wbc

`decoupled_wbc` 模块中也有 G1 的 URDF（可能在 `decoupled_wbc/sim2mujoco/resources/robots/g1/`）。如果该目录下有独立的 URDF 或 MJCF，也请同步修改，保持所有 G1 描述文件一致。

---

## 7. 快速验证

修改后，建议按以下顺序验证：

1. **URDF 语法检查**
   ```bash
   check_urdf gear_sonic/data/robots/g1/g1_29dof.urdf
   ```

2. **MuJoCo 可视化检查**
   ```bash
   python -m mujoco.viewer
   # 然后把 g1_29dof.urdf 或 gear_sonic_deploy/g1/g1_29dof.xml 拖入窗口
   # 确认箱子位置和大小 visually 正确
   ```

3. **Isaac Lab 加载测试**
   ```bash
   python -c "from omni.isaac.lab_assets import *"
   # 或运行你已有的加载脚本
   # 确认无报错，且箱子显示在正确位置
   ```

4. **部署 FK 测试**
   ```bash
   cd gear_sonic_deploy
   # 重新编译（如果有修改 C++ 相关，但其实只改 XML 不需要重编译）
   # 运行 test_fk 或实际部署程序，确认 body 数量/名称未受影响
   ```

---

## 8. 总结

| 修改项 | 修改位置 | 是否必须 |
|--------|---------|---------|
| URDF 中添加 `backpack_box_link` + fixed joint | `gear_sonic/data/robots/g1/g1_29dof.urdf` | 是（如果要重新训练/仿真） |
| MJCF 中添加 `backpack_box_link` body | `gear_sonic_deploy/g1/g1_29dof.xml` | **是（部署必需）** |
| 添加 mesh 文件到 meshes/ 目录 | 对应路径 | 如果使用自定义 mesh |
| 同步修改 decoupled_wbc 中的 G1 URDF | 如有独立副本 | 建议同步 |

如果有箱子的具体尺寸和重量，可以发给我，我可以帮你算出更精确的惯性参数。
