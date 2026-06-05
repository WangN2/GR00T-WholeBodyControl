"""
Pinocchio 前向运动学（FK）演示：G1 机器人
加载 URDF -> 设置关节角度 -> 计算末端位姿
"""
import numpy as np
import pinocchio as pin
from pathlib import Path

# G1 URDF 路径（使用 decoupled_wbc 目录下的版本）
URDF_PATH = Path("decoupled_wbc/sim2mujoco/resources/robots/g1/g1.urdf")
MESH_DIR = URDF_PATH.parent / "meshes"

print("=" * 60)
print("Step 1: 加载 G1 URDF 模型")
print("=" * 60)

# Pinocchio 加载 URDF（需要 mesh 目录来解析相对路径）
model, collision_model, visual_model = pin.buildModelsFromUrdf(
    str(URDF_PATH),
    package_dirs=[str(URDF_PATH.parent)],
    root_joint=None,  # G1 的 URDF 里 floating base 被注释掉了
)

print(f"模型名称: {model.name}")
print(f"关节数量 (nq): {model.nq}")
print(f"速度维度 (nv): {model.nv}")
print(f"连杆数量 (njoints): {model.njoints}")

# 创建数据对象（存储中间计算结果）
data = model.createData()

print("\n" + "=" * 60)
print("Step 2: 查看关键关节名称")
print("=" * 60)

# 列出所有关节名称
joint_names = [model.names[i] for i in range(model.njoints)]
print(f"前 10 个关节: {joint_names[:10]}")
print(f"后 10 个关节: {joint_names[-10:]}")

# 找到末端执行器相关的关节索引
key_joints = {
    "left_wrist_yaw": None,
    "right_wrist_yaw": None,
    "left_ankle_roll": None,
    "right_ankle_roll": None,
    "head_link": None,
}
for i, name in enumerate(joint_names):
    for key in key_joints:
        if key in name:
            key_joints[key] = i

print(f"\n关键关节索引: {key_joints}")

print("\n" + "=" * 60)
print("Step 3: 设置关节配置并计算 FK")
print("=" * 60)

# 初始配置：全部设为零（站立姿态）
q = pin.neutral(model)
print(f"中性姿态 q 维度: {q.shape}, 前 10 个值: {q[:10].round(4)}")

# 计算 Forward Kinematics
pin.forwardKinematics(model, data, q)
pin.updateFramePlacements(model, data)

# 获取关键连杆在三维空间中的位姿（位置 + 朝向）
print("\n--- 站立姿态（全零关节角）---")
for name, idx in key_joints.items():
    if idx is not None:
        # 获取关节对应的连杆位姿（SE3：4x4 齐次变换矩阵）
        placement = data.oMi[idx]  # oMi: frame placement w.r.t. world
        pos = placement.translation
        rot = placement.rotation
        print(f"{name:20s}: pos=({pos[0]:+.3f}, {pos[1]:+.3f}, {pos[2]:+.3f}) [m]")

print("\n" + "=" * 60)
print("Step 4: 改变关节角度，观察末端位置变化")
print("=" * 60)

# 让右臂抬起来（修改右肩俯仰关节）
q_moved = q.copy()

# 找到右肩俯仰关节的索引（在 URDF 中通常叫 right_shoulder_pitch）
right_shoulder_pitch_idx = None
for i, name in enumerate(model.names):
    if "right_shoulder_pitch" in name:
        right_shoulder_pitch_idx = model.idx_qs[i]
        break

if right_shoulder_pitch_idx is not None:
    # 设置右肩向上抬 45 度（0.785 弧度）
    q_moved[right_shoulder_pitch_idx] = -0.785  # 负号方向取决于关节定义
    print(f"设置右肩俯仰关节 (idx={right_shoulder_pitch_idx}) = -45°")
    
    # 重新计算 FK
    pin.forwardKinematics(model, data, q_moved)
    
    # 对比右手腕位置
    rw_idx = key_joints.get("right_wrist_yaw")
    if rw_idx is not None:
        pos_before = pin.neutral(model)  # 用中性姿态再算一次基准
        pin.forwardKinematics(model, data, q)
        pos_zero = data.oMi[rw_idx].translation.copy()
        
        pin.forwardKinematics(model, data, q_moved)
        pos_moved = data.oMi[rw_idx].translation.copy()
        
        print(f"\n右手腕位置变化:")
        print(f"  抬臂前: ({pos_zero[0]:+.3f}, {pos_zero[1]:+.3f}, {pos_zero[2]:+.3f})")
        print(f"  抬臂后: ({pos_moved[0]:+.3f}, {pos_moved[1]:+.3f}, {pos_moved[2]:+.3f})")
        print(f"  位移差: ({(pos_moved-pos_zero)[0]:+.3f}, {(pos_moved-pos_zero)[1]:+.3f}, {(pos_moved-pos_zero)[2]:+.3f})")

print("\n" + "=" * 60)
print("Step 5: 计算右手腕的雅可比矩阵（为 IK 做准备）")
print("=" * 60)

# 雅可比 J 描述：关节速度 -> 末端线速度/角速度
# 需要找到 wrist_yaw 对应的 frame id
rw_idx = key_joints.get("right_wrist_yaw")
if rw_idx is not None:
    # 计算雅可比（6 x nv）：前 3 行是线速度映射，后 3 行是角速度映射
    J = pin.computeFrameJacobian(model, data, q, rw_idx, pin.ReferenceFrame.LOCAL_WORLD_ALIGNED)
    print(f"雅可比矩阵 J 的形状: {J.shape}")
    print(f"前 3 行（线速度部分）:")
    print(J[:3, :6].round(3))  # 只打印前 6 个关节对应的列
    print(f"\n解读: J[:,i] 表示第 i 个关节转动单位速度时，")
    print(f"      右手腕在 (x, y, z) 方向上分别产生多少线速度")

print("\n" + "=" * 60)
print("演示完成！")
print("=" * 60)
