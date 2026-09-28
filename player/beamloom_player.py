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
        steady_projector_browser()
    except (OSError, subprocess.TimeoutExpired):
        return


def steady_projector_browser() -> None:
    """Keep Chromium from crashing when xLights sends a moving picture.

    Pi OS gives Chromium a tiny shared-memory area. Video-sized frames fill it
    and the page dies. This flag makes Chromium use normal memory instead.
    """
    unit = Path("/etc/systemd/system/beamloom-kiosk.service")
    flag = "--disable-dev-shm-usage"
    try:
        text = unit.read_text(encoding="utf-8")
    except OSError:
        return
    if flag in text or "chromium" not in text:
        return
    updated = text.replace("chromium --kiosk ", f"chromium --kiosk {flag} ", 1)
    if updated == text:
        return
    try:
        unit.write_text(updated, encoding="utf-8")
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
      <p>Clock</p>
      <label style="display:inline;margin-right:1rem"><input type="radio" name="enabled" value="0"{"" if clock["enabled"] else " checked"} style="width:auto;height:auto" /> Off</label>
      <label style="display:inline"><input type="radio" name="enabled" value="1"{clock_checked} style="width:auto;height:auto" /> On</label>
      <label for="start">Start at (leave blank to use sunset)</label>
      <input id="start" name="start" value="{escape(clock["start"])}" placeholder="18:30" />
      <label for="latitude">Latitude, only for sunset</label>
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
    let picture = "0";
    let channelSocket;
    function connectChannels() {
      if (channelSocket) channelSocket.onclose = null;
      channelSocket = new WebSocket("ws://" + location.host + "/sync/live?picture=" + picture);
      channelSocket.binaryType = "arraybuffer";
      channelSocket.onmessage = (event) => {
        if (picture !== "1") return;
        const frame = document.getElementById("out");
        if (!frame.contentWindow) return;
        if (event.data instanceof ArrayBuffer) frame.contentWindow.postMessage({type: "beamloom-sync", payload: event.data}, "*", [event.data]);
        else frame.contentWindow.postMessage({type: "beamloom-sync", payload: event.data}, "*");
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
        const nextPicture = target.startsWith("http") ? "1" : "0";
        if (nextPicture !== picture) {
          picture = nextPicture;
          if (channelSocket) channelSocket.close();
        }
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
        want_picture = "picture=0" not in self.path
        last_matrix_at = 0.0
        last_matrix_sent = 0.0
        while True:
            matrix_at, matrix_size = sync.matrix_marker()
            now = time.monotonic()
            # One latest frame only. A 256 x 144 picture is about 20 fps; the
            # smaller picture can move a little faster. Older frames are dropped.
            interval = 0.05 if matrix_size == sync.MATRIX_BYTES else 0.033
            packet = sync.matrix_packet() if want_picture and matrix_at > last_matrix_at and now - last_matrix_sent >= interval else None
            try:
                self._ws_send(1, json.dumps(sync.frame(include_matrix=False), separators=(",", ":")).encode("ascii"))
                if packet is not None:
                    self._ws_send(2, packet)
                    last_matrix_at = matrix_at
                    last_matrix_sent = now
            except (BrokenPipeError, ConnectionResetError, OSError):
                break
            time.sleep(0.03)

    def _ws_send(self, opcode: int, payload: bytes) -> None:
        size = len(payload)
        if size < 126:
            header = bytes([0x80 | opcode, size])
        elif size < 65536:
            header = bytes([0x80 | opcode, 126]) + struct.pack(">H", size)
        else:
            header = bytes([0x80 | opcode, 127]) + struct.pack(">Q", size)
        self.wfile.write(header + payload)
        self.wfile.flush()

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
                "start": (fields.get("start") or [""])[0].strip(),
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
