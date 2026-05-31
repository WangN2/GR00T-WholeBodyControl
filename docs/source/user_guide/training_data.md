# Training Data

## BONES-SEED

[BONES-SEED](https://huggingface.co/datasets/bones-studio/seed) (Skeletal Everyday Embodiment Dataset) is an open dataset of **142,220 annotated human motion animations** for humanoid robotics, created by [Bones Studio](https://bones.studio/datasets). It provides motion capture data in SOMA and Unitree G1 formats with natural language descriptions, temporal segmentation labels, and detailed skeletal metadata.

| | |
|---|---|
| **Total motions** | 142,220 (71,132 original + 71,088 mirrored) |
| **Total duration** | ~288 hours (@ 120 fps) |
| **Performers** | 522 actors (253 F / 269 M) |
| **Age range** | 17–71 years |
| **Height range** | 145–199 cm |
| **Weight range** | 38–145 kg |
| **Output formats** | SOMA Uniform · SOMA Proportional · Unitree G1 MuJoCo-compatible |
| **Annotations** | Up to 6 NL descriptions per motion + temporal segmentation + skeletal metadata |

### Relevance to SONIC

BONES-SEED a large subset of SONIC training data:

- **Unitree G1 joint trajectories** — retargeted for MuJoCo, directly usable for motion tracking training
- **Broad motion coverage** — locomotion, manipulation, dance, sports, communication, and everyday activities across 8 categories and 20 sub-categories
- **Rich language annotations** — up to 6 natural language descriptions per motion, enabling language-conditioned policy learning
- **Temporal segmentation** — per-motion phase labels with timestamps for structured skill decomposition
- **Performer diversity** — 522 actors spanning a wide range of body types, ages, and movement styles

### Motion Categories

| Package       | Motions | Description                                                             |
|---------------|---------|-------------------------------------------------------------------------|
| Locomotion    | 74,488  | Walking, jogging, jumping, climbing, crawling, turning, and transitions |
| Communication | 21,493  | Gestures, pointing, looking, and communicative body language            |
| Interactions  | 14,643  | Object manipulation, pick-and-place, carrying, and tool use             |
| Dances        | 11,006  | Full-body dance performances across multiple styles                     |
| Gaming        | 8,700   | Game-inspired actions and dynamic movements                             |
| Everyday      | 5,816   | Household tasks, consuming, sitting, reading, and daily activities      |
| Sport         | 3,993   | Athletic movements and sports-specific actions                          |
| Other         | 2,081   | Stunts, martial arts, and edge-case motions                             |

### Data Formats

Every motion is available in three formats:

- **SOMA Proportional (BVH)** — per-actor skeleton preserving original body proportions
- **SOMA Uniform (BVH)** — standardized skeleton shared across all motions for batch processing
- **Unitree G1 (CSV)** — joint-angle trajectories retargeted to the Unitree G1 humanoid

### Download

```bash
# Using the Hugging Face CLI
pip install huggingface_hub
huggingface-cli download bones-studio/seed --repo-type dataset --local-dir ./bones-seed
```

```python
# Using Python
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="bones-studio/seed",
    repo_type="dataset",
    local_dir="./bones-seed"
)
```

After downloading, extract the motion archives and convert them to the format SONIC expects.

### One-command pipeline (recommended)

We provide a script that automates download → extraction → conversion → filtering:

```bash
python download_bones_seed.py
```

This will:
1. Download `g1.tar.gz` from HuggingFace (~20–30 GB)
2. Extract CSV motion files
3. Convert CSV → `motion_lib` PKL (120 fps → 30 fps, degrees → radians, cm → m)
4. Filter motions that are physically infeasible for G1
5. Create a symlink at `data/motion_lib_bones_seed/robot_filtered`

The script is idempotent — safe to interrupt and re-run. Already-completed steps are skipped.

**Options:**

```bash
# Use custom output directory
python download_bones_seed.py --output-dir /data/bones_seed

# Skip download (you already have g1.tar.gz)
python download_bones_seed.py --skip-download

# Use more workers for faster conversion
python download_bones_seed.py --workers 32

# Keep the tar archive after extraction
python download_bones_seed.py --keep-tar
```

### Manual steps

If you prefer to run each step manually:

#### 1. Download

```bash
pip install huggingface_hub
huggingface-cli download bones-studio/seed g1.tar.gz --repo-type dataset --local-dir .
```

#### 2. Extract

```bash
tar -xzf g1.tar.gz
# This produces a g1/csv/ directory with session subdirectories
```

#### 3. Convert CSV → motion_lib PKL

```bash
python gear_sonic/data_process/convert_soma_csv_to_motion_lib.py \
    --input /path/to/bones_seed/g1/csv/ \
    --output data/motion_lib_bones_seed/robot \
    --fps 30 --fps_source 120 \
    --individual --num_workers 16
```

This produces one `.pkl` file per motion in `data/motion_lib_bones_seed/robot/`.

#### 4. Filter infeasible motions

```bash
python gear_sonic/data_process/filter_and_copy_bones_data.py \
    --source data/motion_lib_bones_seed/robot \
    --dest data/motion_lib_bones_seed/robot_filtered \
    --workers 16
```

About **8.7%** of motions are filtered out (sitting, cycling, climbing, etc.).

### Result

After processing, your directory structure should look like:

```
data/
├── motion_lib_bones_seed/
│   └── robot_filtered/          # ← symlink to processed data
│       ├── session_001/
│       │   ├── motion_001.pkl
│       │   └── motion_001_M.pkl   # mirrored variant
│       └── ...
└── bones_seed_smpl/             # ← from download_from_hf.py --training
    └── smpl_filtered/
```

### Quick start with sample data (no download needed)

If you just want to verify the pipeline without downloading the full dataset:

```bash
python download_from_hf.py --sample
```

This downloads a single walking sequence (~4 MB) to `sample_data/`.

