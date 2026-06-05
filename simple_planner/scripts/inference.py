"""
Simple Motion Planner Inference Script

加载训练好的模型，从 context + condition 生成未来运动轨迹。

Usage:
    python simple_planner/scripts/inference.py \
        --checkpoint checkpoints/simple_planner/best_model.pt \
        --mode walk \
        --target_vel 1.5

也可以直接从 PKL motion 文件中提取 context 进行生成:
    python simple_planner/scripts/inference.py \
        --checkpoint checkpoints/simple_planner/best_model.pt \
        --context_file data/motion_lib_bones_seed/robot_filtered/motion_000.pkl
"""

import sys
import argparse
import pickle
import numpy as np
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.planner import SimpleMotionPlanner
from data.motion_dataset import build_qpos_from_motionlib, LOCOMOTION_MODES, MODE_DEFAULT_VEL, NUM_CONTEXT_FRAMES, NUM_FUTURE_FRAMES


def parse_args():
    parser = argparse.ArgumentParser(description="Planner Inference")
    parser.add_argument("--checkpoint", type=str, required=True,
                        help="Path to model checkpoint")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    
    # Context 来源
    parser.add_argument("--context_file", type=str, default=None,
                        help="PKL motion file to extract context from")
    parser.add_argument("--context_frame_idx", type=int, default=0,
                        help="Start frame index for context extraction")
    
    # 或手动指定 context
    parser.add_argument("--context", type=str, default=None,
                        help="JSON string of context frames (alternative to context_file)")
    
    # Condition
    parser.add_argument("--mode", type=str, default="walk",
                        choices=["idle", "slow_walk", "walk", "run"],
                        help="Locomotion mode")
    parser.add_argument("--target_vel", type=float, default=None,
                        help="Target velocity (m/s). If None, use mode default.")
    parser.add_argument("--movement_dir", type=str, default="1,0,0",
                        help="Movement direction as x,y,z")
    parser.add_argument("--facing_dir", type=str, default="1,0,0",
                        help="Facing direction as x,y,z")
    parser.add_argument("--height", type=float, default=0.8,
                        help="Target root height")
    
    # 输出
    parser.add_argument("--output", type=str, default=None,
                        help="Output PKL file to save generated trajectory")
    parser.add_argument("--visualize", action="store_true",
                        help="Visualize generated trajectory (requires matplotlib)")
    
    return parser.parse_args()


def load_model(checkpoint_path, device):
    """加载训练好的模型。"""
    checkpoint = torch.load(checkpoint_path, map_location=device)
    
    # 构建模型
    if "model_config" in checkpoint:
        cfg = checkpoint["model_config"]
    else:
        cfg = {
            "d_model": 256,
            "nhead": 8,
            "num_encoder_layers": 4,
            "num_decoder_layers": 4,
            "dim_feedforward": 1024,
            "dropout": 0.0,
        }
    
    model = SimpleMotionPlanner(
        qpos_dim=36,
        d_model=cfg["d_model"],
        nhead=cfg["nhead"],
        num_encoder_layers=cfg["num_encoder_layers"],
        num_decoder_layers=cfg["num_decoder_layers"],
        dim_feedforward=cfg["dim_feedforward"],
        dropout=cfg["dropout"],
    )
    
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()
    
    return model


def extract_context_from_file(pkl_path, start_frame=0, num_frames=NUM_CONTEXT_FRAMES):
    """从 PKL 文件中提取 context 帧。"""
    with open(pkl_path, "rb") as f:
        motion_data = pickle.load(f)
    
    qpos = build_qpos_from_motionlib(motion_data)
    
    end_frame = start_frame + num_frames
    if end_frame > qpos.shape[0]:
        print(f"Warning: Requested frames exceed motion length ({qpos.shape[0]}). Using last {num_frames} frames.")
        start_frame = qpos.shape[0] - num_frames
        end_frame = qpos.shape[0]
    
    context = qpos[start_frame:end_frame]  # [4, 36]
    return context


def parse_direction(dir_str):
    """解析方向字符串。"""
    parts = [float(x.strip()) for x in dir_str.split(",")]
    arr = np.array(parts, dtype=np.float32)
    arr = arr / (np.linalg.norm(arr) + 1e-8)
    return arr


def visualize_trajectory(trajectory, save_path=None):
    """
    可视化生成的轨迹。
    
    绘制:
        - 根位置 XY 轨迹
        - 根高度 Z 随时间变化
        - 部分关节角度随时间变化
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed, skipping visualization")
        return
    
    T = trajectory.shape[0]
    root_pos = trajectory[:, :3]  # [T, 3]
    joints = trajectory[:, 7:]    # [T, 29]
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1. 根位置 XY 平面轨迹
    ax = axes[0, 0]
    ax.plot(root_pos[:, 0], root_pos[:, 1], 'b-', linewidth=2, marker='o', markersize=3)
    ax.plot(root_pos[0, 0], root_pos[0, 1], 'go', markersize=10, label='Start')
    ax.plot(root_pos[-1, 0], root_pos[-1, 1], 'ro', markersize=10, label='End')
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_title('Root Position Trajectory (XY Plane)')
    ax.legend()
    ax.grid(True)
    ax.axis('equal')
    
    # 2. 根高度随时间
    ax = axes[0, 1]
    ax.plot(range(T), root_pos[:, 2], 'g-', linewidth=2)
    ax.set_xlabel('Frame')
    ax.set_ylabel('Height (m)')
    ax.set_title('Root Height over Time')
    ax.grid(True)
    
    # 3. 部分关节角度 (前 5 个关节)
    ax = axes[1, 0]
    for i in range(min(5, joints.shape[1])):
        ax.plot(range(T), joints[:, i], label=f'Joint {i}')
    ax.set_xlabel('Frame')
    ax.set_ylabel('Angle (rad)')
    ax.set_title('Joint Angles (First 5)')
    ax.legend()
    ax.grid(True)
    
    # 4. 根速度
    ax = axes[1, 1]
    velocities = np.linalg.norm(np.diff(root_pos, axis=0), axis=1) * 30.0  # 假设 30fps
    ax.plot(range(len(velocities)), velocities, 'r-', linewidth=2)
    ax.set_xlabel('Frame')
    ax.set_ylabel('Velocity (m/s)')
    ax.set_title('Root Velocity over Time')
    ax.grid(True)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Visualization saved: {save_path}")
    else:
        plt.show()


def main():
    args = parse_args()
    
    print(f"Loading model from: {args.checkpoint}")
    model = load_model(args.checkpoint, args.device)
    
    # 准备 context
    if args.context_file:
        print(f"Extracting context from: {args.context_file}")
        context_np = extract_context_from_file(args.context_file, args.context_frame_idx)
    elif args.context:
        # 从 JSON 字符串解析
        import json
        context_list = json.loads(args.context)
        context_np = np.array(context_list, dtype=np.float32)
    else:
        print("No context provided, using random context")
        context_np = np.random.randn(NUM_CONTEXT_FRAMES, 36).astype(np.float32)
    
    context = torch.from_numpy(context_np).unsqueeze(0).to(args.device)  # [1, 4, 36]
    print(f"Context shape: {context.shape}")
    
    # 准备 condition
    mode = LOCOMOTION_MODES[args.mode]
    target_vel = args.target_vel if args.target_vel is not None else MODE_DEFAULT_VEL[mode]
    movement_dir = parse_direction(args.movement_dir)
    facing_dir = parse_direction(args.facing_dir)
    
    print(f"\nCondition:")
    print(f"  Mode: {args.mode} (id={mode})")
    print(f"  Target Velocity: {target_vel:.2f} m/s")
    print(f"  Movement Direction: {movement_dir}")
    print(f"  Facing Direction: {facing_dir}")
    print(f"  Height: {args.height:.2f} m")
    
    # 转换为 tensor
    mode_t = torch.tensor([mode], dtype=torch.long).to(args.device)
    target_vel_t = torch.tensor([target_vel], dtype=torch.float32).to(args.device)
    movement_dir_t = torch.from_numpy(movement_dir).unsqueeze(0).to(args.device)
    facing_dir_t = torch.from_numpy(facing_dir).unsqueeze(0).to(args.device)
    height_t = torch.tensor([args.height], dtype=torch.float32).to(args.device)
    
    # 推理
    with torch.no_grad():
        future_pred = model(context, mode_t, target_vel_t, movement_dir_t, facing_dir_t, height_t)
    
    future_np = future_pred[0].cpu().numpy()  # [K, 36]
    
    print(f"\nGenerated future trajectory:")
    print(f"  Shape: {future_np.shape}")
    print(f"  Root position (first frame): {future_np[0, :3]}")
    print(f"  Root position (last frame): {future_np[-1, :3]}")
    print(f"  Mean joint angles: {np.mean(np.abs(future_np[:, 7:])):.4f} rad")
    
    # 保存输出
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        result = {
            "context": context_np,           # [4, 36]
            "future": future_np,             # [K, 36]
            "condition": {
                "mode": args.mode,
                "target_vel": target_vel,
                "movement_dir": movement_dir.tolist(),
                "facing_dir": facing_dir.tolist(),
                "height": args.height,
            },
        }
        
        with open(output_path, "wb") as f:
            pickle.dump(result, f)
        print(f"\nResult saved: {output_path}")
    
    # 可视化
    if args.visualize:
        viz_path = args.output.replace(".pkl", ".png") if args.output else None
        # 合并 context 和 future 用于可视化
        full_traj = np.concatenate([context_np, future_np], axis=0)
        visualize_trajectory(full_traj, save_path=viz_path)
    
    print("\nInference completed!")


if __name__ == "__main__":
    main()
