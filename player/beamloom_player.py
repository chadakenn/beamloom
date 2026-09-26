#!/usr/bin/env python3
"""Settings page for one Beamloom projector player.

The Pi runs this at boot. The show PC opens http://beamloom.local/ and does not
sign in on the Pi. The HDMI output stays on /screen and follows the saved PC address.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


def load_config() -> dict:
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    url = data.get("pcUrl", "") if isinstance(data, dict) else ""
    return {"pcUrl": url if isinstance(url, str) else ""}


def save_config(config: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    temporary.replace(CONFIG)


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
    current = url or "Not set. The projector stays on the waiting screen."
    problem = f"<p>{escape(error)}</p>" if error else ""
    network = wifi.status()
    if network["mode"] == "setup":
        wifi_note = f"This Pi is on its setup network. Join Wi-Fi <strong>{escape(network['setupSsid'])}</strong>, password <strong>{escape(network['setupPassword'])}</strong>, then stay on this page."
    elif network["mode"] == "home":
        wifi_note = f"Joined {escape(network['ssid'] or 'the home network')}."
    elif network["mode"] == "ethernet":
        wifi_note = "This Pi is on Ethernet."
    else:
        wifi_note = f"If the Pi is not on your network yet, join Wi-Fi <strong>{escape(wifi.SETUP_SSID)}</strong>, password <strong>{escape(wifi.SETUP_PASSWORD)}</strong>, and open <strong>http://{escape(wifi.SETUP_ADDRESS)}/</strong>."
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Beamloom player</title>
  <style>
    :root {{ color-scheme: dark; }}
    body {{ margin: 0; background: #0e0f12; color: #f4f1ea; font: 18px/1.45 "Segoe UI", sans-serif; }}
    main {{ max-width: 40rem; margin: 0 auto; padding: 2.5rem 1.25rem 4rem; }}
    h1 {{ font-size: 2rem; margin: 0 0 0.5rem; }}
    p {{ color: #b7b2a8; }}
    label {{ display: block; margin: 1.5rem 0 0.4rem; color: #f4f1ea; }}
    input {{ box-sizing: border-box; width: 100%; height: 3rem; border: 1px solid #3a3d44; border-radius: 8px; background: #17191d; color: #f4f1ea; padding: 0 0.8rem; font: inherit; }}
    button {{ margin-top: 1rem; height: 3rem; border: 0; border-radius: 8px; background: #e4b15a; color: #1a1408; font: inherit; padding: 0 1.2rem; }}
    a {{ color: #e4b15a; }}
  </style>
</head>
<body>
  <main>
    <h1>Beamloom player</h1>
    <p>This Pi is the projector. Set it from this page on the show PC. You do not sign in on the Pi.</p>
    <p>{wifi_note}</p>
    <form method="post" action="/wifi">
      <label for="ssid">Home Wi-Fi name</label>
      <input id="ssid" name="ssid" autocomplete="off" />
      <label for="password">Home Wi-Fi password</label>
      <input id="password" name="password" type="password" autocomplete="off" />
      <p>Leave the password empty only if that network is open. The Pi turns off the setup network after this succeeds.</p>
      <button type="submit">Join Wi-Fi</button>
    </form>
    <form method="post" action="/settings">
      <label for="pcUrl">Beamloom PC address</label>
      <input id="pcUrl" name="pcUrl" value="{url}" placeholder="http://192.168.1.20:8751/?player=1" autocomplete="off" />
      <p>On the PC, click <strong>Pi</strong> in the show bar and paste the address it prints.</p>
      <button type="submit">Save</button>
    </form>
    {problem}
    <p>Showing now: {current}</p>
  </main>
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
    html, body { margin: 0; height: 100%; background: #000; color: #d8d4cc; font: 20px/1.4 "Segoe UI", sans-serif; }
    iframe { position: fixed; inset: 0; width: 100%; height: 100%; border: 0; background: #000; }
    p { position: fixed; left: 1.5rem; bottom: 1.5rem; max-width: 36rem; margin: 0; }
  </style>
</head>
<body>
  <p id="wait">Waiting for the show PC. Open http://beamloom.local on that computer.</p>
  <iframe id="out" hidden title="Beamloom output"></iframe>
  <script>
    let current = "";
    async function tick() {
      try {
        const data = await (await fetch("/health")).json();
        const url = typeof data.pcUrl === "string" ? data.pcUrl : "";
        const frame = document.getElementById("out");
        const wait = document.getElementById("wait");
        if (data.wifi && data.wifi.mode === "setup") {
          wait.textContent = "Join Wi-Fi " + data.wifi.setupSsid + ", password " + data.wifi.setupPassword + ", then open http://" + data.wifi.setupAddress;
        } else if (data.wifi && data.wifi.mode === "down") {
          wait.textContent = "No network yet. Connect an Ethernet cable to the router, then open http://beamloom.local on the show PC.";
        }
        if (url && url !== current) {
          current = url;
          frame.hidden = false;
          frame.src = url;
          wait.hidden = true;
        } else if (!url && current) {
          current = "";
          frame.hidden = true;
          frame.removeAttribute("src");
          wait.hidden = false;
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

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/health":
            data = json.dumps({**load_config(), "wifi": wifi.status(), "update": updater.status()}).encode("utf-8")
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
        self.send_error(404)

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
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
            self.send_html(json.dumps({"started": result == "started", "current": result == "current"}))
            return
        length = int(self.headers.get("content-length", "0") or "0")
        if length > 4000:
            self.send_error(413)
            return
        fields = parse_qs(self.rfile.read(length).decode("utf-8", "replace"))
        if path == "/wifi":
            try:
                ssid, password = wifi.clean_wifi((fields.get("ssid") or [""])[0], (fields.get("password") or [""])[0])
            except ValueError as error:
                self.send_html(settings_page(load_config(), str(error)), 400)
                return
            self.send_html(
                "<!doctype html><html lang=en><body style=\"background:#0e0f12;color:#f4f1ea;font:18px sans-serif;padding:2rem\">"
                "<p>Saved. Rejoin your home Wi-Fi, then open http://beamloom.local/</p></body></html>"
            )
            threading.Timer(1.5, lambda: self._join_home(ssid, password)).start()
            return
        if path != "/settings":
            self.send_error(404)
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

    @staticmethod
    def _join_home(ssid: str, password: str) -> None:
        try:
            wifi.join(ssid, password)
        except RuntimeError:
            return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Beamloom player settings on http://{HOST}:{PORT}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
