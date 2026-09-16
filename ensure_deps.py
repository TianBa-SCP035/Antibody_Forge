"""Fill missing Python / frontend packages listed in lockfiles. Used by start_dev.sh/.bat."""

from __future__ import annotations

import hashlib
import importlib.metadata as metadata
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIREMENTS = ROOT / "bbctg_vita_server" / "requirements.txt"
WEB_ROOT = ROOT / "bbctg_vita_web"
PNPM_LOCK = WEB_ROOT / "pnpm-lock.yaml"
NODE_MODULES = WEB_ROOT / "node_modules"
LOCK_STAMP = NODE_MODULES / ".antibody-forge-pnpm-lock.sha256"


def _requirement_specs() -> list[tuple[str, str]]:
    specs: list[tuple[str, str]] = []
    for raw in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        name = line.split(";", 1)[0].strip().split("[", 1)[0]
        for sep in ("===", "==", ">=", "<=", "!=", "~=", ">", "<"):
            if sep in name:
                name = name.split(sep, 1)[0]
                break
        name = name.strip()
        if name:
            specs.append((name, line))
    return specs


def _missing_python_specs() -> list[str]:
    missing: list[str] = []
    for name, spec in _requirement_specs():
        try:
            metadata.version(name)
        except metadata.PackageNotFoundError:
            missing.append(spec)
    return missing


def _ensure_python() -> None:
    missing = _missing_python_specs()
    if not missing:
        print("Python packages OK")
        return
    print("Installing missing Python packages: " + ", ".join(missing))
    subprocess.run(
        [sys.executable, "-m", "pip", "install", *missing],
        check=True,
    )


def _lock_fingerprint() -> str:
    return hashlib.sha256(PNPM_LOCK.read_bytes()).hexdigest()


def _write_lock_stamp(fingerprint: str) -> None:
    NODE_MODULES.mkdir(parents=True, exist_ok=True)
    LOCK_STAMP.write_text(fingerprint + "\n", encoding="utf-8")


def _ensure_frontend() -> None:
    pnpm = shutil.which("pnpm")
    if not pnpm:
        raise FileNotFoundError("pnpm not found on PATH")

    fingerprint = _lock_fingerprint() if PNPM_LOCK.is_file() else ""
    recorded = (
        LOCK_STAMP.read_text(encoding="utf-8").strip()
        if LOCK_STAMP.is_file()
        else ""
    )
    if NODE_MODULES.is_dir() and recorded == fingerprint:
        print("Frontend packages OK")
        return
    if NODE_MODULES.is_dir() and not recorded and fingerprint:
        _write_lock_stamp(fingerprint)
        print("Frontend packages OK")
        return

    print("Installing frontend packages from pnpm-lock.yaml")
    cmd = [pnpm, "install"]
    if PNPM_LOCK.is_file():
        cmd.append("--frozen-lockfile")
    subprocess.run(cmd, cwd=WEB_ROOT, check=True)
    if fingerprint:
        _write_lock_stamp(fingerprint)


def main() -> int:
    _ensure_python()
    _ensure_frontend()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    except subprocess.CalledProcessError as exc:
        print(f"Dependency install failed with exit code {exc.returncode}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
