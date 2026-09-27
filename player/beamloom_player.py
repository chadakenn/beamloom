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
    return {"pcUrl": url if isinstance(url, str) else "", "playMode": mode}


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


def screen_target(mode: str, url: str, stored: bool, pc_up: bool, lighting: bool) -> str:
    """Choose the projector page.

    The Windows picture is used only while that app answers. After it closes,
    a stored show or live xLights data stays on the Pi.
    """
    if mode == "show" and stored:
        return "/play"
    if pc_up and url:
        return url
    if stored or lighting:
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
            data = json.dumps({**load_config(), "wifi": wifi.status(), "update": updater.status(), "join": JOIN, "display": display_status(), "show": show_status(), "pcUp": pc_is_up(), "sync": snap, "syncShow": sync.show_command(snap["multisync"], time.time()), "screen": screen_target(load_config().get("playMode", "auto"), load_config().get("pcUrl", ""), bool(show_status().get("saved")), pc_is_up(), bool(snap.get("universes") or snap.get("matrix")))}).encode("utf-8")
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
