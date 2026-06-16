---
name: wechat-skill
description: Operate the Windows WeChat/Weixin desktop client through the local panxingfeng/mcp_server_wechat + pyweixin setup. Use when asked to send WeChat messages, summarize recent chat history, find groups by members, inspect group membership, download recent chat images/media, install or repair the WeChat MCP server, or troubleshoot local WeChat MCP automation.
---

# Wechat Skill

Use this skill for local Windows WeChat/Weixin desktop automation. The runtime uses `mcp_server_wechat` with local compatibility patches for WeChat/Weixin 4.1+ via `pyweixin`.

Before running UI automation, tell the user not to interact with WeChat until the task finishes.

## Install Or Repair MCP

Run the bundled installer to create the MCP virtual environment, install `mcp_server_wechat`, apply the WeChat 4.1+ patches, and update `~/.codex/config.toml`.

```powershell
$skill = "$HOME\.codex\skills\wechat-skill"
python "$skill\scripts\install_wechat_mcp.py"
```

After install, restart Codex.

The installer configures:

```toml
[mcp_servers.wechat]
command = 'C:\Users\<you>\.codex\mcp\mcp_server_wechat\venv\Scripts\python.exe'
args = ["-m", "mcp_server_wechat", "--folder-path=C:/Users/<you>/.codex/mcp/mcp_server_wechat/history"]
startup_timeout_sec = 120
```

Prerequisites:

- Windows WeChat/Weixin 4.1+ must be installed.
- `Weixin.exe` must be running and logged in before automation.
- Registry key should exist: `HKCU\Software\Tencent\Weixin`.

Check readiness:

```powershell
Get-Process -ErrorAction SilentlyContinue |
  Where-Object { $_.ProcessName -eq 'Weixin' } |
  Select-Object ProcessName,Id,MainWindowTitle,Path
```

Use UTF-8 output for Chinese names:

```powershell
$env:PYTHONIOENCODING='utf-8'
$py = "$HOME\.codex\mcp\mcp_server_wechat\venv\Scripts\python.exe"
```

## Send A Message

Use this for requests like "给 Yvonne 发微信说 ...".

```powershell
$env:PYTHONIOENCODING='utf-8'
$py="$HOME\.codex\mcp\mcp_server_wechat\venv\Scripts\python.exe"
@'
from pyweixin.WeChatAuto import Messages

Messages.send_messages_to_friend(
    friend="Yvonne",
    messages=["你作业做好了吗"],
    search_pages=0,
    send_delay=0.5,
    close_weixin=False,
)
print("SEND_OK")
'@ | & $py -
```

If the command returns `SEND_OK`, report that it was sent. Do not invent delivery/read status.

## Find A Group By Members

Use this when the user describes a group by people in it instead of exact group name.

1. Get shared groups with one named member.
2. Inspect likely candidates with `Contacts.get_groupMembers_info`.
3. If multiple groups match, ask the user to choose.

```powershell
$env:PYTHONIOENCODING='utf-8'
$py="$HOME\.codex\mcp\mcp_server_wechat\venv\Scripts\python.exe"
@'
from pyweixin.WeChatAuto import FriendSettings, Contacts

member = "Jenny Chen"
groups = FriendSettings.get_common_groups(
    friend=member,
    search_pages=0,
    is_maximize=False,
    close_weixin=False,
)
print(groups)

candidates = [g for g in groups if "665zvc" in g or "Jenny Chen" in g]
for group in candidates:
    print(f"=== {group} ===")
    try:
        members = Contacts.get_groupMembers_info(
            group=group,
            search_pages=0,
            is_maximize=False,
            close_weixin=False,
        )
        print(f"COUNT={len(members)}")
        print("\n".join(members))
    except Exception as e:
        print(type(e).__name__, e)
'@ | & $py -
```

## Download Recent Images

`Messages.save_media` saves recent images and videos. When the user specifically asks for images, run a wider media pass, then copy the first N `.png` files into a clean folder.

```powershell
$env:PYTHONIOENCODING='utf-8'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$raw = Join-Path (Resolve-Path '.').Path "wechat_downloads\group_raw_$stamp"
$clean = Join-Path (Resolve-Path '.').Path "wechat_downloads\group_10_images_$stamp"
New-Item -ItemType Directory -Force -Path $raw,$clean | Out-Null

$py="$HOME\.codex\mcp\mcp_server_wechat\venv\Scripts\python.exe"
@"
from pyweixin.WeChatAuto import Messages
Messages.save_media(
    friend="渔之民、Jenny Chen、665zvc",
    number=25,
    target_folder=r"$raw",
    search_pages=0,
    is_maximize=False,
    close_weixin=False,
)
print("SAVE_MEDIA_DONE")
"@ | & $py -

$images = Get-ChildItem -LiteralPath $raw -File -Filter *.png |
  Sort-Object { if ($_.BaseName -match '(\d+)$') { [int]$matches[1] } else { [int]::MaxValue } } |
  Select-Object -First 10

$i=1
foreach ($img in $images) {
  Copy-Item -LiteralPath $img.FullName -Destination (Join-Path $clean ("recent_image_{0:00}.png" -f $i))
  $i++
}

Get-ChildItem -LiteralPath $clean -File | Select-Object Name,Length,LastWriteTime
```

If fewer than the requested number of images are saved, report the actual count and folder.

## Summarize Recent Chat

Use `dump_chat_history` for summaries because it includes timestamps. Export JSON first, then summarize from the file.

```powershell
$env:PYTHONIOENCODING='utf-8'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$outDir = Join-Path (Resolve-Path '.').Path "wechat_summaries\seattle_shanghai_club_$stamp"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$jsonPath = Join-Path $outDir "recent_80_messages.json"

$py="$HOME\.codex\mcp\mcp_server_wechat\venv\Scripts\python.exe"
@"
import json
from pyweixin.WeChatAuto import Messages

records = Messages.dump_chat_history(
    friend="Seattle Shanghai Club",
    number=80,
    is_json=False,
    save_detail=False,
    search_pages=0,
    is_maximize=False,
    close_weixin=False,
)

with open(r"$jsonPath", "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print("JSON=" + r"$jsonPath")
print("COUNT=" + str(len(records)))
"@ | & $py -
```

Summaries should include message count, time range, main topics, decisions, asks, plans, and action items. Mention media only as placeholders unless the user asks to inspect or download it.

## Useful Direct APIs

```python
from pyweixin.WeChatAuto import Contacts, FriendSettings, Messages

Messages.send_messages_to_friend(friend, [message], search_pages=0, close_weixin=False)
Messages.dump_chat_history(friend, number=80, search_pages=0, close_weixin=False)
Messages.pull_messages(friend, number=50, search_pages=0, close_weixin=False)
Messages.save_media(friend, number=25, target_folder=folder, search_pages=0, close_weixin=False)
FriendSettings.get_common_groups(friend, search_pages=0, close_weixin=False)
Contacts.get_groupMembers_info(group, search_pages=0, close_weixin=False)
```

## Troubleshooting

- `NotFoundError` locating main window: check that the visible main window title is `WeChat`; the installer patches `pyweixin\WeChatTools.py` to search `微信`, `WeChat`, then `Weixin`.
- Cannot find sidebar tab: the installer patches `pyweixin\Uielements.py` so the main tab selector accepts `微信|Weixin|WeChat`.
- `UnicodeEncodeError`: set `$env:PYTHONIOENCODING='utf-8'`.
- Search misses a chat: try `search_pages=5`; if there are still multiple possible groups, enumerate candidates and ask the user to choose.
- Do not claim a message was delivered or read; only claim the automation command completed.
