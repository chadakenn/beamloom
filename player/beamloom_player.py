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
