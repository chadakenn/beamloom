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
        steady_projector_browser()
    except (OSError, subprocess.TimeoutExpired):
        return


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
