# Optional AI command

`!ai <query>` uses `gpt-6.1-sol` with medium reasoning through an existing
Codex ChatGPT login. This module is disabled by default. It requires Python
3.11+, a Linux/systemd bridge host, and the reviewed Codex CLI 0.166.0 runtime.
It does not use an API key or fall back to API-key billing.

This integration is intended for a personal, trusted-room bot. Every account
that can send commands to the bot can consume the connected subscription.
Keep ordinary room/invitation restrictions in place. The integration shares
allowance with the account's normal Codex use; it does not provide a separate
subscription allowance or authorize offering a public/shared hosted service.
Consult OpenAI's current integration guidance for other deployment models.

## Commands and data

- `!ai <query>` asks a question, using web lookup when useful.
- `!ai help` explains the commands and that queries go to OpenAI.
- `!ai reset` clears your AI history in this room without clearing usage.
- `!ai usage` reports local daily usage across all rooms.

Only the sender's query and bounded AI history from the current room are sent.
History is stored in the configured SQLite database under `(room ID, user ID)`;
other room messages and normal Codex conversations are not supplied. Replies
are visible to everyone in the room. Reset does not remove Matrix messages.
Do not send information you do not want shared with the room and provider.

## Isolated bridge installation

Install the bot with the optional dependencies (`pip install '.[ai]'` from a
checkout). Review `scripts/install-ai-bridge.py`, the model catalog, and the
systemd templates before installing the privileged bridge.

The installer takes explicit account and executable arguments. Replace the
example values with accounts/paths you control; no login information belongs
in this repository. The Codex account must already have a file-based ChatGPT
login in its normal `.codex/auth.json`. The bot account needs membership in
the group selected for socket access. Do not copy credentials into the bot's
virtualenv, source checkout, or public configuration.

```sh
sudo /usr/bin/python3 -I scripts/install-ai-bridge.py \
  --codex-user YOUR_CODEX_UNIX_USER \
  --codex-binary /absolute/path/to/reviewed/codex-0.166.0 \
  --bot-user chaanbot \
  --bot-group chaanbot \
  --bot-python /absolute/path/to/bot/venv/bin/python
```

The bridge gets a separate root-owned runtime in `/opt/chaanbot-ai`, including
its Python venv/dependencies and a copy of the reviewed Codex binary. Installation
may download `aiohttp` and dependencies into that venv. It never imports code
from the bot-owned Python environment as the Codex user. The installer explicitly
restarts the bridge, waits for preflight, and performs a small subscription
request as the bot account. It restarts the Matrix bot only when you explicitly
supply `--restart-bot` and the bridge check has succeeded.

Enable the module in the existing bot config, then restart the bot:

```ini
[ai]
enabled = true
bridge_socket = /run/chaanbot-ai/bridge.sock
```

If `[modules] enabled` is an explicit allowlist, add `ai`. Remove `ai` from any
module-disabled list. AI being disabled does not initialize AI tables or affect
other modules. The legacy bot itself can still be used without the AI bridge;
the AI feature and installer require Python 3.11+.

## Security boundaries

The bridge runs as the Codex login's Unix user and exposes a fixed operation
over a restricted Unix socket, not a TCP API. Requests cannot select executables,
arguments, providers, model names or endpoints. Home directories are hidden
except the Codex state directory needed for authentication. A separate child-tool
permission profile denies home/config reads and command networking.

Shell, local image/file access, patching, browser/computer automation, plugins,
apps, hooks, skills, memories, code mode and subagent tools are disabled. Hosted
web search and a noninteractive clarification tool remain available. Responses
are text, never server commands. Codex itself can refresh its login and maintain
its own state; the model is not given tools to administer the server.

Before accepting requests, startup verifies root ownership and artifact hashes,
then inspects the actual outgoing tool schema against a loopback-only fake
provider. Unexpected tools/settings fail startup. The event filter is a secondary
alarm, not a way to undo executed actions. Treat model output and web results as
untrusted. These controls reduce exposure; they are not a guarantee against
runtime vulnerabilities or prompt injection affecting answer accuracy.

The version/catalog are deliberately pinned. Normal Codex updates do not silently
replace the bridge binary. Review and test any version/catalog change, update the
expected version in both bridge/installer, and reinstall to regenerate the manifest.
Do not edit installed files in place or replace the pin with a mutable `current` link.

## Usage and delivery limits

Defaults, adjustable in `[ai]`:

| Setting | Default |
| --- | ---: |
| `cooldown_seconds` | 30 |
| `daily_requests` | 20 |
| `daily_tokens` | 100000 |
| `global_daily_requests` | 200 |
| `global_daily_tokens` | 1000000 |
| `request_token_reserve` | 40000 |
| `max_query_bytes` | 4000 |
| `history_turns` | 6 |
| `history_bytes` | 12000 |
| `history_ttl_seconds` | 86400 |
| `max_answer_bytes` | 6000 |

Limits must be positive. Query/history/turn limits cannot exceed their listed
bounds; answer size can be at most 12000 bytes. Replies are shortened on UTF-8
boundaries if necessary and split into messages of at most 3000 UTF-8 bytes.
Matrix delivery results are checked. Only fully delivered answers enter history;
request delivery status is recorded as none/sent/partial/failed.

AI uses tracked background jobs: at most three admitted jobs, one executing and
two queued, with one pending request per Matrix user. Ordinary bot commands and
other rooms remain responsive. Shutdown cancels/awaits jobs and cleans up child
process groups. The systemd drop-in clears the legacy forced-kill command and
uses SIGINT so cleanup can run.

Daily budgets use UTC and survive restarts. A transaction reserves tokens before
queueing, replacing the reservation with reported input/output usage on completion.
Confirmed pre-inference failures release request/token/cooldown charges; their event
IDs remain for deduplication. Unknown usage after interruption retains the reservation.
Queued jobs cancelled before execution are refunded. History expires after 24 hours,
purged on the next query. Old/in-flight guards expire 180 seconds after a process crash.

Token allowances are estimates, not hard provider caps. Reasoning/search usage may
exceed a reservation. This route has no per-request generation/search-call cap;
request limits, bounded input/history and the 120-second timeout provide additional
controls. Codex can retry transport failures internally. Generated answers that
fail Matrix delivery still consume inference usage. Check the ChatGPT usage
dashboard for the actual subscription allowance and reset time.

## Checks and maintenance

```sh
python -m unittest discover -v
sudo systemctl status chaanbot-ai chaanbot
sudo -u chaanbot /absolute/path/to/bot/venv/bin/python -m chaanbot.codex_bridge check
sudo journalctl -u chaanbot-ai -n 30 --no-pager
```

The regression suite uses temporary databases and mocks, not real credentials,
model requests, production databases, or service changes. The bridge `check`
command uses one small subscription request and never posts to Matrix. Startup
schema verification is local-only and consumes no subscription inference.

Never commit credentials, generated manifests, runtime caches, logs or databases.
Only source, tests, a model catalog and generic deployment examples belong in a PR.

References: [Codex authentication](https://learn.chatgpt.com/docs/auth),
[Codex configuration](https://learn.chatgpt.com/docs/config-file/config-reference),
[Codex integrations](https://learn.chatgpt.com/docs/app-server).
