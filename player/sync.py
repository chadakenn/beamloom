"""FPP MultiSync + E1.31 (sACN) + DDP receivers for the Beamloom Pi player.

Keeps a small piece of thread-safe, in-memory state describing what a
connected xLights/FPP show is currently doing. Nothing in this module
touches the projector or the renderer directly -- it only ever updates the
state returned by state()/channels(), which other code (the /health
endpoint today, the live renderer later) reads.

Wire formats:
- MultiSync: FPP's own control protocol. See
  https://github.com/FalconChristmas/fpp/blob/master/docs/ControlProtocol.txt
- E1.31 (sACN): ANSI E1.31-2016, the standard streaming ACN data packet.
- DDP (Distributed Display Protocol): the simpler header used by WLED and
  many other pixel controllers; xLights can output it directly.

All three are UDP, no handshake, no auth -- exactly like real DMX/pixel
hardware on a LAN. Malformed or unexpected packets are dropped silently;
this only ever reads from the network, never writes back.
"""

from __future__ import annotations

import socket
import math
import base64
import struct
import threading
import time

_LOCK = threading.Lock()
_MULTISYNC = {"action": None, "type": None, "name": "", "frame": 0, "elapsed": 0.0, "at": 0.0}
_UNIVERSES: dict[int, bytes] = {}
_UNIVERSE_SEEN: dict[int, float] = {}

MULTISYNC_PORT = 32320
MULTISYNC_GROUP = "239.70.80.80"
E131_PORT = 5568
DDP_PORT = 4048
STALE_AFTER = 5.0  # seconds of silence before a universe/sync is treated as gone
MAX_UNIVERSES = 256
MATRIX_WIDTH = 256
MATRIX_HEIGHT = 144
MATRIX_BYTES = MATRIX_WIDTH * MATRIX_HEIGHT * 3
SMALL_MATRIX_BYTES = 128 * 72 * 3
_MATRIX = bytearray(MATRIX_BYTES)
_MATRIX_RECEIVED = bytearray(MATRIX_BYTES)
_MATRIX_RECEIVED_COUNT = 0
_MATRIX_EXPECTED_BYTES = 0
_MATRIX_FRAME: bytes | None = None
_MATRIX_SEEN = 0.0
_MATRIX_DESTINATION: int | None = None


def scene_at(durations, elapsed: float) -> tuple[int, float]:
    """Map a show clock, in seconds, onto a scene index and the offset inside it.

    Scene lengths shorter than one second are treated as one second. The clock
    wraps, so a longer FPP sequence keeps stepping through the stored scenes.
    """
    spans: list[float] = []
    for item in durations:
        try:
            span = float(item)
        except (TypeError, ValueError):
            span = 10.0
        spans.append(span if math.isfinite(span) and span >= 1 else 10.0)
    if not spans:
        return 0, 0.0
    position = float(elapsed) if isinstance(elapsed, (int, float)) and math.isfinite(float(elapsed)) and float(elapsed) > 0 else 0.0
    position %= sum(spans)
    for index, span in enumerate(spans):
        if position < span:
            return index, position
        position -= span
    return 0, 0.0


def show_command(multisync: dict, now: float) -> dict:
    """Turn the latest MultiSync packet into play, hold, or stop.

    Start and sync play the stored show at the packet's elapsed time. Open
    holds that time without moving. Stop blacks the picture out. A start or
    sync older than a few seconds is ignored so a quiet network falls back to
    the Pi's own loop. One stop packet holds until it goes stale.
    """
    action = multisync.get("action") if isinstance(multisync, dict) else None
    if action not in {"start", "sync", "stop", "open"}:
        return {"action": None, "elapsed": 0.0}
    try:
        at = float(multisync.get("at") or 0)
        elapsed = float(multisync.get("elapsed") or 0)
    except (TypeError, ValueError):
        return {"action": None, "elapsed": 0.0}
    if not math.isfinite(at) or not math.isfinite(elapsed):
        return {"action": None, "elapsed": 0.0}
    if action in {"start", "sync"} and now - at > 3:
        return {"action": None, "elapsed": 0.0}
    if now - at > STALE_AFTER * 6:
        return {"action": None, "elapsed": 0.0}
    if action == "stop":
        return {"action": "stop", "elapsed": max(0.0, elapsed)}
    if action == "open":
        return {"action": "hold", "elapsed": max(0.0, elapsed)}
    return {"action": "play", "elapsed": max(0.0, elapsed)}


def state() -> dict:
    """A JSON-safe snapshot for /health: what's currently syncing, and which
    universes have live data. Does not include raw channel bytes -- callers
    that need those call channels(universe)."""
    now = time.time()
    with _LOCK:
        multisync = dict(_MULTISYNC)
        live = [universe for universe, seen in _UNIVERSE_SEEN.items() if now - seen < STALE_AFTER]
        matrix = bool(_MATRIX_FRAME) and now - _MATRIX_SEEN < STALE_AFTER
    if multisync["at"] and now - multisync["at"] > STALE_AFTER * 6:
        multisync = {"action": None, "type": None, "name": "", "frame": 0, "elapsed": 0.0, "at": 0.0}
    return {"multisync": multisync, "universes": sorted(live), "matrix": matrix}


def channels(universe: int) -> bytes | None:
    """The most recent 512-byte DMX payload for a universe/DDP output id,
    or None if we've never seen it or it's gone stale."""
    with _LOCK:
        seen = _UNIVERSE_SEEN.get(universe, 0.0)
        data = _UNIVERSES.get(universe)
    if data is None or time.time() - seen > STALE_AFTER:
        return None
    return data


def frame() -> dict:
    """JSON frame for the local kiosk WebSocket, max 32 live universes."""
    now = time.time()
    with _LOCK:
        live = sorted((universe, data) for universe, data in _UNIVERSES.items()
                      if now - _UNIVERSE_SEEN.get(universe, 0) < STALE_AFTER)[:32]
        matrix = _MATRIX_FRAME if now - _MATRIX_SEEN < STALE_AFTER else None
    result = {"universes": {str(universe): base64.b64encode(data).decode("ascii") for universe, data in live}}
    if matrix is not None:
        result["matrix"] = base64.b64encode(matrix).decode("ascii")
        result["matrixWidth"] = 128 if len(matrix) == SMALL_MATRIX_BYTES else MATRIX_WIDTH
        result["matrixHeight"] = 72 if len(matrix) == SMALL_MATRIX_BYTES else MATRIX_HEIGHT
    return result


def _set_multisync(action: str, kind: str, name: str, frame: int, elapsed: float) -> None:
    with _LOCK:
        _MULTISYNC.update(action=action, type=kind, name=name, frame=frame, elapsed=elapsed, at=time.time())


def _set_universe(universe: int, data: bytes) -> None:
    with _LOCK:
        if universe not in _UNIVERSES and len(_UNIVERSES) >= MAX_UNIVERSES:
            oldest = min(_UNIVERSE_SEEN, key=_UNIVERSE_SEEN.get)
            _UNIVERSES.pop(oldest, None)
            _UNIVERSE_SEEN.pop(oldest, None)
        _UNIVERSES[universe] = data
        _UNIVERSE_SEEN[universe] = time.time()


def _udp_socket(port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except (AttributeError, OSError):
        pass  # not available on every platform; harmless to skip
    sock.bind(("0.0.0.0", port))
    return sock


# --------------------------------------------------------------------------
# MultiSync (FPP control protocol, packet type 0x01)
# --------------------------------------------------------------------------

_SYNC_ACTIONS = {0: "start", 1: "stop", 2: "sync", 3: "open"}
_SYNC_KINDS = {0: "fseq", 1: "media"}


def _parse_multisync(payload: bytes) -> None:
    if len(payload) < 18 or payload[:4] != b"FPPD" or payload[4] != 0x01:
        return
    # FPP writes its packed C structs in native little-endian order on a Pi.
    extra_length = struct.unpack_from("<H", payload, 5)[0]
    if extra_length < 11 or extra_length > len(payload) - 7:
        return
    action = _SYNC_ACTIONS.get(payload[7])
    kind = _SYNC_KINDS.get(payload[8])
    if action is None or kind is None:
        return
    frame = struct.unpack_from("<I", payload, 9)[0]
    (elapsed,) = struct.unpack_from("<f", payload, 13)
    if not math.isfinite(elapsed) or elapsed < 0:
        return
    name = payload[17:7 + extra_length].split(b"\x00", 1)[0].decode("utf-8", "replace")[:160]
    _set_multisync(action, kind, name, frame, elapsed)


def _multisync_loop() -> None:
    sock = _udp_socket(MULTISYNC_PORT)
    try:
        membership = socket.inet_aton(MULTISYNC_GROUP) + socket.inet_aton("0.0.0.0")
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
    except OSError:
        pass  # unicast MultiSync (the default for new FPP installs) still arrives
    while True:
        try:
            payload, _address = sock.recvfrom(2048)
        except OSError:
            continue
        try:
            _parse_multisync(payload)
        except (struct.error, IndexError):
            continue


# --------------------------------------------------------------------------
# E1.31 / sACN (ANSI E1.31-2016 data packet)
# --------------------------------------------------------------------------

_ACN_ROOT_PREFIX = bytes.fromhex("0010") + bytes.fromhex("0000") + b"ASC-E1.17\x00\x00\x00"
_ROOT_VECTOR_DATA = 0x00000004
_FRAMING_VECTOR_DATA = 0x00000002


def _parse_e131(payload: bytes) -> None:
    if len(payload) < 126 or payload[:16] != _ACN_ROOT_PREFIX:
        return
    if struct.unpack(">I", payload[18:22])[0] != _ROOT_VECTOR_DATA:
        return
    if struct.unpack(">I", payload[40:44])[0] != _FRAMING_VECTOR_DATA:
        return
    (universe,) = struct.unpack(">H", payload[113:115])
    if payload[125] != 0x00:
        return  # non-zero DMX start code; not standard dimmer data, skip
    data = payload[126:126 + 512]
    if not data:
        return
    _set_universe(universe, data.ljust(512, b"\x00"))


def _e131_loop() -> None:
    sock = _udp_socket(E131_PORT)
    while True:
        try:
            payload, _address = sock.recvfrom(2048)
        except OSError:
            continue
        try:
            _parse_e131(payload)
        except (struct.error, IndexError):
            continue


# --------------------------------------------------------------------------
# DDP (Distributed Display Protocol)
# --------------------------------------------------------------------------


def _parse_ddp(payload: bytes) -> None:
    global _MATRIX_FRAME, _MATRIX_SEEN, _MATRIX_DESTINATION, _MATRIX_RECEIVED_COUNT, _MATRIX_EXPECTED_BYTES
    if len(payload) < 10:
        return
    flags = payload[0]
    if flags & 0xC0 != 0x40:  # top two bits must be version 1
        return
    if flags & 0x10:  # STORAGE packets are not live display data
        return
    destination = payload[3]
    (offset,) = struct.unpack(">I", payload[4:8])
    (length,) = struct.unpack(">H", payload[8:10])
    data = payload[10:10 + length]
    if not data or len(payload) - 10 < length or length > 1440 or offset >= MATRIX_BYTES:
        return
    if (offset == 0 and length > 512) or (offset > 0 and destination == _MATRIX_DESTINATION):
        with _LOCK:
            if offset == 0 and length > 512:
                _MATRIX_DESTINATION = destination
                _MATRIX_RECEIVED[:] = bytes(MATRIX_BYTES)
                _MATRIX_RECEIVED_COUNT = 0
                _MATRIX_EXPECTED_BYTES = 0
            end = min(offset + length, MATRIX_BYTES)
            _MATRIX[offset:end] = data[:end - offset]
            _MATRIX_RECEIVED_COUNT += _MATRIX_RECEIVED[offset:end].count(0)
            _MATRIX_RECEIVED[offset:end] = b"\x01" * (end - offset)
            # Both supported sizes end with a 288-byte DDP packet. Its offset
            # tells us which complete frame to publish without guessing from
            # a partial first packet of a larger frame.
            if offset + length in (SMALL_MATRIX_BYTES, MATRIX_BYTES) and length < 1440:
                _MATRIX_EXPECTED_BYTES = offset + length
            if _MATRIX_EXPECTED_BYTES and _MATRIX_RECEIVED_COUNT >= _MATRIX_EXPECTED_BYTES:
                _MATRIX_FRAME = bytes(_MATRIX[:_MATRIX_EXPECTED_BYTES])
                _MATRIX_SEEN = time.time()
    # Matrix packets must not overwrite the matching E1.31 universe's colors.
    if offset >= 512 or length > 512:
        return
    with _LOCK:
        buffer = bytearray(_UNIVERSES.get(destination, bytes(512)))
    end = min(offset + len(data), 512)
    buffer[offset:end] = data[: end - offset]
    _set_universe(destination, bytes(buffer))


def _ddp_loop() -> None:
    sock = _udp_socket(DDP_PORT)
    while True:
        try:
            payload, _address = sock.recvfrom(2048)
        except OSError:
            continue
        try:
            _parse_ddp(payload)
        except (struct.error, IndexError):
            continue


def start() -> None:
    """Start the background listener threads. Safe to call once at boot;
    each listener runs forever on its own daemon thread."""
    for target in (_multisync_loop, _e131_loop, _ddp_loop):
        threading.Thread(target=target, daemon=True).start()
