# BONES-SEED G1 数据手动下载与处理指南

> 适用于无法直接从服务器访问 HuggingFace xet CDN 的场景。在本地/其他机器下载 `g1.tar.gz` 后传输到服务器处理。

---

## 一、在本地机器下载 `g1.tar.gz`

### 方式 1：huggingface-cli（推荐）

```bash
# 安装工具
pip install huggingface_hub

# 登录（如有需要）
huggingface-cli login

# 下载 g1.tar.gz（约 23.5 GB）
huggingface-cli download bones-studio/seed g1.tar.gz \
    --repo-type dataset --local-dir .
```

### 方式 2：直接浏览器下载

打开链接：
```
https://huggingface.co/datasets/bones-studio/seed/tree/main
```

找到 `g1.tar.gz`，点击下载。

### 方式 3：wget/curl（获取直链后）

```bash
# 先获取下载直链（通过浏览器开发者工具或 huggingface-cli 的 --include 参数）
# 然后用 wget 多线程下载
wget -c "<直链地址>" -O g1.tar.gz
```

### 方式 4：git lfs（下载整个仓库）

```bash
git lfs install
git clone https://huggingface.co/datasets/bones-studio/seed bones-seed
cd bones-seed
git lfs pull -I g1.tar.gz
```

---

## 二、传输到服务器

假设你已经在本地拿到了 `g1.tar.gz`，服务器地址为 `<server_ip>`，用户名为 `nio`。

### 方式 1：scp

```bash
# 从本地传到服务器的 /data/wangbin/
scp /本地路径/g1.tar.gz nio@<server_ip>:/data/wangbin/
```

### 方式 2：rsync（断点续传，推荐大文件）

```bash
rsync -avz --progress /本地路径/g1.tar.gz nio@<server_ip>:/data/wangbin/
```

### 方式 3：硬盘/U盘拷贝

直接挂载到 `/data/wangbin/` 或先拷到用户目录再 `mv`。

---

## 三、服务器端后续处理

传输完成后，SSH 到服务器执行以下步骤：

### Step 1：激活环境

```bash
conda activate isaaclab_sim5
cd /home/nio/wangbin/GR00T-WholeBodyControl
```

### Step 2：运行处理脚本（跳过下载，只解压+转换+过滤）

```bash
python download_bones_seed.py --skip-download --workers 32
```

脚本会自动：
1. **解压** `/data/wangbin/g1.tar.gz` → `/data/wangbin/g1/csv/`
2. **转换** CSV → motion_lib PKL（120fps→30fps、度→弧度、轴角转换）
3. **过滤** 剔除 G1 无法执行的动作（坐椅子、骑车、攀爬等，约 8.7%）
4. **创建软链接** `data/motion_lib_bones_seed/robot_filtered`

### Step 3：验证结果

```bash
# 检查过滤后的数据量
find data/motion_lib_bones_seed/robot_filtered -name "*.pkl" | wc -l
# 预期输出：~130,000

# 检查目录结构
ls -la data/motion_lib_bones_seed/
# 应有：robot_filtered -> /data/wangbin/motion_lib_bones_seed/robot_filtered
#      smpl_filtered -> /data/wangbin/smpl_filtered
```

### 如果只想手动执行每一步（不跑脚本）

```bash
# 1. 解压
cd /data/wangbin
tar -xzf g1.tar.gz
# 得到 g1/csv/ 目录，包含大量 session 子目录和 CSV 文件

# 2. CSV → PKL 转换
cd /home/nio/wangbin/GR00T-WholeBodyControl
python gear_sonic/data_process/convert_soma_csv_to_motion_lib.py \
    --input /data/wangbin/g1/csv/ \
    --output /data/wangbin/motion_lib_bones_seed/robot \
    --fps 30 --fps_source 120 \
    --individual --num_workers 16

# 3. 过滤不可执行动作
python gear_sonic/data_process/filter_and_copy_bones_data.py \
    --source /data/wangbin/motion_lib_bones_seed/robot \
    --dest /data/wangbin/motion_lib_bones_seed/robot_filtered \
    --workers 16

# 4. 创建软链接
mkdir -p data/motion_lib_bones_seed
ln -sf /data/wangbin/motion_lib_bones_seed/robot_filtered data/motion_lib_bones_seed/robot_filtered
ln -sf /data/wangbin/smpl_filtered data/motion_lib_bones_seed/smpl_filtered
```

---

## 四、数据文件说明

| 文件/目录 | 大小 | 说明 |
|----------|------|------|
| `g1.tar.gz` | ~23.5 GB | 原始下载文件，可删除以节省空间 |
| `g1/csv/` | ~30 GB | 解压后的 142,220 条运动 CSV |
| `robot/` | ~15 GB | 转换后的原始 PKL（~142K 文件） |
| `robot_filtered/` | ~13 GB | 过滤后的可用 PKL（~130K 文件） |
| `smpl_filtered/` | 31 GB | SMPL 参数数据（已就绪） |

---

## 五、常见问题

**Q：解压后 `g1.tar.gz` 可以删吗？**  
A：可以。处理完成后 `g1.tar.gz` 和 `g1/csv/` 都可以删除，只保留 `robot_filtered/` 即可。

**Q：转换需要多久？**  
A：取决于 CPU 核心数。16 线程约 30–60 分钟。

**Q：磁盘空间不够？**  
A：处理全流程峰值占用约 **80 GB**（23.5 + 30 + 15 + 13），处理完可释放到约 **45 GB**（保留 robot_filtered + smpl_filtered）。
