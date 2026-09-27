"""Receiver packet checks and the first-update bootstrap contract."""
import base64
import json
import re
import socket
import struct
import threading
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

import beamloom_player
import sync
import updater


class ReceiverTest(unittest.TestCase):
    def setUp(self):
        with sync._LOCK:
            sync._MULTISYNC.update(action=None, type=None, name="", frame=0, elapsed=0.0, at=0.0)
            sync._UNIVERSES.clear()
            sync._UNIVERSE_SEEN.clear()
            sync._MATRIX[:] = bytes(sync.MATRIX_BYTES)
            sync._MATRIX_RECEIVED[:] = bytes(sync.MATRIX_BYTES)
            sync._MATRIX_RECEIVED_COUNT = 0
            sync._MATRIX_EXPECTED_BYTES = 0
            sync._MATRIX_FRAME = None
            sync._MATRIX_SEEN = 0.0
            sync._MATRIX_DESTINATION = None

    def test_multisync_start_and_short_packet(self):
        name = b"House Show.fseq\x00"
        packet = b"FPPD\x01" + struct.pack("<H", 10 + len(name)) + b"\x00\x00" + struct.pack("<If", 42, 1.4) + name
        sync._parse_multisync(packet)
        self.assertEqual(sync.state()["multisync"]["action"], "start")
        self.assertEqual(sync.state()["multisync"]["name"], "House Show.fseq")
        self.assertEqual(sync.state()["multisync"]["frame"], 42)
        sync._parse_multisync(b"FPPD\x01")
        self.assertEqual(sync.state()["multisync"]["frame"], 42)

    def test_e131_and_ddp_channels_expire(self):
        sacn = bytearray(129)
        sacn[:16] = sync._ACN_ROOT_PREFIX
        sacn[18:22] = struct.pack(">I", sync._ROOT_VECTOR_DATA)
        sacn[40:44] = struct.pack(">I", sync._FRAMING_VECTOR_DATA)
        sacn[113:115] = struct.pack(">H", 9)
        sacn[126:129] = b"\x0a\x14\x1e"
        sync._parse_e131(bytes(sacn))
        self.assertEqual(sync.channels(9)[:3], b"\x0a\x14\x1e")
        ddp = b"\x40\x00\x00\x07" + struct.pack(">IH", 2, 2) + b"\x80\x90"
        sync._parse_ddp(ddp)
        self.assertEqual(sync.channels(7)[2:4], b"\x80\x90")
        sync._parse_ddp(ddp[:-1])  # incomplete declared payload must not replace the last frame
        self.assertEqual(sync.channels(7)[2:4], b"\x80\x90")
        with patch.object(sync.time, "time", return_value=sync._UNIVERSE_SEEN[9] + 6):
            self.assertIsNone(sync.channels(9))
            self.assertNotIn(9, sync.state()["universes"])

    def test_show_clock_steps_and_stops(self):
        self.assertEqual(sync.scene_at([10, 5], 12), (1, 2))
        self.assertEqual(sync.scene_at([10, 5], 15), (0, 0))
        self.assertEqual(sync.scene_at([], 4), (0, 0.0))
        now = 100.0
        playing = sync.show_command({"action": "sync", "elapsed": 12, "at": now}, now)
        self.assertEqual(playing["action"], "play")
        self.assertEqual(sync.scene_at([10, 5], playing["elapsed"]), (1, 2))
        self.assertEqual(sync.show_command({"action": "sync", "elapsed": 12, "at": now - 4}, now)["action"], None)
        self.assertEqual(sync.show_command({"action": "stop", "elapsed": 3, "at": now}, now)["action"], "stop")
        self.assertEqual(sync.show_command({"action": "open", "elapsed": 3, "at": now}, now)["action"], "hold")

    def test_screen_stays_on_pi_when_the_app_closes(self):
        play = beamloom_player.screen_target
        self.assertEqual(play("live", "http://pc:8751/?player=1", True, True, True), "http://pc:8751/?player=1")
        self.assertEqual(play("live", "http://pc:8751/?player=1", True, False, True), "/play")
        self.assertEqual(play("auto", "http://pc:8751/?player=1", False, False, True), "/play")
        self.assertEqual(play("show", "http://pc:8751/?player=1", True, True, False), "/play")
        self.assertEqual(play("auto", "http://pc:8751/?player=1", False, False, False), "")

    def test_first_update_contains_sync_module(self):
        source = Path(beamloom_player.__file__).read_text(encoding="utf-8")
        payload = re.search(r'ROOT / "sync.py"\)\.write_bytes\(zlib\.decompress\(base64\.b64decode\("([^"]+)"\)\)\)', source)
        self.assertIsNotNone(payload)
        self.assertEqual(zlib.decompress(base64.b64decode(payload.group(1))), Path(sync.__file__).read_bytes())
        self.assertIn("player/sync.py", updater.FILES)

    def test_renderer_frame_carries_rgb_and_dimmer(self):
        sync._set_universe(12, bytes([0, 255, 64, 128]).ljust(512, b"\x00"))
        frame = sync.frame()
        self.assertEqual(base64.b64decode(frame["universes"]["12"])[:4], bytes([0, 255, 64, 128]))
        with patch.object(sync.time, "time", return_value=sync._UNIVERSE_SEEN[12] + 6):
            self.assertEqual(sync.frame()["universes"], {})

    def test_ddp_matrix_assembles_hd_packets_and_expires(self):
        sync._set_universe(1, bytes([11, 22, 33, 44]).ljust(512, b"\x00"))
        first = bytes([255, 0, 0]) * 480
        middle = bytes([0, 255, 0]) * 480
        last = bytes([0, 0, 255]) * 96
        def packet(offset, data):
            return b"\x40\x00\x00\x02" + struct.pack(">IH", offset, len(data)) + data
        sync._parse_ddp(packet(0, first))
        self.assertNotIn("matrix", sync.frame())
        for offset in range(1440, sync.SMALL_MATRIX_BYTES - len(last), 1440):
            sync._parse_ddp(packet(offset, middle))
        self.assertNotIn("matrix", sync.frame())
        sync._parse_ddp(packet(sync.SMALL_MATRIX_BYTES - len(last), last))
        self.assertEqual(sync.channels(1)[:4], bytes([11, 22, 33, 44]))
        pixels = base64.b64decode(sync.frame()["matrix"])
        self.assertEqual(pixels, first + middle * 18 + last)
        self.assertEqual((sync.frame()["matrixWidth"], sync.frame()["matrixHeight"]), (128, 72))
        sync._parse_ddp(packet(0, bytes(1440)))
        self.assertEqual(base64.b64decode(sync.frame()["matrix"]), pixels)
        for offset in range(1440, sync.SMALL_MATRIX_BYTES - len(last), 1440):
            sync._parse_ddp(packet(offset, middle))
        self.assertEqual(base64.b64decode(sync.frame()["matrix"]), pixels)
        sync._parse_ddp(packet(sync.SMALL_MATRIX_BYTES - len(last), last))
        self.assertEqual(base64.b64decode(sync.frame()["matrix"]), bytes(1440) + middle * 18 + last)
        sync._parse_ddp(packet(sync.MATRIX_BYTES, b"\xff"))
        self.assertEqual(base64.b64decode(sync.frame()["matrix"]), bytes(1440) + middle * 18 + last)
        sync._parse_ddp(b"\x40\x00\x00\x01" + struct.pack(">IH", 0, len(first)) + first)
        for offset in range(1440, sync.SMALL_MATRIX_BYTES - len(last), 1440):
            sync._parse_ddp(packet(offset, middle))
        sync._parse_ddp(packet(sync.SMALL_MATRIX_BYTES - len(last), last))
        self.assertEqual(sync.channels(1)[:4], bytes([11, 22, 33, 44]))
        self.assertEqual(base64.b64decode(sync.frame()["matrix"]), bytes(1440) + middle * 18 + last)
        with patch.object(sync.time, "time", return_value=sync._MATRIX_SEEN + 6):
            self.assertNotIn("matrix", sync.frame())

    def test_larger_matrix_waits_for_all_packets_and_reports_dimensions(self):
        def packet(offset, data):
            return b"\x40\x00\x00\x02" + struct.pack(">IH", offset, len(data)) + data
        full = bytes((index % 251 for index in range(sync.MATRIX_BYTES)))
        chunks = [(offset, full[offset:offset + 1440]) for offset in range(0, len(full), 1440)]
        self.assertEqual(len(chunks), 77)
        sync._parse_ddp(packet(*chunks[0]))
        sync._parse_ddp(packet(*chunks[-1]))  # last can arrive before a middle packet
        for offset, data in chunks[1:-2]:
            sync._parse_ddp(packet(offset, data))
        self.assertNotIn("matrix", sync.frame())
        sync._parse_ddp(packet(*chunks[-2]))
        result = sync.frame()
        self.assertEqual((result["matrixWidth"], result["matrixHeight"]), (256, 144))
        self.assertEqual(base64.b64decode(result["matrix"]), full)
        self.assertGreater(len(json.dumps(result)), 65535)  # WebSocket needs its 64-bit length header
        self.assertEqual(sync.matrix_marker()[1], sync.MATRIX_BYTES)
        self.assertNotIn("matrix", sync.frame(include_matrix=False))

    def test_kiosk_websocket_streams_channel_frame(self):
        sync._set_universe(12, bytes([7, 8, 9, 10]).ljust(512, b"\x00"))
        server = beamloom_player.ThreadingHTTPServer(("127.0.0.1", 0), beamloom_player.Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with socket.create_connection(server.server_address, timeout=2) as client:
                client.settimeout(2)
                client.sendall(b"GET /sync/live HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n")
                response = client.recv(30000)
                while b"\r\n\r\n" not in response:
                    response += client.recv(30000)
                head, payload = response.split(b"\r\n\r\n", 1)
                self.assertIn(b"101 Switching Protocols", head)
                while len(payload) < 4:
                    payload += client.recv(30000)
                self.assertEqual(payload[:2], b"\x81\x7e")
                length = struct.unpack(">H", payload[2:4])[0]
                while len(payload) < 4 + length:
                    payload += client.recv(30000)
                frame = json.loads(payload[4:4 + length])
                self.assertEqual(base64.b64decode(frame["universes"]["12"])[:4], bytes([7, 8, 9, 10]))
        finally:
            server.shutdown()
            server.server_close()

    def test_kiosk_websocket_streams_large_matrix_frame(self):
        with sync._LOCK:
            sync._MATRIX_FRAME = bytes([12, 34, 56]) * (256 * 144)
            sync._MATRIX_SEEN = sync.time.time()
        server = beamloom_player.ThreadingHTTPServer(("127.0.0.1", 0), beamloom_player.Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with socket.create_connection(server.server_address, timeout=2) as client:
                client.settimeout(2)
                client.sendall(b"GET /sync/live HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n")
                response = client.recv(30000)
                while b"\r\n\r\n" not in response:
                    response += client.recv(30000)
                _, payload = response.split(b"\r\n\r\n", 1)
                while len(payload) < 10:
                    payload += client.recv(30000)
                self.assertEqual(payload[:2], b"\x81\x7f")
                length = struct.unpack(">Q", payload[2:10])[0]
                while len(payload) < 10 + length:
                    payload += client.recv(30000)
                frame = json.loads(payload[10:10 + length])
                self.assertEqual((frame["matrixWidth"], frame["matrixHeight"]), (256, 144))
                self.assertEqual(len(base64.b64decode(frame["matrix"])), sync.MATRIX_BYTES)
                payload = payload[10 + length:]
                while len(payload) < 2:
                    payload += client.recv(30000)
                self.assertEqual(payload[0], 0x81)
                small_length = payload[1]
                while len(payload) < 2 + small_length:
                    payload += client.recv(30000)
                self.assertNotIn("matrix", json.loads(payload[2:2 + small_length]))
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
