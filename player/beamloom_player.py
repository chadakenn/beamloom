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
from datetime import datetime
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
# Existing Pi installs have an older updater which does not yet fetch schedule.py.
# The first update writes this copy; later updates fetch schedule.py normally.
try:
    import schedule
except ModuleNotFoundError as error:
    if error.name != "schedule":
        raise
    (ROOT / "schedule.py").write_bytes(zlib.decompress(base64.b64decode("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")))
    import schedule
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
    """The Pi draws an arrow in the middle even when the page hides it.

    Chromium on Wayland sends its own cursor picture, so a CSS rule is not
    enough. Every cursor theme becomes a blank image, and the pointer is
    pushed off the projector.
    """
    try:
        changed = _blank_cursor_themes()
        dropin = Path("/etc/systemd/system/beamloom-kiosk.service.d/hide-cursor.conf")
        text = (
            "[Service]\n"
            "Environment=XCURSOR_THEME=beamloom-blank\n"
            "Environment=XCURSOR_SIZE=1\n"
            "Environment=XCURSOR_PATH=/usr/share/icons\n"
            "Environment=WLR_NO_HARDWARE_CURSORS=1\n"
        )
        dropin.parent.mkdir(parents=True, exist_ok=True)
        if not dropin.is_file() or dropin.read_text(encoding="utf-8") != text:
            dropin.write_text(text, encoding="utf-8")
            changed = True
        if changed:
            subprocess.run(["systemctl", "daemon-reload"], timeout=15, check=False)
            subprocess.run(["systemctl", "try-restart", "beamloom-kiosk.service"], timeout=20, check=False)
        steady_projector_browser()
        park_projector_cursor()
    except (OSError, subprocess.TimeoutExpired):
        return


def _blank_cursor_themes() -> bool:
    changed = False
    theme = Path("/usr/share/icons/beamloom-blank")
    (theme / "cursors").mkdir(parents=True, exist_ok=True)
    index = theme / "index.theme"
    index_text = "[Icon Theme]\nName=beamloom-blank\nComment=Hidden projector cursor\nInherits=hicolor\n"
    if not index.is_file() or index.read_text(encoding="utf-8") != index_text:
        index.write_text(index_text, encoding="utf-8")
        changed = True
    homes = [theme / "cursors"]
    icons = Path("/usr/share/icons")
    if icons.is_dir():
        homes.extend(path for path in icons.glob("*/cursors") if path.is_dir())
    beamloom_home = Path("/home/beamloom/.icons/beamloom-blank/cursors")
    homes.append(beamloom_home)
    for folder in homes:
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        names = set(CURSOR_NAMES)
        try:
            names.update(path.name for path in folder.iterdir() if path.is_file() or path.is_symlink())
        except OSError:
            pass
        for name in names:
            path = folder / name
            try:
                if path.is_symlink():
                    path.unlink()
                elif path.is_file() and path.read_bytes() == BLANK_CURSOR:
                    continue
                path.write_bytes(BLANK_CURSOR)
                changed = True
            except OSError:
                continue
    return changed


_cursor_fd: int | None = None


def _open_pointer() -> int | None:
    if not Path("/dev/uinput").exists():
        return None
    fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
    try:
        import fcntl
        for bit, codes in ((0x40045564, (2,)), (0x40045566, (0, 1))):
            for code in codes:
                fcntl.ioctl(fd, bit, code)
        name = b"Beamloom cursor"
        setup = struct.pack("HHHH", 3, 0x16, 1, 1) + name + bytes(80 - len(name)) + struct.pack("I", 0)
        fcntl.ioctl(fd, 0x405C5503, setup)
        fcntl.ioctl(fd, 0x5501)
    except OSError:
        os.close(fd)
        return None
    return fd


def _nudge_cursor() -> None:
    global _cursor_fd
    if _cursor_fd is None:
        _cursor_fd = _open_pointer()
    if _cursor_fd is None:
        return
    event = "llHHi" if struct.calcsize("l") == 8 else "iiHHi"
    try:
        os.write(_cursor_fd, struct.pack(event, 0, 0, 2, 0, 20000) + struct.pack(event, 0, 0, 2, 1, 20000) + struct.pack(event, 0, 0, 0, 0, 0))
    except OSError:
        os.close(_cursor_fd)
        _cursor_fd = None


def park_projector_cursor() -> None:
    def work() -> None:
        time.sleep(3)
        deadline = time.time() + 90
        while time.time() < deadline:
            _nudge_cursor()
            time.sleep(5)
    threading.Thread(target=work, daemon=True).start()


def steady_projector_browser() -> None:
    """Keep Chromium from crashing when xLights sends a moving picture.

    Pi OS gives Chromium a tiny shared-memory area. Video-sized frames fill it
    and the page dies. This flag makes Chromium use normal memory instead.
    """
    unit = Path("/etc/systemd/system/beamloom-kiosk.service")
    flag = "--disable-dev-shm-usage"
    try:
        text = unit.read_text(encoding="utf-8")
    except OSError:
        return
    if flag in text or "chromium" not in text:
        return
    updated = text.replace("chromium --kiosk ", f"chromium --kiosk {flag} ", 1)
    if updated == text:
        return
    try:
        unit.write_text(updated, encoding="utf-8")
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
    park_projector_cursor()


def show_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")[:40]
    return slug or "show"


def library_root() -> Path:
    return show_root().parent / "library"


def read_config_file() -> dict:
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def clean_playlist(value: object) -> dict:
    raw = value if isinstance(value, dict) else {}
    items = []
    seen = set()
    incoming = raw.get("items")
    if isinstance(incoming, list):
        for item in incoming[:24]:
            if not isinstance(item, dict):
                continue
            ident = item.get("id")
            if not isinstance(ident, str) or not re.fullmatch(r"[a-z0-9-]{1,40}", ident) or ident in seen:
                continue
            seen.add(ident)
            items.append({"id": ident, "enabled": item.get("enabled") is not False})
    return {"loop": raw.get("loop") is not False, "items": items}


def read_show_folder(path: Path) -> dict | None:
    try:
        project = json.loads((path / "project.json").read_text(encoding="utf-8"))
        media = json.loads((path / "media.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(project, dict):
        return None
    files = media if isinstance(media, list) else []
    scenes = project.get("scenes")
    return {
        "id": path.name,
        "name": str(project.get("name") or "Show")[:80],
        "files": len([item for item in files if isinstance(item, dict)]),
        "bytes": sum(int(item.get("bytes", 0)) for item in files if isinstance(item, dict)),
        "scenes": len(scenes) if isinstance(scenes, list) else 0,
    }


def migrate_legacy_show() -> None:
    """Keep an older single stored show when the playlist library is new."""
    final = show_root()
    if final.is_symlink() or not (final / "project.json").is_file():
        return
    info = read_show_folder(final)
    if info is None:
        return
    ident = show_slug(info["name"])
    library_root().mkdir(parents=True, exist_ok=True)
    dest = library_root() / ident
    if not dest.exists():
        shutil.copytree(final, dest)
    shutil.rmtree(final)
    final.symlink_to(dest, target_is_directory=True)
    playlist = clean_playlist(read_config_file().get("playlist"))
    if ident not in {item["id"] for item in playlist["items"]}:
        playlist["items"].append({"id": ident, "enabled": True})
        save_config({"playlist": playlist})


def link_active_show(dest: Path) -> None:
    final = show_root()
    final.parent.mkdir(parents=True, exist_ok=True)
    if final.is_symlink() or final.is_file():
        final.unlink()
    elif final.exists():
        migrate_legacy_show()
        if final.is_symlink() or final.is_file():
            final.unlink()
        elif final.exists():
            shutil.rmtree(final)
    final.symlink_to(dest, target_is_directory=True)


def stored_shows() -> tuple[list[dict], bool]:
    try:
        migrate_legacy_show()
    except OSError:
        pass
    playlist = clean_playlist(read_config_file().get("playlist"))
    enabled = {item["id"]: item["enabled"] for item in playlist["items"]}
    order = [item["id"] for item in playlist["items"]]
    rows = []
    folder = library_root()
    if folder.is_dir():
        for path in folder.iterdir():
            if not path.is_dir() or not re.fullmatch(r"[a-z0-9-]{1,40}", path.name):
                continue
            info = read_show_folder(path)
            if info is None:
                continue
            info["enabled"] = enabled.get(path.name, True)
            rows.append(info)
    rows.sort(key=lambda item: order.index(item["id"]) if item["id"] in order else len(order))
    return rows, playlist["loop"]


def save_playlist(loop: bool, items: list[dict]) -> None:
    save_config({"playlist": clean_playlist({"loop": loop, "items": items})})


def show_status() -> dict:
    rows, _loop = stored_shows()
    enabled = [row for row in rows if row["enabled"]]
    chosen = enabled or rows
    if not chosen:
        project_path = show_root() / "project.json"
        if not project_path.is_file():
            return {"saved": False, "name": "", "files": 0, "bytes": 0}
        try:
            project = json.loads(project_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"saved": False, "name": "", "files": 0, "bytes": 0}
        return {"saved": True, "name": project.get("name", "") if isinstance(project, dict) else "", "files": 0, "bytes": 0}
    row = chosen[0]
    if len(enabled) > 1:
        return {"saved": True, "name": f"{len(enabled)} shows", "files": sum(item["files"] for item in enabled), "bytes": sum(item["bytes"] for item in enabled)}
    return {"saved": bool(enabled), "name": row["name"], "files": row["files"], "bytes": row["bytes"]}


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
    project = json.loads((stage / "project.json").read_text(encoding="utf-8"))
    ident = show_slug(project.get("name") if isinstance(project, dict) else "Show")
    library_root().mkdir(parents=True, exist_ok=True)
    dest = library_root() / ident
    if dest.exists():
        shutil.rmtree(dest)
    stage.rename(dest)
    rows, loop = stored_shows()
    items = [{"id": row["id"], "enabled": row["enabled"]} for row in rows if row["id"] != ident]
    items.append({"id": ident, "enabled": True})
    save_playlist(loop, items)
    link_active_show(dest)
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
    result = {"pcUrl": url if isinstance(url, str) else "", "playMode": mode}
    result["schedule"] = schedule.clean(data.get("schedule") if isinstance(data, dict) else None)
    return result


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
    kept["schedule"] = schedule.clean(current.get("schedule"))
    kept["playlist"] = clean_playlist(current.get("playlist"))
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


def screen_target(mode: str, url: str, stored: bool, pc_up: bool, lighting: bool, scheduled: bool | None = None) -> str:
    """Choose the projector page.

    The Windows picture is used only while that app answers. A dusk clock can
    hold the stored show until sunset. xLights data and an explicit stored-show
    choice still play.
    """
    if mode == "show" and stored:
        return "/play"
    if pc_up and url:
        return url
    if lighting:
        return "/play"
    if stored and scheduled is not False:
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


def show_media_path(media_id: str, root: Path | None = None) -> tuple[Path, str] | None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", media_id):
        return None
    base = show_root() if root is None else root
    folder = (base / "media").resolve()
    path = (folder / media_id).resolve()
    if path.parent != folder or not path.is_file():
        return None
    mime = "application/octet-stream"
    try:
        items = json.loads((base / "media.json").read_text(encoding="utf-8"))
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and item.get("id") == media_id and item.get("mime") in SHOW_TYPES:
                mime = str(item["mime"])
    except (OSError, json.JSONDecodeError):
        pass
    return path, mime


def _form_number(fields: dict, name: str) -> float | None:
    raw = (fields.get(name) or [""])[0].strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


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


def page_nav(active: str) -> str:
    setup = "active" if active == "setup" else ""
    playlist = "active" if active == "playlist" else ""
    return f'<nav class="tabs"><a class="{setup}" href="/">Setup</a><a class="{playlist}" href="/playlist">Playlist</a></nav>'


def playlist_action(fields: dict) -> None:
    rows, loop = stored_shows()
    ids = [row["id"] for row in rows]
    action = (fields.get("action") or ["save"])[0]
    ident = (fields.get("id") or [""])[0]
    if action == "remove" and ident in ids:
        target = library_root() / ident
        if target.is_dir():
            shutil.rmtree(target)
        remaining = [row for row in rows if row["id"] != ident]
        save_playlist(loop, [{"id": row["id"], "enabled": row["enabled"]} for row in remaining])
        if remaining:
            link_active_show(library_root() / remaining[0]["id"])
        elif show_root().is_symlink():
            show_root().unlink()
        return
    if action in {"up", "down"} and ident in ids:
        index = ids.index(ident)
        swap = index - 1 if action == "up" else index + 1
        if 0 <= swap < len(ids):
            ids[index], ids[swap] = ids[swap], ids[index]
        enabled = {row["id"]: row["enabled"] for row in rows}
        save_playlist(loop, [{"id": item, "enabled": enabled[item]} for item in ids])
        return
    chosen = [item for item in fields.get("order") or [] if item in ids]
    for item in ids:
        if item not in chosen:
            chosen.append(item)
    checked = set(fields.get("play") or [])
    save_playlist((fields.get("loop") or ["1"])[0] != "0", [{"id": item, "enabled": item in checked} for item in chosen])


def playlist_page(error: str = "") -> str:
    rows, loop = stored_shows()
    loop_on = " checked" if loop else ""
    loop_off = "" if loop else " checked"
    if rows:
        blocks = []
        for index, row in enumerate(rows):
            checked = " checked" if row["enabled"] else ""
            ident = escape(row["id"])
            label = escape(row["name"])
            blocks.append(f"""
            <div class="row">
              <input type="hidden" name="order" value="{ident}" form="playlist-save">
              <label class="check"><input type="checkbox" name="play" value="{ident}" form="playlist-save"{checked}> {label}</label>
              <span>{row["scenes"]} scene(s), {row["files"]} file(s)</span>
              <button type="submit" form="up-{index}" {"disabled" if index == 0 else ""}>Up</button>
              <button type="submit" form="down-{index}" {"disabled" if index == len(rows) - 1 else ""}>Down</button>
              <button type="submit" form="remove-{index}">Remove</button>
            </div>
            <form id="up-{index}" method="post" action="/playlist"><input type="hidden" name="action" value="up"><input type="hidden" name="id" value="{ident}"></form>
            <form id="down-{index}" method="post" action="/playlist"><input type="hidden" name="action" value="down"><input type="hidden" name="id" value="{ident}"></form>
            <form id="remove-{index}" method="post" action="/playlist" onsubmit="return confirm('Remove {label} from this Pi?')"><input type="hidden" name="action" value="remove"><input type="hidden" name="id" value="{ident}"></form>""")
        listing = "".join(blocks)
    else:
        listing = "<p>No shows are stored yet. In the Windows app, open a show and press <strong>Send show</strong>. Sending the same name again updates that show.</p>"
    problem = f'<p class="error">{escape(error)}</p>' if error else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Beamloom playlist</title>
  <style>
    :root {{ color-scheme: dark; }}
    body {{ margin: 0; background: radial-gradient(circle at 50% 0%, #18283a, #0e0f12 55%); color: #f4f1ea; font: 18px/1.45 "Segoe UI", sans-serif; }}
    main {{ max-width: 40rem; margin: 0 auto; padding: 2.5rem 1.25rem 4rem; }}
    h1 {{ font-size: 2.4rem; margin: 0 0 0.5rem; }}
    p {{ color: #b7b2a8; }}
    .eyebrow {{ color: #70dfcb; font-size: .8rem; letter-spacing: .16em; font-weight: 700; text-transform: uppercase; }}
    .tabs {{ display: flex; gap: .5rem; margin: 1rem 0 1.4rem; }}
    .tabs a {{ color: #b7b2a8; text-decoration: none; padding: .45rem .9rem; border-radius: 999px; border: 1px solid #3a3d44; }}
    .tabs a.active {{ color: #1a1408; background: #e4b15a; border-color: #e4b15a; }}
    .card {{ background: #181d26; border: 1px solid #3a3d44; border-radius: 16px; padding: 1.5rem; margin: 1.2rem 0; }}
    .row {{ display: flex; flex-wrap: wrap; align-items: center; gap: .6rem; margin: .9rem 0; }}
    .check {{ display: flex; align-items: center; gap: .4rem; margin: 0; min-width: 10rem; }}
    .row span {{ color: #b7b2a8; font-size: .9rem; }}
    label {{ display: block; margin: 1rem 0 0.4rem; color: #f4f1ea; }}
    input[type="radio"], input[type="checkbox"] {{ width: auto; height: auto; }}
    button {{ height: 2.4rem; border: 0; border-radius: 8px; background: #e4b15a; color: #1a1408; font: inherit; padding: 0 .8rem; cursor: pointer; }}
    button[disabled] {{ opacity: .35; }}
    .error {{ color: #ffb4b4; }}
  </style>
</head>
<body>
  <main>
    <div class="eyebrow">Projector player</div>
    <h1>Beamloom</h1>
    {page_nav("playlist")}
    <section class="card">
      <h2>Playlist</h2>
      <p>Checked shows play from top to bottom. Loop on repeats the list. Loop off plays it once, then the projector stays dark. The PC can be off.</p>
      <form id="playlist-save" method="post" action="/playlist">
        <input type="hidden" name="action" value="save">
        <label class="check"><input type="radio" name="loop" value="1"{loop_on}> Loop on</label>
        <label class="check"><input type="radio" name="loop" value="0"{loop_off}> Loop off</label>
      </form>
      {listing}
      <button type="submit" form="playlist-save">Save playlist</button>
    </section>
    {problem}
  </main>
</body>
</html>
"""


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
    rows, looping = stored_shows()
    enabled_rows = [row for row in rows if row["enabled"]]
    if not rows:
        stored_note = "No show is stored on this Pi yet. Send one from the Windows app."
    elif len(enabled_rows) == 1:
        stored_note = f"Playlist: <strong>{escape(enabled_rows[0]['name'])}</strong>. It plays on the projector when the PC is off."
    elif enabled_rows and looping:
        stored_note = f"Playlist: <strong>{len(enabled_rows)} shows</strong> play in a loop when the PC is off."
    elif enabled_rows:
        stored_note = f"Playlist: <strong>{len(enabled_rows)} shows</strong> play once when the PC is off."
    else:
        stored_note = "Shows are stored, but none are checked on the Playlist tab."
    mode = config.get("playMode", "auto")
    options = "".join(
        f'<option value="{value}"{" selected" if mode == value else ""}>{label}</option>'
        for value, label in (
            ("auto", "Play the stored show when the PC is off"),
            ("show", "Always play the stored show"),
            ("live", "Only show the PC"),
        )
    )
    clock = schedule.status(config.get("schedule"), datetime.now().astimezone())
    clock_checked = " checked" if clock["enabled"] else ""
    latitude = "" if clock["latitude"] is None else clock["latitude"]
    longitude = "" if clock["longitude"] is None else clock["longitude"]
    clock_note = escape(clock["note"] or "The Pi clock is off. The stored show plays whenever the PC is off.")
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
    .tabs {{ display: flex; gap: .5rem; margin: 1rem 0 1.2rem; }}
    .tabs a {{ color: #b7b2a8; text-decoration: none; padding: .45rem .9rem; border-radius: 999px; border: 1px solid #3a3d44; }}
    .tabs a.active {{ color: #1a1408; background: #e4b15a; border-color: #e4b15a; }}
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
    {page_nav("setup")}
    <p>Set up the Pi from your PC. The picture appears on the screen connected to this Pi.</p>
    <p>{stored_note}</p>
    <section class="card">
    <h2>Dusk clock</h2>
    <p>The Pi's clock says <strong>{escape(clock["now"])}</strong>. {clock_note} The PC can be off. Choose <strong>Always play the stored show</strong> above if you do not want the clock to wait.</p>
    <form method="post" action="/schedule">
      <p>Clock</p>
      <label style="display:inline;margin-right:1rem"><input type="radio" name="enabled" value="0"{"" if clock["enabled"] else " checked"} style="width:auto;height:auto" /> Off</label>
      <label style="display:inline"><input type="radio" name="enabled" value="1"{clock_checked} style="width:auto;height:auto" /> On</label>
      <label for="start">Start at (leave blank to use sunset)</label>
      <input id="start" name="start" value="{escape(clock["start"])}" placeholder="18:30" />
      <label for="latitude">Latitude, only for sunset</label>
      <input id="latitude" name="latitude" value="{latitude}" inputmode="decimal" placeholder="40.71" autocomplete="off" />
      <label for="longitude">Longitude</label>
      <input id="longitude" name="longitude" value="{longitude}" inputmode="decimal" placeholder="-74.01" autocomplete="off" />
      <label for="after">Minutes after sunset</label>
      <input id="after" name="after" value="{clock["afterSunset"]}" inputmode="numeric" />
      <label for="end">Stop at</label>
      <input id="end" name="end" value="{escape(clock["end"])}" placeholder="23:00" />
      <button type="submit">Save clock</button>
    </form>
    </section>
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
    html, body, iframe, * { margin: 0; cursor: none !important; }
    html, body { height: 100%; background: #080b12; color: #f5f3ed; font: 20px/1.5 "Segoe UI", sans-serif; overflow: hidden; }
    iframe { position: fixed; inset: 0; width: 100%; height: 100%; border: 0; background: #000; }
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
    let picture = "0";
    let channelSocket;
    function connectChannels() {
      if (channelSocket) channelSocket.onclose = null;
      channelSocket = new WebSocket("ws://" + location.host + "/sync/live?picture=" + picture);
      channelSocket.binaryType = "arraybuffer";
      channelSocket.onmessage = (event) => {
        if (picture !== "1") return;
        const frame = document.getElementById("out");
        if (!frame.contentWindow) return;
        if (event.data instanceof ArrayBuffer) frame.contentWindow.postMessage({type: "beamloom-sync", payload: event.data}, "*", [event.data]);
        else frame.contentWindow.postMessage({type: "beamloom-sync", payload: event.data}, "*");
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
        } else if (data.clock && data.clock.enabled && data.clock.on === false && data.show && data.show.saved) {
          title.textContent = "Waiting for dusk";
          message.textContent = data.clock.note || "The stored show starts at dusk.";
          step.textContent = "Pi clock: " + data.clock.now;
        } else {
          title.textContent = "Ready for your show";
          message.textContent = "The Pi is connected. Open Beamloom on your show PC.";
          step.textContent = "Open http://beamloom.local to check settings";
        }
        const target = typeof data.screen === "string" ? data.screen : "";
        const nextPicture = target.startsWith("http") ? "1" : "0";
        if (nextPicture !== picture) {
          picture = nextPicture;
          if (channelSocket) channelSocket.close();
        }
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
        want_picture = "picture=0" not in self.path
        last_matrix_at = 0.0
        last_matrix_sent = 0.0
        while True:
            matrix_at, matrix_size = sync.matrix_marker()
            now = time.monotonic()
            # One latest frame only. A 256 x 144 picture is about 20 fps; the
            # smaller picture can move a little faster. Older frames are dropped.
            interval = 0.05 if matrix_size == sync.MATRIX_BYTES else 0.033
            packet = sync.matrix_packet() if want_picture and matrix_at > last_matrix_at and now - last_matrix_sent >= interval else None
            try:
                self._ws_send(1, json.dumps(sync.frame(include_matrix=False), separators=(",", ":")).encode("ascii"))
                if packet is not None:
                    self._ws_send(2, packet)
                    last_matrix_at = matrix_at
                    last_matrix_sent = now
            except (BrokenPipeError, ConnectionResetError, OSError):
                break
            time.sleep(0.03)

    def _ws_send(self, opcode: int, payload: bytes) -> None:
        size = len(payload)
        if size < 126:
            header = bytes([0x80 | opcode, size])
        elif size < 65536:
            header = bytes([0x80 | opcode, 126]) + struct.pack(">H", size)
        else:
            header = bytes([0x80 | opcode, 127]) + struct.pack(">Q", size)
        self.wfile.write(header + payload)
        self.wfile.flush()

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
            config = load_config()
            clock = schedule.status(config.get("schedule"), datetime.now().astimezone())
            stored_show = bool(show_status().get("saved"))
            data = json.dumps({**config, "wifi": wifi.status(), "update": updater.status(), "join": JOIN, "display": display_status(), "show": show_status(), "pcUp": pc_is_up(), "sync": snap, "syncShow": sync.show_command(snap["multisync"], time.time()), "clock": clock, "screen": screen_target(config.get("playMode", "auto"), config.get("pcUrl", ""), stored_show, pc_is_up(), bool(snap.get("universes") or snap.get("matrix")), clock["active"])}).encode("utf-8")
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
        if path == "/playlist":
            self.send_html(playlist_page())
            return
        if path == "/show/playlist":
            rows, loop = stored_shows()
            self._json({"loop": loop, "items": [{"id": row["id"], "name": row["name"], "enabled": row["enabled"], "files": row["files"], "scenes": row["scenes"]} for row in rows]})
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
        library_match = re.fullmatch(r"/library/([a-z0-9-]{1,40})/(project|files|media/[A-Za-z0-9_-]{1,64})", path)
        if library_match:
            show_id, kind = library_match.group(1), library_match.group(2)
            folder = (library_root() / show_id).resolve()
            if folder.parent != library_root().resolve() or not folder.is_dir():
                self.send_error(404)
                return
            if kind == "project":
                project = folder / "project.json"
                if not project.is_file():
                    self.send_error(404)
                    return
                self._send_file(project, "application/json")
                return
            if kind == "files":
                try:
                    items = json.loads((folder / "media.json").read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    items = []
                self._json(items if isinstance(items, list) else [])
                return
            media_id = kind.removeprefix("media/")
            found = show_media_path(media_id, folder)
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
        if path == "/playlist":
            try:
                playlist_action(fields)
            except OSError:
                self.send_html(playlist_page("The Pi could not update the playlist."), 500)
                return
            self.send_response(303)
            self.send_header("location", "/playlist")
            self.end_headers()
            return
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
        if path == "/schedule":
            saved = schedule.clean({
                "enabled": (fields.get("enabled") or [""])[0] == "1",
                "latitude": _form_number(fields, "latitude"),
                "longitude": _form_number(fields, "longitude"),
                "afterSunset": _form_number(fields, "after"),
                "start": (fields.get("start") or [""])[0].strip(),
                "end": (fields.get("end") or ["23:00"])[0].strip(),
            })
            save_config({"schedule": saved})
            if "application/json" in self.headers.get("Accept", ""):
                self._json({"ok": True, "clock": schedule.status(saved, datetime.now().astimezone())})
                return
            self.send_response(303)
            self.send_header("location", "/")
            self.end_headers()
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
