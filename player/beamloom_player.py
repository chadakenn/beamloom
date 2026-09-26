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
