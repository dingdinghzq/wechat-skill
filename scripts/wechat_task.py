#!/usr/bin/env python
"""Direct task runner for the WeChat skill."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def add_vendor_to_path() -> Path:
    skill_root = Path(__file__).resolve().parents[1]
    vendor_root = skill_root / "vendor"
    sys.path.insert(0, str(vendor_root))
    return vendor_root


def load_pyweixin():
    add_vendor_to_path()
    from pyweixin.WeChatAuto import Contacts, FriendSettings, Messages

    return Contacts, FriendSettings, Messages


def bool_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--maximize", action="store_true", help="Maximize the WeChat window.")
    parser.add_argument("--close-weixin", action="store_true", help="Close WeChat when the task finishes.")


def common_ui_args(parser: argparse.ArgumentParser, *, search_pages: int = 0) -> None:
    parser.add_argument("--search-pages", type=int, default=search_pages)
    bool_arg(parser)


def write_json(data: Any, out: str | None = None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if out:
        path = Path(out).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    print(text)


def parse_list(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    parts = value.replace("，", ",").replace("；", ",").replace(";", ",").split(",")
    return [part.strip() for part in parts if part.strip()]


def numeric_suffix(path: Path) -> tuple[int, str]:
    digits = ""
    for char in reversed(path.stem):
        if char.isdigit():
            digits = char + digits
        elif digits:
            break
    return (int(digits) if digits else 999_999, path.name)


def default_output_dir(kind: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return (Path.cwd() / "wechat_outputs" / f"{kind}_{stamp}").resolve()


def command_import_check(args: argparse.Namespace) -> int:
    Contacts, FriendSettings, Messages = load_pyweixin()
    write_json(
        {
            "status": "ok",
            "imports": [
                Contacts.__name__,
                FriendSettings.__name__,
                Messages.__name__,
            ],
        }
    )
    return 0


def command_readiness(args: argparse.Namespace) -> int:
    import psutil
    import winreg

    processes = []
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        info = proc.info
        if (info.get("name") or "").lower() == "weixin.exe":
            processes.append(info)

    registry_ok = False
    registry_error = None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Tencent\Weixin"):
            registry_ok = True
    except OSError as exc:
        registry_error = str(exc)

    write_json(
        {
            "status": "ok" if processes and registry_ok else "not_ready",
            "weixin_processes": processes,
            "registry_ok": registry_ok,
            "registry_error": registry_error,
        }
    )
    return 0 if processes and registry_ok else 1


def command_send_message(args: argparse.Namespace) -> int:
    _, _, Messages = load_pyweixin()
    Messages.send_messages_to_friend(
        friend=args.to,
        messages=[args.message],
        search_pages=args.search_pages,
        send_delay=args.delay,
        is_maximize=args.maximize,
        close_weixin=args.close_weixin,
    )
    write_json({"status": "ok", "action": "send-message", "to": args.to, "count": 1})
    return 0


def command_send_messages(args: argparse.Namespace) -> int:
    _, _, Messages = load_pyweixin()
    Messages.send_messages_to_friend(
        friend=args.to,
        messages=args.message,
        search_pages=args.search_pages,
        send_delay=args.delay,
        is_maximize=args.maximize,
        close_weixin=args.close_weixin,
    )
    write_json({"status": "ok", "action": "send-messages", "to": args.to, "count": len(args.message)})
    return 0


def command_send_to_many(args: argparse.Namespace) -> int:
    _, _, Messages = load_pyweixin()
    friends = parse_list(args.to)
    messages = parse_list(args.message)
    if len(messages) == 1:
        message_lists = [[messages[0]] for _ in friends]
    elif len(messages) == len(friends):
        message_lists = [[message] for message in messages]
    else:
        raise ValueError("--message must contain one message or the same count as --to")

    Messages.send_messages_to_friends(
        friends=friends,
        messages=message_lists,
        send_delay=args.delay,
        is_maximize=args.maximize,
        close_weixin=args.close_weixin,
    )
    write_json({"status": "ok", "action": "send-to-many", "to": friends, "count": len(friends)})
    return 0


def command_common_groups(args: argparse.Namespace) -> int:
    _, FriendSettings, _ = load_pyweixin()
    groups = FriendSettings.get_common_groups(
        friend=args.member,
        search_pages=args.search_pages,
        is_maximize=args.maximize,
        close_weixin=args.close_weixin,
    )
    write_json({"status": "ok", "member": args.member, "groups": groups, "count": len(groups)}, args.out)
    return 0


def command_group_members(args: argparse.Namespace) -> int:
    Contacts, _, _ = load_pyweixin()
    members = Contacts.get_groupMembers_info(
        group=args.group,
        search_pages=args.search_pages,
        is_maximize=args.maximize,
        close_weixin=args.close_weixin,
    )
    write_json({"status": "ok", "group": args.group, "members": members, "count": len(members)}, args.out)
    return 0


def command_dump_chat(args: argparse.Namespace) -> int:
    _, _, Messages = load_pyweixin()
    records = Messages.dump_chat_history(
        friend=args.chat,
        number=args.number,
        search_content=args.search_content,
        is_json=False,
        save_detail=args.save_detail,
        target_folder=args.detail_dir,
        search_pages=args.search_pages,
        is_maximize=args.maximize,
        close_weixin=args.close_weixin,
    )
    if isinstance(records, tuple) and len(records) == 3 and all(isinstance(item, list) for item in records):
        records = records[0]
    elif not isinstance(records, list):
        records = list(records)
    payload = {"status": "ok", "chat": args.chat, "count": len(records), "records": records}
    write_json(payload, args.out)
    return 0


def command_pull_messages(args: argparse.Namespace) -> int:
    _, _, Messages = load_pyweixin()
    records = Messages.pull_messages(
        friend=args.chat,
        number=args.number,
        search_pages=args.search_pages,
        is_maximize=args.maximize,
        close_weixin=args.close_weixin,
    )
    payload = {"status": "ok", "chat": args.chat, "count": len(records), "records": records}
    write_json(payload, args.out)
    return 0


def command_save_media(args: argparse.Namespace) -> int:
    _, _, Messages = load_pyweixin()
    out_dir = Path(args.out).expanduser().resolve() if args.out else default_output_dir("media")
    out_dir.mkdir(parents=True, exist_ok=True)
    Messages.save_media(
        friend=args.chat,
        number=args.number,
        target_folder=str(out_dir),
        search_pages=args.search_pages,
        is_maximize=args.maximize,
        close_weixin=args.close_weixin,
    )
    files = sorted([str(path) for path in out_dir.iterdir() if path.is_file()])
    write_json({"status": "ok", "chat": args.chat, "out": str(out_dir), "count": len(files), "files": files})
    return 0


def command_save_images(args: argparse.Namespace) -> int:
    _, _, Messages = load_pyweixin()
    image_dir = Path(args.out).expanduser().resolve() if args.out else default_output_dir("images")
    raw_dir = Path(args.raw).expanduser().resolve() if args.raw else image_dir.parent / f"{image_dir.name}_raw"
    image_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    scan_number = args.scan_number if args.scan_number is not None else max(args.number * 3, args.number)
    Messages.save_media(
        friend=args.chat,
        number=scan_number,
        target_folder=str(raw_dir),
        search_pages=args.search_pages,
        is_maximize=args.maximize,
        close_weixin=args.close_weixin,
    )

    candidates = sorted(
        [path for path in raw_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS],
        key=numeric_suffix,
    )[: args.number]
    copied = []
    for index, src in enumerate(candidates, 1):
        dst = image_dir / f"recent_image_{index:02d}{src.suffix.lower()}"
        shutil.copy2(src, dst)
        copied.append(str(dst))

    write_json(
        {
            "status": "ok",
            "chat": args.chat,
            "requested": args.number,
            "count": len(copied),
            "image_dir": str(image_dir),
            "raw_dir": str(raw_dir),
            "files": copied,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run WeChat desktop automation tasks directly.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("import-check")
    p.set_defaults(func=command_import_check)

    p = subparsers.add_parser("readiness")
    p.set_defaults(func=command_readiness)

    p = subparsers.add_parser("send-message")
    p.add_argument("--to", required=True)
    p.add_argument("--message", required=True)
    p.add_argument("--delay", type=float, default=0.5)
    common_ui_args(p)
    p.set_defaults(func=command_send_message)

    p = subparsers.add_parser("send-messages")
    p.add_argument("--to", required=True)
    p.add_argument("--message", action="append", required=True)
    p.add_argument("--delay", type=float, default=0.5)
    common_ui_args(p)
    p.set_defaults(func=command_send_messages)

    p = subparsers.add_parser("send-to-many")
    p.add_argument("--to", required=True, help="JSON list or comma-separated friend names.")
    p.add_argument("--message", required=True, help="One message or JSON/comma list matching --to.")
    p.add_argument("--delay", type=float, default=0.5)
    bool_arg(p)
    p.set_defaults(func=command_send_to_many)

    p = subparsers.add_parser("common-groups")
    p.add_argument("--member", required=True)
    p.add_argument("--out")
    common_ui_args(p)
    p.set_defaults(func=command_common_groups)

    p = subparsers.add_parser("group-members")
    p.add_argument("--group", required=True)
    p.add_argument("--out")
    common_ui_args(p)
    p.set_defaults(func=command_group_members)

    p = subparsers.add_parser("dump-chat")
    p.add_argument("--chat", required=True)
    p.add_argument("--number", type=int, default=80)
    p.add_argument("--out")
    p.add_argument("--search-content")
    p.add_argument("--save-detail", action="store_true")
    p.add_argument("--detail-dir")
    common_ui_args(p)
    p.set_defaults(func=command_dump_chat)

    p = subparsers.add_parser("pull-messages")
    p.add_argument("--chat", required=True)
    p.add_argument("--number", type=int, default=50)
    p.add_argument("--out")
    common_ui_args(p)
    p.set_defaults(func=command_pull_messages)

    p = subparsers.add_parser("save-media")
    p.add_argument("--chat", required=True)
    p.add_argument("--number", type=int, default=25)
    p.add_argument("--out")
    common_ui_args(p)
    p.set_defaults(func=command_save_media)

    p = subparsers.add_parser("save-images")
    p.add_argument("--chat", required=True)
    p.add_argument("--number", type=int, default=10)
    p.add_argument("--scan-number", type=int)
    p.add_argument("--out")
    p.add_argument("--raw")
    common_ui_args(p)
    p.set_defaults(func=command_save_images)

    return parser


def main() -> int:
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        write_json({"status": "error", "error_type": type(exc).__name__, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
