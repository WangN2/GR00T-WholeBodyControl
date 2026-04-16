# Agent Guidance for GR00T-WholeBodyControl

## Project Overview

This is the official repository for NVIDIA GEAR's **GR00T Whole-Body Control (WBC)** projects. It contains model checkpoints, training/evaluation scripts, and deployment stacks for humanoid robot whole-body controllers. The repository hosts two major systems:

1. **Decoupled WBC**: Decoupled controller (RL for lower body, IK for upper body) used in GR00T N1.5 and N1.6.
2. **GEAR-SONIC Series**: Generalist humanoid whole-body controller based on large-scale motion tracking.

## Repository Structure

```
GR00T-WholeBodyControl/
├── decoupled_wbc/          # Python package: Decoupled WBC controller
│   ├── control/            #   Controller logic, teleop, GUI, CLI
│   ├── data/               #   Data utilities
│   ├── dexmg/              #   Dexterous manipulation related
│   ├── docker/             #   Docker configs
│   ├── scripts/            #   Standalone scripts
│   ├── sim2mujoco/         #   MuJoCo simulation utilities
│   └── tests/              #   Pytest suite
├── gear_sonic/             # Python package: SONIC teleoperation & sim
│   ├── data/               #   Data loading and processing
│   ├── isaac_utils/        #   Isaac Lab / Isaac Sim utilities
│   ├── scripts/            #   Standalone scripts
│   ├── trl/                #   TRL / training related code
│   └── utils/              #   General utilities
├── gear_sonic_deploy/      # C++ inference stack for real-robot deployment
│   ├── src/                #   C++ source code
│   ├── g1/                 #   Unitree G1 robot specific code
│   ├── policy/             #   Policy inference wrappers
│   ├── thirdparty/         #   Vendored C++ dependencies
│   ├── docker/             #   Deployment docker configs
│   └── CMakeLists.txt      #   Main CMake build file
├── external_dependencies/  # External git submodules / vendored deps
├── docs/                   # Sphinx / GitHub Pages documentation source
├── install_scripts/        # Setup scripts (Leap SDK, MuJoCo, PICO, ROS)
├── legal/                  # License and attribution files
├── download_from_hf.py     # Helper to download checkpoints from HuggingFace
└── pyproject.toml          # Root-level tooling config (black, isort, ruff, mypy)
```

## Build & Development Setup

### Python Environment
- **Python version**: `~=3.10.0`
- **Recommended**: Use a dedicated virtual environment.

### Installing Packages
```bash
# Decoupled WBC (minimal)
pip install -e decoupled_wbc/

# Decoupled WBC (full dependencies for sim, visualization, data collection)
pip install -e "decoupled_wbc[full]"

# Decoupled WBC (development)
pip install -e "decoupled_wbc[dev]"

# GEAR-SONIC (teleoperation stack)
pip install -e "gear_sonic[teleop]"

# GEAR-SONIC (MuJoCo simulation)
pip install -e "gear_sonic[sim]"
```

### C++ Deployment Stack (`gear_sonic_deploy`)
- Requires **CMake >= 3.14**, **C++20**, **TensorRT**, **ONNXRuntime**, and optionally **CUDA Toolkit**.
- Build steps are managed by `gear_sonic_deploy/deploy.sh` and `CMakeLists.txt`.
- See the [Installation Guide](https://nvlabs.github.io/GR00T-WholeBodyControl/getting_started/installation_deploy.html) for detailed instructions.

## Code Style & Linting

Configuration is centralized in the root `pyproject.toml`.

- **Formatter**: `black` (line-length `100`)
- **Import sorting**: `isort` (black-compatible profile)
- **Linter**: `ruff` (line-length `115`, target Python 3.10)
- **Type checker**: `mypy` (configured but not enforced in CI)

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

### Excluded paths
- `external_dependencies/` is excluded from all Python tooling.
- `gear_sonic/dexmg/` is excluded from ruff.

## Testing

- **Framework**: `pytest`
- **Test directory**: `decoupled_wbc/tests/`
- Run tests with:
  ```bash
  pytest decoupled_wbc/tests/
  ```

## Important Conventions

### Package Layout
- Both `decoupled_wbc` and `gear_sonic` are installed **from the repository root** (`where = [".."]` in their `pyproject.toml`).
- When importing, treat `decoupled_wbc` and `gear_sonic` as top-level packages.

### C++ Code Style
- `gear_sonic_deploy` uses `.clang-format` and `.cmake-format.py`.
- Keep C++20 features compatible with the deployment target (Jetson / x86_64 with TensorRT).

### Git LFS
- The repository uses Git LFS for media and model assets. After cloning, run:
  ```bash
  git lfs pull
  ```

## Common Tasks

### Download checkpoints
```bash
python download_from_hf.py
```

### Run teleoperation (GEAR-SONIC)
Refer to `gear_sonic/scripts/` and the [VR Teleoperation Setup docs](https://nvlabs.github.io/GR00T-WholeBodyControl/getting_started/vr_teleop_setup.html).

### Run simulation
Look for `run_sim_loop.py` or similar scripts inside `gear_sonic/scripts/` and `decoupled_wbc/scripts/`.

### Build documentation
Docs are built with Sphinx under `docs/` (see `docs/Makefile`).

## License Notes

- **Source Code**: Apache License 2.0
- **Model Weights / Checkpoints**: NVIDIA Open Model License
- Always check the `/legal` folder and `LICENSE` file before redistributing.
