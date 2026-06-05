#!/usr/bin/env python3
"""
Download and process BONES-SEED G1 motion data for SONIC training.

This script automates the full pipeline:
  1. Download g1.tar.gz from bones-studio/seed (HuggingFace)
  2. Extract CSV motion files
  3. Convert CSV → motion_lib PKL (unit conversion, downsampling, axis-angle)
  4. Filter physically infeasible motions for G1
  5. Symlink results to data/motion_lib_bones_seed/robot_filtered

Usage:
    python download_bones_seed.py                    # Full pipeline
    python download_bones_seed.py --skip-download    # Use existing g1.tar.gz
    python download_bones_seed.py --skip-filter      # Skip filtering step
    python download_bones_seed.py --workers 32       # Use 32 parallel workers
    python download_bones_seed.py --output-dir /path # Custom output directory

Requirements:
    pip install huggingface_hub pandas numpy scipy joblib

The script is idempotent — safe to re-run. Already-completed steps are skipped.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

DATASET_REPO = "bones-studio/seed"
G1_TAR_NAME = "g1.tar.gz"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download and process BONES-SEED G1 motion data"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to store downloaded and processed data. "
             "Defaults to repo-root/data/",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download step (use existing g1.tar.gz in output-dir)",
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip extraction step (use existing csv/ directory)",
    )
    parser.add_argument(
        "--skip-convert",
        action="store_true",
        help="Skip CSV→PKL conversion (use existing robot/ directory)",
    )
    parser.add_argument(
        "--skip-filter",
        action="store_true",
        help="Skip motion filtering step",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=16,
        help="Number of parallel workers for CSV→PKL conversion (default: 16)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Target FPS for motion_lib output (default: 30)",
    )
    parser.add_argument(
        "--fps-source",
        type=int,
        default=120,
        help="Source FPS of BONES-SEED CSV (default: 120)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Hugging Face token (or set HF_TOKEN env var / run `huggingface-cli login`)",
    )
    parser.add_argument(
        "--keep-tar",
        action="store_true",
        help="Keep g1.tar.gz after extraction (default: delete to save space)"
    )
    return parser.parse_args()


def ensure_hf_hub():
    try:
        from huggingface_hub import hf_hub_download
        return hf_hub_download
    except ImportError:
        print("ERROR: huggingface_hub is not installed.")
        print("  pip install huggingface_hub")
        sys.exit(1)


def step_download(hf_hub_download, output_dir: Path, token: str | None) -> Path:
    """Download g1.tar.gz from HuggingFace."""
    tar_path = output_dir / G1_TAR_NAME
    if tar_path.exists():
        print(f"[SKIP] {tar_path} already exists.")
        return tar_path

    print(f"[DOWNLOAD] {G1_TAR_NAME} from {DATASET_REPO} ...")
    print("  This is ~20-30 GB and may take a while.")
    cached = hf_hub_download(
        repo_id=DATASET_REPO,
        filename=G1_TAR_NAME,
        repo_type="dataset",
        token=token,
        local_dir=str(output_dir),
    )
    # hf_hub_download with local_dir places file directly
    downloaded = Path(cached)
    if downloaded != tar_path and downloaded.exists():
        shutil.move(str(downloaded), str(tar_path))
    print(f"[DONE] Saved to {tar_path}")
    return tar_path


def step_extract(tar_path: Path, output_dir: Path, keep_tar: bool) -> Path:
    """Extract g1.tar.gz and locate the csv/ directory."""
    extract_dir = output_dir / "g1"
    csv_dir = extract_dir / "csv"

    if csv_dir.exists():
        print(f"[SKIP] {csv_dir} already exists.")
        return csv_dir

    print(f"[EXTRACT] {tar_path} → {extract_dir} ...")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=output_dir)
    print(f"[DONE] Extracted.")

    # Validate
    if not csv_dir.exists():
        # Try to find csv/ deeper in the tree
        candidates = list(extract_dir.rglob("csv"))
        candidates = [c for c in candidates if c.is_dir()]
        if candidates:
            csv_dir = candidates[0]
            print(f"[INFO] Found CSV directory at: {csv_dir}")
        else:
            print(f"ERROR: Cannot find CSV directory inside {extract_dir}")
            sys.exit(1)

    if not keep_tar:
        print(f"[CLEANUP] Removing {tar_path} to save space ...")
        tar_path.unlink()

    return csv_dir


def step_convert(csv_dir: Path, robot_raw: Path, fps: int, fps_source: int, workers: int):
    """Convert CSV → motion_lib PKL."""
    if robot_raw.exists() and any(robot_raw.rglob("*.pkl")):
        n_existing = sum(1 for _ in robot_raw.rglob("*.pkl"))
        print(f"[SKIP] {robot_raw} already contains {n_existing} PKL files.")
        return

    repo_root = Path(__file__).resolve().parent
    converter = repo_root / "gear_sonic" / "data_process" / "convert_soma_csv_to_motion_lib.py"
    if not converter.exists():
        print(f"ERROR: Converter script not found: {converter}")
        sys.exit(1)

    print(f"[CONVERT] CSV → PKL ...")
    print(f"  Input : {csv_dir}")
    print(f"  Output: {robot_raw}")
    print(f"  FPS   : {fps_source} → {fps}")
    print(f"  Workers: {workers}")

    cmd = [
        sys.executable, str(converter),
        "--input", str(csv_dir),
        "--output", str(robot_raw),
        "--fps", str(fps),
        "--fps_source", str(fps_source),
        "--individual",
        "--num_workers", str(workers),
    ]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("ERROR: CSV→PKL conversion failed.")
        sys.exit(1)
    print("[DONE] Conversion complete.")


def step_filter(robot_raw: Path, robot_filtered: Path, workers: int):
    """Filter physically infeasible motions."""
    if robot_filtered.exists() and any(robot_filtered.rglob("*.pkl")):
        n_existing = sum(1 for _ in robot_filtered.rglob("*.pkl"))
        print(f"[SKIP] {robot_filtered} already contains {n_existing} PKL files.")
        return

    repo_root = Path(__file__).resolve().parent
    filter_script = repo_root / "gear_sonic" / "data_process" / "filter_and_copy_bones_data.py"
    if not filter_script.exists():
        print(f"ERROR: Filter script not found: {filter_script}")
        sys.exit(1)

    print(f"[FILTER] Removing infeasible motions ...")
    print(f"  Source: {robot_raw}")
    print(f"  Dest  : {robot_filtered}")

    cmd = [
        sys.executable, str(filter_script),
        "--source", str(robot_raw),
        "--dest", str(robot_filtered),
        "--workers", str(workers),
    ]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("ERROR: Filtering failed.")
        sys.exit(1)
    print("[DONE] Filtering complete.")


def step_symlink(robot_filtered: Path, repo_root: Path):
    """Create symlink data/motion_lib_bones_seed/robot_filtered → processed data."""
    link_dir = repo_root / "data" / "motion_lib_bones_seed"
    link_dir.mkdir(parents=True, exist_ok=True)
    link_path = link_dir / "robot_filtered"

    if link_path.exists() or link_path.is_symlink():
        print(f"[SKIP] Symlink already exists: {link_path}")
        return

    print(f"[SYMLINK] {link_path} -> {robot_filtered}")
    link_path.symlink_to(robot_filtered.resolve(), target_is_directory=True)
    print("[DONE] Symlink created.")


def print_summary(robot_raw: Path, robot_filtered: Path):
    """Print final statistics."""
    n_raw = sum(1 for _ in robot_raw.rglob("*.pkl")) if robot_raw.exists() else 0
    n_filtered = sum(1 for _ in robot_filtered.rglob("*.pkl")) if robot_filtered.exists() else 0

    print("\n" + "=" * 60)
    print("  BONES-SEED G1 Data Pipeline Summary")
    print("=" * 60)
    print(f"  Raw motions      : {n_raw:,} PKL files")
    print(f"  Filtered motions : {n_filtered:,} PKL files")
    print(f"  Filter rate      : {(1 - n_filtered/max(n_raw,1))*100:.1f}%")
    print("=" * 60)
    print("\n  Training command:")
    print("    python gear_sonic/train_agent_trl.py \\")
    print("        +exp=manager/universal_token/all_modes/sonic_release \\")
    print("        num_envs=4096 headless=True \\")
    print("        ++manager_env.commands.motion.motion_lib_cfg.motion_file="
          "data/motion_lib_bones_seed/robot_filtered")
    print("=" * 60)


def main():
    args = parse_args()
    hf_hub_download = ensure_hf_hub()

    repo_root = Path(__file__).resolve().parent
    output_dir = args.output_dir if args.output_dir else repo_root / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define paths
    tar_path = output_dir / G1_TAR_NAME
    csv_dir = output_dir / "g1" / "csv"
    robot_raw = output_dir / "motion_lib_bones_seed" / "robot"
    robot_filtered = output_dir / "motion_lib_bones_seed" / "robot_filtered"

    print("=" * 60)
    print("  BONES-SEED G1 — Download & Process Pipeline")
    print(f"  Output dir: {output_dir}")
    print("=" * 60)

    # Step 1: Download
    if not args.skip_download:
        tar_path = step_download(hf_hub_download, output_dir, args.token)
    else:
        if not tar_path.exists():
            print(f"ERROR: --skip-download set but {tar_path} not found.")
            sys.exit(1)
        print(f"[SKIP] Using existing: {tar_path}")

    # Step 2: Extract
    if not args.skip_extract:
        csv_dir = step_extract(tar_path, output_dir, args.keep_tar)
    else:
        if not csv_dir.exists():
            print(f"ERROR: --skip-extract set but {csv_dir} not found.")
            sys.exit(1)
        print(f"[SKIP] Using existing CSV dir: {csv_dir}")

    # Step 3: Convert
    if not args.skip_convert:
        step_convert(csv_dir, robot_raw, args.fps, args.fps_source, args.workers)
    else:
        if not robot_raw.exists():
            print(f"ERROR: --skip-convert set but {robot_raw} not found.")
            sys.exit(1)
        print(f"[SKIP] Using existing raw PKL dir: {robot_raw}")

    # Step 4: Filter
    if not args.skip_filter:
        step_filter(robot_raw, robot_filtered, args.workers)
    else:
        if not robot_filtered.exists():
            print(f"ERROR: --skip-filter set but {robot_filtered} not found.")
            sys.exit(1)
        print(f"[SKIP] Using existing filtered PKL dir: {robot_filtered}")

    # Step 5: Symlink
    step_symlink(robot_filtered, repo_root)

    # Summary
    print_summary(robot_raw, robot_filtered)


if __name__ == "__main__":
    main()
