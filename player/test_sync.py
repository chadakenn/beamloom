"""Receiver packet checks and the first-update bootstrap contract."""
import base64
import re
import struct
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

    def test_first_update_contains_sync_module(self):
        source = Path(beamloom_player.__file__).read_text(encoding="utf-8")
        payload = re.search(r'ROOT / "sync.py"\)\.write_bytes\(zlib\.decompress\(base64\.b64decode\("([^"]+)"\)\)\)', source)
        self.assertIsNotNone(payload)
        self.assertEqual(zlib.decompress(base64.b64decode(payload.group(1))), Path(sync.__file__).read_bytes())
        self.assertIn("player/sync.py", updater.FILES)


if __name__ == "__main__":
    unittest.main()
