#!/usr/bin/env python3
"""Settings page for one Beamloom projector player.

The Pi runs this at boot. The show PC opens http://beamloom.local/ and does not
sign in on the Pi. The HDMI output stays on /screen and follows the saved PC address.
"""

from __future__ import annotations

import json
import base64
import http.client
import hashlib
import struct
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import zlib
from datetime import datetime
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import wifi
import updater
# Existing Pi installs have an older updater which does not yet fetch schedule.py.
# The first update writes this copy; later updates fetch schedule.py normally.
try:
    import schedule
except ModuleNotFoundError as error:
    if error.name != "schedule":
        raise
    (ROOT / "schedule.py").write_bytes(zlib.decompress(base64.b64decode("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")))
    import schedule
# Existing Pi installs have an older updater which does not yet fetch sync.py.
# The first update carries a compressed copy; later updates fetch sync.py normally.
try:
    import sync
except ModuleNotFoundError as error:
    if error.name != "sync":
        raise
    (ROOT / "sync.py").write_bytes(zlib.decompress(base64.b64decode("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")))
    import sync
CONFIG = Path(os.environ.get("BEAMLOOM_PLAYER_CONFIG", ROOT / "player.json"))
PORT = int(os.environ.get("BEAMLOOM_PLAYER_PORT", "8080"))
HOST = os.environ.get("BEAMLOOM_PLAYER_HOST", "0.0.0.0")
JOIN = {"state": "idle", "message": ""}
BLANK_CURSOR = base64.b64decode("WGN1chAAAAAAAAEAAQAAAAIA/f8BAAAAHAAAACQAAAACAP3/AQAAAAEAAAABAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAA=")
CURSOR_NAMES = ("left_ptr", "default", "pointer", "arrow", "top_left_arrow")


def hide_projector_cursor() -> None:
    """Replace Cage's centered arrow. A player update can do this without a new SD card."""
    try:
        folder = Path("/usr/share/icons/beamloom-blank/cursors")
        folder.mkdir(parents=True, exist_ok=True)
        changed = False
        for name in CURSOR_NAMES:
            path = folder / name
            if not path.is_file() or path.read_bytes() != BLANK_CURSOR:
                path.write_bytes(BLANK_CURSOR)
                changed = True
        dropin = Path("/etc/systemd/system/beamloom-kiosk.service.d/hide-cursor.conf")
        text = "[Service]\nEnvironment=XCURSOR_THEME=beamloom-blank\nEnvironment=XCURSOR_SIZE=1\n"
        dropin.parent.mkdir(parents=True, exist_ok=True)
        if not dropin.is_file() or dropin.read_text(encoding="utf-8") != text:
            dropin.write_text(text, encoding="utf-8")
            changed = True
        if changed:
            subprocess.run(["systemctl", "daemon-reload"], timeout=15, check=False)
            subprocess.run(["systemctl", "try-restart", "beamloom-kiosk.service"], timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return


SHOW_MEDIA_LIMIT = 512 * 1024 * 1024
SHOW_TYPES = {"image/png", "image/jpeg", "video/mp4", "video/webm", "video/quicktime"}


def show_root() -> Path:
    return Path(os.environ.get("BEAMLOOM_SHOW_DIR", "/var/lib/beamloom/show"))


def show_staging() -> Path:
    root = show_root()
    return root.parent / f"{root.name}-next"


def restart_kiosk() -> None:
    try:
        subprocess.run(["systemctl", "restart", "beamloom-kiosk.service"], timeout=12, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return


def show_status() -> dict:
    project_path = show_root() / "project.json"
    if not project_path.is_file():
        return {"saved": False, "name": "", "files": 0, "bytes": 0}
    try:
        project = json.loads(project_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"saved": False, "name": "", "files": 0, "bytes": 0}
    try:
        media = json.loads((show_root() / "media.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        media = []
    files = media if isinstance(media, list) else []
    return {
        "saved": True,
        "name": project.get("name", "") if isinstance(project, dict) else "",
        "files": len(files),
        "bytes": sum(int(item.get("bytes", 0)) for item in files if isinstance(item, dict)),
    }


def begin_show() -> None:
    stage = show_staging()
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "media").mkdir(parents=True)
    (stage / "media.json").write_text("[]\n", encoding="utf-8")


def save_show_project(body: bytes) -> None:
    stage = show_staging()
    if not stage.is_dir():
        raise ValueError("Start the send first.")
    try:
        project = json.loads(body)
    except json.JSONDecodeError as error:
        raise ValueError("The project file was not valid.") from error
    if not isinstance(project, dict) or not isinstance(project.get("name"), str) or not isinstance(project.get("scenes"), list):
        raise ValueError("The project file was not valid.")
    project["name"] = project["name"][:80]
    (stage / "project.json").write_text(json.dumps(project), encoding="utf-8")


def save_show_media(handler: BaseHTTPRequestHandler, media_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", media_id):
        raise ValueError("That media file was rejected.")
    stage = show_staging()
    if not (stage / "project.json").is_file():
        raise ValueError("Send the project before its files.")
    try:
        size = int(handler.headers.get("content-length", "0"))
    except ValueError as error:
        raise ValueError("That media file was rejected.") from error
    if size < 1 or size > SHOW_MEDIA_LIMIT:
        raise ValueError("A show file must be under 512 MB.")
    mime = handler.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if mime not in SHOW_TYPES:
        raise ValueError("Only PNG, JPEG, MP4, WebM, and MOV files can be stored.")
    try:
        name = base64.b64decode(handler.headers.get("x-beamloom-name", ""), validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("That media file was rejected.") from error
    name = " ".join(name.split())[:80] or "Media"
    if shutil.disk_usage(stage).free < size + 32 * 1024 * 1024:
        raise ValueError("The Pi does not have enough free space for this show.")
    target = stage / "media" / media_id
    remaining = size
    try:
        with target.open("wb") as handle:
            while remaining:
                chunk = handler.rfile.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise ValueError("The file upload stopped early.")
                handle.write(chunk)
                remaining -= len(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    items = json.loads((stage / "media.json").read_text(encoding="utf-8"))
    items = [item for item in items if not isinstance(item, dict) or item.get("id") != media_id]
    items.append({"id": media_id, "name": name, "mime": mime, "bytes": size})
    (stage / "media.json").write_text(json.dumps(items), encoding="utf-8")


def commit_show() -> dict:
    stage = show_staging()
    if not (stage / "project.json").is_file():
        raise ValueError("There is no project to store.")
    final = show_root()
    final.parent.mkdir(parents=True, exist_ok=True)
    previous = final.parent / f"{final.name}-previous"
    if previous.exists():
        shutil.rmtree(previous)
    if final.exists():
        final.rename(previous)
    stage.rename(final)
    shutil.rmtree(previous, ignore_errors=True)
    return show_status()


def display_status() -> dict:
    try:
        result = subprocess.run(["systemctl", "show", "beamloom-kiosk.service", "--property=ActiveState,SubState,Result", "--no-pager"],
                                capture_output=True, text=True, timeout=3, check=False)
        fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        state = fields.get("ActiveState", "unknown")
        message = ""
        if state != "active":
            recent = subprocess.run(["journalctl", "-u", "beamloom-kiosk.service", "-n", "5", "--no-pager", "-o", "cat"],
                                    capture_output=True, text=True, timeout=3, check=False)
            message = recent.stdout[-1200:]
        return {"state": state, "detail": fields.get("SubState", ""), "result": fields.get("Result", ""), "message": message}
    except (OSError, subprocess.TimeoutExpired):
        return {"state": "unknown", "detail": "", "result": "", "message": "Display status is unavailable."}


def check_pc(value: str) -> str:
    url = clean_url(value)
    parsed = urlparse(url)
    try:
        address = ip_address(parsed.hostname or "")
    except ValueError as error:
        raise ValueError("Use the PC's local IP address from Beamloom.") from error
    if not address.is_private or address.is_loopback or address.is_link_local or parsed.scheme != "http" or parsed.port != 8751 or parsed.path not in {"", "/"} or parsed.query != "player=1" or parsed.fragment:
        raise ValueError("Use the local PC address shown by the Pi button in Beamloom.")
    connection = http.client.HTTPConnection(parsed.hostname, 8751, timeout=3)
    try:
        connection.request("GET", "/?player=1")
        response = connection.getresponse()
        if response.status != 200 or "text/html" not in response.getheader("content-type", ""):
            raise ValueError("The PC did not answer with a Beamloom page.")
        if b"<title>Beamloom</title>" not in response.read(2048):
            raise ValueError("That address answered, but it is not the Beamloom live page.")
    except (OSError, TimeoutError) as error:
        raise ValueError("The Pi cannot reach the PC. Check that Pi output is running and allow Beamloom through the Windows firewall.") from error
    finally:
        connection.close()
    return url


def load_config() -> dict:
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    url = data.get("pcUrl", "") if isinstance(data, dict) else ""
    mode = data.get("playMode", "auto") if isinstance(data, dict) else "auto"
    if mode not in {"auto", "show", "live"}:
        mode = "auto"
    result = {"pcUrl": url if isinstance(url, str) else "", "playMode": mode}
    result["schedule"] = schedule.clean(data.get("schedule") if isinstance(data, dict) else None)
    return result


def save_config(config: dict) -> None:
    current = {}
    try:
        loaded = json.loads(CONFIG.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            current = loaded
    except (OSError, json.JSONDecodeError):
        current = {}
    current.update(config)
    mode = current.get("playMode", "auto")
    kept = {"pcUrl": current.get("pcUrl", "") if isinstance(current.get("pcUrl"), str) else "", "playMode": mode if mode in {"auto", "show", "live"} else "auto"}
    kept["schedule"] = schedule.clean(current.get("schedule"))
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG.with_suffix(".tmp")
    temporary.write_text(json.dumps(kept, indent=2) + "\n", encoding="utf-8")
    temporary.replace(CONFIG)


_PC = {"up": False, "checked": 0.0}


def pc_is_up() -> bool:
    now = time.time()
    if now - _PC["checked"] < 3:
        return bool(_PC["up"])
    _PC["checked"] = now
    parsed = urlparse(load_config()["pcUrl"])
    if not parsed.hostname or not parsed.port:
        _PC["up"] = False
        return False
    try:
        with socket.create_connection((parsed.hostname, parsed.port), 0.4):
            _PC["up"] = True
    except OSError:
        _PC["up"] = False
    return bool(_PC["up"])


def screen_target(mode: str, url: str, stored: bool, pc_up: bool, lighting: bool, scheduled: bool | None = None) -> str:
    """Choose the projector page.

    The Windows picture is used only while that app answers. A dusk clock can
    hold the stored show until sunset. xLights data and an explicit stored-show
    choice still play.
    """
    if mode == "show" and stored:
        return "/play"
    if pc_up and url:
        return url
    if lighting:
        return "/play"
    if stored and scheduled is not False:
        return "/play"
    return ""


PLAY_PAGE = "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"


def play_page() -> str:
    path = Path(__file__).with_name("play.html")
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    except OSError:
        pass
    return zlib.decompress(base64.b64decode(PLAY_PAGE)).decode("utf-8")


def show_media_path(media_id: str) -> tuple[Path, str] | None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", media_id):
        return None
    root = (show_root() / "media").resolve()
    path = (root / media_id).resolve()
    if path.parent != root or not path.is_file():
        return None
    mime = "application/octet-stream"
    try:
        items = json.loads((show_root() / "media.json").read_text(encoding="utf-8"))
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and item.get("id") == media_id and item.get("mime") in SHOW_TYPES:
                mime = str(item["mime"])
    except (OSError, json.JSONDecodeError):
        pass
    return path, mime


def _form_number(fields: dict, name: str) -> float | None:
    raw = (fields.get(name) or [""])[0].strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def clean_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if len(value) > 300 or any(character.isspace() for character in value):
        raise ValueError("too long")
    lowered = value.lower()
    if lowered.startswith(("javascript:", "data:", "file:")):
        raise ValueError("bad url")
    if "://" not in value:
        value = "http://" + value
    parsed = urlparse(value)
    try:
        parsed.port
    except ValueError as error:
        raise ValueError("bad url") from error
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("bad url")
    if parsed.username or parsed.password:
        raise ValueError("bad url")
    return value


def settings_page(config: dict, error: str = "") -> str:
    url = escape(config["pcUrl"])
    current = url or "No show PC selected yet."
    problem = f"<p>{escape(error)}</p>" if error else ""
    network = wifi.status()
    display = display_status()
    display_note = "Projector display is running." if display["state"] == "active" else f"Projector display: {escape(display['state'])} {escape(display['detail'])}. {escape(display['result'])}"
    display_error = f"<pre style='white-space:pre-wrap;overflow-wrap:anywhere'>{escape(display['message'])}</pre>" if display["message"] else ""
    if network["mode"] == "setup":
        wifi_note = f"This Pi is on its setup network. Join Wi-Fi <strong>{escape(network['setupSsid'])}</strong>, password <strong>{escape(network['setupPassword'])}</strong>, then stay on this page."
        if JOIN["state"] == "failed":
            wifi_note += f" <strong>Connection failed: {escape(JOIN['message'])}</strong> Check the Wi-Fi name and password and try again."
    elif network["mode"] == "home":
        wifi_note = f"Joined {escape(network['ssid'] or 'the home network')}."
    elif network["mode"] == "ethernet":
        wifi_note = "This Pi is on Ethernet."
    else:
        wifi_note = f"If the Pi is not on your network yet, join Wi-Fi <strong>{escape(wifi.SETUP_SSID)}</strong>, password <strong>{escape(wifi.SETUP_PASSWORD)}</strong>, and open <strong>http://{escape(wifi.SETUP_ADDRESS)}/</strong>."
    stored = show_status()
    mode = config.get("playMode", "auto")
    options = "".join(
        f'<option value="{value}"{" selected" if mode == value else ""}>{label}</option>'
        for value, label in (
            ("auto", "Play the stored show when the PC is off"),
            ("show", "Always play the stored show"),
            ("live", "Only show the PC"),
        )
    )
    stored_note = (
        f"Stored show: <strong>{escape(str(stored['name']))}</strong>, {stored['files']} file(s). It loops on the projector when the PC is off."
        if stored["saved"] else "No show is stored on this Pi yet. Send one from the Windows app."
    )
    clock = schedule.status(config.get("schedule"), datetime.now().astimezone())
    clock_checked = " checked" if clock["enabled"] else ""
    latitude = "" if clock["latitude"] is None else clock["latitude"]
    longitude = "" if clock["longitude"] is None else clock["longitude"]
    clock_note = escape(clock["note"] or "The Pi clock is off. The stored show plays whenever the PC is off.")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Beamloom player</title>
  <style>
    :root {{ color-scheme: dark; }}
    body {{ margin: 0; background: radial-gradient(circle at 50% 0%, #18283a, #0e0f12 55%); color: #f4f1ea; font: 18px/1.45 "Segoe UI", sans-serif; }}
    main {{ max-width: 40rem; margin: 0 auto; padding: 2.5rem 1.25rem 4rem; }}
    h1 {{ font-size: 2.4rem; margin: 0 0 0.5rem; }}
    p {{ color: #b7b2a8; }}
    .eyebrow {{ color: #70dfcb; font-size: .8rem; letter-spacing: .16em; font-weight: 700; text-transform: uppercase; }}
    .card {{ background: #181d26; border: 1px solid #3a3d44; border-radius: 16px; padding: 1.5rem; margin: 1.2rem 0; }}
    .card h2 {{ margin: 0; font-size: 1.25rem; }}
    .status {{ padding: .8rem 1rem; background: #17382f; border: 1px solid #397d68; border-radius: 10px; color: #d9fff4; overflow-wrap: anywhere; }}
    details {{ margin-top: 1.5rem; }}
    summary {{ cursor: pointer; color: #e4b15a; }}
    label {{ display: block; margin: 1.5rem 0 0.4rem; color: #f4f1ea; }}
    input, select {{ box-sizing: border-box; width: 100%; height: 3rem; border: 1px solid #3a3d44; border-radius: 8px; background: #17191d; color: #f4f1ea; padding: 0 0.8rem; font: inherit; }}
    button {{ margin-top: 1rem; height: 3rem; border: 0; border-radius: 8px; background: #e4b15a; color: #1a1408; font: inherit; padding: 0 1.2rem; cursor: pointer; }}
    a {{ color: #e4b15a; }}
  </style>
</head>
<body>
  <main>
    <div class="eyebrow">Projector player</div>
    <h1>Beamloom</h1>
    <p>Set up the Pi from your PC. The picture appears on the screen connected to this Pi.</p>
    <p>{stored_note}</p>
    <section class="card">
    <h2>Dusk clock</h2>
    <p>The Pi's clock says <strong>{escape(clock["now"])}</strong>. {clock_note} The PC can be off. Choose <strong>Always play the stored show</strong> above if you do not want the clock to wait.</p>
    <form method="post" action="/schedule">
      <label><input type="checkbox" name="enabled" value="1"{clock_checked} style="width:auto;height:auto" /> Start the stored show at dusk</label>
      <label for="latitude">Latitude</label>
      <input id="latitude" name="latitude" value="{latitude}" inputmode="decimal" placeholder="40.71" autocomplete="off" />
      <label for="longitude">Longitude</label>
      <input id="longitude" name="longitude" value="{longitude}" inputmode="decimal" placeholder="-74.01" autocomplete="off" />
      <label for="after">Minutes after sunset</label>
      <input id="after" name="after" value="{clock["afterSunset"]}" inputmode="numeric" />
      <label for="end">Stop at</label>
      <input id="end" name="end" value="{escape(clock["end"])}" placeholder="23:00" />
      <button type="submit">Save clock</button>
    </form>
    </section>
    <form method="post" action="/output">
      <label for="playMode">Projector picture</label>
      <select id="playMode" name="playMode">{options}</select>
      <button type="submit">Save</button>
    </form>
    <div class="status">{wifi_note}</div>
    <section class="card">
    <h2>Connect your show PC</h2>
    <p>In the Windows app, click <strong>Pi</strong>. Enter the PC address it shows below, then press Save. You can close the Windows app after the show is stored. xLights can keep sending to this Pi.</p>
    <form method="post" action="/settings">
      <label for="pcUrl">PC address</label>
      <input id="pcUrl" name="pcUrl" value="{url}" placeholder="http://192.168.1.20:8751/?player=1" autocomplete="off" />
      <button type="button" id="test-pc">Test PC connection</button>
      <button type="submit">Save PC address</button>
      <p id="test-result" role="status"></p>
    </form>
    <p>Showing now: <strong>{current}</strong></p>
    <p>If the projector stays on a text boot screen, restart the Pi once after saving the address.</p>
    </section>
    <section class="card"><h2>Projector status</h2><p>{display_note}</p>{display_error}
    <form method="post" action="/display/restart" onsubmit="return confirm('Restart the projector display? The picture may disappear for a moment.')"><button type="submit">Restart display</button></form>
    </section>
    <details><summary>Change Wi-Fi network</summary>
    <p>Only use this if you want to move the Pi to another network.</p>
    <form method="post" action="/wifi">
      <label for="ssid">Home Wi-Fi name</label>
      <input id="ssid" name="ssid" autocomplete="off" />
      <label for="password">Home Wi-Fi password</label>
      <input id="password" name="password" type="password" autocomplete="off" />
      <p>Leave the password empty only if that network is open. The Pi turns off the setup network after this succeeds.</p>
      <button type="submit">Join Wi-Fi</button>
    </form>
    </details>
    {problem}
  </main>
  <script>
    document.getElementById("test-pc").addEventListener("click", async () => {{
      const result = document.getElementById("test-result");
      result.textContent = "Checking from the Pi…";
      try {{
        const response = await fetch("/check", {{method: "POST", headers: {{"content-type": "application/x-www-form-urlencoded"}}, body: new URLSearchParams({{pcUrl: document.getElementById("pcUrl").value}})}});
        const data = await response.json();
        result.textContent = data.ok ? "Connected. You can save this address." : data.error;
      }} catch {{ result.textContent = "The Pi could not complete the check."; }}
    }});
  </script>
</body>
</html>
"""


def screen_page() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Beamloom</title>
  <style>
    html, body { margin: 0; height: 100%; background: #080b12; color: #f5f3ed; font: 20px/1.5 "Segoe UI", sans-serif; cursor: none; }
    iframe { position: fixed; inset: 0; width: 100%; height: 100%; border: 0; background: #000; cursor: none; }
    .ambient { position: fixed; inset: 0; background: radial-gradient(ellipse at 50% 42%, #243750 0, #101929 35%, #080b12 72%); }
    .card { position: fixed; left: 50%; top: 50%; transform: translate(-50%, -50%); box-sizing: border-box; width: min(90vw, 780px); padding: clamp(2rem, 5vw, 4rem); border: 1px solid #40536a; border-radius: 24px; background: #111b2bd9; box-shadow: 0 24px 90px #0008; text-align: center; }
    .mark { margin: 0 auto 1.4rem; width: 74px; height: 74px; border-radius: 24px; display: grid; place-items: center; background: linear-gradient(140deg, #00bca8, #7454e6, #e94593); font-size: 2.8rem; font-weight: bold; }
    .eyebrow { color: #80e2d0; letter-spacing: .2em; font-size: .7rem; font-weight: bold; text-transform: uppercase; }
    h1 { margin: .5rem 0; font-size: clamp(2rem, 5vw, 3.5rem); line-height: 1.1; }
    p { margin: 1rem 0 0; color: #c6d3e2; }
    .step { margin: 1.4rem auto 0; padding: 1.1rem; border-radius: 12px; background: #26354a; overflow-wrap: anywhere; }
    .hint { font-size: .8rem; color: #9eb0c4; }
  </style>
</head>
<body>
  <div id="waiting" class="ambient"><div class="card"><div class="mark">B</div><div class="eyebrow">Beamloom player</div><h1 id="title">Ready for your show</h1><p id="message">Connect this Pi to your show PC to begin.</p><div class="step" id="step">On your PC, open http://beamloom.local</div><p class="hint" id="hint">This screen updates automatically. No keyboard or reboot needed.</p></div></div>
  <iframe id="out" hidden title="Beamloom output"></iframe>
  <script>
    let current = "";
    let channelSocket;
    function connectChannels() {
      channelSocket = new WebSocket("ws://" + location.host + "/sync/live");
      channelSocket.onmessage = (event) => {
        const frame = document.getElementById("out");
        if (frame.contentWindow) frame.contentWindow.postMessage({type: "beamloom-sync", payload: event.data}, "*");
      };
      channelSocket.onclose = () => setTimeout(connectChannels, 1000);
    }
    connectChannels();
    async function tick() {
      try {
        const data = await (await fetch("/health")).json();
        const frame = document.getElementById("out");
        const waiting = document.getElementById("waiting");
        const title = document.getElementById("title");
        const message = document.getElementById("message");
        const step = document.getElementById("step");
        if (data.wifi && data.wifi.mode === "setup") {
          title.textContent = data.join && data.join.state === "failed" ? "Wi-Fi didn't connect" : "Connect to Wi-Fi";
          message.textContent = data.join && data.join.state === "failed" ? data.join.message : "On your phone or PC, join the Beamloom Wi-Fi network.";
          step.textContent = "Network: " + data.wifi.setupSsid + "  ·  Password: " + data.wifi.setupPassword + "  ·  Open http://" + data.wifi.setupAddress;
        } else if (data.wifi && data.wifi.mode === "down") {
          title.textContent = "Waiting for a network";
          message.textContent = "Connect an Ethernet cable to your router to set up this Pi.";
          step.textContent = "Then open http://beamloom.local on your PC";
        } else if (data.clock && data.clock.enabled && data.clock.on === false && data.show && data.show.saved) {
          title.textContent = "Waiting for dusk";
          message.textContent = data.clock.note || "The stored show starts at dusk.";
          step.textContent = "Pi clock: " + data.clock.now;
        } else {
          title.textContent = "Ready for your show";
          message.textContent = "The Pi is connected. Open Beamloom on your show PC.";
          step.textContent = "Open http://beamloom.local to check settings";
        }
        const target = typeof data.screen === "string" ? data.screen : "";
        if (target && target !== current) {
          current = target;
          frame.hidden = false;
          frame.src = target;
          waiting.hidden = true;
        } else if (!target && current) {
          current = "";
          frame.hidden = true;
          frame.removeAttribute("src");
          waiting.hidden = false;
        }
      } catch (error) {}
    }
    tick();
    setInterval(tick, 2000);
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def stream_sync(self) -> None:
        """Read-only local channel feed for the Pi's kiosk browser."""
        key = self.headers.get("Sec-WebSocket-Key", "")
        if self.headers.get("Upgrade", "").lower() != "websocket" or len(key) > 100:
            self.send_error(400)
            return
        try:
            if len(base64.b64decode(key, validate=True)) != 16:
                raise ValueError("bad key")
        except (ValueError, base64.binascii.Error):
            self.send_error(400)
            return
        accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        self.close_connection = True
        last_matrix_at = 0.0
        last_matrix_sent = 0.0
        while True:
            matrix_at, matrix_size = sync.matrix_marker()
            now = time.monotonic()
            # Send the latest complete frame, never a backlog of old pictures.
            # The large 256 x 144 canvas needs fewer browser uploads per second.
            interval = 0.08 if matrix_size == sync.MATRIX_BYTES else 0.04
            send_matrix = matrix_at > last_matrix_at and now - last_matrix_sent >= interval
            snapshot = sync.frame(include_matrix=send_matrix)
            if "matrix" in snapshot:
                last_matrix_at = matrix_at
                last_matrix_sent = now
            data = json.dumps(snapshot, separators=(",", ":")).encode("ascii")
            size = len(data)
            header = b"\x81" + (bytes([size]) if size < 126 else b"\x7e" + struct.pack(">H", size) if size < 65536 else b"\x7f" + struct.pack(">Q", size))
            try:
                self.wfile.write(header + data)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                break
            time.sleep(0.025)

    def log_message(self, fmt: str, *args) -> None:
        return

    def send_html(self, body: str, status: int = 200) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path, mime: str) -> None:
        size = path.stat().st_size
        start, end = 0, max(0, size - 1)
        status = 200
        range_header = self.headers.get("Range")
        if range_header:
            if not range_header.startswith("bytes=") or "," in range_header:
                self.send_error(416)
                return
            left, _, right = range_header.removeprefix("bytes=").partition("-")
            try:
                if left == "":
                    start = max(0, size - int(right))
                else:
                    start = int(left)
                    end = int(right) if right else size - 1
            except ValueError:
                self.send_error(416)
                return
            if start >= size or start > end:
                self.send_error(416)
                return
            end = min(end, size - 1)
            status = 206
        length = 0 if size == 0 else end - start + 1
        self.send_response(status)
        self.send_header("content-type", mime)
        self.send_header("accept-ranges", "bytes")
        self.send_header("content-length", str(length))
        self.send_header("cache-control", "no-store")
        if status == 206:
            self.send_header("content-range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if length == 0:
            return
        with path.open("rb") as handle:
            handle.seek(start)
            remaining = length
            while remaining:
                chunk = handle.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                remaining -= len(chunk)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/sync/live":
            self.stream_sync()
            return
        if path == "/health":
            snap = sync.state()
            config = load_config()
            clock = schedule.status(config.get("schedule"), datetime.now().astimezone())
            stored_show = bool(show_status().get("saved"))
            data = json.dumps({**config, "wifi": wifi.status(), "update": updater.status(), "join": JOIN, "display": display_status(), "show": show_status(), "pcUp": pc_is_up(), "sync": snap, "syncShow": sync.show_command(snap["multisync"], time.time()), "clock": clock, "screen": screen_target(config.get("playMode", "auto"), config.get("pcUrl", ""), stored_show, pc_is_up(), bool(snap.get("universes") or snap.get("matrix")), clock["active"])}).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.send_header("cache-control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/screen":
            self.send_html(screen_page())
            return
        if path == "/":
            self.send_html(settings_page(load_config()))
            return
        if path == "/show":
            self._json(show_status())
            return
        if path == "/play":
            self.send_html(play_page())
            return
        if path == "/show/project":
            project = show_root() / "project.json"
            if not project.is_file():
                self.send_error(404)
                return
            self._send_file(project, "application/json")
            return
        if path == "/show/files":
            try:
                items = json.loads((show_root() / "media.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                items = []
            self._json(items if isinstance(items, list) else [])
            return
        if path.startswith("/show/media/"):
            found = show_media_path(path.removeprefix("/show/media/"))
            if not found:
                self.send_error(404)
                return
            self._send_file(*found)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/show/start" or path == "/show/project" or path == "/show/finish" or path.startswith("/show/media/"):
            self._receive_show(path)
            return
        if path in {"/connect", "/check", "/display/restart"}:
            origin = self.headers.get("Origin")
            if origin and urlparse(origin).hostname != self.headers.get("Host", "").split(":", 1)[0]:
                self.send_error(403, "Open the Pi settings page directly")
                return
        if path == "/display/restart":
            threading.Thread(target=lambda: subprocess.run(["systemctl", "restart", "beamloom-kiosk.service"], timeout=12, check=False), daemon=True).start()
            self.send_response(303)
            self.send_header("location", "/")
            self.end_headers()
            return
        if path == "/update":
            configured = urlparse(load_config()["pcUrl"]).hostname
            try:
                allowed = configured and self.client_address[0] in {
                    entry[4][0] for entry in socket.getaddrinfo(configured, None)
                }
            except OSError:
                allowed = False
            if not allowed or self.headers.get("X-Beamloom-Update") != "1":
                self.send_error(403, "Only the configured show PC can update this Pi")
                return
            result = updater.start()
            self.send_html(json.dumps({"started": result == "started", "busy": result == "busy"}))
            return
        length = int(self.headers.get("content-length", "0") or "0")
        if length > 4000:
            self.send_error(413)
            return
        fields = parse_qs(self.rfile.read(length).decode("utf-8", "replace"))
        if path in {"/connect", "/check"}:
            try:
                url = check_pc((fields.get("pcUrl") or [""])[0])
                if path == "/connect":
                    save_config({"pcUrl": url})
                answer = {"ok": True, "pcUrl": url}
                status = 200
            except ValueError as error:
                answer = {"ok": False, "error": str(error)}
                status = 400
            data = json.dumps(answer).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.send_header("cache-control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/wifi":
            try:
                ssid, password = wifi.clean_wifi((fields.get("ssid") or [""])[0], (fields.get("password") or [""])[0])
            except ValueError as error:
                self.send_html(settings_page(load_config(), str(error)), 400)
                return
            JOIN.update(state="connecting", message="Trying to join your Wi-Fi.")
            self.send_html("""<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="8;url=http://beamloom.local/"><body style="background:#101929;color:#f5f3ed;font:20px/1.5 Segoe UI,sans-serif;max-width:32rem;margin:15vh auto;padding:2rem"><h1>Connecting to your Wi-Fi…</h1><p>The Beamloom setup network will disappear if the connection succeeds. Connect your phone or PC to your home Wi-Fi, then open <a style="color:#80e2d0" href="http://beamloom.local/">beamloom.local</a>.</p><p>No reboot is needed. If Beamloom Wi-Fi comes back, reconnect to it and check the error on the setup page.</p></body></html>""")
            threading.Timer(1.5, lambda: self._join_home(ssid, password)).start()
            return
        if path == "/schedule":
            saved = schedule.clean({
                "enabled": (fields.get("enabled") or [""])[0] == "1",
                "latitude": _form_number(fields, "latitude"),
                "longitude": _form_number(fields, "longitude"),
                "afterSunset": _form_number(fields, "after"),
                "end": (fields.get("end") or ["23:00"])[0].strip(),
            })
            save_config({"schedule": saved})
            if "application/json" in self.headers.get("Accept", ""):
                self._json({"ok": True, "clock": schedule.status(saved, datetime.now().astimezone())})
                return
            self.send_response(303)
            self.send_header("location", "/")
            self.end_headers()
            return
        if path != "/settings" and path != "/output":
            self.send_error(404)
            return
        if path == "/output":
            mode = (fields.get("playMode") or ["auto"])[0]
            if mode not in {"auto", "show", "live"}:
                mode = "auto"
            save_config({"playMode": mode})
            if mode == "show" and show_status()["saved"]:
                threading.Thread(target=restart_kiosk, daemon=True).start()
            if "application/json" in self.headers.get("Accept", ""):
                self._json({"ok": True, "playMode": mode})
                return
            self.send_response(303)
            self.send_header("location", "/")
            self.end_headers()
            return
        try:
            url = clean_url((fields.get("pcUrl") or [""])[0])
        except ValueError:
            self.send_html(settings_page(load_config(), "That address needs to be a web address, such as http://192.168.1.20:8751/?player=1"), 400)
            return
        save_config({"pcUrl": url})
        self.send_response(303)
        self.send_header("location", "/")
        self.end_headers()

    def _json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _receive_show(self, path: str) -> None:
        try:
            if path == "/show/start":
                begin_show()
                self._json({"ok": True})
                return
            if path == "/show/project":
                length = int(self.headers.get("content-length", "0") or "0")
                if length < 2 or length > 2 * 1024 * 1024:
                    raise ValueError("The project file was not valid.")
                body = self.rfile.read(length)
                if len(body) != length:
                    raise ValueError("The project file was not valid.")
                save_show_project(body)
                self._json({"ok": True})
                return
            if path == "/show/finish":
                self._json({"ok": True, "show": commit_show()})
                return
            save_show_media(self, path.removeprefix("/show/media/"))
            self._json({"ok": True})
        except ValueError as error:
            self._json({"ok": False, "error": str(error)}, 400)
        except OSError:
            self._json({"ok": False, "error": "The Pi could not store the show."}, 500)

    @staticmethod
    def _join_home(ssid: str, password: str) -> None:
        try:
            wifi.join(ssid, password)
        except RuntimeError as error:
            JOIN.update(state="failed", message=str(error))
        else:
            JOIN.update(state="connected", message="Connected to your home Wi-Fi.")


def main() -> None:
    hide_projector_cursor()
    sync.start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Beamloom player settings on http://{HOST}:{PORT}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
