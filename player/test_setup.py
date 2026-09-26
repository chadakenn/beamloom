import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

import beamloom_player as player


class SetupTest(unittest.TestCase):
    def test_check_pc_rejects_non_lan_and_requires_a_live_page(self):
        for url in ("http://169.254.1.2:8751/?player=1", "http://127.0.0.1:8751/?player=1",
                    "https://192.168.1.64:8751/?player=1", "http://192.168.1.64:8080/?player=1",
                    "http://192.168.1.64:8751/other"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                player.check_pc(url)

        class Response:
            status = 200

            def getheader(self, name, default=None):
                return "text/html" if name == "content-type" else default

            def read(self, size):
                return b"<!doctype html><title>Beamloom</title>"

        class Connection:
            def __init__(self, host, port, timeout):
                self.host, self.port = host, port

            def request(self, method, path):
                assert (method, path) == ("GET", "/?player=1")

            def getresponse(self):
                return Response()

            def close(self):
                pass

        with patch.object(player.http.client, "HTTPConnection", Connection):
            self.assertEqual(player.check_pc("http://192.168.1.64:8751/?player=1"),
                             "http://192.168.1.64:8751/?player=1")

    def test_connect_only_saves_after_the_pi_reaches_the_pc(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(player, "CONFIG", Path(directory) / "player.json"):
                server = player.ThreadingHTTPServer(("127.0.0.1", 0), player.Handler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    def post():
                        connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
                        connection.request("POST", "/connect", urlencode({"pcUrl": "http://192.168.1.64:8751/?player=1"}),
                                           {"Content-Type": "application/x-www-form-urlencoded"})
                        response = connection.getresponse()
                        result = response.status, json.loads(response.read())
                        connection.close()
                        return result

                    with patch.object(player, "check_pc", side_effect=ValueError("PC unreachable")):
                        self.assertEqual(post()[0], 400)
                        self.assertEqual(player.load_config()["pcUrl"], "")
                    with patch.object(player, "check_pc", return_value="http://192.168.1.64:8751/?player=1"):
                        self.assertEqual(post()[0], 200)
                        self.assertEqual(player.load_config()["pcUrl"], "http://192.168.1.64:8751/?player=1")
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join()


if __name__ == "__main__":
    unittest.main()
