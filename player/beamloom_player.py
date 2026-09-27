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
        while True:
            data = json.dumps(sync.frame(), separators=(",", ":")).encode("ascii")
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
