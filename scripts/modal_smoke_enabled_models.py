from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from token_holdem.agents import ROSTER
from token_holdem.model_runtime import configured_modal_model_names


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test Modal inference for enabled Token Hold'em model seats.")
    parser.add_argument("--run", action="store_true", help="Run commands instead of printing them.")
    args = parser.parse_args()

    enabled = configured_modal_model_names()
    names = [profile.name for profile in ROSTER if profile.name in enabled]
    if not names:
        raise SystemExit("No Modal models are enabled by TOKEN_HOLDEM_MODAL_MODEL_NAMES.")

    for name in names:
        command = ["uv", "run", "modal", "run", "modal_inference.py::smoke", "--model-name", name]
        if args.run:
            subprocess.run(command, check=True)
        else:
            print(" ".join(command))


if __name__ == "__main__":
    main()
