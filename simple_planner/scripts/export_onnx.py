"""
Export Simple Motion Planner to ONNX

将训练好的 PyTorch 模型导出为 ONNX 格式，用于后续部署。

Usage:
    python simple_planner/scripts/export_onnx.py \
        --checkpoint checkpoints/simple_planner/best_model.pt \
        --output planner_simple.onnx
"""

import sys
from pathlib import Path

import torch
import argparse

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.planner import SimpleMotionPlanner


def parse_args():
    parser = argparse.ArgumentParser(description="Export Planner to ONNX")
    parser.add_argument("--checkpoint", type=str, required=True,
                        help="Path to model checkpoint (.pt file)")
    parser.add_argument("--output", type=str, default="simple_planner.onnx",
                        help="Output ONNX file path")
    parser.add_argument("--d_model", type=int, default=256)
    parser.add_argument("--nhead", type=int, default=8)
    parser.add_argument("--num_encoder_layers", type=int, default=4)
    parser.add_argument("--num_decoder_layers", type=int, default=4)
    parser.add_argument("--dim_feedforward", type=int, default=1024)
    parser.add_argument("--dropout", type=float, default=0.0)  # 推理时 dropout=0
    parser.add_argument("--opset", type=int, default=14,
                        help="ONNX opset version")
    return parser.parse_args()


def main():
    args = parse_args()
    
    print(f"Loading checkpoint: {args.checkpoint}")
    checkpoint = torch.load(args.checkpoint, map_location="cpu")
    
    # 从 checkpoint 或命令行参数构建模型
    if "model_config" in checkpoint:
        cfg = checkpoint["model_config"]
        print("Using model config from checkpoint")
    else:
        cfg = {
            "d_model": args.d_model,
            "nhead": args.nhead,
            "num_encoder_layers": args.num_encoder_layers,
            "num_decoder_layers": args.num_decoder_layers,
            "dim_feedforward": args.dim_feedforward,
            "dropout": args.dropout,
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
    model.eval()
    
    print(f"Model loaded. Epoch: {checkpoint.get('epoch', 'N/A')}, Loss: {checkpoint.get('loss', 'N/A')}")
    
    # 创建 dummy 输入
    batch_size = 1
    context = torch.randn(batch_size, 4, 36)
    mode = torch.randint(0, 4, (batch_size,))
    target_vel = torch.randn(batch_size)
    movement_dir = torch.randn(batch_size, 3)
    facing_dir = torch.randn(batch_size, 3)
    height = torch.randn(batch_size)
    
    # 导出 ONNX
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    input_names = ["context", "mode", "target_vel", "movement_dir", "facing_dir", "height"]
    output_names = ["future"]
    
    # 动态 batch 维度
    dynamic_axes = {
        "context": {0: "batch_size"},
        "mode": {0: "batch_size"},
        "target_vel": {0: "batch_size"},
        "movement_dir": {0: "batch_size"},
        "facing_dir": {0: "batch_size"},
        "height": {0: "batch_size"},
        "future": {0: "batch_size"},
    }
    
    print(f"Exporting to ONNX: {output_path}")
    
    torch.onnx.export(
        model,
        (context, mode, target_vel, movement_dir, facing_dir, height),
        str(output_path),
        input_names=input_names,
        output_names=output_names,
        dynamic_axes=dynamic_axes,
        opset_version=args.opset,
        do_constant_folding=True,
    )
    
    print(f"ONNX export successful: {output_path}")
    
    # 验证 ONNX 模型
    try:
        import onnx
        onnx_model = onnx.load(str(output_path))
        onnx.checker.check_model(onnx_model)
        print("ONNX model validation passed!")
        
        # 打印模型信息
        print(f"\nONNX Model Info:")
        print(f"  IR version: {onnx_model.ir_version}")
        print(f"  Opset: {onnx_model.opset_import}")
        print(f"  Inputs:")
        for input in onnx_model.graph.input:
            print(f"    {input.name}: {[d.dim_value if d.dim_value else d.dim_param for d in input.type.tensor_type.shape.dim]}")
        print(f"  Outputs:")
        for output in onnx_model.graph.output:
            print(f"    {output.name}: {[d.dim_value if d.dim_value else d.dim_param for d in output.type.tensor_type.shape.dim]}")
        
    except ImportError:
        print("onnx package not installed, skipping validation")
    except Exception as e:
        print(f"ONNX validation warning: {e}")


if __name__ == "__main__":
    main()
