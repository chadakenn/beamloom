const { test } = require("node:test");
const assert = require("node:assert/strict");
const net = require("node:net");
const http = require("node:http");
const os = require("node:os");
const { startLiveServer } = require("./live.cjs");

function get(port, path) {
  return new Promise((resolve, reject) => {
    http.get({ hostname: "127.0.0.1", port, path }, (response) => {
      const chunks = [];
      response.on("data", (chunk) => chunks.push(chunk));
      response.on("end", () => resolve({ status: response.statusCode, type: response.headers["content-type"], body: Buffer.concat(chunks) }));
    }).on("error", reject);
  });
}

test("registered PNG is served by clip id; invalid and unknown ids are rejected", async () => {
  const interfaces = os.networkInterfaces;
  os.networkInterfaces = () => ({});
  const server = await startLiveServer({ root: __dirname, port: 0 });
  try {
    const bytes = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLytQAAAABJRU5ErkJggg==", "base64");
    assert.equal(server.registerImage("photo-1", "image/png", bytes), true);
    const jpeg = Buffer.from([255, 216, 255, 217]);
    assert.equal(server.registerImage("photo-2", "image/jpeg", jpeg), true);
    assert.equal(server.registerImage("bad/id", "image/png", bytes), false);
    assert.equal(server.registerImage("fake-video", "video/mp4", bytes), false);
    const oversized = Buffer.alloc(25 * 1024 * 1024 + 1);
    bytes.copy(oversized, 0, 0, 8);
    assert.equal(server.registerImage("too-large", "image/png", oversized), false);
    const image = await get(server.port, "/media/photo-1");
    assert.equal(image.status, 200);
    assert.equal(image.type, "image/png");
    assert.deepEqual(image.body, bytes);
    const jpegResponse = await get(server.port, "/media/photo-2");
    assert.equal(jpegResponse.type, "image/jpeg");
    assert.deepEqual(jpegResponse.body, jpeg);
    assert.equal((await get(server.port, "/media/unknown-id")).status, 404);
    assert.equal((await get(server.port, "/media/bad%2Fid")).status, 404);
  } finally {
    await server.stop();
    os.networkInterfaces = interfaces;
  }
});

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
test("a finished MP4 is served in ranges and a bad video is rejected", async () => {
  const interfaces = os.networkInterfaces;
  os.networkInterfaces = () => ({});
  const server = await startLiveServer({ root: __dirname, port: 0 });
  try {
    const body = Buffer.alloc(16);
    body.writeUInt32BE(16, 0);
    body.write("ftyp", 4);
    body.write("mp42", 8);
    assert.equal(server.beginVideo("clip-1", "video/mp4", body.length), "started");
    assert.equal(server.videoChunk("clip-1", 0, body.subarray(0, 8)), true);
    assert.equal(server.videoChunk("clip-1", 8, body.subarray(8)), true);
    assert.equal(server.finishVideo("clip-1"), true);
    assert.equal(server.beginVideo("clip-1", "video/mp4", body.length), "ready");
    assert.equal(server.beginVideo("../clip", "video/mp4", body.length), false);
    assert.equal(server.beginVideo("huge", "video/mp4", 512 * 1024 * 1024 + 1), false);
    assert.equal(server.beginVideo("text", "video/avi", 16), false);
    const whole = await get(server.port, "/media/clip-1");
    assert.equal(whole.status, 200);
    assert.equal(whole.type, "video/mp4");
    assert.deepEqual(whole.body, body);
    const part = await new Promise((resolve, reject) => {
      const request = http.request({ hostname: "127.0.0.1", port: server.port, path: "/media/clip-1", headers: { range: "bytes=4-7" } }, (response) => {
        const chunks = [];
        response.on("data", (chunk) => chunks.push(chunk));
        response.on("end", () => resolve({ status: response.statusCode, range: response.headers["content-range"], body: Buffer.concat(chunks) }));
      });
      request.on("error", reject);
      request.end();
    });
    assert.equal(part.status, 206);
    assert.equal(part.range, "bytes 4-7/16");
    assert.deepEqual(part.body, Buffer.from("ftyp"));
    const webm = Buffer.concat([Buffer.from([0x1a, 0x45, 0xdf, 0xa3]), Buffer.alloc(8)]);
    assert.equal(server.beginVideo("clip-2", "video/webm", webm.length), "started");
    assert.equal(server.videoChunk("clip-2", 0, webm), true);
    assert.equal(server.finishVideo("clip-2"), true);
    const fake = Buffer.alloc(16);
    assert.equal(server.beginVideo("clip-3", "video/mp4", fake.length), "started");
    assert.equal(server.videoChunk("clip-3", 0, fake), true);
    assert.equal(server.finishVideo("clip-3"), false);
    assert.equal((await get(server.port, "/media/clip-3")).status, 404);
  } finally {
    await server.stop();
    os.networkInterfaces = interfaces;
  }
});
