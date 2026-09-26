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
            data = json.dumps({**load_config(), "wifi": wifi.status(), "update": updater.status(), "join": JOIN, "display": display_status(), "show": show_status(), "pcUp": pc_is_up()}).encode("utf-8")
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
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Beamloom player settings on http://{HOST}:{PORT}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
