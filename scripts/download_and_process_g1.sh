#!/bin/bash
# BONES-SEED G1 数据下载与处理流水线
# 下载 g1.tar.gz → 解压 → CSV转PKL → 过滤 → 链接到项目

set -euo pipefail

REPO_ROOT="/home/nio/wangbin/GR00T-WholeBodyControl"
DATA_DIR="/data/wangbin"
G1_TAR="$DATA_DIR/g1.tar.gz"
G1_EXTRACT_DIR="$DATA_DIR/g1"
ROBOT_RAW="$DATA_DIR/motion_lib_bones_seed/robot"
ROBOT_FILTERED="$DATA_DIR/motion_lib_bones_seed/robot_filtered"
LOCK_FILE="$DATA_DIR/.g1_processing.lock"
DONE_FILE="$DATA_DIR/.g1_processing.done"
LOG_FILE="$DATA_DIR/g1_download_process.log"

# 如果已经处理完成，直接退出
if [[ -f "$DONE_FILE" ]]; then
    echo "[$(date)] G1 data already processed. Exiting." | tee -a "$LOG_FILE"
    exit 0
fi

# 防止重复运行
if [[ -f "$LOCK_FILE" ]]; then
    echo "[$(date)] Another instance is running (lock file exists). Exiting." | tee -a "$LOG_FILE"
    exit 1
fi
touch "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

echo "========================================" | tee -a "$LOG_FILE"
echo "[$(date)] Starting G1 data pipeline" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# 1. 下载 g1.tar.gz（增加超时，启用断点续传）
if [[ ! -f "$G1_TAR" ]]; then
    echo "[$(date)] Downloading g1.tar.gz from HuggingFace..." | tee -a "$LOG_FILE"
    export HF_HUB_DOWNLOAD_TIMEOUT=3600
    export HF_HUB_ENABLE_HF_TRANSFER=1
    cd "$DATA_DIR"
    if ! huggingface-cli download bones-studio/seed g1.tar.gz --repo-type dataset --local-dir . 2>&1 | tee -a "$LOG_FILE"; then
        echo "[$(date)] Download failed. Will retry on next run." | tee -a "$LOG_FILE"
        exit 1
    fi
else
    echo "[$(date)] g1.tar.gz already exists, skipping download." | tee -a "$LOG_FILE"
fi

# 2. 解压
if [[ ! -d "$G1_EXTRACT_DIR" ]]; then
    echo "[$(date)] Extracting g1.tar.gz..." | tee -a "$LOG_FILE"
    cd "$DATA_DIR"
    tar -xzf g1.tar.gz 2>&1 | tee -a "$LOG_FILE"
    echo "[$(date)] Extraction complete." | tee -a "$LOG_FILE"
else
    echo "[$(date)] g1/ directory already exists, skipping extraction." | tee -a "$LOG_FILE"
fi

# 3. 检查 CSV 目录
G1_CSV_DIR="$G1_EXTRACT_DIR/csv"
if [[ ! -d "$G1_CSV_DIR" ]]; then
    # 尝试其他可能的路径
    G1_CSV_DIR=$(find "$G1_EXTRACT_DIR" -maxdepth 2 -type d -name "csv" | head -1)
    if [[ -z "$G1_CSV_DIR" ]]; then
        echo "[$(date)] ERROR: Cannot find CSV directory in $G1_EXTRACT_DIR" | tee -a "$LOG_FILE"
        exit 1
    fi
fi
echo "[$(date)] Found G1 CSV dir: $G1_CSV_DIR" | tee -a "$LOG_FILE"

# 4. CSV → motion_lib PKL 转换
cd "$REPO_ROOT"
conda run -n isaaclab_sim5 python gear_sonic/data_process/convert_soma_csv_to_motion_lib.py \
    --input "$G1_CSV_DIR" \
    --output "$ROBOT_RAW" \
    --fps 30 --fps_source 120 \
    --individual \
    --num_workers 16 2>&1 | tee -a "$LOG_FILE"

echo "[$(date)] CSV → PKL conversion complete." | tee -a "$LOG_FILE"

# 5. 过滤不可执行动作
conda run -n isaaclab_sim5 python gear_sonic/data_process/filter_and_copy_bones_data.py \
    --source "$ROBOT_RAW" \
    --dest "$ROBOT_FILTERED" \
    --workers 16 2>&1 | tee -a "$LOG_FILE"

echo "[$(date)] Filtering complete." | tee -a "$LOG_FILE"

# 6. 建立项目软链接
mkdir -p "$REPO_ROOT/data/motion_lib_bones_seed"
rm -f "$REPO_ROOT/data/motion_lib_bones_seed/robot_filtered"
ln -sf "$ROBOT_FILTERED" "$REPO_ROOT/data/motion_lib_bones_seed/robot_filtered"

echo "[$(date)] Symlink created: data/motion_lib_bones_seed/robot_filtered -> $ROBOT_FILTERED" | tee -a "$LOG_FILE"

# 7. 统计结果
ROBOT_COUNT=$(find "$ROBOT_FILTERED" -name "*.pkl" | wc -l)
echo "[$(date)] robot_filtered total PKL files: $ROBOT_COUNT" | tee -a "$LOG_FILE"

# 标记完成
touch "$DONE_FILE"
rm -f "$LOCK_FILE"

echo "========================================" | tee -a "$LOG_FILE"
echo "[$(date)] G1 data pipeline COMPLETE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# 清理 cron job（确保只执行一次）
(crontab -l 2>/dev/null | grep -v "download_and_process_g1.sh") | crontab - 2>/dev/null || true
