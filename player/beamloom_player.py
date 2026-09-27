#!/usr/bin/env python3
"""Settings page for one Beamloom projector player.

The Pi runs this at boot. The show PC opens http://beamloom.local/ and does not
sign in on the Pi. The HDMI output stays on /screen and follows the saved PC address.
"""

from __future__ import annotations

import json
import base64
import http.client
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
        const target = mode === "live" ? url : mode === "show" && stored ? "/play" : stored && data.pcUp === false ? "/play" : url;
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
        if path == "/health":
            data = json.dumps({**load_config(), "wifi": wifi.status(), "update": updater.status(), "join": JOIN, "display": display_status(), "show": show_status(), "pcUp": pc_is_up(), "sync": sync.state()}).encode("utf-8")
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
