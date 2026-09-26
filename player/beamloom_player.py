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


def show_status() -> dict:
    project_path = show_root() / "project.json"
    if not project_path.is_file():
        return {"saved": False, "name": "", "files": 0, "bytes": 0}
    try:
        project = json.loads(project_path.read_text(encoding="utf-8"))
        media = json.loads((show_root() / "media.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"saved": False, "name": "", "files": 0, "bytes": 0}
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


PLAY_PAGE = "eNqlPG1T20jS3/MrJr66KxmEkWQbzFtSJECWOkLyANm9LYpiZXtsayNLPkkG+/b470+/zEgzsp1k97YqIM109/T0e4+GPX49TAfFcibFpJjGb14d4y8Rh8n4pCGTBg7IcPjmlRDHU1mEYjAJs1wWJ415MdrpNcQuTRVREcs372Q4jdN0KvJJ+ny8y4M4nRdLfhK0iiv66XAp/hDTMBtHyaHwjsRERuNJcSh8z/v7keiHg6/jLJ0nw0PxN8+D+cE8y9PsUCRpIo9E+iSzUZw+H4pJNBzK5Ei8EPVBmDyFOVAeRvksDpeHoh+ng69H4jkaFhNN3V4LMY93FYvHu7zdY+QQfimC0fCkkc6LxpvjXR6BqXyQRbPizatBmuSF+Ofl9dmtOIGln8McVvJckQMoLOKCNIsiGshDEbhCTvsyyw9F2xVZlIzhqeOKQRrPpwk8d10xlvGh2HNFIlPA3ndFOM/SLDwUPYRLRhJoHYoDV8yyKJ/iJlxRRLEEbB/WmkXJ80QiDT8QL0eKuw/nV8jc/b3XOoA1vNZegD/9vQdX4Fgb3w7wR6/DQ/sE4PUILOAxv8LsdnmoQ28B/dwPHh70gj+f39zBgr/9DRSVR2ki2p4nZP4KdAJydEApYQHDJ15TRIl4koNAhO/jaHb06imNhmAYUeI0QZjj+PFzmkcIC+QAruMQHDHnCr/lNUGDv+llL25OP6xbdpbJQUQDE1D9TIDthMXRK2CFaIpRFo6PXs2TaJRmU1i9aIv5ZfJUDRGH8xuZV0NEQ8zvoqlcGfw0CwdRsVwZv5BhMZFZNR4lMPoxzL/Whj7NizhK5HtwgaLOhZq7B+2tLPAuQ9NOZL7KKKxSmEur4fdpUmQwtTJxGxbzjLRU4+2fUTK0eAJhfZBxNZSH01kss+BMzH+OhjKt4f8U5mqYV5qAwzi0tRmqPJOwboIqGRRODnYwTAsHFI4Qjh/soxm2fb+132w2xZbotPe7vVa30237QRuNQVFN0iiXFVlwcnqOwDwAIM2cGQDT0AiHaDUYAjjGD2GUOIsAjof65ZDYVuygEYIlNkuYwQpMaaglzHA9HYbRjM6RK9gf/nPaLU/siAB+wgDBKClNo4WD/0KIqa6YtxZNl8YGrhjq93lrCSgvtmfpZWYL9qvAAVe7ADd4D7IZthYuWXtrCctaE0vNYVtMABO9BHjCd2e2UA5ZbuEJN9paLMUu/PpPiQjhjhdto3AIPhoJpzQMcXIifOZRKOBCLmC/0mGDAuaemq1s3EfUFyHjXDIFNE3E9jS2sgWgwPYwR26DVkcLntwXhoAPiMPGW8Cq0BSmNoUu6aNOoattwWAclaF26lMwVVB+t+lqERz0OHxSKO3BeD5N02IC7jpDtK4KzgkwPX8CleBigG+ss63EqeyxR6Q6XfSPWfrsTF3kuEmI3W6FtnVC6wJdXBimrYUpHwClWCbjYoIb39EW3VX0mYd1GvBtDRSTDPIqyMNawWt3VSAP+7nDPqh2GATI8A4yzL86+5ZC+svSaysN+L4NA/UIQMnFzNlBMTDtHcBFUfgdXDioFMZIkDmKFT6DdWwuMPp4dTZ7lvq1hvdIw6TnToCrO0oiWyz6bV6XNgHz25Y6DzjvIhpuaVXtiGTYVrBRK4GtlfFidafdTVvtoaQsUY2XqwrdpM/uKnYWoUFMw4UzhsgxXlqzAxnHOkxyvJ6rQBM4PVxhDUEoCAVadLtLFr3XRTmDZugNXzCbaGvxKQjQMltirxU01+qN9tNj/+ygAojrLV5ruwTrck3ENRWBocTGy016aNvRTYfCfVZfGSHU7tJMOJg5MXdBKRyJY6j64Pf2tiajRTBS6S0sMG1ZU/lCi5NkOIowWO8361AzkqCHMrOBD1BEbKCdGk7lijZKu+U30Su0yPNZbTXUv4ouRnjJwRryJS1mJkeD1zUhr7PnKt/ZYodHLXX2VHoRVOWv00TH9oiszhE5dskIxmK/HjGwjl9xBBXsTU/IgM4+JY4qYkG4p0W8PZvmIM2kDl2I124Fm9KK8jk2mr0qq3C04aIeh5HNZt1mVUjCLdKSWxTXN5lt1xYWdIkyB2bAH49qw2WVpYIHgVo7nEzI0gLOPpCEvumrGCGJLr5UuY9JRUkOVQGqAIVvBS1el9OrnRvCTCP4pJPJxKXsiqJgguviAYmr26scHemUMjV6Jq9dEcKt8SIAzT7U3ijj/ZpBRv0+9T4kD96Uj4Xgth7B6HpAA5VZ7ZHRBjVjO6iZ7Qyq9Ioy0vG50FTr7Neo7q8Lt5hYTb0xwxyfNxVCgQpwVGB06oUQh8FuQGozCSO/KzThqcRnJzjo0M9eDd8Q4F5NMB0z+G8ZZnmgQv0mZfVsZT2HT9JWVV0x3W6luAX5tc0JWY3f6tZsFVdbrWNwXzu8KMUSCn7dtVVNLqFB3kCkg85VUWmy5i0idpryKNZ6JGbvoLmuHuGKSedFdpRkuNbHK5Vsb1JJRXevw2FeaRhp8M4Qp9ddywoZVZtRqPQiVrYVJvtjsNEfD9anap2kA0sI61I1kP6TqXo1U3cwk9pAm5JuD2yoaYiSJLCSzQNKzdS19CrK1LUNZVxg82tkZEjIq/m4u1I6hNlXbWHYsxMhl+lROAo8rwwKuoecS0oDlU0M0tyBcqzX9rEhqW1un4qQMt5S5m9T/tvbb67UB0h8S/GFXrX37VLAr3WNyu2sfMJVY9mFdbqW9/o6x9h748111uxOWeI3t6Ok+yzlzPRfgy2DoaDGkCovuuzNuIFeLS6zkBzVhdAym5u6sqsjS1E1+uby/KjWg5MyEcuamcFw3Qrs7L8P4wmX6Si5Pynk5HsSrgnCV7EfSTFv6vdmuQSWXFBPung0NxpSnRgWYeLMWktXzFoLSxBhNl2TUFEUiFlPFj44Ovhh5VLaDaOktFrE29Vis+Kr92elSHR/yFRHIRVjXPGsOcrYr84UZlVMCVRlvTbjqIKBC10MAKwsFNgWr1frmLtltCeH0cs1VR+7WoOZMR5PM0kOXq9KUkvlPHadxSax7gALFlFhiGOYfby2BDLG6QXxZR4lkIqYQUXFOtrVnGL1U6GUZ7lsO9VZZjyfYkTHoGyWS4Ef8LmE32UB7weqDWbqgziczpyycEMqTfpY4Zqnw03zLL5cUg7Hkiq0xJmqLO8qk8BnOqZkuRrDy2Z1GIiH4msOkqCilgX3qL0jq5YvBVbaYRZO6zzAOkRBL8rkVnj6BtiydjA4j2P+OIG42OypZVAn3P1V1Rp1w8AtEzBERKy6mthKnNGyqB3fqK5nrXyt+jEtinRauiTyY3FADL7hAPyWyCFlV+E1xaGqNDcdBKp2rHQD8+MF0i1PO/op2FXZrY1C2KDJ5zDKITYO5F16zowFZWO57ghkr1ZX4doRrmcx0BT9TIZfdWmARH4HInj07qNMbW7fCg+2S5NWUYTuU354iR5c+hZQDvz+YAHjGEz3QUyhNTGI01zmhU4PIco0oqaWXQ0dlGdcmmhC8MbzMRzHdzVKDof/+XXfw/9WpIgKtQfL+KsYqionlKETojmoZvg1BJm+8f6Pf3B3eIzDaOchGBvmB2XlIQLtMo5622aYUu+vzfb6pe4KkvhTwG/ruzkUO/ZIaXnKJdIRiVd9aAO2UVQ+ELKPZ9wSxKXF0cirOakJV5+CWEH6w54hdswQuKjWofrOVg+KEPr1B0xqMlHFIX6W+e3o1avRPBnQJ8783/Mwg5393zwcOgXE2QII9fFfzHbOnzmHCx+/iWSkgH6Grj9cqqElDwGLw0WAVhhbUGpIQx2VNOl8sGBgorxNOAgXt+hEjueXPL/k+SXPG3SGFJ6Rwy1abof4wGdfx/bX13P8Ct6K8osoiQoJnQK46X//Kz6CRloYMmkAXFzuQAGrPnUlEByrZVCaTr6oLZKT8Q0xcOPxksNs5MilgvUVgPENLZHP4gIV3Q5OsyxcOvdKsiSNbYGlV0HiU+IlKZTjIOmxq8WsUCbY8JLYlKwVihoHlIlLsPQTU+ADfaIrDSFK8HvAT+k0HWfhbLJ0pqb+Q89Db7n3IBCFnk/PbXoO6Bk/64c+w/j0zDAdemaYfXwOGCagZ4bp0jPD9B4qgQ9oTaS0RfM7RAmfoSwbEBN6wKNJjwFxMqBJHvBpkql4BnliFzdQAnl+SYH4x12XaytADyeJvIKmtRWgb5APvArINyjgnYlB4Fdr+wYF7O4HQVCt7RuM+V7d6BkIBbWtgFAu24oyiOGvOAB2pWs9AEwEU/oPmPOA+AJ4VlT5GJSPfgXgVwB+BRBUAEEFECgANl51B0NdmcFyczCfyqRojWVxHkt8fLe8HDp0k6apr2yMqdIkHATEElYuCqfxLPvjOGi44g8RxtB+HXK9AMaZFFEYR2F+CN43l3gRRkLhVESzOJLDU4bFGfFSLjLL0I+wBBrHrQHUA4X8zEMOwJReN0insyiWDt6HgoiXzrOBNP0un0CrkZlUbmmEECjOwwQD3RKywy8lLQWi1lHIDFNWvq8BAATBk59DrAyLEspF9PefPn6+vDp/vL07vftyC0VlMcnSZ1L8eZZBL25SuExG6VU61quglTX4uWFeJOAhVCMgh0URDiaKPSU7t5QOAOD1nvN/Pd7+dHp2fuPSbR+sIX4EFa/ofDy/viuRcUAh96GfPi2KLOpfqQtCFQnw9AZd/WkwLFRCX7UOFRBPzHO5Os76689HI1t/72jEqZZXA/B2enNz+uvjuy8XF8gloyo4ej6DRn4VrtMjFZ39en368fL949nN6S+MJJOwH8ufIarLBe+RvdPj6Sdj4nMKVSowgWewRO3i6tPpnasdADvcckvqYoS5pzt1V6LalB6BV1Db3Zeb88fgzNW4DAcvl9NwLIOzOphHPNx8eHfq4m023x6Bhy/Xt5cfrs/PHt/9enfukh1+gR30VPjxmGXYTLf70CxXK007qi9ovP5yc/r58Zat/ur04+fHu0+P52cfzv8Clbv/lcrHy+vHi8urO1QzDF9dXp+f3vxJEqcf1pJgXcYp3h764wUiEvY7PJhgE5uOxH0D79pAPGzgxRz6jScH9KCqUnpWZS09Y9/IAEaPQwPVYYIGLBSOPkOgl6rLp1c876KHDzKm33TaQU/66KPx0MR93CPbD2yVEIq+8P2vVa9GMNg/YLQ0k99HKvcDBZCKBuqCmR85RErdEqrcJELTxqSExvkxnDnlzBOC1mZiSSnjdznAtM5pF8emchhhM3D/wO/5QCbyMhnKBbWl1dhtEYI74+nxTGbIGDYsrSR91tRDSDhP8hZhAajRMJuAUVQ4VrU/w5BFpQE2SM+ghPS5NZRP0UB+jhYyvkH5YGAH1wyaVYXwXKJBDwmRhJ7pVq2jEu4AUmZS/IKXY7E6nmVNA33yg+g/0XVaEx/TmAKhi7fQRZ4AN8ChGuUbuDQ8wTt/FjCAHtUAAYwv6mKkjOTzLM0Kh4OKieraaHZJzSn4AtJjNDTFC/UXFgak29YIhOs4sKkMOomTN4KeWnhRBVgFvDJJI9ZKYYYztwV+aHdwHtQF1t3K0RjyXyLotxtkh7uNZonKhonmTmyBiOwq74nPE5WZajgjcTMAtOX00MJLRUswv0LiSUgAjS8DHCq6hkAgUX7ETTtkspZIhtohbmE9mm7l82wUDoDVKfiIg48kIHxo0RKXwyaIL8bE9S5NYxkmbAxGLLuPhi7z84AhjffUVAIdgtrCHHfXVHuZhcCiUycCygBcAK8+zP0lNVqKBBpFlMxlNfGjejRPn14rbZb70JMlkzivREvZ1ilPXgRPttIEaneMHA5xrijmpHeXX1dw8gwTR2MX793vkgR2G9B3REMNyKcsxpHia2VPK5zaVleW8FxZqCreadB8o/qUR+qazjnkYe19pMbiNJ3VhvBefn6ZqFBvzoTzIsVZPWxR/+4eK+pOswUpYzBxWIR/vNiMVtKkV31BqBKO7WtshsOmqA9vXEkfhLLjgNVhnDMivpa2nQQ0tHHiaSqj9JfWUxjPZe6g0kBO+HcUvPXBPMtAO/Rxgk5JXwQxJxyJXQGAv3xbSPxl1IqZyNM1pC1IXVYjhOMYI3SWhPhD1R60tFz1qYkWQzYhDtkjEJDuH8poymMtPpXc0O8OVSViZiVIeNxKs6zz+yojP7Q0wi19588puPr8ERT/pEStDTvD0yEza0Pg1LhaVVamd4y3bfxA8XdhbeCoQqkKgUTdIjFarhWWrfA8zEJD7lQU6PYRgmv2Po3TzClra9+adKhLvPp0o/qSx3eXd0Zmz02T0+q1lcE38f8NhlacJhBlkKULrHAd5AtshTfBNlPLJIqTtY0Yz3C1Foy4WoN69nt53ETzFZo+aPWNnUFFMlPx1ToD8c26KM24i8fOxKceizut9kMt1WByQ8ezMyDa0f2DtgwUmUqCedTHC1Un6tMGwr3muZQLdH0cTab42nYYghukWSIzNlVzQBmWOMb7inauUgccyOmJlY3B5XzwstJXPLeqITul3xBGPpOSi4/ymsmquDGuuOwvu+RBdLs8HFRXsoiRhWZDs071Ar9QpHH+EItDwQN0p8LW/LKcW1Zzqgx8aVprAXfPYUa3ys1z89mCDkbhl8+/Av7VfrCw+fxM04AAtnLmquasaiF5qiuA7AVreuPbVP3TlDJO2ldNPvdkjffRQ/kNCW34PsILM9hAGYLCY0t/FQpj0AMdBe6YogvMDyzlqcXtvL/+4AJLaSC5on6wmSxatEdPbAWXePCnDiJQGJuspfxQYtqZcgOyNG8javlhxkQd8eAm1KgMCV9dFu+Uv5lCycANU0P5Q20yzAYTnArwK6dlH2nZjq5xVDVJ38PMAe2o+NVz09wxqGpvZVKC8S0dZ4ZnP+gnSs30jsD1I2OawO9qG+f4a52Co++75jtyUb0va/NLmiceMHebnJaZe50CzIMGV9gbN/yoNmHlhCeLkrsayzXyKA4LbNgxoEDcgOiA4eUenx+am+NYdfRhW1i/HP+OfeoTEndF7ia5gYJqovzWToAg/Y2LVCcv314mr+5h1BcyptYvpXSGpzou/wHrPSFC0f71Qbx9W3OIscSjevxT0ntzGRhuPqDEaMZbMY222tEHGdNft1Jwxt+++h3YcZn79NVkVvXvVs9ZdrY6zP3Ieae2Q/OIH//jcvqHT0O/cQiqD/zXyFsflVHlouKzqJfq38TzSjzVtXwHWMuGz6BxR++uzq/PDEGwB4A7DlVYHA4b5JY0dgE1KWJ9uj6nvcJvhVv2THUCOXSMMvk2DTxR/XL7eHvz/pGKVZPmj6GdXn3+6bTaH5amFCNy0trN5en1h6vzW1JadVXrW2UtFOBhvkwGomqBsIK3zuMymc/gAU00fA4jqEMk9lGqNVVtTqOqpzV8K/2qWxucqw4YmUoJ9nueJo5RrsZRzi3EmtVG+JffvJY+nGRwWAx8hjHUCNMtw3etk/uL7Zv6IE2drO4ocjp/oZbG0YdLEJnLdhgNRJMzeuBLrrSsVksRpuT0Vr/h/zDg+3pU56RgyedP0BZfoRCgNnIaIOjoP3hwDj0VQCoFH7063tV/0n+8q/78f5f/pwj/DyGy4ek="


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
