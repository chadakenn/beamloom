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
    <p>In the Windows app, click <strong>Pi</strong>. Enter the PC address it shows below, then press Save. Keep the Windows app open during the show.</p>
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
        const url = typeof data.pcUrl === "string" ? data.pcUrl : "";
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
        const stored = Boolean(data.show && data.show.saved);
        const mode = data.playMode || "auto";
        const fpp = data.syncShow && (data.syncShow.action === "play" || data.syncShow.action === "stop" || data.syncShow.action === "hold");
        const target = mode === "live" ? url : fpp && stored ? "/play" : mode === "show" && stored ? "/play" : stored && data.pcUp === false ? "/play" : url;
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
            data = json.dumps({**load_config(), "wifi": wifi.status(), "update": updater.status(), "join": JOIN, "display": display_status(), "show": show_status(), "pcUp": pc_is_up(), "sync": sync.state(), "syncShow": sync.show_command(sync.state()["multisync"], time.time())}).encode("utf-8")
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
