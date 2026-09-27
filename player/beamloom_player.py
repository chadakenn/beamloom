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
