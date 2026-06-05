# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Primary Reference

A detailed, up-to-date guide already lives at [AGENTS.md](AGENTS.md). It covers the technology stack, repo layout, install/build commands, code style, tests, architecture, and security considerations in depth. **Read it before starting any non-trivial task** — the notes below only add Claude-Code-specific guidance and surface the highest-leverage details.

## High-Level Architecture

This is NVIDIA GEAR's repository for **GR00T Whole-Body Control** — humanoid robot controllers. Three independent subsystems live side by side:

1. **`decoupled_wbc/`** — Python package. Decoupled controller (RL lower body + IK upper body) used in GR00T N1.5 / N1.6. ROS 2-based IPC.
2. **`gear_sonic/`** — Python package. Generalist motion-tracking foundation policy (SONIC). Hydra configs, custom RL on top of HuggingFace TRL, Isaac Lab training. ZMQ-based IPC at runtime.
3. **`gear_sonic_deploy/`** — C++20 + TensorRT real-time inference stack for real-robot deployment. 4-thread architecture (Input 100 Hz, Control 50 Hz, Planner 10 Hz, Command Writer 500 Hz). Built with `just` + CMake.

A standalone educational `simple_planner/` (PyTorch Transformer motion-completion) is **not** part of the deploy stack.

## Repo-Specific Quirks That Bite

These are non-obvious things that have caused issues — apply them defensively:

- **Both Python packages install from the repo root.** Both `decoupled_wbc/pyproject.toml` and `gear_sonic/pyproject.toml` set `where = [".."]`. Always run `pip install -e decoupled_wbc/` (or `gear_sonic/`) **from the repo root**, and import as top-level packages: `from decoupled_wbc.control.policy import ...`, never `from control.policy import ...`.
- **Multiple isolated venvs by workflow.** The project does *not* use one venv. `install_scripts/install_*.sh` create `.venv_sim`, `.venv_teleop`, `.venv_data_collection`, `.venv_camera` separately via `uv`. Training requires Isaac Lab (Python 3.11) installed separately.
- **TensorRT version is a hard requirement, not a recommendation.** x86_64 needs **TensorRT 10.13**; Jetson/JetPack 6 needs **10.7**. Wrong version → silently incorrect inference → unsafe robot behavior. Don't relax this.
- **Git LFS.** Meshes and ONNX models are LFS-tracked. Without `git lfs pull`, you get ~130-byte pointers and silent failures (invisible robot in sim, broken inference). `docs/source/_static/**` is intentionally excluded from LFS — don't "fix" that exclusion.
- **`gear_sonic/train_agent_trl.py` has a `sys.path` manipulation at the top** to ensure HuggingFace `trl` is imported instead of the local `gear_sonic/trl/` directory. Do not remove it.
- **Symlinks for large artifacts.** `logs_eval/`, `logs_rl/`, `sonic_release/` are symlinks under `/data/wangbin/GR00T-WholeBodyControl_data/`. Don't try to git-add their contents.
- **No tests under `gear_sonic/`.** All Python tests live in `decoupled_wbc/tests/` (configured in root `pyproject.toml`). The only CI workflow (`.github/workflows/docs.yml`) just builds Sphinx docs.
- **`external_dependencies/` is excluded from black/isort/ruff/mypy/pyright.** `gear_sonic/dexmg/` and `*.ipynb` are excluded from ruff. Don't reformat them.
- **ZMQ ports are fixed protocol.** Robot state on 5557, PICO SMPL on 5556, camera frames on 5555. The 2026-03-24 update changed ZMQ header size to 1280 bytes — don't assume older protocol.

## Common Commands

| Need to... | Command |
|-----------|---------|
| Lint check | `make run-checks` or `./lint.sh` |
| Lint auto-fix | `./lint.sh --fix` or `make format` |
| Run Python tests | `pytest decoupled_wbc/tests/` |
| Run a single test | `pytest decoupled_wbc/tests/control/robot_model/robot_model_test.py::test_name` |
| Build C++ deploy | `cd gear_sonic_deploy && just build` |
| Deploy on robot | `cd gear_sonic_deploy && ./deploy.sh real` |
| Deploy in MuJoCo | `cd gear_sonic_deploy && ./deploy.sh sim` |
| Verify environment | `python check_environment.py` (`--training` / `--deploy` to scope) |
| Download checkpoints | `python download_from_hf.py` (`--training` / `--sample`) |
| Build docs | `cd docs && make html` |

Linter config lives in the root `pyproject.toml`: black line-length **100**, ruff line-length **115** (target `py310`), ruff lint rules `E, F, I`. C++ uses `.clang-format` (ColumnLimit 120).

## Working in This Repo

- **Safety-critical code.** This codebase drives a physical humanoid (Unitree G1). Changes to `G1Env`, `JointSafetyMonitor`, the C++ control loop, or model checkpoints can cause real-world harm. When in doubt about a change to the deploy stack, ask before acting.
- **Modified hardware needs retraining.** Backpack/payload changes mass/CoM/inertia. Don't suggest deploying release checkpoints on modified G1 — point users to `g1_backpack_urdf_example.md` and the retraining flow.
- **Config-driven runtime.** Most entry points use `tyro.cli(SomeConfigDataclass)` (Decoupled WBC) or Hydra composition (SONIC training, 100+ YAML fragments under `gear_sonic/config/`). Prefer adding/overriding config fields rather than threading new arguments through call sites.
- **Joint-group abstraction.** Both packages slice configuration vectors via named groups (`"upper_body"`, `"lower_body"`, `"arms"`, `"left_arm"`, ...) defined in `RobotSupplementalInfo` / `supplemental_info`. Use them instead of hardcoded indices.
- **Chinese-language docs are first-class.** Many files in `docs/` and `.zh.md` sidecars contain detail that English docs do not. When researching a topic, search both languages.
