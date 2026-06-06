"""Run the test suite and CLI smoke check across Python versions."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

DEFAULT_VERSIONS = ("3.11", "3.12", "3.13", "3.14", "3.15")


def main() -> None:
    """Run compatibility checks for requested Python versions."""
    args = _parse_args()
    root = Path(__file__).resolve().parents[1]
    for version in args.versions:
        if _python_unavailable(version) and args.skip_missing:
            print(f"Skipping Python {version}: not available to uv")
            continue
        _run_for_version(root, version)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("versions", nargs="*", default=DEFAULT_VERSIONS)
    parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="Skip versions uv cannot find instead of failing.",
    )
    return parser.parse_args()


def _python_unavailable(version: str) -> bool:
    """Return whether uv cannot find or download the requested Python."""
    result = subprocess.run(
        ["uv", "python", "find", version],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode != 0


def _run_for_version(root: Path, version: str) -> None:
    """Run project checks for one Python version."""
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env["UV_PROJECT_ENVIRONMENT"] = str(root / ".compat-venvs" / f"py{version}")
    env["UV_LINK_MODE"] = "copy"
    print(f"Testing Python {version}")
    _run(["uv", "sync", "--python", version], root, env)
    _run(["uv", "run", "--python", version, "pytest"], root, env)
    _run(
        ["uv", "run", "--python", version, "subtitle-srt-translator", "--help"],
        root,
        env,
    )


def _run(command: list[str], root: Path, env: dict[str, str]) -> None:
    """Run a subprocess command from the project root."""
    executable = shutil.which(command[0])
    if executable is None:
        raise RuntimeError(f"Required command not found: {command[0]}")
    subprocess.run(command, cwd=root, env=env, check=True)


if __name__ == "__main__":
    main()
