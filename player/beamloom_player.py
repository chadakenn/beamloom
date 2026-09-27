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


PLAY_PAGE = "eNqlPGtz27qx3/MrGHV6hrJpmaQkW34l4yROjtu8rp303I7Hk1ISLPGYIhWSsq2m+e93HwAIkJST9HZ6YhJYLIB97wLU8dNpNinXS+HMy0Xy7Mkx/nGSKJ2ddETawQYRTZ89cZzjhSgjZzKP8kKUJ51VebMz6ji71FXGZSKevRDRIsmyhVPMs/vjXW7E7qJc85NDs3jOOJuunW/OIspncXro+EfOXMSzeXnoBL7/1yNnHE1uZ3m2SqeHzl98H/onq7zI8kMnzVJx5GR3Ir9JsvtDZx5PpyI9cr4T9kmU3kUFYJ7GxTKJ1ofOOMkmt0fOfTwt5wq7PReOPN6VSzze5e0e4wrhj0QYT0862arsPDve5RboKiZ5vCyfPZlkaVE6fz9//+rSOYGp76MCZvI9pwBQmMQDapZlPBGHTug5YjEWeXHo9D0nj9MZPA08Z5Ilq0UKz0PPmYnk0NnznFRkMHrfc6JVnuXRoTNCuPRGAK5D58BzlnlcLHATnlPGiYDRAcy1jNP7uUAcAcxW3IpElIgogAln86zAbcOMxTKeCiBnADMuV4vlLbIhgGnv43KChNp3vh/Jrb05e4s7u7ryewcA7vf2Qvw32Lv2HGzr49sB/jMacNM+AfgjAgu5LahGDofcNKC3kP7dD6+v1YT/OLv4BBP+6y/A5SLOUqfv+44ongBDgQkucDQqofnE7zpx6tyJSehEL5N4efTkLounIFVx6naBE7Pky8esiBEW0AHcwCU4WpznBD2/C+z/l5r29cXpm7Zpl7mYxNQwB7lZOiB4UXn0BJZCOJ2bPJodPVml8U2WL2D2su+sztO7qolWuLoQRdVEOJzVp3ghGo0fltEkLteN9tciKucir9rjFFrfRcVtrenDqkziVLwE/Snrq5B9V8C9xgQvctSLVBTNhcIspTm1bH6ZpWUOXY2Oy6hc5cSl2tr+HqdTa01ArDciqZqKaLFMRB6+clb/ABnNauN/j4q25st1OjlLo3EiGtix62WWZM3VY8+reLHAjXHTHHTXJUItUYByAbtIkcGT0i1AqqZZ6YL4IIQbhPso1P0g6O13u11nyxn094ej3nAw7AdhH0VLYk2zuBAVWrA39ByDsAFAlrtLAKamG2yi2aAJ4Hh8BK20shjguGmsm5xtuRwUaZDrroaZNGC02GuYaTsehlELXeGqYH/4n9vv+c6OE8K/0EAwkkqL+MHF/yIw756z6j10PWqbeM5Uva96axjy3dZTNc3ygbU0dEFxX4NSvQTaTHsPHulObw3TWh1rtcK+M4eRqHOwJnx3lw9SvfUW7nCjvYe1swt//q0HguXlSftIHIKPbxxXi5lzcuIEvEZHApfiAfYrXBZPWNxdt5fPxjj0uyOSQjAGFHQc7avRUhYAA8vDClcb9gaK8GQMoAnWAQbaeAuZFQrDwsYwJH7UMQyVLBgLR2bInQZkmiVUMOx6igQHIzbGZJhH0F4ssqycg/IvcdhQmvoUFr26A5bgZDDemGdbklPK44hQDYaoH8vs3l14uOIuDRwOq2FbJzQv4MWJoduamLwLYEpEOivnuPEdJdFDiZ/X0MaBwOZAOc/BxQM9rBn8/lC6hWhcuKyDcodhiAvewQXzn8G+xZDxWmttxYEgsGEgNAIo8bB0d5AMjHsHxiIpggFOHFYM40Hgh8rGOsO2ZT6g9fHryxxZ7Fcc3iMOE58HIc7uSopsMem3eV7aBPRvW+w8YC+Ow3BLTbbjIEO2wo1cCW2uzB6aOx1u2uoIKWWRarZuMnQTP4fN0XmMArGIHtwZWI7Z2uqdiCRRZpLt9UoamtAd4QwtCCE2dVCi+0OS6L0h0hk4Q2/4gt5ESUtARoCm2XL2emG3lW+0nxHr5wAZQKve4rm2NdiQIyyO0AgMKTZbb+JD37ZuyhTuM/u0hZC7y3LHRYeLvgui8tg5hgAU/m5vKzSKBDfSvUUlui2rq3hQ5CQa3sRorPe7daglUdBHmtnAB0giFtBBbUylivaQfi/oolYokhfL2mzIf2ldDPNSgDQUa5rMdI7GWltM3mDPk7qzxQqPXBrsSffiUMLRxomBrRF5fUWk2HohaIuDusXAlKKhCNLYm5qQA559chyVxQJzT5P4ezbOSZYLZbpwXL8XbnIrUudYaPYqr8LWhlMEbMZldusyK00SbpGm3CK7vklshzaxIGEVBSwG9PGo1qyjLGk8CNTa4XxOkhay9wEn9KiuooUkvPhS+T5GFacFRAXIAiS+ZbR4Xnavtm+IcjUgIJ7M5x55VyQFI2yzB0Su4ahSdMSjaWpkYH6/QoRb40kAmnWov5HG+zWBjMdjyqSIHrypAAPBbdWC1vWAGiqx2iOhDWvCdlAT2yXE/BVmxBNwoCnn2a9h3W8zt+hYTb7xgtk+bwqEQmngKMAY1AMhNoPDkNhmIsb1NnDCkx7PSnAwoH9HtfEGAfdqhBmYxn/LEMsDaeo3MWtkM+s+uhM2q+qMGQ4rxj2QXtsrIakJesOarOJszTgG97XDk5ItIeM3bI1qCgHp9gYkA1SuCkuXOW8hsd2UT7bWJzL7B922eIQjJuUXWVHSaauOVyzZ3sSSCu/egM285DDi4J3hmNGwdSkkVH0eQqEXLWVbjmR9DDfq40G7q1ZOOrSI0OaqAfUvuuqmpx6gJ7WBNjndEchQ1yAlUaDhzUNyzZS1jCrMlLVNRVJi8mt4ZHDITX88bIQOUX6rJAxzdkLkMT4yR6Hva6OgcsiVIDdQycQkK1wIx0b9ABOS2ub2KQjR9pY8f5/8395+txEfIPItuS7Uqr3HQ4GgljVKtbP8CUeNOgsbDC3tDZSPsffGmxu07E5K4qPbkdS9F2Jp6q+xLGNBYW1BMrwYsjbjBkY1u8xEcmUWQtNsTup0VkeSImP0zeH5US0HJ2biKKtnCc11KbC9/z60pxymI+V+kcjpjyhcI0QgbT+i4rXJv5vpElp0QT6p4NHcaERxYlRGqbvsrT1n2XuwCBHlixaHiqTAkXVnEYCigx5WKqXUME611OK4XUU2y776v0pFwvtTonoTUTDGEU9LKWO/qiksK5sSysi61ePIgIEDXTQAzCwk2BbPV8uYh9rak8Ko6boyj/1BDBb0LX5CPCOIpbw0fEWto0Sp35TWfqWQA80cQoTBMiGzCymQWVocvF2RXtVIx9llX9Ou2Eg7RiPW4m0zP2enHRpY5Fp20KOr+kED08UvYNqM6M/o/vFECQuO2+xQybcjDLc/dJn5w1oMOy44Yd3sf9vd75qGDfZg0coJs17sKydCuLcbyx0YyyVJwCCKvaPNsJEKkjTkg8wnjZTU1FrRpE1Yn0yjUNThJciAWTViju6xnNpVlSTG2tYkiRZLl8Vsh+Vkh5m8TSzalnvnVZkHNy2qGQwN3QwbCeYBdVCkBpNvVLhBe5SlMoU9mVJt5nL/V4OsPCanw3YS9QtWDuC6HmfGT3tVn18ln1KpZ8raS+Gn1EFj8mii2tx0EmtESjOlymFv4HGC6zktjeTA94wYyo50ZcYf8qkgBd04EQfdhmW3zRVvvLsBJ5udff63IeRW/ZZikR2nQYJuXTmQIkwXkmYMpVXmrSLxR6K04YaAnCVlVKudcV4mxrLS+Ih+WXHefrP67Dk/M1jVOmuDW5MZpu3QKNbjQqsSTLukD35e0jlKUwc8aJMaiUBA6QLVDEDK2hKKAeZiRtxBhUpDIcJuPYFQCjF5XOqnkBvg1AdWWiANlZgVChbpi/9NwQkAVn5ki8vl960mzpG/UUtYP7guRiaTzSGtbpsn5hJKw/BtFMk9K1z4aidP6rRk1G0pJNpx06ThAvi0vr+nvezXhmtueA2uIqMLVmMMHy+llpRy+6cHWuOsc7FsVc4bKxiq0AB59VX69CC0ffpX6dO5jkbNO1RC+1pzWjdJPLkVOTnsEcfmFJKaZkyWD6r62CNhpCzQma6Kq6AjFV9uMS902Y4lBGm9zTs2RIOgeYUbvVutplfm0Z1IWs6v/H0zWvxqORYe5JlHTOr4vFSVTEVWqv1xQRwDnK9sWxV3PKvhK0cPwAULadtpHdsrDGma8gFYd1oivjwbt4Q1ptf4ylqNY0emIPTD1nU+GoRIH2BGIfuNQhQzE6m2zdvcplXWtF3y0fQ0eGWCo9NRVbtay5zaLr8yCnWubdyTkEejEqFxS6LlCNx3fvvNqQ/2u8qcsZm2T+1R0wyh0pawOsiglAWnk1is+ydqp1hUrYboCyecklZXJJLVAgtFaHfNKmwYhHzcGbBr8/dDebrG2JkBuh6MWLp0Hcszr7B0awyR9m46E1T4Td2FLB56MtPEZ7r9wHwxmtfd6o4B3txpOZ+O00KUnEmMjqwjAk0wbY7yaFFfA8xDGNSkjK6xpkfA1jW7CrE536DCsUZ0hTzR4dZaZwN0tMAIDBLRUj2FrFG+ULSonQrLw5RW+lpl6awss4XO9HE91gpogc+4rvOc0CFmT47rOoeygL3pfoEMtLUamTesEK9O0scZyJU+BLqJYIPmOqdxUUbpRHzKznhh4WPpYrBXi69w7hjnsxbQdca5iG5ViIFI/gQkeKMnQJraq30OynzInVaohOqjb4fF1x5dMdINf15bwAmniGOMgewIL8kKUZTKXURI05jOyljVUEG5x6OOrrNLwTC2J5ThUSs7R/hf0G2EPk6TishQu1H7BbmgKi5EGroRioOM9J+CkRkb72jpUMCPsRnlPGI3pqQ8QqBdHiPfthlG8/2peWr3va4KgtYngZ/Xd3Po7NgtWvKkSmQ3RF55GxCWjaQKAJHt2TwN4tHkKORVn1CIqxtmzCB1+9AgO3oYnFTxUF4GtCGargVWZNywg9m1+QQnoe5j0ikXCkOE98L+dfTkyc0qndCNzeLrKsqBBv+ziqZuCRa5hCnH+F/CGsG3NqcPAV7KyolV4xyNxHQtm9bcBJuZPoQor4kFJZsU1JHGSRcUSgYmzNs0BuGSHl0J4P4196+5f839Bp4pGXJc4RZNt0PrwOdAeYGn71d4I7gXF6/jNC6FC2O6zn/+47wD3vUowcAGMAZiB4ISedcuBTNaTYPUdIuH2iQFiekUTTyGxS4vo8BVSthAAhiX+FJx77xGkeiHp3kerd0rSVmixjZVAkoinyQvUUG3A6VnniKzHDLH5J/IJmkth8h2GAIxbEkAJb0G13RHUAtCnOKFpN+zRTbLo+V87S5M/ke+j3p15YPJivyAnvv0HNIz3lKOAoYJ6JlhBvTMMPv4HDJMSM8MM6RnhhldVwSf0JyIaYv6dwgTPgcQPdAiVINPnT4DYmdIndwQUCdj8Q30tFzcgAbyA42B1o+71nNLQB87Cb2EprklYGCgD/0KKDAw4P3xSRhUcwcGBsy6JmFYzR0YCwv8utAzEBJqWwIhXbYlZiDDf6MAeCzWqgEgIuj8f0KcJ7QugGdG6cdQPwYVQFABBBVAWAGEFUAoAVh45ZVy+fkABqaT1UKkZW8myrNE4OOL9fnUpa8KuuoG+oxiUhqDgBjsiofS7dyL8SwJO57zzYmS5Tw65MgChDMt4yiJo+IQtG8l8KMAASFWGS+TWExPGRZ7nO96kmWOeoTB0izpTSByKMVHbnIBRmvdJFss40S4+G0IWLxslU+EqXfFPJpSJqyxXFILDSA7Dx0MdEmDXX7RuCSInEcOZhgdIz8FACAEd36MMIYsNZSHw19+ePfx/O3Zl8tPp58+X0L4Wc7z7J4Yf5bnWe6aGM7Tm+xtNlOzoJR1+Llj3mTmJmQjDI7KMprM5fIk7TxNHQDArxXO/vfL5e+nr84uPPp4AaONnxmKXxy8O3v/SQ/GBjl4DBn7aVnm8fit/N6hQgGa3qEvGToMCzHTreKhBOKOVSGa7cy/8ermxubfC2pxq+llA7ydXlyc/vPLi8+vX+MqeaiEo+dXURk14bCKAY2v/vn+9N35yy+vLk7/4EGCwoR/gFUXD7xH1k6fu++Mjo8ZxLOwCLwEQthev/1w+slTCoBHbHpL8ma2uadP8rJ2tSnVAq/Atk+fL86+hK88NZbh4OV8Ec1E+KoO5tMaLt68OPXwy57AboGHz+8vz9+8P3v15cU/P515JIefYQcjaX58XjJsZji87urZtGjH9QmN1z8uTj9+uWSpf3v67uOXTx++nL16c/ZfYPn0/8Xy7vz9l9fnbz8hm6H57fn7s9OLX0Rx+qYVBfMyybBY/O07WCTMjLgxxXQ3u3GuOnjZH+xhB78MoL9YY6AHGb/SswyA6RkzTAYwsiFqqMoOCrCUY1S1gV6qegC9YkWNHt6IhP5SsYSeVOWEh1VhsX6nQot+4wC5c93FTV/hHq9ZhMFufeYvVpomAMGAWDCip3b040F68xAtSdMhP4kJYpdQyW8aKp2KUQ/Qg6Ekv4uWru65Q9DWngK3OI/SFPJ7uz8R3HspREp5rhyxiEDXH142vCUrsXSYboddI67cHNCjj/vQ/4ejWg9/6Qdd+2FtKnatdBRjwJtON5x25IoZpFqz3kU2ucVww/CZsOdJiUyVH7ZUYJIQf4gxv4NXLw53dztY6JeM6uH3efDe2cVhu0l8J9gvVVh6WboAQY0omXTFncD0/+SZrBCgy0T3CypCXb0p2GVIcE/AzZV46baDLq/q6nGSDDlkQNm2iq44cS3zta48MO1Uvelvlx/e95b4IahbIbMy7KcEitKFH9OBAMG8cmX1HlpeNv4TCEfLI0sJ4SBbzBp0116iY8lab5KIiByYPL+pLMdVPIWkN51kUzG9RhPygSYETwR0EUVjml6RxBCygKHu41mBIoMihAIEWnD46sZTPW09rj0HgZoBiBpEcYfGcOz41vszZ69/cHBgEEwuu8lHbq+YuO9TSRZiwnQljmpLHq9L0uPKG/Vu8mzhRmU2diWqrgf0muPFYBApfOjhPy+h67R0/W5th4RRzX6Cd7Kx3G0xpAA5VzvzeAkayXeDg1K3IIwQvTS7dy1ZsuSGdZGm07T47TerUy3p+MQZoFRjv6X1TX4u4we2Va3UMZH/GokYr0mjgD5uojvmfXMdOpNZsG5bC5Z2kGISCrUCPM3X18gNaUfTZFYQ5Wy1OqJcIKJjO4B8kmstVuOINA/PVPueQ3/AKOENL3weWJOaWK6oG0HRf4Xq6y6b2/g/e2/LVVltjLDpsK4+ZKOYVPhlUblusrkLzOxkDmYTEwOgBh2iNuwrVQzRuhKLgTIYWuB3x4Z198hgUqZn2XzLF4CPf53l1BEVRTxLF2Stv6ncpmpEbW7ai6q/Z5mORyEnrHoE2GxGkdjQ88wZ+mR1KupipUgpJ3b7m9JvZVss3Qdf2roFnduxOdiQ0GMJobnIHS5ayyHfnHw2PnSuCNFVfA3pf4gHg/IdS9wtbaFswxK3jvwODYC+BEDZ+E7OHgIo9BbowmmVFBSIaYxl06trGRBMRCrO06l4MIIEbLssI0hn8AhzKXKMtbC0q8QXoSIQmDtxibAA1Olw6wR/uMCakVpOS0Zv1ElxIBgf+luAl0uiZQG23MzVl1FK/CEQsGRLl8FJxKnQgkV4yGakN6PO3lTGu5d0O70gmQp8dX5GGVdWRnQ/ECfo5WK6AqfpFquFR02sQasF3d+KUqXURNLqw3w5p173M/CIzxutf5WTHbI6V9ZOk1w+HsvVsNFVrdvGORtZZjW/BL8isOtuJVvU4EGscAM24LBa8He2Jvp958TCoKr1Nh76QQiFymfJilBdHM3HZZYkL5HFMnSswi9ZV4voLnx0H8Wl4/KfGwEGze3gj1Yk5bzT7fb+LCDg1wfTlDRxnMt2HtV5nt2jS7QaehEv4nkN7lDrJZONkMFg9ynLJ0gEPajxGKMgjHo363iuZCkP0IwFEDoVVt003O7t8ikHni5WStCiTbRppTeAhk8Za1bfhpK7+441O82Km7h0rTOGJRZKWE/i1L0HlgLJpuIOYsSP6DYvUE9IPSCzN/TjXg8D9Qo9fqbfNXFlmW+SxGDg/qAMZgsnMtVr/pPDf+c0xxiPvJqY2REy5p7YZWVG2DzHnzqY2KnU/VENEMD4p1KwPhOL+2WWly6XMsyhnj3MLuRz4Q98IkbLBnnjUmA5kixq7waI67oYl6/JfNBTD7/PhaXKKJvcB45qeA/suaSw0MV+YBekyb0CTXDxR1yCrlCEsdvRiYTMcMldxSxwtiu640sQMt9VcIYbYgBQCnro4bfUazD6pcCT2hBUigGUKhkEWRXiHW5aGWODJFOVOV8KadohMsvxLpC03/hIBMKHHk1xPu0C+RIsl73IMsiFUhaGeh5EwJQF8Z66kqBTYFtU4O66ci/LCJbo1pEAM2BsjB7BNFC/zEaLkXbe8it8NE/Hn0pu6n3UI30VXyNpKew0g0iOZbM0yejKEUeAEmNBfPf4tTGmyLFcBYk7GM1dogBl9vHUznaMKw9PpTw1VmpL3aZSCPV3qtuOxK7FigMNrPgfybYky5a1JvxlJIgdZc3I7IlWZYa9qtnC/sM9Vtjdbo+srssk/PbdXmhFTXpVdxor4ti6xmI47Tr15o0zqYsarDgx585GnKWobYdeCtq4kWEyQ+tL7y5KVqJwkWnspuXWJ6s8B+7Q5SuKSJopx+NE4nudls3ENb0H9wYuzgrpKJRDNyhjU7A/duVEdvQYsgt2yG4Bg3R1ra2pDA05aGo1q+wyYRrL4ctEPFt2Hh/kNkchDTqNCIK65lkyrVSbdwz+POd7Cu2InleuEpwS0ouuS1K4gAfdlLGp8FEn/om86VoLoh+NVbZ5LVJsrcCf8PUo5DN6qxSAV8VQHA7ipT38hTOCVgdQtIqrCrOOKmU8IgNzMzyoBe/W6E2RvDE3BXe0OGvF4MHUWMUNa7+u8baNEfZfHUuSNhGhFiW3bdhQgmkeGQpA0Zk6PcSKH5XTXX20ElidLh0Svv1wIY+lvrw4/2SEWIWp+1rPgDw/lHcQOJR0kCgrYzYqD8eUMwOcTDumh07nIcG4qOh4TBjp0kEVvzkZn1zQT8bd8MkFpQ2MUZ3wTrI8pV+QgxGcVqwpo8DD4Qca2/Ie6HdfvV/D/z2Kjzkw6dqmgH/+6iuYufI0BR+Hm3+NdTAXmQGWSpZhiYu1OEaSv/XwkXv40CG84UOHC9S4x6NIc1ggh6lrSIHBToiHl9K7W+f+gRmVZzmfXONpXEDniny62L+uBTp09RrMvh1/oXRcXZvJpAzBiniMv2JwIi/+Ua2G+yRr1WUtLuPUCt0IJ5lL/WaDLmnij4TYkZK0Y2zGzFgQ5C4A3ppGUWcwA20saESxFNK66W+7m+RGrybtqjKmWzSvlW3Sj3hZS6dolV/Iz7kkh9xAd+Rtzq9137rqk0nI9641F6zuPsrpcrh5V2z5QJeB4E/Af0L+07+2RvOdEYUD9Lxxz0j2WbFqeldnQFvdtX5xUwon7atGnyuSxqv4Wt+wRBmmWmqIdVSDUKGqf9lQXOfC6y87JulC8/qhPqm/XI3bD+sxkQOUDfa/I+vTv7ljKTjHyy7y8B2JsUla9DVCU86kGkg/ummovrZoDpUGcdPQWJuEW4/Ju+AbxWCtOV3vSH2odUb5ZI5dIUYGlnxk+lS1RVFlJ90WNRv0YcyJ09/Ud4yf6TQ6BQjf2nWXeN8B9USymd4RuH5Nijrw1unGPr7LKuHo9rP5jquo3te1/jX10xowcjRXquPGNgaYh+ueY2/c0KNah+UT7ixMXtOWq8E3SVTiuTIaFLAbYB3QvFzh83V3sx2rjvttCauKwT+QT3UrwGvQ3UQ3kVDdblXMtDvwSuzGSarbBo9PU1RfKdQnMrrap5I8w5sMHv+A7RUNhJTx9tp5/rymEDKyoSKOMmLGcRxdMwMB+mE0ZB32mwVG4/YARnT6FExOqeMt62iFtwpPG/dn3MDwDOxsDnxDKnVfZbgrbNoC6gscBjL8AUid4rYwU9/yMMcYAmeaankVkL7Kwp/evTJ5Cs3daxRP6vEbetiXM77B77MAmDwh/g3k39B2goXipkVpDH9roURVu7PqTWbwyF7mZ65YaYIbtwr1jQPnpy9gPXLvSt0xbBEHdTuHAkd9bljL0x8d5+txsmTxA2BFG772hjt68fbs/SuDEGyAwBpOpVeaQvpL5MS215AH4agP789or/BXjtUFkzqCYpKDzj2OAy9xfb78cnnx8gslSCbOnxt2+vbj76fV/jAzIBNdENcuzk/fv3l7dklMq75DeyyraJ6KUMlvw4lILoolPAh9KqKOQ6hCJasdHYPMakAvu62ErjrcYyQayDxKUVMmccE5bMuEN/gr3FVJTh0Q8hCYErSIR8kWxm+400Zt578s6FSYuL5VnfxhVZbya/P8TxfJUHIUSqMydl5dbbFyf4mcAofn6k3XV74/2XDi/gP+y8MV0IAzvFr0FmkFIa3bAb7E/8Y7fpD/A6RxXHb0pBAlnoXnd1Hi6g4Pr39gJ4vQ0ZPjXfWb7ce78vfdd/lX7/8PeQWAtQ=="


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
