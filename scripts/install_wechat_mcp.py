#!/usr/bin/env python
"""Install the bundled WeChat MCP server for Codex on Windows."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


PACKAGE = "mcp_server_wechat==0.8"
VENDORED_PACKAGES = ("mcp_server_wechat", "pyweixin")


def run(args: list[str]) -> None:
    print("+", " ".join(str(a) for a in args))
    subprocess.check_call(args)


def copy_vendor_package(vendor_root: Path, site_packages: Path, package_name: str) -> None:
    source = vendor_root / package_name
    target = site_packages / package_name
    if not source.is_dir():
        raise RuntimeError(f"Missing bundled package: {source}")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def update_codex_config(codex_home: Path, python_exe: Path, history_dir: Path) -> None:
    config_path = codex_home / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    block = (
        "[mcp_servers.wechat]\n"
        f"args = [\"-m\", \"mcp_server_wechat\", \"--folder-path={history_dir.as_posix()}\"]\n"
        f"command = '{str(python_exe)}'\n"
        "startup_timeout_sec = 120\n"
    )

    text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    pattern = re.compile(r"(?ms)^\[mcp_servers\.wechat\]\n.*?(?=^\[|\Z)")
    if pattern.search(text):
        text = pattern.sub(lambda _match: block + "\n", text).rstrip() + "\n"
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\n" + block
    config_path.write_text(text, encoding="utf-8")


def main() -> None:
    if os.name != "nt":
        raise SystemExit("This installer is for Windows WeChat/Weixin desktop automation.")

    script_dir = Path(__file__).resolve().parent
    skill_root = script_dir.parent
    vendor_root = skill_root / "vendor"
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    mcp_root = codex_home / "mcp" / "mcp_server_wechat"
    venv_dir = mcp_root / "venv"
    history_dir = mcp_root / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    if not (venv_dir / "Scripts" / "python.exe").exists():
        run([sys.executable, "-m", "venv", str(venv_dir)])

    python_exe = venv_dir / "Scripts" / "python.exe"
    run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(python_exe), "-m", "pip", "install", "--upgrade", PACKAGE])

    site_packages_raw = subprocess.check_output(
        [
            str(python_exe),
            "-c",
            "import sysconfig; print(sysconfig.get_paths()['purelib'])",
        ],
        text=True,
    ).strip()
    site_packages = Path(site_packages_raw)

    for package_name in VENDORED_PACKAGES:
        copy_vendor_package(vendor_root, site_packages, package_name)

    update_codex_config(codex_home, python_exe, history_dir)

    subprocess.check_call(
        [
            str(python_exe),
            "-c",
            "from mcp_server_wechat.WechatServer import WeChatServer; "
            "from mcp_server_wechat.WechatClient import Messages, Navigator; "
            "print('IMPORT_OK')",
        ]
    )
    print(f"Installed MCP venv: {venv_dir}")
    print(f"Copied bundled source from: {vendor_root}")
    print(f"Updated Codex config: {codex_home / 'config.toml'}")
    print("Restart Codex to load the wechat MCP server.")


if __name__ == "__main__":
    main()
