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
            # Keep only the latest complete frame. Limit the largest picture
            # so the kiosk can render it without building a playback backlog.
            interval = 0.083 if matrix_size == sync.HD_MATRIX_BYTES else (0.05 if matrix_size == sync.MATRIX_BYTES else 0.033)
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
