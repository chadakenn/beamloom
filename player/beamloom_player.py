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
    (ROOT / "sync.py").write_bytes(zlib.decompress(base64.b64decode("eNrNW1tz2ziyfuevwFFqz5AZmZZkx/EqkasUS0m841tZymS2vC4WJEIW1xTJIcHY3pz899PdAO+U45nNw3gmlkgAjUaj++sL4E6n8/7ykp2lvvRmj8GS/cymfXuvz8xkfHxuweNkcslisRTeFxEnbBXGTK4Feyf4xg/DDbv0WOTzRxHbhvGLEFHCOEs23PdZ5MEoFq6gfyy4u5PwlegyL9jZiE0YP7JEcimYK5Jl7C284Jbdr7lk3FiGQSCWUrjs4dS7XctkFzlM1uE98xK2TONYBNJ/ZG4Ig2x2Hso1jvYCmAg6bEI39YUhw3S5FgkxG8Xhv4EisK65BwquiEXMXA+WhsR2dpgnWRjAVwELZWnkAnc03FCMxkKmcQBcLTTrprW7XHPg1U9Mqwvce8s1A2Zg9DJ0BTNxpt214L5cGzBhBPxKJkOXP3aJCx9EWrDiA8nYYiiqBGT5GThDaW+4TIbGTrFDQwbi+Clh4X0A8wQyDn1coAyXoW+zmRAGY2spo2S4u3vryXW6sJfhZvc996H38Tr2Ernhye4qinYXfrjYhQeYeNcNl8nusaJ3mZGTDxKmLivEkI3PZyfq1c6g1z9QSwGBBC6PXfgCC9jgfkBvBjLkLOLLOyFtIISqZE6AAdjwFDcYvqPysGxCIE/UvE3kg0hAdi7uRaKk/vl0OmEwDyxww4NHLevIexB+JgkYlbzJ9IYtecDCVEapxM3N9hqEOwb1RK0UjIOUP00uuywIGWymm6z5naAnnso1qoV44KQhvneHu8V9Njn7bZdmNdaw5HskEQag9qfjc5udcR93DTgGXUsD8RApXVZSSGhCNw6jCN4lnk+q/MYgzS20j5SArWKwL5RHIOR9GN8BW9R6H3uomgugaBudTscwqKfjrFJQUeE4DOQXxmBLQRCCpnphkBiGfpeEyEf2BNq1zr4veCIO9vN+Mk6XeT9lwrCt+QtvIwzDOb04/oWNimb7FMibluGcfTqdn8z+eX4MrV87IEFgojMEYw1Auh35GIniKeAbfOp04PsqVg89+C58HsHW45ONz1yqr98M59P5ya/Tq9l0NoRtXcprsKwuqAiI5QYnLPVwZtPpebnXyg+51L2MnE3n8uJqDi/3BnuDXun1h6uLT5fwvjPY+7v9umcf4v8dY9rf62dDXr06ODRAtbPn/d7+oTGbj0+nzvj9fHqFXeweYy9YIkBNYWMBE2nrAR4XArQF1BBUhQBW7CaIwqANaEioODxhtyAn42z8W7FsoDl4dQDv5lcnvzmfTybzj9VXH6cnHz4iN/39/ezdu3/OaWRl1EtWHfGS7RkfJ06N8qv+oPQ2Jz44PCy9zujXh79kjaE4y+xsfHpaH9sfHELj6wH10I3wGreWxzF/NGvTWVkn52p6PAXpTP5Yb+f44tM5LqWXN01/u5wez6Ep46loen81PpsOlaKx/yP9hXb8yLuguuEYuxg1mc7mJ+fj+ckFKCL6gOpIw3AFKMRSBMLh0nTTWJlsl2kDGCqdtdjOEZMpIGNZkYeAhgxsp3PGI3S96CaXPlghutpM47qALTLEZpwFGlzxgEhK6BKuVokAhAwSD7yWB0hNJGfUFbT0Vq4TpBuDm4ABiKnQoCgTnJU0tWix2RxoEydE7j6GtXQBfoALPwxugRa5dfF7SoZwR7EDuKIoQu8BiBKmt2vtXMBEXMU7uEa9XvpMIh4kQ8DmRF7nhn19Q20YqgBQblAOuVCVuPBHxo/FQ0YLRhMZEwdaebN4WIpIMnMOuDWN4zDusl+5n6rvViuZPmpA+V1icwD9wDWpg7ci7LW9ZOUFMBm9tWhPqP0IKMD+J4IIKU5gDOC5XnNOW8UlCJjZjFGYeLjYfDFajyyk4CWw0eCtlyJ73WVmoU+W4qHKW5WK6lGjfMR6it0GE38bsSTd0PoSq9gYVMGuWivsjwjSjYi5lkNSEimwnJN6S/2r4tbL1/SyrnmXfOzOiAYbTZFp+wPDcSBQgsjCNTcYbCUUbKHjwHjgvmyF+DI3vDnSongOI0ZZiqWVz0eTDylI7rJ16IO8Yf2g01FmaJKTr4adp0EYEJXVHi2aSxXIEkEI/rTcyQ3b7AL0ikgheYxZuXLQ7B7iPwiAICb+QrHyDGZlCx+o6MAY1pFi+JJKm40xigNOwliZFjID9DKj52wl7nMXBg7Kuw0Ug2jSv6cerFQHKmwF8b8KUCDeJWo426Wnw1ZIHCLgOqA1RpmYFPNpID0fw7XbUCAecF9UTV7FEqDb+SbZt0KaWYxRV/K8V5d2zVJaSsCr1UsTRNMCTfzaISlgLIKj6BOYxM8QxNz51rC8ZnhTCVy+GQ20ge3JTLO+CAkLAPXolbBHb/WWEdlc5WHPhas/sgANPlVgQHOAaZsNGS786bn0prRsyDcyFTBItoOCPGJ7/8WCciLleO0lO/hv+R6NtNo8RShXrILUhj+YFOxmAmwjTHr4JGE0pWcRbhmL+PPdsRozVRrcQMQx+8fs4pwSfpYEMGYNCoKor7PhIaX6P5WTedxagKgubS6l0kQsi4oTSM6+6IwZk0qbTRAelM0u/RQCl5hD4KPycR2gQfK25JQSagjiiFCImusQMADbWJ7BZzNZdgY0qB0jhbD4y1S2hZDKKO8pdiA3SeiPgjCL9KewY+IdgpNsIhJI9gCeUAhS92riYmMckphWoa3U721ZX28KPjhk1g8YAIehb1aCVqtkNZVQtUIqU7Z8QdeISDelsfWWJyynLJUfnwJWtDefCrW1APxOrj7wPsEA1jVxGyxoUrIi7cYvmUo39IEidlLxctRfOH/wa5sQvD6WyCC0h0RpBztikQAc2yNAtks7XcrwsAySlSXcLlGCDpQSgOzvxU9fhM70lVKgS4bfP6lEUPvETEvb9JGGjeqqhO6i0Lc8qsQfqtOUBswqnfPok7qB5ydWsZRW2EammRV9aGBU7nb1MxLUglfb4KhYwNwu8Csw8yxsyYqRd16Y3AGoeK5cQ4wlsPpDdamAXX14p+hgoVCXOJ6UXW5DFfPB1ddeKPQhUVAmVZHFdhNrxh96Ri3X7TKDrpCNmaq7hZ6gmUEXoyvCUIl1F/JqFR/4TVrPo1LO67vVysFWyrUcfDvxWt2g2ygb6CkS8V3FUtUrG7XJ7Bx9/Ai4UpkNC9uKxar6bXh8J2KzlGpT0IW5dCnVnsM2gxVuIhW1e//RZe48BYA8AsZKhHWIZv0dwn69zwRvT6pgm661m1xFzSBlbLW9csaDINqrC69MpUu7V3UdWkTEuKndraNWMyRXA3s3j1PRDAQwDFDjclv1Q/C7ymLZZ7GYUTmyizEG2xsoJ5mj9p9wxdrLarAv4R1CjVXzuQrPgjLuaX9bEV7xk3vhp6HVqpq8dT3cG9w8A2Gqsn2Wx67BSSwScH/kcMu+7yvYQwHnwwwHFwf7IsCzCpOkY7uCHjo8WXpeZ5u0UMTfvjXRK4PDsnEiN9eZr8XaTGNmDRT1ubfQ+IxGTIS+toCfArnqq22IoptrmPPtugReN1uY+EgQsp2L14MtTCgUe5IL1aWFDW2rihNtkU4ipJPHO6YKsYYIfl2wsMDVXzG40l/JFimkaa0uFtvXZltFVGur4zE940h9gMeFmG6EE6s5R/hLzzmi3/mko7z2xOWoZNdWeWWZ6lVjMaWIugj7DK5BR/OQW+f4pTo62hghXv7KQiCtFNurUIolkQRNbOOVhmnwvBOPoyY2VOGkhDZRGJmKXpdWsaWjIrS9c0Exzy5QOSm6aidW6VfGVS3+1I0cdVJk4nFPEQSrl7b6UILB7wS5pRZTP43fOyfn03k3a53B1jiTDwB4+auTy8uri/mF82lyaeX0bNh//AyjnNTs4tTB4RVqztX002w6nkyuuqxvNSstf5wWHuLktLJCyljqI0tdTbmY1UspEU8SPOJBDeNfuOfzhU/HghjHP2JRT+Kx4BvIY+ONL6CzDFly50XFkhdgOKbZAR+N/3WwmBlLy6qENVhNN4wXkNr+qB8gVhQsTSzJ1w+Vu1mBDs2b9R56IJwfyoHh0FHb+BhPSPDA5WuPiiOq6tMvCiWDYV6U2xtm9Tg9+peT80k+dpWI3/XQjXA93snSO8gvQOlLmKlTtHY40bGs7oNevX+IQZh+cT3cv2H/Az4Nr1BMOuUW1YCyqoeq9PiCzj70Oa4nEyVhlx3rwDVBlAq49KjmIaUvdkQA6whgDizI0nHzpWdrJZUxd9RBDdqhCn3TAGk6eDJsdt5iAKx567JX1nXvJltgZTQssI/LqLw8qgphh71uXVNel63sJoVGmVRe3yhtRheRd6SNq3Q7vLHqZcAiAKaxW3IldbpA4eYWOZyU5fD3XA75UYi1beCqPLC/Z22vieZHIihHXbt9y3qtvAaK1Wzh/dfD15CYlKV/YycRaIC56PzroYeg0Eem82gplaudQyyaxAIgZik6EGv2D/SqWsMDFRkoB619c1HYy6wkH+Rgqd6smYUG/LKTqJ6jtwDxRmwW4G/WXlS4Ci8A/rgMA7N23o7ZWaNPDozW99A98ygnlyUn44CTcM6mZ+/AB37EloKjCtZraG8iO3jMJa8c79AFH5AXx5AbY+VA3JNh0+GD7wOcUPrHeByDJasq5P3aA8eA6dITR5G5pjncdWP0FkpodiyWX0gjB739w8b5ZIN3/EE494JUbJ9tGyg2zz+1aQjlBU/wzK3tCDSf8oe7KnUVaZfhXSRwy9WrSOXrRj/cRcGEztXFxdy5vJq+z+8kJDbuxlo8gHr2+qCboLmN9z39vjOeHe8Au/3XaMvZv46h6P46PZ5fXDmT8XzMyHWon32D8sOT8w/begyqvk309/p/2K0NDip+rX9A/qu+6FYM81ZVxDQ7RyWUve4fDgeDGwQtolhf6p8hud8b7u8XJFvE00q1yNAbKI81ojLP/b1hv/+qcEN5w+BV5tgbgK6iv2DnPyIOqfqrTlMRp9+oc/vsjpzrbTZ49xC0tVvEgLoGW0x1MMRt+RlLyjdld0PpT9sC25MmlS/Z/r/TRJpAq8u0LymSLVSZ5yJ9fvPJ+ovDWdkO/oJI9v27kD8YwcoY4brR0xBx64cL7lcrVN1aobDlelPxsnq/qnhfvVy1DY7ao6WVz2+TkokUQaxq+V+wy+Oesk/ACDRIvF4g70O2wCB7AxbAFoKhWWBU2d+CPQW1vqIyA1wZf5hW7nCiJarjSL1vlWy7RBATdi/gOjjOeN/Tgae6fNWKSBXIG2ZBsaniwu9i2OGw39ND6sjSgybAFR1g1qEFHUEt4Ifub3V33arygv7+fg9f6BtkR0/U+qsS1svG04FeVoJRJAGgKHLOehzpDhUpjtp0zyofLDTLQHrmpyYeNqq+LdNgXaXgZeuITP+vhzdZqNC8jPi9waXLidu6tlxWLHcTlGhhpUovPNv2RhGyVnpSTddq1BDIZAWla3wAnVAtN8Yz+P951BRLibC9DNNAmj3rSVo1VsiH9TvsJeRuJX6qNF6wdyFsbpJGEZ0H0FFNQkIhFeF4gVUf1wIc64vq7EQmmlyNmhR4rSlN9F3/7JRHp5x4yStd+F6yzu9d3abg7PA6Izq5GjGMVGPpAcquvBiASRdZwhVekOQxXpBUR0VbVDjbSSwVmM0ydLUE3dzusva/JUsePl/JaizUOdwyDmfcoiJHoy2DtjOlTk0y28oUdthO5ma7sekLu/XDpRfsTJ1sZKBP3gNBMgT/QaUbOs+C5H9Jf3+iUpMs6sLLLaEfxvq+arFtR3SZugKjFegpAWUbjC3S1Qo0o3zHuXZqX0InfSUeoz5LFxLbAUGd/3QJfY1imlbzZ037rwaeLQwockXACfHHc+PN7GL9Xz3cLIVUPyLa1NerYlkXUafTURdGUfnwhuVtDPDp0hVoEdBlTfUnRGyG168AlOieU4h3rLnE41r5RmkCBwjLR8VpQH/cRddOsOIm1VVNl4tNGGii+XksHeYiRtFxilmrF3VLGUW32OzSYou/F5nTN1MRG6mPrp51RIfKthaD8f9oAk1j")))
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


def fpp_show_match(multisync: dict, rows: list[dict], now: float) -> dict:
    """Match a fresh FPP sequence filename to one enabled local show.

    Never guess when two show names collapse to the same key. This prevents
    an unrelated sequence from silently playing the wrong mapped picture.
    """
    command = sync.show_command(multisync, now)
    if not command.get("action") or multisync.get("type") != "fseq":
        return {"action": None}
    name = str(multisync.get("name") or "")[:160].replace("\\", "/").rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0] if name.lower().endswith((".fseq", ".eseq")) else name
    key = re.sub(r"[^a-z0-9]+", "", stem.casefold())
    matches = [row for row in rows if row.get("enabled") and re.sub(r"[^a-z0-9]+", "", str(row.get("name", "")).casefold()) == key] if key else []
    if len(matches) != 1:
        return {"action": "waiting", "sequence": name, "reason": "ambiguous" if matches else "missing"}
    return {**command, "sequence": name, "showId": matches[0]["id"], "showName": matches[0]["name"]}


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


def screen_target(mode: str, url: str, stored: bool, pc_up: bool, lighting: bool, scheduled: bool | None = None, fpp: bool = False) -> str:
    """Choose the projector page.

    The Windows picture is used only while that app answers. A dusk clock can
    hold the stored show until sunset. xLights data and an explicit stored-show
    choice still play.
    """
    if mode == "show" and stored:
        return "/play"
    if mode == "auto" and fpp and stored:
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
            rows, _loop = stored_shows()
            sync_show = fpp_show_match(snap["multisync"], rows, time.time())
            stored_show = bool(show_status().get("saved"))
            data = json.dumps({**config, "wifi": wifi.status(), "update": updater.status(), "join": JOIN, "display": display_status(), "show": show_status(), "pcUp": pc_is_up(), "sync": snap, "syncShow": sync_show, "clock": clock, "screen": screen_target(config.get("playMode", "auto"), config.get("pcUrl", ""), stored_show, pc_is_up(), bool(snap.get("universes") or snap.get("matrix")), clock["active"], sync_show.get("action") is not None)}).encode("utf-8")
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
