"""Local, fixed-operation bridge to the existing Unix user's Codex login."""

import argparse
import asyncio
import json
import hashlib
import logging
import os
from pathlib import Path
import signal

import aiohttp
from aiohttp import web

ROOT = Path("/opt/chaanbot-ai")
SOCKET = Path("/run/chaanbot-ai/bridge.sock")
CATALOG = ROOT / "ai-codex-model.json"
CODEX = str(ROOT / "codex")
EXPECTED_VERSION = "codex-cli 0.166.0"
logger = logging.getLogger(__name__)


class PlanError(ValueError):
    """Safe-to-display bridge failure with explicit accounting semantics."""
    def __init__(self, message, inference_started=True):
        super().__init__(message)
        self.inference_started = inference_started


class PreflightError(ValueError):
    """Confirmed failure before starting inference; do not charge a reservation."""


class BridgeConnection:
    def __init__(self, path=SOCKET):
        self.path = Path(path)

    def available(self):
        return self.path.is_socket()


def clean_environment():
    # In particular, never inherit API keys, parent agent settings, or CODEX_HOME.
    allowed = {"HOME", "USER", "LOGNAME", "PATH", "LANG", "SSL_CERT_FILE", "SSL_CERT_DIR",
               "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy"}
    return {key: value for key, value in os.environ.items() if key in allowed}


def command(cwd, probe_url=None):
    settings = {
        "model_provider": "openai", "model_catalog_json": str(CATALOG),
        "model_reasoning_effort": "medium", "web_search": "live",
        "forced_login_method": "chatgpt", "analytics.enabled": False,
        "features.shell_tool": False, "features.view_image": False,
        "features.apps": False, "features.plugins": False, "features.multi_agent": False,
        "features.multi_agent_v2": False, "features.goals": False,
        "features.hooks": False, "features.memories": False, "features.shell_snapshot": False,
        "features.skill_search": False, "features.skip_host_skill_discovery": True,
        "features.browser_use": False, "features.computer_use": False,
        "features.image_generation": False, "features.code_mode.enabled": False,
        "features.code_mode_host": False, "features.standalone_web_search": True,
        "default_permissions": "chaanbot_web",
        "permissions.chaanbot_web.filesystem": {":minimal": "read", ":workspace_roots": "read",
                                                "/home": "deny", "/etc": "deny", str(ROOT): "read"},
        "permissions.chaanbot_web.network.enabled": False,
    }
    if probe_url is not None:
        settings.update({"model_provider": "bridge_probe", "features.enable_request_compression": False,
            "model_providers.bridge_probe.name": "Local tool verification",
            "model_providers.bridge_probe.base_url": probe_url,
            "model_providers.bridge_probe.wire_api": "responses",
            "model_providers.bridge_probe.requires_openai_auth": False,
            "model_providers.bridge_probe.supports_websockets": False,
            "model_providers.bridge_probe.request_max_retries": 0,
            "model_providers.bridge_probe.stream_max_retries": 0})
    result = [CODEX, "--strict-config", "exec", "--ignore-user-config", "--ignore-rules", "--ephemeral",
              "--skip-git-repo-check", "--model", "gpt-6.1-sol",
              "--json", "--color", "never", "--cd", str(cwd)]
    for name, value in settings.items():
        encoded = ("{" + ", ".join(json.dumps(k) + " = " + json.dumps(v) for k, v in value.items()) + "}"
                   if isinstance(value, dict) else json.dumps(value))
        result += ["-c", name + "=" + encoded]
    return result + ["-"]


def validate_payload(payload):
    if not isinstance(payload, dict) or set(payload) != {"instructions", "input"}:
        raise ValueError("Invalid bridge request")
    if not isinstance(payload["instructions"], str) or len(payload["instructions"].encode()) > 4096:
        raise ValueError("Invalid bridge instructions")
    items = payload["input"]
    if not isinstance(items, list) or not 1 <= len(items) <= 13:
        raise ValueError("Invalid history")
    for item in items:
        if (not isinstance(item, dict) or set(item) != {"role", "content"}
                or item["role"] not in ("user", "assistant") or not isinstance(item["content"], str)):
            raise ValueError("Invalid history item")
    if len(json.dumps(items, ensure_ascii=False).encode()) > 20000:
        raise ValueError("History too large")
    return payload["instructions"] + "\n\nConversation (JSON data):\n" + json.dumps(items, ensure_ascii=False)


async def infer(payload, cwd):
    prompt = validate_payload(payload)
    env = clean_environment()
    try:
        status = await asyncio.create_subprocess_exec(CODEX, "login", "status", env=env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    except OSError as error:
        raise PreflightError("Codex login check is unavailable") from error
    try:
        stdout, stderr = await asyncio.wait_for(status.communicate(), 10)
    except BaseException as error:
        if status.returncode is None:
            status.kill()
        await status.wait()
        if isinstance(error, asyncio.CancelledError):
            raise
        raise PreflightError("Codex login check did not finish") from error
    if status.returncode != 0 or b"Logged in using ChatGPT" not in stdout + stderr:
        raise PreflightError("The bridge's Codex user must be signed in with ChatGPT.")
    try:
        process = await asyncio.create_subprocess_exec(*command(cwd), env=env,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True, limit=1024 * 1024)
    except OSError as error:
        raise PreflightError("Codex could not be started") from error
    try:
        process.stdin.write(prompt.encode())
        await process.stdin.drain()
        process.stdin.close()
        answer, usage, completed, output_bytes = [], None, False, 0
        async with asyncio.timeout(120):
            async for line in process.stdout:
                output_bytes += len(line)
                if output_bytes > 2 * 1024 * 1024:
                    raise ValueError("Codex output limit exceeded")
                event = json.loads(line)
                kind = event.get("type")
                if kind in ("item.started", "item.completed"):
                    item = event.get("item", {})
                    if item.get("type") not in ("agent_message", "reasoning", "web_search", "error"):
                        raise ValueError("Codex attempted a tool outside the bridge's web-only configuration.")
                    if kind == "item.completed" and item.get("type") == "agent_message":
                        text = item.get("text", "")
                        if not isinstance(text, str):
                            raise ValueError("Invalid answer")
                        answer.append(text)
                elif kind == "turn.completed":
                    completed = True
                    metrics = event.get("usage", {})
                    if isinstance(metrics.get("input_tokens"), int) and isinstance(metrics.get("output_tokens"), int):
                        usage = metrics["input_tokens"] + metrics["output_tokens"]
                elif kind == "turn.failed":
                    raise ValueError("Codex could not finish the request. Check subscription usage and login.")
            await process.wait()
        if process.returncode != 0 or not completed or not answer:
            raise ValueError("Codex returned no completed answer. Check subscription usage and login.")
        return {"status": "completed", "usage": {"total_tokens": usage}, "output": [
            {"type": "message", "role": "assistant", "content": [
                {"type": "output_text", "text": "\n".join(answer), "annotations": []}]}]}
    finally:
        if process.returncode is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await process.wait()


def verify_artifacts():
    """Fail closed if the pinned deployment changed or has writable parents."""
    manifest = ROOT / "manifest.json"
    for path in [ROOT, *ROOT.parents, manifest]:
        info = path.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("Bridge deployment must be root-owned and not group/other-writable")
    data = json.loads(manifest.read_text())
    if data["version"] != EXPECTED_VERSION:
        raise ValueError("Unreviewed Codex version")
    for name, digest in data["sha256"].items():
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT) or path.is_symlink():
            raise ValueError("Invalid deployment path")
        for ancestor in [path, *path.parents]:
            if ancestor == ROOT.parent:
                break
            info = ancestor.stat()
            if info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError("Writable bridge artifact")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Changed bridge artifact")


def exposed_tools(request):
    tools = list(request.get("tools", []))
    for item in request.get("input", []):
        if isinstance(item, dict) and item.get("type") == "additional_tools":
            tools.extend(item.get("tools", []))
    names = []

    def check(tool, prefix=""):
        kind, name = tool.get("type"), tool.get("name", "")
        if kind == "namespace":
            for child in tool.get("tools", []):
                check(child, prefix + name + ".")
        elif kind == "function" and prefix + name == "functions.request_user_input":
            names.append(prefix + name)
        elif kind in ("web_search", "web_search_preview"):
            names.append(kind)
        else:
            raise ValueError("Unexpected exposed tool")
    for tool in tools:
        check(tool)
    return names


async def verify_tools(cwd):
    """Inspect the real CLI's outgoing schema against a local fake provider."""
    captured = []

    async def endpoint(request):
        if request.method == "GET":
            return web.json_response(json.loads(CATALOG.read_text()))
        value = await request.json()
        captured.append(value)
        return web.json_response({"error": {"message": "Local verification complete"}}, status=400)

    app = web.Application(client_max_size=2 * 1024 * 1024)
    app.router.add_route("*", "/{path:.*}", endpoint)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    process = None
    try:
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        process = await asyncio.create_subprocess_exec(
            *command(cwd, "http://127.0.0.1:{}/v1".format(port)), env=clean_environment(),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL, start_new_session=True)
        await asyncio.wait_for(process.communicate(b"Local tool verification. Say hello."), 30)
        requests = [value for value in captured if value.get("model") == "gpt-6.1-sol"]
        if not requests:
            raise ValueError("Could not verify outgoing Codex tools")
        for value in requests:
            exposed_tools(value)
            if value.get("reasoning", {}).get("effort") != "medium":
                raise ValueError("Unexpected reasoning effort")
        print("Pinned Codex tool schema verified", flush=True)
    finally:
        if process is not None and process.returncode is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await process.wait()
        await runner.cleanup()


def create_app(cwd):
    busy = False

    async def respond(request):
        nonlocal busy
        # Claim admission before reading a request body, without an intervening await.
        if busy:
            return web.json_response({"error": "busy", "inference_started": False}, status=429)
        busy = True
        try:
            try:
                async with asyncio.timeout(5):
                    payload = await request.json()
                validate_payload(payload)
            except (ValueError, asyncio.TimeoutError):
                return web.json_response({"error": "invalid_request", "inference_started": False}, status=400)
            try:
                response = await infer(payload, cwd)
                return web.json_response(response)
            except PreflightError:
                return web.json_response({"error": "login_unavailable", "inference_started": False}, status=503)
            except (ValueError, asyncio.TimeoutError, OSError):
                logger.warning("Codex inference did not complete")
                return web.json_response({"error": "inference_failed", "inference_started": True}, status=503)
        finally:
            busy = False

    app = web.Application(client_max_size=32768)
    app.router.add_post("/ask", respond)
    return app


async def serve(socket_path):
    verify_artifacts()
    cwd = socket_path.parent / "empty"
    cwd.mkdir(mode=0o700, exist_ok=True)
    await verify_tools(cwd)
    app = create_app(cwd)
    runner = web.AppRunner(app, access_log=None, handler_cancellation=True)
    await runner.setup()
    try:
        await web.UnixSite(runner, str(socket_path)).start()
        socket_path.chmod(0o660)
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["serve", "check"])
    parser.add_argument("--socket", type=Path, default=SOCKET)
    args = parser.parse_args()
    if args.command == "check":
        async def check():
            async with aiohttp.ClientSession(connector=aiohttp.UnixConnector(path=str(args.socket)),
                    timeout=aiohttp.ClientTimeout(total=140)) as session:
                async with session.post("http://localhost/ask", json={
                    "instructions": "Answer briefly. Do not use any tools.",
                    "input": [{"role": "user", "content": "Say exactly: Chaanbot Codex bridge OK"}],
                }) as response:
                    result = await response.json()
                    if response.status != 200:
                        raise SystemExit("Bridge check failed")
                    print(json.dumps(result))
        asyncio.run(check())
    else:
        logging.basicConfig(level=logging.INFO)
        asyncio.run(serve(args.socket))


if __name__ == "__main__":
    main()
