"""Install Beamloom player files from a pinned GitHub main commit.

This updates the player, not Raspberry Pi OS. Keep the previous files for recovery.
"""
import base64
import json
import os
import shutil
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path('/opt/beamloom-player')
STATE = Path('/var/lib/beamloom/update.json')
BACKUP = Path('/var/lib/beamloom/previous-player')
STAGED = Path('/var/lib/beamloom/next-player')
REPO = 'https://api.github.com/repos/chadakenn/beamloom'
FILES = {
    'player/beamloom_player.py': ROOT / 'beamloom_player.py',
    'player/wifi.py': ROOT / 'wifi.py',
    'player/updater.py': ROOT / 'updater.py',
    'player/systemd/beamloom-player.service': Path('/etc/systemd/system/beamloom-player.service'),
    'player/systemd/beamloom-wifi.service': Path('/etc/systemd/system/beamloom-wifi.service'),
    'player/systemd/beamloom-kiosk.service': Path('/etc/systemd/system/beamloom-kiosk.service'),
}
_lock = threading.Lock()


def status():
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {'state': 'idle', 'version': (ROOT / 'version').read_text().strip() if (ROOT / 'version').exists() else 'image build'}


def write(state, **kwargs):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps({'state': state, **kwargs}))
    tmp.replace(STATE)


def api(path):
    req = urllib.request.Request(REPO + path, headers={'User-Agent': 'Beamloom-Pi-player', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=20) as response:
        data = response.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError('Update response too large')
    return json.loads(data)


def _update():
    backup = BACKUP
    staged = STAGED
    changed = []
    try:
        sha = api('/commits/main')['sha']
        if sha == status().get('version'):
            write('current', version=sha)
            return
        staged.mkdir(parents=True, exist_ok=True)
        for index, (source, _) in enumerate(FILES.items()):
            result = api('/contents/' + source + '?ref=' + sha)
            content = base64.b64decode(result['content'])
            if len(content) > 1024 * 1024:
                raise ValueError('Update file too large')
            (staged / str(index)).write_bytes(content)
        backup.mkdir(parents=True, exist_ok=True)
        for index, target in enumerate(FILES.values()):
            if target.exists():
                shutil.copy2(target, backup / str(index))
            os.replace(staged / str(index), target)
            target.chmod(0o644)
            changed.append((index, target))
        subprocess.run(['systemctl', 'daemon-reload'], check=True, timeout=15)
        (ROOT / 'version').write_text(sha + '\n')
        write('installed', version=sha, message='Player updated. Restarting services.')
        # Restart after the HTTP request has finished; the Pi may briefly disconnect.
        subprocess.Popen(['/bin/sh', '-c', 'sleep 2; systemctl restart beamloom-wifi.service beamloom-player.service beamloom-kiosk.service'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except Exception as error:
        for index, target in reversed(changed):
            previous = backup / str(index)
            if previous.exists():
                shutil.copy2(previous, target)
        if changed:
            subprocess.run(['systemctl', 'daemon-reload'], check=False)
        write('error', version=(ROOT / 'version').read_text().strip() if (ROOT / 'version').exists() else 'image build', message=str(error)[:240])
    finally:
        shutil.rmtree(staged, ignore_errors=True)
        _lock.release()


def start():
    if not _lock.acquire(blocking=False):
        return False
    write('downloading', version=status().get('version', 'image build'))
    threading.Thread(target=_update, daemon=True).start()
    return True
