const crypto = require("node:crypto");
const fs = require("node:fs");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".json": "application/json",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".gif": "image/gif",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".txt": "text/plain; charset=utf-8",
  ".map": "application/json",
};

const WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";

function lanUrls(port) {
  const urls = [];
  for (const list of Object.values(os.networkInterfaces())) {
    for (const net of list ?? []) {
      const v4 = net.family === "IPv4" || net.family === 4;
      if (!v4 || net.internal) continue;
      urls.push(`http://${net.address}:${port}/?player=1`);
    }
  }
  if (urls.length === 0) urls.push(`http://127.0.0.1:${port}/?player=1`);
  return urls;
}

function safeFile(root, pathname) {
  const relative = decodeURIComponent(pathname).replace(/^[/\\]+/, "");
  if (!relative || relative.includes("\0")) return null;
  const file = path.resolve(root, relative);
  const fromRoot = path.relative(root, file);
  if (fromRoot.startsWith("..") || path.isAbsolute(fromRoot) || !path.extname(file)) return null;
  return file;
}

function sendText(socket, text) {
  const payload = Buffer.from(text);
  let header;
  if (payload.length < 126) header = Buffer.from([0x81, payload.length]);
  else if (payload.length < 65536) header = Buffer.from([0x81, 126, payload.length >> 8, payload.length & 0xff]);
  else return;
  socket.write(Buffer.concat([header, payload]));
}

function takeFrame(buffer) {
  if (buffer.length < 2) return null;
  const opcode = buffer[0] & 0x0f;
  const masked = (buffer[1] & 0x80) !== 0;
  let length = buffer[1] & 0x7f;
  let offset = 2;
  if (length === 126) {
    if (buffer.length < 4) return null;
    length = buffer.readUInt16BE(2);
    offset = 4;
  } else if (length === 127) {
    return { error: true };
  }
  if (buffer.length < offset + (masked ? 4 : 0) + length) return null;
  const mask = masked ? buffer.subarray(offset, offset + 4) : null;
  if (masked) offset += 4;
  const payload = Buffer.from(buffer.subarray(offset, offset + length));
  if (mask) {
    for (let i = 0; i < payload.length; i += 1) payload[i] ^= mask[i % 4];
  }
  return { opcode, payload, rest: buffer.subarray(offset + length) };
}

function attachSocket(socket, clients) {
  let buffer = Buffer.alloc(0);
  socket.on("data", (chunk) => {
    buffer = Buffer.concat([buffer, chunk]);
    for (;;) {
      const frame = takeFrame(buffer);
      if (!frame) return;
      if (frame.error) {
        socket.destroy();
        return;
      }
      buffer = frame.rest;
      if (frame.opcode === 0x8) {
        socket.end(Buffer.from([0x88, 0x00]));
        clients.delete(socket);
        return;
      }
      if (frame.opcode === 0x9) {
        const header = Buffer.alloc(2);
        header[0] = 0x8a;
        header[1] = frame.payload.length;
        socket.write(Buffer.concat([header, frame.payload]));
      }
    }
  });
  socket.on("close", () => clients.delete(socket));
  socket.on("error", () => clients.delete(socket));
}

function startLiveServer({ root, port = 8751 }) {
  const clients = new Set();
  let last = null;
  const server = http.createServer((request, response) => {
    const url = new URL(request.url ?? "/", "http://127.0.0.1");
    if (url.pathname === "/" || url.pathname === "/index.html") {
      if (!url.searchParams.has("player")) {
        response.writeHead(302, { location: "/?player=1" });
        response.end();
        return;
      }
      const file = path.join(root, "index.html");
      fs.readFile(file, (error, body) => {
        if (error) {
          response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
          response.end("Beamloom player files are missing. Open the installed app, not the source preview.");
          return;
        }
        response.writeHead(200, { "content-type": MIME[".html"] });
        response.end(body);
      });
      return;
    }
    const file = safeFile(root, url.pathname);
    if (!file) {
      response.writeHead(404);
      response.end();
      return;
    }
    fs.readFile(file, (error, body) => {
      if (error) {
        response.writeHead(404);
        response.end();
        return;
      }
      response.writeHead(200, { "content-type": MIME[path.extname(file).toLowerCase()] ?? "application/octet-stream" });
      response.end(body);
    });
  });
  server.on("upgrade", (request, socket) => {
    const url = new URL(request.url ?? "/", "http://127.0.0.1");
    const key = request.headers["sec-websocket-key"];
    if (url.pathname !== "/live" || !key) {
      socket.destroy();
      return;
    }
    const accept = crypto.createHash("sha1").update(key + WS_GUID).digest("base64");
    socket.write(
      "HTTP/1.1 101 Switching Protocols\r\n" +
        "Upgrade: websocket\r\n" +
        "Connection: Upgrade\r\n" +
        `Sec-WebSocket-Accept: ${accept}\r\n\r\n`,
    );
    clients.add(socket);
    attachSocket(socket, clients);
    if (last) sendText(socket, last);
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "0.0.0.0", () => {
      server.off("error", reject);
      const listening = server.address();
      const actual = typeof listening === "object" && listening ? listening.port : port;
      resolve({
        port: actual,
        urls: lanUrls(actual),
        publish(frame) {
          last = JSON.stringify(frame);
          for (const socket of clients) sendText(socket, last);
        },
        stop() {
          for (const socket of clients) socket.destroy();
          clients.clear();
          return new Promise((done) => server.close(() => done()));
        },
      });
    });
  });
}

module.exports = { startLiveServer };
