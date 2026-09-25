#!/usr/bin/env python3
"""First-boot Wi-Fi for the Beamloom player.

If the Pi is not already on Ethernet or a saved network, it starts a setup
network named Beamloom. The show PC joins that network and sends the home
Wi-Fi name and password. The password is handed to NetworkManager and is not
written into the player settings file.
"""

from __future__ import annotations

import os
import subprocess
import sys

SETUP_SSID = "Beamloom"
SETUP_PASSWORD = "beamloom"
SETUP_ADDRESS = "192.168.4.1"
SETUP_CONNECTION = "BeamloomSetup"


def apply_enabled() -> bool:
    return os.environ.get("BEAMLOOM_WIFI_APPLY") == "1"


def clean_wifi(ssid: str, password: str) -> tuple[str, str]:
    ssid = ssid.strip()
    if not ssid or len(ssid) > 32 or any(character in ssid for character in "\r\n\x00"):
        raise ValueError("Enter the Wi-Fi name.")
    if any(character in password for character in "\r\n\x00") or len(password) > 63:
        raise ValueError("That Wi-Fi password cannot be used.")
    if password and len(password) < 8:
        raise ValueError("A Wi-Fi password needs at least 8 characters. Leave it empty for an open network.")
    return ssid, password


def describe(devices: str, active: str) -> dict:
    ethernet = False
    wifi_up = False
    for line in devices.splitlines():
        parts = line.split(":")
        if len(parts) < 3:
            continue
        kind, state = parts[1], parts[2]
        if kind == "ethernet" and state == "connected":
            ethernet = True
        if kind == "wifi" and state == "connected":
            wifi_up = True
    names = []
    for line in active.splitlines():
        name = line.split(":")[0].replace("\\:", ":")
        if name:
            names.append(name)
    if ethernet:
        mode = "ethernet"
        ssid = ""
    elif SETUP_CONNECTION in names or (wifi_up and SETUP_SSID in names):
        mode = "setup"
        ssid = SETUP_SSID
    elif wifi_up:
        mode = "home"
        ssid = next((name for name in names if name != SETUP_CONNECTION), "")
    else:
        mode = "down"
        ssid = ""
    return {
        "mode": mode,
        "ssid": ssid,
        "setupSsid": SETUP_SSID,
        "setupPassword": SETUP_PASSWORD,
        "setupAddress": SETUP_ADDRESS,
    }


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, capture_output=True, text=True, timeout=45)


def status(run=None) -> dict:
    if run is None and not apply_enabled():
        return describe("", "")
    run = run or _run
    devices = run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"])
    active = run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"])
    return describe(getattr(devices, "stdout", ""), getattr(active, "stdout", ""))


def wifi_device(devices: str) -> str:
    for line in devices.splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[1] == "wifi" and parts[0]:
            return parts[0]
    return "wlan0"


def start_setup(run=None) -> dict:
    if run is None and not apply_enabled():
        raise RuntimeError("The setup network only starts on the Pi.")
    run = run or _run
    devices = run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"])
    device = wifi_device(getattr(devices, "stdout", ""))
    run(["nmcli", "connection", "delete", SETUP_CONNECTION])
    run([
        "nmcli", "device", "wifi", "hotspot",
        "ifname", device,
        "con-name", SETUP_CONNECTION,
        "ssid", SETUP_SSID,
        "password", SETUP_PASSWORD,
    ])
    run([
        "nmcli", "connection", "modify", SETUP_CONNECTION,
        "ipv4.addresses", f"{SETUP_ADDRESS}/24",
        "ipv4.method", "shared",
        "connection.autoconnect", "no",
    ])
    run(["nmcli", "connection", "up", SETUP_CONNECTION])
    return describe("", f"{SETUP_CONNECTION}:802-11-wireless") | {"mode": "setup", "ssid": SETUP_SSID}


def ensure(run=None, attempts: int = 15, pause=None) -> dict:
    import time
    for attempt in range(attempts):
        current = status(run)
        if current["mode"] in {"ethernet", "home"}:
            return current
        if attempt + 1 < attempts and pause:
            pause(2)
        elif attempt + 1 < attempts and pause is None and apply_enabled():
            time.sleep(2)
    if run is None and not apply_enabled():
        return status(run)
    return start_setup(run)


def join(ssid: str, password: str, run=None) -> None:
    ssid, password = clean_wifi(ssid, password)
    if run is None and not apply_enabled():
        raise RuntimeError("Wi-Fi is changed on the Pi, not from this computer.")
    run = run or _run
    devices = run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"])
    device = wifi_device(getattr(devices, "stdout", ""))
    run(["nmcli", "connection", "down", SETUP_CONNECTION])
    command = ["nmcli", "device", "wifi", "connect", ssid, "ifname", device]
    if password:
        command = ["nmcli", "device", "wifi", "connect", ssid, "password", password, "ifname", device]
    result = run(command)
    if getattr(result, "returncode", 0) != 0:
        start_setup(run)
        raise RuntimeError("Could not join that network. The setup network is still up.")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] != "ensure":
        print("Usage: wifi.py ensure", file=sys.stderr)
        sys.exit(2)
    current = ensure()
    print(current["mode"])


if __name__ == "__main__":
    main()
