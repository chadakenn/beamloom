const { test } = require("node:test");
const assert = require("node:assert/strict");
const net = require("node:net");
const os = require("node:os");
const { startLiveServer } = require("./live.cjs");

function connected(port) {
  return new Promise((resolve, reject) => {
    const socket = net.connect(port, "127.0.0.1", () => {
      socket.write("GET /live HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n");
    });
    socket.once("error", reject);
    socket.once("data", () => resolve(socket));
  });
}

test("live server accepts a fragmented ping and closes an oversized incomplete frame", async () => {
  const interfaces = os.networkInterfaces;
  os.networkInterfaces = () => ({});
  const server = await startLiveServer({ root: __dirname, port: 0 });
  let socket;
  try {
    socket = await connected(server.port);
    const pong = new Promise((resolve) => socket.once("data", resolve));
    socket.write(Buffer.from([0x89, 0x81, 0x01, 0x02]));
    socket.write(Buffer.from([0x03, 0x04, 0x61 ^ 0x01]));
    assert.deepEqual(await pong, Buffer.from([0x8a, 0x01, 0x61]));
    assert.equal(server.stats().viewers, 1);
    const closed = new Promise((resolve) => socket.once("close", resolve));
    // A declared 65 KB frame sent in chunks must not grow the server buffer forever.
    socket.write(Buffer.from([0x82, 0xfe, 0xff, 0xff, 0, 0, 0, 0]));
    socket.write(Buffer.alloc(65536));
    await closed;
    assert.equal(server.stats().viewers, 0);
  } finally {
    socket?.destroy();
    await server.stop();
    os.networkInterfaces = interfaces;
  }
});
