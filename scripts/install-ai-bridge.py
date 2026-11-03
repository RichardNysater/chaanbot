#!/usr/bin/env python3
"""Install an isolated, pinned Codex bridge. Run explicitly as an administrator."""

import argparse
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
import time

ROOT = Path('/opt/chaanbot-ai')
EXPECTED_VERSION = 'codex-cli 0.166.0'
NAME = re.compile(r'^[a-z_][a-z0-9_-]*\$?$')


def account(value):
    if not NAME.fullmatch(value):
        raise argparse.ArgumentTypeError('Use a conventional Unix account/group name')
    return value


def unit_path(value):
    """Quote a unit path without allowing line or systemd-specifier injection."""
    if not Path(value).is_absolute() or any(ord(char) < 32 for char in value):
        raise ValueError('Unit paths must be absolute and contain no control characters')
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'


def render_unit(template, codex_user, bot_group, state):
    if not NAME.fullmatch(codex_user) or not NAME.fullmatch(bot_group):
        raise ValueError('Invalid service account/group')
    return (template.replace('@CODEX_USER@', codex_user)
            .replace('@BOT_GROUP@', bot_group)
            .replace('@CODEX_STATE@', unit_path(str(state))))


def check_root_path(path):
    for item in [path, *path.parents]:
        if item.is_symlink():
            raise ValueError('Refusing symlinked installation paths')
        if item.exists():
            info = item.stat()
            if info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError('Installation and interpreter paths must be protected by root')


def run(*args, **kwargs):
    return subprocess.run([str(arg) for arg in args], check=True, **kwargs)


def manifest(root):
    hashes = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in root.rglob('*')
              if path.is_file() and not path.is_symlink() and path.name != 'manifest.json'}
    target = root / 'manifest.json'
    target.write_text(json.dumps({'version': EXPECTED_VERSION, 'sha256': hashes}, indent=2) + '\n')
    target.chmod(0o644)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex-user', required=True, type=account,
                        help='Unix user whose existing ChatGPT login the bridge will use')
    parser.add_argument('--codex-binary', required=True, type=Path,
                        help='Trusted Codex 0.166.0 binary to copy and pin (not credentials)')
    parser.add_argument('--bot-user', default='chaanbot', type=account)
    parser.add_argument('--bot-group', default='chaanbot', type=account)
    parser.add_argument('--bot-python', required=True, type=Path,
                        help='Bot interpreter, used only as the bot account for the smoke check')
    parser.add_argument('--system-python', default=Path('/usr/bin/python3'), type=Path)
    parser.add_argument('--restart-bot', action='store_true',
                        help='Restart chaanbot.service only after the bridge smoke check succeeds')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Run this reviewed script explicitly as root')
    if sys.version_info < (3, 11):
        parser.error('The bridge requires Python 3.11 or later')
    user = pwd.getpwnam(args.codex_user)
    pwd.getpwnam(args.bot_user)
    grp.getgrnam(args.bot_group)
    state = Path(user.pw_dir) / '.codex'
    if not (state / 'auth.json').is_file():
        parser.error('The selected user needs an existing file-based Codex ChatGPT login')
    binary = args.codex_binary.resolve(strict=True)
    python = args.system_python.absolute()
    if not args.bot_python.is_absolute():
        parser.error('--bot-python must be an absolute path')
    check_root_path(python.parent)
    check_root_path(python.resolve(strict=True))
    check_root_path(ROOT)
    run(python, '-I', '-c',
        'import sys; sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ required")')
    version = run('runuser', '-u', args.codex_user, '--', binary, '--version',
                  stdout=subprocess.PIPE, text=True).stdout.strip()
    if version != EXPECTED_VERSION:
        parser.error('Only the reviewed Codex 0.166.0 binary is supported')
    repo = Path(__file__).resolve().parents[1]

    # Stop before replacing files. Inference is unavailable if any check fails;
    # the existing Matrix bot is not restarted until the new bridge is healthy.
    subprocess.run(['systemctl', 'stop', 'chaanbot-ai.service'], check=False)
    ROOT.mkdir(mode=0o755, parents=True, exist_ok=True)
    run(python, '-I', '-m', 'venv', ROOT / 'venv')
    bridge_python = ROOT / 'venv/bin/python'
    # Dependencies are installed into a root-owned venv, never imported from the
    # bot-owned environment. Install the trusted source/dependencies you reviewed.
    run(bridge_python, '-I', '-m', 'pip', 'install', '--disable-pip-version-check',
        'aiohttp>=3.9,<4')
    shutil.copyfile(binary, ROOT / 'codex')
    (ROOT / 'codex').chmod(0o755)
    shutil.copyfile(repo / 'chaanbot/codex_bridge.py', ROOT / 'bridge.py')
    shutil.copyfile(repo / 'examples/ai-codex-model.json', ROOT / 'ai-codex-model.json')
    for path in [ROOT, *ROOT.rglob('*')]:
        if not path.is_symlink():
            os.chown(path, 0, 0)
            # Runtime files contain no credentials and must remain readable by
            # the service user regardless of the administrator's umask.
            path.chmod(0o755 if path.is_dir() or path.stat().st_mode & 0o111 else 0o644)
    manifest(ROOT)
    unit = render_unit((repo / 'examples/systemd/chaanbot-ai.service.in').read_text(),
                       args.codex_user, args.bot_group, state)
    Path('/etc/systemd/system/chaanbot-ai.service').write_text(unit)
    dropin = Path('/etc/systemd/system/chaanbot.service.d')
    dropin.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(repo / 'examples/systemd/chaanbot-ai-shutdown.conf', dropin / 'ai-shutdown.conf')
    run('systemctl', 'daemon-reload')
    run('systemctl', 'enable', 'chaanbot-ai.service')
    subprocess.run(['systemctl', 'reset-failed', 'chaanbot-ai.service'], check=False)
    run('systemctl', 'restart', 'chaanbot-ai.service')
    for _ in range(60):
        if Path('/run/chaanbot-ai/bridge.sock').is_socket():
            break
        if subprocess.run(['systemctl', 'is-failed', '--quiet', 'chaanbot-ai.service']).returncode == 0:
            raise RuntimeError('Bridge preflight failed; the Matrix bot was not restarted')
        time.sleep(1)
    else:
        raise RuntimeError('Bridge startup timed out; the Matrix bot was not restarted')
    run('runuser', '-u', args.bot_user, '--', args.bot_python, '-I', '-m',
        'chaanbot.codex_bridge', 'check')
    if args.restart_bot:
        run('systemctl', 'restart', 'chaanbot.service')
    print('Bridge verified. Enable [ai] enabled = true and restart the bot to use !ai.')


if __name__ == '__main__':
    main()
