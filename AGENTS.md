# Agent Guidance for GR00T-WholeBodyControl

## Project Overview

This is the official repository for NVIDIA GEAR's **GR00T Whole-Body Control (WBC)** projects. It contains model checkpoints, training/evaluation scripts, and deployment stacks for humanoid robot whole-body controllers. The repository hosts two major systems:

1. **Decoupled WBC** — Decoupled controller (RL for lower body, IK for upper body) used in GR00T N1.5 and N1.6.
2. **GEAR-SONIC Series** — Generalist humanoid whole-body controller based on large-scale motion tracking.

**Contact:** `gear-wbc@nvidia.com`  
**Live docs:** https://nvlabs.github.io/GR00T-WholeBodyControl/

---

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Python runtime** | 3.10+ (3.11 required for Isaac Lab training) |
| **ML framework** | PyTorch >= 2.4.0, HuggingFace TRL 0.28.0, Transformers |
| **Simulation** | Isaac Lab / Isaac Sim (training), MuJoCo (deployment sim bridge) |
| **C++ deployment** | C++20, CMake >= 3.14, TensorRT, ONNX Runtime, CUDA Toolkit |
| **Robot middleware** | ROS 2 Humble (Decoupled WBC), Unitree SDK2 DDS (SONIC deploy), ZMQ (SONIC data collection) |
| **Geometry / IK** | Pinocchio |
| **Dataset format** | LeRobot v2.1 (HuggingFace `datasets`, `parquet` + H.264 MP4) |
| **Documentation** | Sphinx (`sphinx_book_theme`), hosted on GitHub Pages |
| **Task runner** | `just` (C++ build recipes), `make` / `lint.sh` (Python checks) |

---

## Repository Structure

```
GR00T-WholeBodyControl/
├── decoupled_wbc/              # Python package: Decoupled WBC controller
│   ├── control/                #   Core control stack (policies, envs, teleop, sensors, GUI)
│   │   ├── base/               #     Abstract Policy / Env interfaces
│   │   ├── policy/             #     Concrete policies (G1GearWbcPolicy, G1DecoupledWholeBodyPolicy)
│   │   ├── envs/g1/            #     G1Env (real + sim), safety monitor
│   │   ├── robot_model/        #     Pinocchio wrappers (RobotModel, ReducedRobotModel)
│   │   ├── teleop/             #     Device streamers, IK solvers, GUI
│   │   ├── main/teleop/        #     Runtime entry points (control loops, data exporter)
│   │   ├── sensor/             #     Camera sensors (OAK, RealSense)
│   │   └── utils/              #     ROS 2 helpers, telemetry, logging
│   ├── data/                   #   LeRobot-compatible data exporter (Gr00tDataExporter)
│   ├── dexmg/                  #   Dexterous manipulation & RoboCasa environments
│   ├── docker/                 #   Deployment Docker configs (Dockerfile.deploy, entrypoints)
│   ├── scripts/                #   Standalone utilities (deploy_g1.py, webcam recorder)
│   ├── sim2mujoco/             #   MuJoCo simulation bridge for GEAR-WBC policies
│   └── tests/                  #   Pytest suite (mirrors control/ hierarchy)
├── gear_sonic/                 # Python package: SONIC teleoperation, training & sim
│   ├── camera/                 #   Camera server stack (ZMQ streaming)
│   ├── config/                 #   Hydra YAML configs (100+ files: env, rewards, actor/critic)
│   ├── data/                   #   Dataset utilities, robot model assets, exporter
│   ├── data_process/           #   Offline motion preprocessing (SOMA/CSV/BVH → motion lib)
│   ├── envs/                   #   Isaac Lab environment definitions & wrappers
│   ├── isaac_utils/            #   IsaacSim math / rotation helpers
│   ├── scripts/                #   Standalone scripts (sim loop, data exporter, teleop server)
│   ├── trl/                    #   Custom RL framework built on HuggingFace TRL
│   │   ├── modules/            #     Actor/Critic, Universal Token Model, base backbones
│   │   ├── trainer/            #     PPO trainer (with/without aux losses)
│   │   ├── losses/             #     Token-based losses
│   │   ├── callbacks/          #     W&B, model save, motion eval, resampling
│   │   └── utils/              #     GAE, schedulers, SMPL-X lite, rotation conversions
│   └── utils/                  #   Shared utilities (teleop solvers, MuJoCo sim, motion lib)
├── gear_sonic_deploy/          # C++ inference stack for real-robot deployment
│   ├── src/                    #   C++ source code
│   │   ├── TRTInference/       #     TensorRT wrapper library (ONNX → TRT conversion)
│   │   ├── audio_thread/       #     Audio feedback thread (TTS / beep)
│   │   └── g1/                 #     G1-specific code
│   │       └── g1_deploy_onnx_ref/   # Main deployment executable (4-thread real-time)
│   ├── thirdparty/             #   Vendored dependencies (unitree_sdk2)
│   ├── policy/                 #   Model checkpoints & observation YAML configs
│   ├── planner/                #   ONNX locomotion planner models
│   ├── reference/              #   Pre-recorded reference motion CSVs
│   ├── cmake/                  #   Custom Find modules (TensorRT, ONNXRuntime)
│   ├── docker/                 #   Deployment docker configs
│   ├── scripts/                #   Environment setup (deps, ROS2, env vars)
│   ├── deploy.sh               #   User-facing deployment launcher
│   ├── .justfile               #   Build recipes (configure + build + run)
│   └── CMakeLists.txt          #   Main CMake build file
├── external_dependencies/      # External git submodules / vendored deps
│   ├── unitree_sdk2_python/    #   Unitree SDK2 Python bindings
│   └── XRoboToolkit-PC-Service-Pybind_X86_and_ARM64/
├── docs/                       # Sphinx / GitHub Pages documentation
│   ├── source/                 #   RST / Markdown source (English + Chinese `.zh.md`)
│   ├── 算法解析/               #   Algorithm deep-dives (IK, retargeting, action chunking)
│   ├── 数据集讲解/             #   Dataset guides
│   └── requirements.txt        #   Sphinx build dependencies
├── install_scripts/            # One-click setup scripts (MuJoCo, PICO, data collection, ROS)
├── legal/                      # License and attribution files
├── download_from_hf.py         # Download checkpoints from HuggingFace (nvidia/GEAR-SONIC)
├── check_environment.py        # Pre-flight environment verification
├── pyproject.toml              # Root-level tooling config (black, isort, ruff, mypy, pytest)
├── Makefile                    # `run-checks`, `format`, `build`
├── lint.sh                     # Bash wrapper for ruff + black (supports `--fix`)
└── README.md / CITATION.cff    # Project metadata
```

**Note on symlinks:** `logs_eval`, `logs_rl`, and `sonic_release` are symlinks pointing under `/data/wangbin/GR00T-WholeBodyControl_data/`, keeping large artifacts outside the git tree.

---

## Build & Development Setup

### Environment Isolation

The project uses **multiple isolated virtual environments** for different workflows. Install scripts under `install_scripts/` create these automatically with `uv`.

| Workflow | Setup Command | Venv name | Python |
|----------|--------------|-----------|--------|
| MuJoCo simulation | `bash install_scripts/install_mujoco_sim.sh` | `.venv_sim` | 3.10 |
| PICO VR teleop | `bash install_scripts/install_pico.sh` | `.venv_teleop` | 3.10 |
| Data collection | `bash install_scripts/install_data_collection.sh` | `.venv_data_collection` | 3.10 |
| Camera server | `bash install_scripts/install_camera_server.sh` | `.venv_camera` | 3.10 |

All install scripts use `uv` for venv/package management, target Python 3.10, auto-install `uv` if missing, and are designed to run from the repo root.

### Python Packages

Both `decoupled_wbc` and `gear_sonic` are installed **from the repository root** (`where = [".."]` in their `pyproject.toml`). Always run install commands from the repo root.

```bash
# Decoupled WBC (minimal)
pip install -e decoupled_wbc/

# Decoupled WBC (full dependencies: sim, viz, data collection)
pip install -e "decoupled_wbc[full]"

# Decoupled WBC (development: pytest, ruff, black, ipdb)
pip install -e "decoupled_wbc[dev]"

# GEAR-SONIC (teleoperation stack)
pip install -e "gear_sonic[teleop]"

# GEAR-SONIC (MuJoCo simulation)
pip install -e "gear_sonic[sim]"

# GEAR-SONIC (training stack — Isaac Lab must be installed separately)
pip install -e "gear_sonic[training]"

# GEAR-SONIC (camera server)
pip install -e "gear_sonic[camera]"

# GEAR-SONIC (data collection / VLA export)
pip install -e "gear_sonic[data_collection]"
```

**Important:** Training requires **Isaac Lab 2.3+** installed separately (not a pip dependency). It also requires **Python 3.11** (Isaac Lab constraint).

### C++ Deployment Stack (`gear_sonic_deploy`)

- **Requirements:** CMake >= 3.14, C++20, TensorRT (10.13 x86_64 / 10.7 Jetson), ONNX Runtime, `just` command runner.
- **Optional:** ROS 2 Humble, CUDA Toolkit >= 10.2.

**Quick build (native):**
```bash
cd gear_sonic_deploy
./scripts/install_deps.sh          # system deps
source scripts/setup_env.sh        # set TensorRT_ROOT, CUDA, ROS2 paths
just build
```

**Docker (recommended):**
```bash
cd gear_sonic_deploy/docker
./run-ros2-dev.sh                  # mounts ~/TensorRT, auto-builds image
# inside container:
just build
```

**Run:**
```bash
./deploy.sh sim      # MuJoCo Sim2Sim
./deploy.sh real     # Real G1 robot (auto-detects 192.168.123.x subnet)
```

See [Installation Guide](https://nvlabs.github.io/GR00T-WholeBodyControl/getting_started/installation_deploy.html) for detailed instructions.

---

## Code Style & Linting

Configuration is centralized in the root `pyproject.toml`.

| Tool | Setting |
|------|---------|
| **Black** | line-length `100` |
| **isort** | `profile = "black"`, multi-line output `3` |
| **Ruff** | line-length `115`, target Python `3.10`, lint rules `E, F, I` |
| **mypy** | `ignore_missing_imports = true`, `check_untyped_defs = true` (not enforced in CI) |
| **Pyright** | `reportPrivateImportUsage = false` |

### Running Checks

```bash
# Check only
make run-checks
# or
./lint.sh

# Auto-fix
./lint.sh --fix
make format
```

`lint.sh` auto-installs `black` and `ruff` via pip if missing. In fix mode it runs `ruff check --fix .`, `ruff check --select I --fix .`, and `black .`. In check mode it runs the same commands with `--check` flags.

### Excluded paths
- `external_dependencies/` is excluded from **all** Python tooling (black, isort, ruff, mypy, pyright).
- `gear_sonic/dexmg/` is excluded from ruff.
- `*.ipynb` files are excluded from ruff.

### C++ Code Style
- `gear_sonic_deploy` uses `.clang-format` and `.cmake-format.py`.
- Keep C++20 features compatible with the deployment target (Jetson / x86_64 with TensorRT).

---

## Testing

- **Framework:** `pytest`
- **Test directory:** `decoupled_wbc/tests/`
- **Config:** `pyproject.toml` sets `testpaths = "decoupled_wbc/tests/"`, log level `DEBUG`.

```bash
pytest decoupled_wbc/tests/
```

### Test Structure

Tests mirror the `control/` hierarchy:

- `tests/control/main/teleop/test_g1_control_loop.py` — Integration tests (squat, walk, stop, eef tracking). Some marked `@pytest.mark.skip` because "cicd test always gets killed".
- `tests/control/policy/interpolation_policy/` — Unit tests for interpolation policies.
- `tests/control/robot_model/robot_model_test.py` — Pinocchio robot model tests (~911 lines, 30+ test functions).
- `tests/control/teleop/test_teleop_retargeting_ik.py` — Teleop IK tests. Parametrized over mode and side; asserts position error < 1cm, rotation error < 1°.
- `tests/data/test_exporter.py` — LeRobot exporter tests (interrupt/resume, workflow). Requires `ffmpeg`; skipped if unavailable.
- `tests/sim/test_sim_data_collection.py` — Simulation data collection tests. Supports `unit` (50 steps) and `pre_merge` (500 steps + EEF tracking thresholds) modes.

**Note:** There is no automated test runner in CI. The only GitHub Action (`docs.yml`) builds and deploys Sphinx documentation.

---

## Architecture & Key Conventions

### 1. Package Layout

Both `decoupled_wbc` and `gear_sonic` use `where = [".."]` in their `pyproject.toml`. This means they are importable as top-level packages **only when installed from the repo root**. Never import them as nested sub-packages.

```python
# Correct
from decoupled_wbc.control.policy import G1GearWbcPolicy
from gear_sonic.trl.modules import ActorCritic

# Incorrect
from control.policy import G1GearWbcPolicy   # will fail
```

### 2. Decoupled WBC Architecture

The `decoupled_wbc` package implements a **decoupled whole-body controller**:

```
Teleop / Planner / Keyboard
        ↓
[Upper Body Policy]  ←  IK / Interpolation  →  target_upper_body_pose
        ↓                                                    ↓
[G1DecoupledWholeBodyPolicy]  ←  combines both  →  full q
        ↑                                                    ↑
[Lower Body Policy]  ←  RL ONNX policy (gear_wbc)  →  body_action
        ↑
   Observations from G1Env
```

- **`Policy`** (`control/base/policy.py`) — Abstract interface: `set_goal()`, `set_observation()`, `get_action()`.
- **`G1Env`** (`control/envs/g1/g1_env.py`) — Main environment. Supports real robot and simulation. Runs `JointSafetyMonitor` on every `queue_action()`.
- **`RobotModel`** (`control/robot_model/robot_model.py`) — Pinocchio wrapper with FK caching, gravity compensation, and named joint group indexing.
- **`G1GearWbcPolicy`** — Lower-body RL policy. Loads two ONNX models (standing & walking), maintains observation history.
- **`G1DecoupledWholeBodyPolicy`** — Orchestrates upper and lower body. Includes a **1-second safety timeout** for teleop mode.
- **ROS 2 as IPC backbone** — Control loop, teleop, and data collection communicate via ROS 2 topics (e.g., `ControlPolicy/upper_body_pose`, `G1Env/env_state_act`). `ROSManager` wraps `rclpy` initialization.

### 3. SONIC / Universal Token Architecture

`gear_sonic` uses a **multi-encoder / multi-decoder tokenizer** (Action Transform Module):

- **Encoders:** G1 kinematics, SMPL body pose, VR teleop (3-point), SOMA skeleton.
- **Quantizer:** FSQ (Finite Scalar Quantization) — `fsq_level_list: [8,8,8,5,5,5]`.
- **Decoders:** G1 Dynamic Decoder (runtime) + G1 Kinematic Decoder (auxiliary loss only).
- The policy outputs **latent tokens** (e.g., 64-dim) which are decoded into 29-DOF body actions.

The `ManagerEnvWrapper` (`envs/wrapper/manager_env_wrapper.py`) supports three action modes for distillation:
- `residual` — RL policy outputs residual added to ATM encoded tokens (teacher).
- `direct_latent` — Student policy outputs full latent, bypassing encoder.
- `mixed` — Mixed teacher/student rollouts within the same batch.

### 4. ZMQ-Centric Data Flow (SONIC)

Real-robot data collection avoids ROS 2 entirely:
- C++ deploy publishes robot state on **ZMQ port 5557**.
- PICO teleop publishes SMPL pose on **ZMQ port 5556**.
- Camera server publishes frames on **TCP port 5555**.

### 5. Joint Groups Abstraction

Both packages use named joint groups (`"upper_body"`, `"lower_body"`, `"arms"`, `"left_arm"`, etc.) defined in `RobotSupplementalInfo` / `supplemental_info` to slice configuration vectors cleanly.

### 6. Safety-First Design

- `G1Env` runs a `JointSafetyMonitor` on every `queue_action()`.
- The decoupled policy injects safe default navigation commands on teleop timeout.
- C++ deploy has temperature monitoring (warning >= 90°C, clear < 85°C), fall detection (IMU pitch > ±45°), and emergency stop.
- **Idle readaptation** — Double-threshold state machine (IDLE → ADAPTING → RECOVERING) adapts idle pose toward actual robot state to avoid joint drift.

### 7. LeRobot Dataset Compatibility

Data export is built on HuggingFace `datasets` and `lerobot`:
- `Gr00tDataExporter` extends `LeRobotDataset` with video writers, modality configs, and resume-from-interruption support.
- Modality config JSON defines `observation.state`, `observation.images.ego_view`, `action.wbc`, `teleop.smpl_*`, etc.
- Output format: LeRobot v2.1 (`parquet` + H.264 MP4).

### 8. Config-Driven Runtime

Most entry points use **`tyro.cli(SomeConfigDataclass)`** for CLI generation (Decoupled WBC) or **Hydra composition** (SONIC training). Configs live in:
- `decoupled_wbc/control/main/teleop/configs/configs.py` and YAML files (`g1_gear_wbc.yaml`).
- `gear_sonic/config/` — 100+ Hydra YAML fragments for observations, rewards, terminations, events, actor/critic.

### 9. C++ Real-Time Threading Model

`g1_deploy_onnx_ref` runs **4 recurrent threads** via Unitree SDK `CreateRecurrentThreadEx`:

| Thread | Frequency | Responsibility |
|--------|-----------|----------------|
| Input | 100 Hz | Poll active input interface (keyboard / gamepad / ZMQ / ROS2) |
| Control | 50 Hz | Gather observations → run TensorRT/ONNX inference → compute motor targets |
| Planner | 10 Hz | Re-plan locomotion trajectory (27 modes), resampled 30→50 Hz via SLERP + linear interpolation |
| Command Writer | 500 Hz | Publish `LowCmd_` motor commands via DDS |

**State machine:** `INIT → WAIT_FOR_CONTROL → CONTROL`

**Model caching:** TensorRT engines are cached on disk with prefixes (`policy_`, `policy_fp16_`, `encoder_`, etc.) to avoid rebuilding ONNX→TRT on every launch. Cache files include SHA256 hash of ONNX + GPU name + precision.

**Observation system:** YAML-driven via `observation_config.yaml`. Each observation type has a name, dimension, and `ObservationFunction` lambda. Pre-allocated buffers avoid allocations in the control loop.

**Input interface hierarchy:** `InputInterface` → `SimpleKeyboard` / `Gamepad` / `ZMQEndpointInterface` / `ZMQManager` / `GamepadManager` / `InterfaceManager` (composite, allows hot-swapping at runtime) / `ROS2InputHandler` (conditional on `HAS_ROS2`).

**Locomotion planner:** 27 locomotion modes (V2) including IDLE, SLOW_WALK, WALK, RUN, various squats/kneels, CRAWLING, BOXING, punches, jumps, stealth walks, injured walk, ledge walking, object carrying, styled walks (zombie, gun, scare, happy dance). Output is 30 Hz motion sequence resampled to 50 Hz.

**Architecture detection:** The CMake build detects `aarch64`/`arm64` (enables DLA via `cudla`, except on Thor) vs `x86_64`/`amd64` (no DLA).

---

## Security & Safety Considerations

1. **TensorRT Version Mismatch = Dangerous Behavior**
   - Exact versions are **hard requirements**, not recommendations:
     - **x86_64:** TensorRT 10.13
     - **Jetson / JetPack 6:** TensorRT 10.7
   - Using the wrong version produces **silently incorrect inference results** without runtime errors, which can cause dangerous robot behavior.

2. **Modified Robot Deployment**
   - Adding a backpack/box changes mass distribution, CoM, and inertia.
   - **Direct deployment of release checkpoints on modified G1 is unsafe.**
   - Must update simulation models (MuJoCo XML, IsaacLab USD/URDF) with measured physical parameters and retrain/finetune.
   - See `docs/改装G1实机部署工作清单.md` for the full checklist.

3. **Observation Config Mismatch**
   - If adding extra sensors (second IMU, cameras, LiDAR), do **not** modify the 154D ONNX input directly.
   - Must retrain the policy or do sensor fusion outside the policy input.

4. **Network Isolation**
   - G1 communicates via DDS over ethernet (`192.168.123.x` subnet).
   - Multiple G1s in the same lab require DDS Domain ID isolation to prevent command crosstalk.

5. **Git LFS**
   - Mesh files and model assets are LFS-tracked.
   - Without `git lfs pull`, meshes are ~130 byte pointers, causing invisible/broken robots in sim.

6. **Vulnerability Reporting**
   - Report security vulnerabilities through [NVIDIA's coordinated disclosure process](https://www.nvidia.com/en-us/security/) or email `psirt@nvidia.com`. Do not open public issues for security bugs.

---

## Documentation

- **Generator:** Sphinx (`sphinx_book_theme`, NVIDIA/Isaac Lab style)
- **Build:** `cd docs && make html` → output in `docs/build/html/`
- **Deploy:** Auto-deployed to GitHub Pages via `.github/workflows/docs.yml`
- **Prerequisites:** `sphinx`, `sphinx-book-theme`, `sphinx-design`, `sphinxemoji`, `autodocsumm`, `sphinxcontrib-bibtex`, `myst-parser`, `sphinx-copybutton`, `sphinxcontrib-video`

### Chinese Documentation

The repo contains extensive Chinese-language docs under `docs/`:
- `GR00T-SONIC 完整技术文档.md` — Full technical doc (dataset → pretraining → training → eval → ONNX export → deployment)
- `GR00T-WholeBodyControl 安装与复现手册.md` — Step-by-step installation guide
- `GR00T-WholeBodyControl 项目文件结构详解.md` — Project file structure deep dive
- `docs/算法解析/` — Algorithm deep-dives (IK, SMPL→G1 retargeting, action chunking)
- `docs/数据集讲解/` — Dataset guides and comparisons
- Many files inside `docs/source/` have `.zh.md` sidecar translations.

---

## Common Tasks

### Download Checkpoints

```bash
python download_from_hf.py                    # ONNX models for deployment
python download_from_hf.py --training          # PyTorch checkpoint + SMPL data
python download_from_hf.py --sample            # Sample data only (quick start)
```

### Environment Verification

```bash
python check_environment.py              # Check everything
python check_environment.py --training   # Training checks only
python check_environment.py --deploy     # Deployment checks only
```

### Run Teleoperation (Decoupled WBC)

```bash
# Unified one-click deployment (tmux)
python decoupled_wbc/scripts/deploy_g1.py

# Or run individual loops
python decoupled_wbc/control/main/teleop/run_g1_control_loop.py
python decoupled_wbc/control/main/teleop/run_teleop_policy_loop.py
```

### Run Teleoperation (GEAR-SONIC)

```bash
# PICO VR teleop server
python gear_sonic/scripts/pico_manager_thread_server.py

# All-in-one tmux launcher (C++ deploy + teleop + exporter + camera)
python gear_sonic/scripts/launch_data_collection.py
```

### Run Simulation

```bash
# GEAR-SONIC MuJoCo sim
python gear_sonic/scripts/run_sim_loop.py

# Decoupled WBC MuJoCo sim
python decoupled_wbc/sim2mujoco/scripts/run_mujoco_gear_wbc.py
```

### Run Training

```bash
# Requires Isaac Lab installed separately + Python 3.11
python gear_sonic/train_agent_trl.py
```

### Build Documentation

```bash
cd docs && make html
```

---

## License Notes

- **Source Code:** Apache License 2.0
- **Model Weights / Checkpoints:** NVIDIA Open Model License
- Always check the `/legal` folder and `LICENSE` file before redistributing.

---

## Quick Reference

| Need to... | Command / Location |
|-----------|-------------------|
| Install minimal Python deps | `pip install -e decoupled_wbc/` |
| Install full dev deps | `pip install -e "decoupled_wbc[dev]"` |
| Install SONIC training deps | `pip install -e "gear_sonic[training]"` |
| Run Python linter / formatter | `make run-checks` / `./lint.sh --fix` |
| Run tests | `pytest decoupled_wbc/tests/` |
| Build C++ deploy | `cd gear_sonic_deploy && just build` |
| Deploy on real robot | `cd gear_sonic_deploy && ./deploy.sh real` |
| Deploy in sim | `cd gear_sonic_deploy && ./deploy.sh sim` |
| Download models | `python download_from_hf.py` |
| Verify env | `python check_environment.py` |
| Build docs | `cd docs && make html` |
| Pull LFS assets | `git lfs pull` |
