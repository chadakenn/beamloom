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
