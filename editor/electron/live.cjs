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
const MAX_CLIENT_FRAME = 64 * 1024;
const MAX_IMAGE_BYTES = 25 * 1024 * 1024;
const MAX_VIDEO_BYTES = 512 * 1024 * 1024;
const CLIP_ID = /^[a-zA-Z0-9_-]{1,64}$/;
const VIDEO_MIME = new Set(["video/mp4", "video/webm", "video/quicktime"]);

function asBuffer(data) {
  if (ArrayBuffer.isView(data)) return Buffer.from(data.buffer, data.byteOffset, data.byteLength);
  if (data instanceof ArrayBuffer) return Buffer.from(data);
  return null;
}

function validImage(mime, bytes) {
  return (mime === "image/png" && bytes.length >= 8 && bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) ||
    (mime === "image/jpeg" && bytes.length >= 3 && bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255);
}

function validVideo(mime, file) {
  const head = Buffer.alloc(12);
  const fd = fs.openSync(file, "r");
  try {
    const read = fs.readSync(fd, head, 0, 12, 0);
    if (mime === "video/webm") return read >= 4 && head[0] === 0x1a && head[1] === 0x45 && head[2] === 0xdf && head[3] === 0xa3;
    return read >= 8 && head.toString("ascii", 4, 8) === "ftyp";
  } finally {
    fs.closeSync(fd);
  }
}

function lanUrls(port) {
  const urls = [];
  for (const [name, list] of Object.entries(os.networkInterfaces())) {
    if (/tailscale|zerotier|wireguard|\bwg\d*\b|\btun\d*\b/i.test(name)) continue;
    for (const net of list ?? []) {
      const v4 = net.family === "IPv4" || net.family === 4;
      if (!v4 || net.internal) continue;
      // Link-local and VPN addresses cannot normally be reached by a Pi on the home LAN.
      if (!/^(?:192\.168\.|10\.|172\.(?:1[6-9]|2\d|3[01])\.)/.test(net.address)) continue;
      urls.push(`http://${net.address}:${port}/?player=1`);
    }
  }
  urls.sort((a, b) => {
    const rank = (url) => url.includes("//192.168.") ? 0 : url.includes("//10.") ? 1 : 2;
    return rank(a) - rank(b);
  });
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
    if (buffer.length + chunk.length > MAX_CLIENT_FRAME) {
      socket.destroy();
      return;
    }
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
  const images = new Map();
  const videos = new Map();
  const pendingVideos = new Map();
  let mediaDir = null;
  let last = null;
  const ensureDir = () => {
    if (!mediaDir) mediaDir = fs.mkdtempSync(path.join(os.tmpdir(), "beamloom-live-"));
    return mediaDir;
  };
  const serveVideo = (request, response, video) => {
    const size = video.size;
    const range = request.headers.range;
    if (!range) {
      response.writeHead(200, {
        "content-type": video.mime,
        "content-length": size,
        "accept-ranges": "bytes",
        "cache-control": "no-store",
        "x-content-type-options": "nosniff",
      });
      const stream = fs.createReadStream(video.file);
      stream.on("error", () => response.destroy());
      stream.pipe(response);
      return;
    }
    const match = /^bytes=(\d+)-(\d*)$/.exec(range);
    const start = match ? Number(match[1]) : NaN;
    let end = match && match[2] ? Number(match[2]) : size - 1;
    if (!match || start >= size || end < start) {
      response.writeHead(416, { "content-range": `bytes */${size}` });
      response.end();
      return;
    }
    end = Math.min(end, size - 1);
    response.writeHead(206, {
      "content-type": video.mime,
      "content-length": end - start + 1,
      "content-range": `bytes ${start}-${end}/${size}`,
      "accept-ranges": "bytes",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff",
    });
    const stream = fs.createReadStream(video.file, { start, end });
    stream.on("error", () => response.destroy());
    stream.pipe(response);
  };
  const server = http.createServer((request, response) => {
    const url = new URL(request.url ?? "/", "http://127.0.0.1");
    if (url.pathname.startsWith("/media/")) {
      const id = url.pathname.slice("/media/".length);
      if (request.method !== "GET" || !CLIP_ID.test(id)) {
        response.writeHead(404);
        response.end();
        return;
      }
      const image = images.get(id);
      if (image) {
        response.writeHead(200, { "content-type": image.mime, "content-length": image.bytes.length, "cache-control": "no-store", "x-content-type-options": "nosniff" });
        response.end(image.bytes);
        return;
      }
      const video = videos.get(id);
      if (video) {
        serveVideo(request, response, video);
        return;
      }
      response.writeHead(404);
      response.end();
      return;
    }
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
        stats() {
          return { viewers: clients.size };
        },
        registerImage(id, mime, data) {
          if (typeof id !== "string" || !CLIP_ID.test(id) || videos.has(id) || pendingVideos.has(id)) return false;
          const bytes = asBuffer(data);
          if (!bytes || !bytes.length || bytes.length > MAX_IMAGE_BYTES || !validImage(mime, bytes)) return false;
          if (!images.has(id)) images.set(id, { mime, bytes: Buffer.from(bytes) });
          return true;
        },
        beginVideo(id, mime, size) {
          if (typeof id !== "string" || !CLIP_ID.test(id) || !VIDEO_MIME.has(mime) || images.has(id)) return false;
          if (!Number.isInteger(size) || size < 12 || size > MAX_VIDEO_BYTES) return false;
          if (videos.has(id)) return "ready";
          if (pendingVideos.has(id)) return false;
          const file = path.join(ensureDir(), id);
          fs.writeFileSync(file, Buffer.alloc(0));
          pendingVideos.set(id, { mime, file, received: 0, size });
          return "started";
        },
        videoChunk(id, offset, data) {
          const item = typeof id === "string" ? pendingVideos.get(id) : null;
          const bytes = asBuffer(data);
          if (!item || !Number.isInteger(offset) || offset !== item.received || !bytes || !bytes.length) return false;
          if (item.received + bytes.length > item.size) return false;
          fs.appendFileSync(item.file, bytes);
          item.received += bytes.length;
          return true;
        },
        finishVideo(id) {
          const item = typeof id === "string" ? pendingVideos.get(id) : null;
          if (!item || item.received !== item.size || !validVideo(item.mime, item.file)) {
            if (item) {
              pendingVideos.delete(id);
              fs.rmSync(item.file, { force: true });
            }
            return false;
          }
          pendingVideos.delete(id);
          videos.set(id, { mime: item.mime, file: item.file, size: item.size });
          return true;
        },
        publish(frame) {
          last = JSON.stringify(frame);
          for (const socket of clients) sendText(socket, last);
        },
        stop() {
          images.clear();
          videos.clear();
          pendingVideos.clear();
          if (mediaDir) fs.rmSync(mediaDir, { recursive: true, force: true });
          mediaDir = null;
          last = null;
          for (const socket of clients) socket.destroy();
          clients.clear();
          return new Promise((done) => server.close(() => done()));
        },
      });
    });
  });
}

module.exports = { startLiveServer, lanUrls };
