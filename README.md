# WeChat Skill for Codex

A pure Codex skill for automating the Windows WeChat/Weixin desktop app.

This repository packages a self-contained skill that lets Codex operate local WeChat through bundled `pyweixin` automation code and a skill-local Python runtime. It does not require an MCP server, background service, or Codex restart after installation.

## What It Can Do

- Send messages to a friend or group chat
- Send one message to multiple chats
- Export recent chat history as JSON for summarization
- Find shared groups by a member name
- Inspect group members for a candidate group chat
- Download recent images or media from a chat
- Check whether local WeChat automation is ready

## Requirements

- Windows
- Codex desktop or Codex CLI with local skills support
- Python 3.10+
- WeChat/Weixin desktop 4.1+
- WeChat must be running and logged in before automation

This skill controls the visible desktop client. While a task is running, avoid touching WeChat, moving its windows, or using the keyboard/mouse in that app.

## Install

Clone or copy this repository into your Codex skills folder:

```powershell
$skills = "$HOME\.codex\skills"
git clone https://github.com/dingdinghzq/wechat-skill.git "$skills\wechat-skill"
```

Install the skill runtime:

```powershell
$skill = "$HOME\.codex\skills\wechat-skill"
python "$skill\scripts\install_wechat_skill.py"
```

The installer creates:

```text
wechat-skill\.venv\
```

It installs only the Windows automation dependencies and uses the bundled `vendor\pyweixin` source directly.

## Quick Check

```powershell
$env:PYTHONIOENCODING = "utf-8"
$skill = "$HOME\.codex\skills\wechat-skill"
$py = "$skill\.venv\Scripts\python.exe"
$task = "$skill\scripts\wechat_task.py"

& $py $task import-check
& $py $task readiness
```

`import-check` verifies the bundled automation package loads. `readiness` checks whether `Weixin.exe` is running and the expected WeChat registry key exists.

## Use With Codex

After installation, ask Codex naturally:

```text
Use $wechat-skill to send Example Friend a WeChat message saying "hello"
```

```text
Use $wechat-skill to summarize the latest 80 messages from Example Group Chat
```

```text
Use $wechat-skill to download the latest 10 images from Example Group Chat
```

Codex will read `SKILL.md` and run the direct task scripts.

## Direct Commands

You can also run the task script yourself.

Send one message:

```powershell
& $py $task send-message --to "Example Friend" --message "hello" --search-pages 0 --delay 0.5
```

Send multiple messages to one chat:

```powershell
& $py $task send-messages --to "Example Friend" --message "first" --message "second" --search-pages 0
```

Find shared groups with a contact:

```powershell
& $py $task common-groups --member "Example Teammate" --search-pages 0 --out ".\wechat_outputs\common_groups.json"
```

Inspect group members:

```powershell
& $py $task group-members --group "Example Group Chat" --search-pages 0 --out ".\wechat_outputs\group_members.json"
```

Export recent chat history:

```powershell
& $py $task dump-chat --chat "Example Group Chat" --number 80 --search-pages 0 --out ".\wechat_outputs\recent_chat.json"
```

Download recent images:

```powershell
& $py $task save-images --chat "Example Group Chat" --number 10 --scan-number 25 --search-pages 0 --out ".\wechat_outputs\images"
```

Download recent images and videos:

```powershell
& $py $task save-media --chat "Example Group Chat" --number 25 --search-pages 0 --out ".\wechat_outputs\media"
```

## Why No MCP?

Earlier versions used `mcp_server_wechat` as a wrapper around local WeChat automation. The current design removes that layer:

- No MCP server process
- No `~/.codex/config.toml` MCP block
- No server startup timeout
- No restart after install
- Easier debugging through direct Python commands

The installer removes a legacy `[mcp_servers.wechat]` config block if it finds one.

## Repository Layout

```text
wechat-skill/
├── SKILL.md
├── scripts/
│   ├── install_wechat_skill.py
│   └── wechat_task.py
└── vendor/
    └── pyweixin/
```

`SKILL.md` is what Codex reads during normal skill use. `scripts/wechat_task.py` is the direct command runner. `vendor/pyweixin` contains the bundled automation source used by the task runner.

## Troubleshooting

If `readiness` returns `not_ready`, make sure WeChat/Weixin is installed, running, and logged in.

If Codex cannot find a chat, retry with more search pages:

```powershell
& $py $task dump-chat --chat "Example Group Chat" --number 80 --search-pages 5
```

If Chinese output is garbled, set UTF-8 output first:

```powershell
$env:PYTHONIOENCODING = "utf-8"
```

If old MCP tools still appear in a currently running Codex session, restart Codex once to unload the old server. Future use should go through this pure skill.

## Safety Notes

This skill automates the desktop client in your active Windows session. It can click, type, read chat UI, and save local media. Review requests carefully before running send or download tasks, and only automate chats you are allowed to access.

The task runner reports that a send command completed; it does not claim delivery or read status.

## License

See [LICENSE](LICENSE).
