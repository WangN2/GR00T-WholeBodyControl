"""
Simple Motion Planner Training Script

训练基于 Transformer 的条件运动补全模型。

Usage:
    python simple_planner/scripts/train.py \
        --data_dir data/motion_lib_bones_seed/robot_filtered \
        --output_dir checkpoints/simple_planner \
        --batch_size 32 \
        --num_epochs 100 \
        --lr 1e-4
"""

import os
import sys
import argparse
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

# 添加项目根目录到 sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.planner import SimpleMotionPlanner
from data.motion_dataset import get_dataloader, NUM_CONTEXT_FRAMES, NUM_FUTURE_FRAMES


def parse_args():
    parser = argparse.ArgumentParser(description="Train Simple Motion Planner")
    
    # Data
    parser.add_argument("--data_dir", type=str, default="data/motion_lib_bones_seed/robot_filtered",
                        help="Directory containing motion_lib PKL files")
    parser.add_argument("--num_samples_per_motion", type=int, default=100,
                        help="Number of training samples per motion clip")
    
    # Model
    parser.add_argument("--d_model", type=int, default=256)
    parser.add_argument("--nhead", type=int, default=8)
    parser.add_argument("--num_encoder_layers", type=int, default=4)
    parser.add_argument("--num_decoder_layers", type=int, default=4)
    parser.add_argument("--dim_feedforward", type=int, default=1024)
    parser.add_argument("--dropout", type=float, default=0.1)
    
    # Training
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--num_epochs", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight_decay", type=float, default=1e-4)
    parser.add_argument("--num_workers", type=int, default=4)
    parser.add_argument("--grad_clip", type=float, default=1.0)
    parser.add_argument("--save_every", type=int, default=10,
                        help="Save checkpoint every N epochs")
    
    # Logging
    parser.add_argument("--output_dir", type=str, default="checkpoints/simple_planner")
    parser.add_argument("--use_wandb", action="store_true")
    parser.add_argument("--wandb_project", type=str, default="simple_planner")
    parser.add_argument("--seed", type=int, default=42)
    
    # Device
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    
    return parser.parse_args()


def set_seed(seed):
    """设置随机种子。"""
    import random
    import numpy as np
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def save_checkpoint(model, optimizer, epoch, loss, save_path):
    """保存模型检查点。"""
    torch.save({
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "loss": loss,
        "model_config": {
            "d_model": model.d_model,
            "nhead": model.transformer_encoder.layers[0].self_attn.num_heads,
            "num_encoder_layers": len(model.transformer_encoder.layers),
            "num_decoder_layers": len(model.transformer_decoder.layers),
            "dim_feedforward": model.transformer_encoder.layers[0].linear1.out_features,
            "dropout": model.transformer_encoder.layers[0].dropout.p,
        },
    }, save_path)
    print(f"Checkpoint saved: {save_path}")


def train_epoch(model, dataloader, optimizer, device, grad_clip):
    """训练一个 epoch。"""
    model.train()
    total_loss = 0.0
    total_metrics = {}
    num_batches = 0
    
    for batch in dataloader:
        # 移设备
        context = batch["context"].to(device)           # [B, 4, 36]
        future = batch["future"].to(device)             # [B, K, 36]
        mode = batch["mode"].to(device)                 # [B]
        target_vel = batch["target_vel"].to(device)     # [B]
        movement_dir = batch["movement_dir"].to(device) # [B, 3]
        facing_dir = batch["facing_dir"].to(device)     # [B, 3]
        height = batch["height"].to(device)             # [B]
        
        # 前向 + 损失
        optimizer.zero_grad()
        loss, metrics = model.compute_loss(
            context, future, mode, target_vel, movement_dir, facing_dir, height
        )
        
        # 反向传播
        loss.backward()
        
        # 梯度裁剪
        if grad_clip > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        
        optimizer.step()
        
        # 统计
        total_loss += loss.item()
        for k, v in metrics.items():
            total_metrics[k] = total_metrics.get(k, 0.0) + v
        num_batches += 1
    
    avg_loss = total_loss / num_batches
    avg_metrics = {k: v / num_batches for k, v in total_metrics.items()}
    
    return avg_loss, avg_metrics


def validate(model, dataloader, device):
    """验证。"""
    model.eval()
    total_loss = 0.0
    total_metrics = {}
    num_batches = 0
    
    with torch.no_grad():
        for batch in dataloader:
            context = batch["context"].to(device)
            future = batch["future"].to(device)
            mode = batch["mode"].to(device)
            target_vel = batch["target_vel"].to(device)
            movement_dir = batch["movement_dir"].to(device)
            facing_dir = batch["facing_dir"].to(device)
            height = batch["height"].to(device)
            
            loss, metrics = model.compute_loss(
                context, future, mode, target_vel, movement_dir, facing_dir, height
            )
            
            total_loss += loss.item()
            for k, v in metrics.items():
                total_metrics[k] = total_metrics.get(k, 0.0) + v
            num_batches += 1
    
    avg_loss = total_loss / num_batches
    avg_metrics = {k: v / num_batches for k, v in total_metrics.items()}
    
    return avg_loss, avg_metrics


def main():
    args = parse_args()
    
    # 设置随机种子
    set_seed(args.seed)
    
    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化 wandb
    if args.use_wandb:
        try:
            import wandb
            wandb.init(project=args.wandb_project, config=vars(args))
        except ImportError:
            print("wandb not installed, skipping wandb logging")
            args.use_wandb = False
    
    # 检查数据目录
    has_pkl = os.path.exists(args.data_dir) and len(list(Path(args.data_dir).rglob("*.pkl"))) > 0
    if not has_pkl:
        print(f"WARNING: No .pkl files found in {args.data_dir}!")
        print("Creating dummy data for testing...")
        import tempfile
        dummy_dir = tempfile.mkdtemp()
        # 创建一些 dummy PKL 文件
        import pickle
        import numpy as np
        for i in range(5):
            T = np.random.randint(300, 600)
            motion_data = {
                "root_trans_offset": np.random.randn(T, 3).astype(np.float32),
                "root_rot": np.random.randn(T, 4).astype(np.float32),
                "dof": np.random.randn(T, 29).astype(np.float32) * 0.5,
            }
            # 归一化四元数
            motion_data["root_rot"] = motion_data["root_rot"] / np.linalg.norm(
                motion_data["root_rot"], axis=1, keepdims=True
            )
            with open(os.path.join(dummy_dir, f"motion_{i:03d}.pkl"), "wb") as f:
                pickle.dump(motion_data, f)
        args.data_dir = dummy_dir
        print(f"Using dummy data from: {dummy_dir}")
    
    # 创建 DataLoader
    print(f"Loading data from: {args.data_dir}")
    # 80% train, 20% val
    from data.motion_dataset import MotionDataset
    full_dataset = MotionDataset(
        data_dir=args.data_dir,
        num_samples_per_motion=args.num_samples_per_motion,
    )
    
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(
        full_dataset, [train_size, val_size]
    )
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=True,
    )
    
    print(f"Train samples: {len(train_dataset)}, Val samples: {len(val_dataset)}")
    
    # 创建模型
    print("Creating model...")
    model = SimpleMotionPlanner(
        qpos_dim=36,
        d_model=args.d_model,
        num_context_frames=NUM_CONTEXT_FRAMES,
        num_future_frames=NUM_FUTURE_FRAMES,
        num_modes=4,
        nhead=args.nhead,
        num_encoder_layers=args.num_encoder_layers,
        num_decoder_layers=args.num_decoder_layers,
        dim_feedforward=args.dim_feedforward,
        dropout=args.dropout,
    ).to(args.device)
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {total_params:,}")
    
    # 优化器
    optimizer = optim.AdamW(
        model.parameters(),
        lr=args.lr,
        weight_decay=args.weight_decay,
    )
    
    # 学习率调度器（Cosine Annealing）
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.num_epochs, eta_min=1e-6
    )
    
    # 训练循环
    print(f"\n{'='*60}")
    print("Training started!")
    print(f"{'='*60}\n")
    
    best_val_loss = float('inf')
    
    for epoch in range(1, args.num_epochs + 1):
        epoch_start = time.time()
        
        # Train
        train_loss, train_metrics = train_epoch(model, train_loader, optimizer, args.device, args.grad_clip)
        
        # Validate
        val_loss, val_metrics = validate(model, val_loader, args.device)
        
        # 学习率调度
        scheduler.step()
        current_lr = optimizer.param_groups[0]["lr"]
        
        epoch_time = time.time() - epoch_start
        
        # 打印日志
        print(f"Epoch [{epoch}/{args.num_epochs}] | Time: {epoch_time:.1f}s | LR: {current_lr:.2e}")
        print(f"  Train Loss: {train_loss:.6f} | MSE: {train_metrics['mse']:.6f} | Root: {train_metrics['root_pos_l1']:.6f}")
        print(f"  Val   Loss: {val_loss:.6f} | MSE: {val_metrics['mse']:.6f} | Root: {val_metrics['root_pos_l1']:.6f}")
        
        # Wandb 日志
        if args.use_wandb:
            wandb.log({
                "epoch": epoch,
                "train/loss": train_loss,
                "train/mse": train_metrics['mse'],
                "train/root_pos_l1": train_metrics['root_pos_l1'],
                "val/loss": val_loss,
                "val/mse": val_metrics['mse'],
                "val/root_pos_l1": val_metrics['root_pos_l1'],
                "lr": current_lr,
            })
        
        # 保存检查点
        if epoch % args.save_every == 0:
            ckpt_path = output_dir / f"checkpoint_epoch_{epoch:03d}.pt"
            save_checkpoint(model, optimizer, epoch, val_loss, ckpt_path)
        
        # 保存最佳模型
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_path = output_dir / "best_model.pt"
            save_checkpoint(model, optimizer, epoch, val_loss, best_path)
            print(f"  *** Best model saved! Val Loss: {val_loss:.6f}")
    
    print(f"\n{'='*60}")
    print("Training completed!")
    print(f"Best validation loss: {best_val_loss:.6f}")
    print(f"Checkpoints saved to: {output_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
