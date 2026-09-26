import base64
import http.client
import json
import os
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

    def test_send_show_keeps_the_old_copy_until_the_new_one_finishes(self):
        with tempfile.TemporaryDirectory() as directory:
            os.environ["BEAMLOOM_SHOW_DIR"] = str(Path(directory) / "show")
            server = player.ThreadingHTTPServer(("127.0.0.1", 0), player.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                def post(path, body=b"", headers=None):
                    connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
                    connection.request("POST", path, body, headers or {"Content-Length": str(len(body))})
                    response = connection.getresponse()
                    result = response.status, json.loads(response.read())
                    connection.close()
                    return result

                self.assertEqual(post("/show/finish")[0], 400)
                project = json.dumps({"name": "Facade", "scenes": []}).encode()
                self.assertEqual(post("/show/start")[1]["ok"], True)
                self.assertEqual(post("/show/project", project, {"Content-Type": "application/json", "Content-Length": str(len(project))})[1]["ok"], True)
                media = b"\xff\xd8\xff"
                self.assertEqual(post("/show/media/bad$id", media)[0], 400)
                saved = post("/show/media/clip1", media, {
                    "Content-Type": "image/jpeg",
                    "Content-Length": str(len(media)),
                    "X-Beamloom-Name": base64.b64encode(b"Porch.jpg").decode(),
                })
                self.assertEqual(saved[1]["ok"], True)
                finished = post("/show/finish")
                self.assertEqual(finished[0], 200)
                self.assertEqual(finished[1]["show"]["name"], "Facade")
                self.assertEqual(finished[1]["show"]["files"], 1)
                self.assertEqual((Path(directory) / "show" / "media" / "clip1").read_bytes(), media)
                other = json.dumps({"name": "Other", "scenes": []}).encode()
                self.assertEqual(post("/show/start")[1]["ok"], True)
                self.assertEqual(post("/show/project", other, {"Content-Type": "application/json", "Content-Length": str(len(other))})[1]["ok"], True)
                self.assertEqual(json.loads((Path(directory) / "show" / "project.json").read_text())["name"], "Facade")
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == "__main__":
    unittest.main()
