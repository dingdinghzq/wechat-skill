#!/usr/bin/env python
"""Install and patch the local WeChat MCP server for Codex on Windows."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


PACKAGE = "mcp_server_wechat==0.8"


def run(args: list[str]) -> None:
    print("+", " ".join(str(a) for a in args))
    subprocess.check_call(args)


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Could not find expected text in {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_wechat_client(site_packages: Path) -> None:
    path = site_packages / "mcp_server_wechat" / "WechatClient.py"
    backup = path.with_suffix(path.suffix + ".codex-backup")
    if not backup.exists():
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    replace_once(
        path,
        "from pywechat import Systemsettings, NotFolderError, Tools, NoChatHistoryError\n"
        "from pywechat.WechatAuto import Messages",
        "from pyweixin import SystemSettings as Systemsettings, Tools, Navigator\n"
        "from pyweixin.Errors import NotFolderError, NoChatHistoryError\n"
        "from pyweixin.WeChatAuto import Messages",
    )
    replace_once(
        path,
        "if not Systemsettings.is_dirctory(folder_path):",
        "if not os.path.isdir(folder_path):",
    )
    replace_once(
        path,
        "chat_history_result = Tools.open_chat_history(friend=friend, wechat_path=wechat_path, is_maximize=is_maximize,\n"
        "                                                          close_wechat=close_wechat, search_pages=search_pages)",
        "chat_history_result = Navigator.open_chat_history(friend=friend, wechat_path=wechat_path, is_maximize=is_maximize,\n"
        "                                                              close_wechat=close_wechat, search_pages=search_pages)",
    )
    replace_once(
        path,
        "chat_history_result = Tools.open_chat_history(friend=friend, is_maximize=is_maximize,\n"
        "                                                          close_weixin=close_wechat, search_pages=search_pages)",
        "chat_history_result = Navigator.open_chat_history(friend=friend, is_maximize=is_maximize,\n"
        "                                                              close_weixin=close_wechat, search_pages=search_pages)",
    )

    text = path.read_text(encoding="utf-8")
    text = text.replace("delay=delay,", "send_delay=delay,")
    text = text.replace(
        "Messages.send_message_to_friends(\n"
        "                friends=friends,\n"
        "                message=message\n"
        "            )",
        "if isinstance(message, list):\n"
        "                messages = [[item] for item in message]\n"
        "            else:\n"
        "                messages = [[message] for _ in friends]\n"
        "            Messages.send_messages_to_friends(\n"
        "                friends=friends,\n"
        "                messages=messages,\n"
        "                send_delay=delay\n"
        "            )",
    )
    text = text.replace(
        "Messages.send_messages_to_friends(\n"
        "                friends=friends,\n"
        "                messages=messages\n"
        "            )",
        "Messages.send_messages_to_friends(\n"
        "                friends=friends,\n"
        "                messages=messages,\n"
        "                send_delay=delay\n"
        "            )",
    )
    path.write_text(text, encoding="utf-8")


def patch_pyweixin(site_packages: Path) -> None:
    tools = site_packages / "pyweixin" / "WeChatTools.py"
    backup = tools.with_suffix(tools.suffix + ".codex-backup")
    if not backup.exists():
        backup.write_text(tools.read_text(encoding="utf-8"), encoding="utf-8")
    replace_once(
        tools,
        "hwnd=win32gui.FindWindow('Qt51514QWindowIcon','微信')\n"
        "        if hwnd==0:hwnd=win32gui.FindWindow('Qt51514QWindowIcon','Weixin')",
        "hwnd=win32gui.FindWindow('Qt51514QWindowIcon','微信')\n"
        "        if hwnd==0:hwnd=win32gui.FindWindow('Qt51514QWindowIcon','WeChat')\n"
        "        if hwnd==0:hwnd=win32gui.FindWindow('Qt51514QWindowIcon','Weixin')",
    )

    ui = site_packages / "pyweixin" / "Uielements.py"
    backup = ui.with_suffix(ui.suffix + ".codex-backup")
    if not backup.exists():
        backup.write_text(ui.read_text(encoding="utf-8"), encoding="utf-8")
    text = ui.read_text(encoding="utf-8")
    text = text.replace(
        "self.Weixin={'title':'微信','control_type':'Button','class_name':\"mmui::XTabBarItem\"}",
        "self.Weixin={'title_re':'微信|Weixin|WeChat','control_type':'Button','class_name':\"mmui::XTabBarItem\"}",
    )
    text = text.replace(
        "self.Weixin={'title':'Weixin','control_type':'Button','class_name':\"mmui::XTabBarItem\"}",
        "self.Weixin={'title_re':'微信|Weixin|WeChat','control_type':'Button','class_name':\"mmui::XTabBarItem\"}",
    )
    ui.write_text(text, encoding="utf-8")


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

    patch_wechat_client(site_packages)
    patch_pyweixin(site_packages)
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
    print(f"Updated Codex config: {codex_home / 'config.toml'}")
    print("Restart Codex to load the wechat MCP server.")


if __name__ == "__main__":
    main()
