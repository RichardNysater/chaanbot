# Optional AI command

`!ai <query>` uses `gpt-6.1-sol`; `!aifast <query>` uses the faster, lower-cost
`gpt-6-luna` model. Both use medium reasoning through an existing Codex ChatGPT
login. This module is disabled by default. It requires Python
3.11.5+, a Linux/systemd bridge host, and the reviewed Codex CLI 0.166.0 runtime.
It does not use an API key or fall back to API-key billing.

This integration is intended for a personal, trusted-room bot. Every account
that can send commands to the bot can consume the connected subscription.
Keep ordinary room/invitation restrictions in place. The integration shares
allowance with the account's normal Codex use; it does not provide a separate
subscription allowance or authorize offering a public/shared hosted service.
Consult OpenAI's current integration guidance for other deployment models.

## Commands and data

- `!ai <query>` asks Sol a question, using web lookup when useful.
- `!aifast <query>` asks Luna, with the same context, web lookup, and reply limits.
- `!ai help` explains the commands and that queries and recent room messages go to OpenAI.
- `!ai usage` or `!aifast usage` reports shared local daily usage across all rooms.
- `!aifast help` shows the same help as `!ai help`.

Both commands share cooldowns, daily request/token budgets, event deduplication,
and pending-request limits. Switching commands does not provide extra allowance.
There is no automatic fallback to Sol if Luna is unavailable. Model access and
subscription allowance depend on the signed-in account; this integration does
not introduce API billing or promise a particular usage discount.

Each query sends up to 20 preceding text messages from the same Matrix room,
including messages from other participants and Chaanbot's replies. Every message
is labelled with its sender's full Matrix user ID. The current request is sent
once, separately with the requester's ID. Messages after the triggering command
are excluded, even when the AI job waits in the queue. Room messages are untrusted
background data, not instructions or grants of authority.

History is fetched from Matrix for each question, so it works after bot restarts.
Retrieval allows at most five API calls and ten seconds total. It may return fewer
than 20 messages because of history access, filtering, or size limits. Only plain
text is included: attachments, membership events, redacted messages, and edit
events as standalone messages are excluded. Edit histories are not reconstructed.
If retrieval fails or times out, no AI request is sent and the reservation is
refunded. Empty accessible history is valid and the question can still be asked.

There is no separate personal AI history and no `!ai reset` command. Existing
personal history tables are left untouched but are no longer read or written.
Recent room context is not saved locally. Request accounting remains persistent
in SQLite and usage limits remain per user across rooms. Replies are visible to
everyone in the room. Normal Codex conversations and other rooms are not supplied.
Ensure room participants understand that asking AI shares recent room text with
OpenAI.

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
all supported installations require Python 3.11.5+.

## Security boundaries

The bridge runs as the Codex login's Unix user and exposes a fixed operation
over a restricted Unix socket, not a TCP API. Requests cannot select executables,
arguments, providers, arbitrary model names or endpoints. An optional profile
selector accepts only `standard` (Sol) or `fast` (Luna); omitted profiles keep Sol
for compatibility with older bot clients. Home directories are hidden
except the Codex state directory needed for authentication. A separate child-tool
permission profile denies home/config reads and command networking.

Shell, local image/file access, patching, browser/computer automation, plugins,
apps, hooks, skills, memories, code mode and subagent tools are disabled. Hosted
web search and a noninteractive clarification tool remain available. Responses
are text, never server commands. Codex itself can refresh its login and maintain
its own state; the model is not given tools to administer the server.

Before accepting requests, startup verifies root ownership and artifact hashes,
then inspects both profiles' outgoing tool schemas against a loopback-only fake
provider. Unexpected tools/settings fail startup. The event filter is a secondary
alarm, not a way to undo executed actions. Treat model output and web results as
untrusted. These controls reduce exposure; they are not a guarantee against
runtime vulnerabilities or prompt injection affecting answer accuracy.

The version/catalog are deliberately pinned. Normal Codex updates do not silently
replace the bridge binary. Review and test any version/catalog change, update the
expected version in both bridge/installer, and reinstall to regenerate the manifest.
Do not edit installed files in place or replace the pin with a mutable `current` link.

When upgrading from the Sol-only bridge, reinstall the reviewed bridge source
and two-model catalog using the installer above before upgrading the bot. This
regenerates the integrity manifest and runs startup tool checks for both profiles.
The Codex binary remains pinned at 0.166.0. An old bridge continues to serve `!ai`
but rejects `!aifast` before inference; it does not silently run the wrong model.

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
| `context_messages` | 20 |
| `context_bytes` | 12000 |
| `max_answer_bytes` | 6000 |

Limits must be positive. Query/context/message-count limits cannot exceed their
listed bounds; answer size can be at most 12000 bytes. The newest whole context
messages that fit the serialized byte budget are retained. If the newest message
alone is too large, its body is shortened safely with a marker. Sender IDs remain
intact. The complete input must also fit the bridge's existing encoded size limit.
Replies are shortened on UTF-8 boundaries if necessary and split into messages of
at most 3000 UTF-8 bytes. Matrix delivery results are checked; request delivery
status is recorded as none/sent/partial/failed.

For existing configurations, `history_bytes` is accepted as a fallback when
`context_bytes` is absent. `history_turns` and `history_ttl_seconds` no longer
apply. Context is selected by room-message count, not by personal conversation
turns or a local expiry timer.

AI uses tracked background jobs: at most three admitted jobs, one executing and
two queued, with one pending request per Matrix user. Ordinary bot commands and
other rooms remain responsive. Shutdown cancels/awaits jobs and cleans up child
process groups. The systemd drop-in clears the legacy forced-kill command and
uses SIGINT so cleanup can run.

Daily budgets use UTC and survive restarts. A transaction reserves tokens before
queueing, replacing the reservation with reported input/output usage on completion.
Confirmed pre-inference failures release request/token/cooldown charges; their event
IDs remain for deduplication. Unknown usage after interruption retains the reservation.
Queued jobs cancelled before execution are refunded. Old/in-flight guards expire
180 seconds after a process crash.

Token allowances are estimates, not hard provider caps. Reasoning/search usage may
exceed a reservation. This route has no per-request generation/search-call cap;
request limits, bounded input/context and the 120-second timeout provide additional
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

Model guidance: OpenAI describes Luna as a faster, lower-cost option for lighter
work in its [model-selection guidance](https://learn.chatgpt.com/docs/agent-configuration/subagents).
The commands select different models; they do not enable Codex's premium Fast service tier.
