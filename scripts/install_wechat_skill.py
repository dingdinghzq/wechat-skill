#!/usr/bin/env python
"""Install the pure WeChat skill runtime on Windows."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


DEPENDENCIES = [
    "pywinauto==0.6.9",
    "PyAutoGUI==0.9.54",
    "pywin32",
    "pywin32-ctypes>=0.2.2",
    "psutil>=5.9.5",
    "pillow>=10.4.0",
    "packaging>=23.2",
    "emoji>=2.14.1",
    "pycaw>=20240210.0",
    "sounddevice>=0.5.1",
    "soundfile>=0.13.1",
]


def run(args: list[str]) -> None:
    print("+", " ".join(str(a) for a in args))
    subprocess.check_call(args)


def remove_legacy_mcp_config(codex_home: Path) -> bool:
    config_path = codex_home / "config.toml"
    if not config_path.exists():
        return False

    text = config_path.read_text(encoding="utf-8")
    pattern = re.compile(r"(?ms)^\[mcp_servers\.wechat\]\n.*?(?=^\[|\Z)")
    new_text, count = pattern.subn("", text)
    if not count:
        return False

    config_path.write_text(new_text.rstrip() + "\n", encoding="utf-8")
    return True


def main() -> None:
    if os.name != "nt":
        raise SystemExit("This installer is for Windows WeChat/Weixin desktop automation.")

    skill_root = Path(__file__).resolve().parents[1]
    vendor_root = skill_root / "vendor" / "pyweixin"
    task_script = skill_root / "scripts" / "wechat_task.py"
    venv_dir = Path(os.environ.get("WECHAT_SKILL_VENV", skill_root / ".venv"))
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))

    if not vendor_root.is_dir():
        raise SystemExit(f"Missing bundled pyweixin source: {vendor_root}")
    if not task_script.exists():
        raise SystemExit(f"Missing task runner: {task_script}")

    if not (venv_dir / "Scripts" / "python.exe").exists():
        run([sys.executable, "-m", "venv", str(venv_dir)])

    python_exe = venv_dir / "Scripts" / "python.exe"
    run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(python_exe), "-m", "pip", "install", "--upgrade", *DEPENDENCIES])
    run([str(python_exe), str(task_script), "import-check"])

    removed_config = remove_legacy_mcp_config(codex_home)
    print(f"Installed skill venv: {venv_dir}")
    print(f"Using bundled source: {vendor_root}")
    if removed_config:
        print(f"Removed legacy [mcp_servers.wechat] from: {codex_home / 'config.toml'}")
    print("Pure WeChat skill is ready. No MCP server or Codex restart is required.")


if __name__ == "__main__":
    main()
