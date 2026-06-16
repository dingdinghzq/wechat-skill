---
name: wechat-skill
description: Operate the Windows WeChat/Weixin desktop client directly from a pure Codex skill using bundled pyweixin automation and a skill-local Python runtime. Use when asked to install or repair the WeChat skill, send WeChat messages, summarize or export recent chat history, find groups by members, inspect group membership, download recent chat images/media, or troubleshoot local WeChat desktop automation without MCP.
---

# Wechat Skill

Use this skill for local Windows WeChat/Weixin desktop automation. This is a pure skill: do not use an MCP server, do not configure `mcp_servers.wechat`, and do not require a Codex restart after install.

Before running UI automation, tell the user not to interact with WeChat until the task finishes.

## Install Or Repair

Run the bundled installer to create a skill-local venv and install only the Windows automation dependencies. The installer also removes the legacy `[mcp_servers.wechat]` block from `~/.codex/config.toml` if it exists.

```powershell
$skill = "$HOME\.codex\skills\wechat-skill"
python "$skill\scripts\install_wechat_skill.py"
```

Runtime variables for task commands:

```powershell
$env:PYTHONIOENCODING='utf-8'
$skill = "$HOME\.codex\skills\wechat-skill"
$py = "$skill\.venv\Scripts\python.exe"
$task = "$skill\scripts\wechat_task.py"
```

Check readiness:

```powershell
& $py $task import-check
& $py $task readiness
```

Prerequisites:

- Windows WeChat/Weixin 4.1+ must be installed.
- `Weixin.exe` must be running and logged in before automation.
- Registry key should exist: `HKCU\Software\Tencent\Weixin`.

## Send Messages

For requests like "给 Yvonne 发微信说 ...":

```powershell
& $py $task send-message --to "Yvonne" --message "你作业做好了吗" --search-pages 0 --delay 0.5
```

If the command returns `"status": "ok"`, report that the send command completed. Do not invent delivery or read status.

For several messages to one chat:

```powershell
& $py $task send-messages --to "Yvonne" --message "第一条" --message "第二条" --search-pages 0 --delay 0.5
```

For one message to several chats:

```powershell
& $py $task send-to-many --to '["Yvonne","Jenny Chen"]' --message "同一条消息" --delay 0.5
```

## Find Groups

When the user describes a group by people in it instead of an exact group name, first list common groups with one named member:

```powershell
$out = Join-Path (Resolve-Path '.').Path "wechat_outputs\common_groups.json"
& $py $task common-groups --member "Jenny Chen" --search-pages 0 --out $out
```

Inspect likely candidates:

```powershell
$out = Join-Path (Resolve-Path '.').Path "wechat_outputs\group_members.json"
& $py $task group-members --group "GROUP_NAME" --search-pages 0 --out $out
```

If multiple groups match the described members, ask the user to choose. If the user chooses "the first one", use the first matching candidate from the last enumerated list.

## Download Images Or Media

Use `save-images` when the user asks for images. It performs a wider media scan, then copies only image files into a clean folder.

```powershell
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$out = Join-Path (Resolve-Path '.').Path "wechat_outputs\images_$stamp"
& $py $task save-images --chat "GROUP_OR_CHAT_NAME" --number 10 --scan-number 25 --search-pages 0 --out $out
```

Use `save-media` when the user asks for images and videos together:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$out = Join-Path (Resolve-Path '.').Path "wechat_outputs\media_$stamp"
& $py $task save-media --chat "GROUP_OR_CHAT_NAME" --number 25 --search-pages 0 --out $out
```

If fewer files are saved than requested, report the actual count and folder.

## Summarize Recent Chat

Export JSON first, then summarize from the saved file. Prefer `dump-chat` because it includes timestamps.

```powershell
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$out = Join-Path (Resolve-Path '.').Path "wechat_outputs\seattle_shanghai_club_$stamp.json"
& $py $task dump-chat --chat "Seattle Shanghai Club" --number 80 --search-pages 0 --out $out
```

Summaries should include message count, time range, main topics, decisions, asks, plans, and action items. Mention media only as placeholders unless the user asks to inspect or download it.

Use `pull-messages` only when the chat-history window path fails:

```powershell
$out = Join-Path (Resolve-Path '.').Path "wechat_outputs\recent_messages.json"
& $py $task pull-messages --chat "CHAT_NAME" --number 50 --search-pages 0 --out $out
```

## Troubleshooting

- `NotFoundError` locating main window: check that the visible main window title is `WeChat`; bundled `pyweixin\WeChatTools.py` searches `微信`, `WeChat`, then `Weixin`.
- Cannot find sidebar tab: bundled `pyweixin\Uielements.py` has a main tab selector that accepts `微信|Weixin|WeChat`.
- `UnicodeEncodeError`: set `$env:PYTHONIOENCODING='utf-8'`.
- Search misses a chat: try `--search-pages 5`; if there are still multiple possible groups, enumerate candidates and ask the user to choose.
- If legacy MCP tools still appear in the current Codex session after conversion, restart Codex once to unload the old server; future skill use should run only `scripts\wechat_task.py`.
