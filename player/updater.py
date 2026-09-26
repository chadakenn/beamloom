"""Install a published Beamloom release onto the player.

Updates come from a GitHub release tag such as 0.1.5, never from the moving
main branch. Only the three player programs are replaced. Startup files stay
on the card. If the new player does not answer, the previous programs are put back.
"""
import base64
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path("/opt/beamloom-player")
STATE = Path("/var/lib/beamloom/update.json")
BACKUP = Path("/var/lib/beamloom/previous-player")
STAGED = Path("/var/lib/beamloom/next-player")
FINISH = Path("/var/lib/beamloom/finish-update.py")
REPO = "https://api.github.com/repos/chadakenn/beamloom"
FILES = {
    "player/beamloom_player.py": ROOT / "beamloom_player.py",
    "player/wifi.py": ROOT / "wifi.py",
    "player/updater.py": ROOT / "updater.py",
    "player/play.html": ROOT / "play.html",
}
_update_lock = threading.Lock()
_cache_lock = threading.Lock()
_offer = {"tag": None, "checked": 0.0}


def parse_version(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d+\.\d+\.\d+", value):
        return None
    return tuple(int(part) for part in value.split("."))


def newer(latest, current):
    new = parse_version(latest)
    old = parse_version(current)
    if new is None:
        return False
    if old is None:
        return False
    return new > old


def current_version():
    try:
        text = (ROOT / "version").read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return text if parse_version(text) else ""


def release_tag(payload, current):
    if not isinstance(payload, dict) or payload.get("draft") or payload.get("prerelease"):
        raise ValueError("Not a published release")
    tag = payload.get("tag_name", "")
    if parse_version(tag) is None:
        raise ValueError("Latest release is not a Beamloom version")
    if not newer(tag, current):
        return None
    return tag


def file_bytes(payload, source):
    if not isinstance(payload, dict) or payload.get("path") != source or payload.get("type") != "file":
        raise ValueError("Update file did not match")
    if payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
        raise ValueError("Update file did not match")
    content = base64.b64decode(payload["content"], validate=False)
    if not content or len(content) > 1024 * 1024:
        raise ValueError("Update file is the wrong size")
    return content


def status():
    try:
        saved = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {"state": "idle"}
    if not isinstance(saved, dict):
        saved = {"state": "idle"}
    if update_is_stuck(saved, time.time()):
        message = "The last update did not finish. You can try again."
        write("idle", message=message)
        saved = {"state": "idle", "message": message}
    saved["version"] = current_version() or "not set"
    _schedule_check()
    available = _offer["tag"]
    saved["available"] = available if newer(available or "", saved["version"]) else None
    return saved


def write(state, **kwargs):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps({"state": state, "at": time.time(), **kwargs}), encoding="utf-8")
    temporary.replace(STATE)


def update_is_stuck(saved, now):
    if not isinstance(saved, dict) or saved.get("state") not in {"restarting", "downloading"}:
        return False
    started = saved.get("at")
    return not isinstance(started, (int, float)) or now - started > 90


def api(path):
    request = urllib.request.Request(
        REPO + path,
        headers={"User-Agent": "Beamloom-Pi-player", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError("Update response too large")
    return json.loads(data)


def _schedule_check():
    now = time.time()
    with _cache_lock:
        if now - _offer["checked"] < 900:
            return
        _offer["checked"] = now

    def work():
        try:
            tag = release_tag(api("/releases/latest"), current_version())
        except Exception:
            tag = None
        with _cache_lock:
            _offer["tag"] = tag

    threading.Thread(target=work, daemon=True).start()


def _restore(changed):
    for index, target in reversed(changed):
        previous = BACKUP / str(index)
        if previous.exists():
            shutil.copy2(previous, target)
    previous_version = BACKUP / "version"
    if previous_version.exists():
        shutil.copy2(previous_version, ROOT / "version")


def _finish_script():
    return """#!/usr/bin/env python3
import json, shutil, subprocess, time, urllib.request
from pathlib import Path
time.sleep(2)
subprocess.run(["systemctl", "restart", "beamloom-player.service"], check=False)
ok = False
for _ in range(8):
    time.sleep(1)
    try:
        urllib.request.urlopen("http://127.0.0.1/health", timeout=2).read(10000)
        ok = True
        subprocess.run(["systemctl", "restart", "beamloom-kiosk.service"], check=False)
        break
    except Exception:
        pass
state = Path("/var/lib/beamloom/update.json")
version = Path("/opt/beamloom-player/version")
if ok:
    current = version.read_text(encoding="utf-8").strip() if version.exists() else "not set"
    state.write_text(json.dumps({"state": "installed", "version": current, "message": "Player updated."}))
else:
    backup = Path("/var/lib/beamloom/previous-player")
    targets = [
        Path("/opt/beamloom-player/beamloom_player.py"),
        Path("/opt/beamloom-player/wifi.py"),
        Path("/opt/beamloom-player/updater.py"),
    ]
    for index, target in enumerate(targets):
        previous = backup / str(index)
        if previous.exists():
            shutil.copy2(previous, target)
    previous_version = backup / "version"
    if previous_version.exists():
        shutil.copy2(previous_version, version)
    subprocess.run(["systemctl", "restart", "beamloom-player.service"], check=False)
    restored = version.read_text(encoding="utf-8").strip() if version.exists() else "not set"
    state.write_text(json.dumps({"state": "error", "version": restored, "message": "The new player did not answer. The previous player is back."}))
"""


def _update():
    changed = []
    current = current_version()
    try:
        tag = release_tag(api("/releases/latest"), current)
        if tag is None:
            write("current", version=current or "not set", message="This Pi is already on the published release.")
            return
        write("downloading", version=current or "not set", message=f"Downloading release {tag}.")
        if STAGED.exists():
            shutil.rmtree(STAGED)
        STAGED.mkdir(parents=True)
        staged_files = []
        for source in FILES:
            staged_files.append(file_bytes(api("/contents/" + source + "?ref=" + tag), source))
        BACKUP.mkdir(parents=True, exist_ok=True)
        for index, target in enumerate(FILES.values()):
            (STAGED / str(index)).write_bytes(staged_files[index])
            if target.exists():
                shutil.copy2(target, BACKUP / str(index))
            os.replace(STAGED / str(index), target)
            target.chmod(0o644)
            changed.append((index, target))
        if (ROOT / "version").exists():
            shutil.copy2(ROOT / "version", BACKUP / "version")
        (ROOT / "version").write_text(tag + "\n", encoding="utf-8")
        FINISH.write_text(_finish_script(), encoding="utf-8")
        FINISH.chmod(0o700)
        launch = ["/usr/bin/python3", str(FINISH)]
        if os.path.exists("/usr/bin/systemd-run"):
            launch = ["/usr/bin/systemd-run", "--unit", f"beamloom-player-finish-{int(time.time())}", "--collect", *launch]
        subprocess.Popen(launch, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        write("restarting", version=tag, message=f"Restarting into release {tag}.")
    except Exception as error:
        _restore(changed)
        write("error", version=current_version() or "not set", message=str(error)[:240])
    finally:
        shutil.rmtree(STAGED, ignore_errors=True)
        _update_lock.release()


def start():
    if status().get("state") == "restarting":
        return "busy"
    if not _update_lock.acquire(blocking=False):
        return "busy"
    write("checking", version=current_version() or "not set", message="Checking for a new release.")
    threading.Thread(target=_update, daemon=True).start()
    return "started"
