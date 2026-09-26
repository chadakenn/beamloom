const { app, BrowserWindow, autoUpdater, ipcMain, protocol, screen, shell } = require("electron");
const { readFile } = require("node:fs/promises");
const fs = require("node:fs");
const https = require("node:https");
const http = require("node:http");
const dns = require("node:dns/promises");
const os = require("node:os");
const path = require("node:path");
const { startLiveServer } = require("./live.cjs");
const { squirrelInstall, isSquirrelInstalled } = require("./squirrel.cjs");
const { newerRelease } = require("./update-version.cjs");

if (squirrelInstall(process.execPath)) {
  app.quit();
  return;
}

protocol.registerSchemesAsPrivileged([
  { scheme: "beamloom", privileges: { standard: true, secure: true, supportFetchAPI: true, stream: true } },
]);

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

let editor;
let projector;
let live;

function piAddress(host) {
  if (typeof host !== "string" || host.length > 100 || !/^[a-z0-9.-]+$/i.test(host)) throw new Error("Enter the Pi's local address");
  if (host !== "beamloom.local" && !/^([a-z0-9-]+\.)+local$/i.test(host) && !/^(10\.\d{1,3}|192\.168|172\.(1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}$/.test(host)) throw new Error("Use a local Pi address");
  return host;
}

function piRequest(host, method = "GET", timeout = 2500) {
  return new Promise((resolve, reject) => {
    const started = Date.now();
    const request = http.request({ hostname: piAddress(host), port: 80, path: method === "POST" ? "/update" : "/health", method, timeout,
      headers: method === "POST" ? { "X-Beamloom-Update": "1" } : {} }, (response) => {
      let body = "";
      response.on("data", (chunk) => { body += chunk; if (body.length > 10000) request.destroy(new Error("Pi response too large")); });
      response.on("end", () => {
        if (response.statusCode !== 200) return reject(new Error(`Pi returned ${response.statusCode}`));
        try { resolve({ ...JSON.parse(body), latencyMs: Date.now() - started }); } catch { reject(new Error("Invalid Pi response")); }
      });
    });
    request.on("timeout", () => request.destroy(new Error("Pi did not respond")));
    request.on("error", reject);
    request.end();
  });
}

function piSetupRequest(host, route, pcUrl) {
  return new Promise((resolve, reject) => {
    const body = new URLSearchParams({ pcUrl }).toString();
    const request = http.request({ hostname: piAddress(host), port: 80, path: route, method: "POST", timeout: 5000,
      headers: { "content-type": "application/x-www-form-urlencoded", "content-length": Buffer.byteLength(body) } }, (response) => {
      let data = "";
      response.on("data", (chunk) => { data += chunk; if (data.length > 4000) request.destroy(new Error("Pi response too large")); });
      response.on("end", () => {
        if (response.statusCode === 404) return reject(new Error("This Pi needs a newer player for one-click setup. Open its settings page and save the PC address there."));
        try {
          const result = JSON.parse(data);
          if (!result.ok) return reject(new Error(result.error || "The Pi could not connect to this PC"));
          resolve(result);
        } catch (error) { reject(error); }
      });
    });
    request.on("timeout", () => request.destroy(new Error("Pi did not respond")));
    request.on("error", reject);
    request.end(body);
  });
}

const showFiles = new Map();
const SHOW_ID = /^[a-zA-Z0-9_-]{1,64}$/;

function piPost(host, route, headers, body) {
  return new Promise((resolve, reject) => {
    const request = http.request({ hostname: piAddress(host), port: 80, path: route, method: "POST", headers }, (response) => {
      let data = "";
      response.on("data", (chunk) => { data += chunk; if (data.length > 8000) request.destroy(new Error("Pi response too large")); });
      response.on("end", () => {
        if (response.statusCode === 404) return reject(new Error("This Pi needs Update Pi player before it can store a show."));
        try {
          const result = JSON.parse(data);
          if (!result.ok) return reject(new Error(result.error || "The Pi could not store the show."));
          resolve(result);
        } catch (error) { reject(error); }
      });
    });
    request.setTimeout(180000, () => request.destroy(new Error("The Pi stopped receiving the show.")));
    request.on("error", reject);
    if (body && typeof body.pipe === "function") body.pipe(request);
    else request.end(body ?? Buffer.alloc(0));
  });
}

function showResult(error) {
  return { ok: false, error: error instanceof Error ? error.message : "The Pi could not store the show." };
}

async function discoverPi() {
  const candidate = live?.urls.find((url) => /^http:\/\/(?:192\.168\.|10\.|172\.)/.test(url));
  if (!candidate) return [];
  const address = new URL(candidate).hostname;
  const prefix = address.split(".").slice(0, 3).join(".");
  const found = [];
  let next = 1;
  await Promise.all(Array.from({ length: 24 }, async () => {
    while (next < 255) {
      const host = `${prefix}.${next++}`;
      if (host === address) continue;
      try {
        const response = await piRequest(host, "GET", 650);
        if (typeof response.pcUrl === "string" && response.wifi && response.update) found.push({ host, wifi: response.wifi });
      } catch { /* Other LAN devices are expected. */ }
    }
  }));
  return found;
}

function fileFromRequest(root, requestUrl) {
  let pathname = "";
  try {
    pathname = decodeURIComponent(new URL(requestUrl).pathname);
  } catch {
    return null;
  }
  const relative = pathname.replace(/^[/\\]+/, "");
  if (!relative || relative.includes("\0")) return null;
  const file = path.resolve(root, relative);
  const fromRoot = path.relative(root, file);
  if (fromRoot.startsWith("..") || path.isAbsolute(fromRoot) || !path.extname(file)) return null;
  return file;
}

function createWindow({ output = false, display } = {}) {
  const bounds = display?.bounds;
  const window = new BrowserWindow({
    width: bounds?.width ?? (output ? 1280 : 1440),
    height: bounds?.height ?? (output ? 720 : 900),
    x: bounds?.x,
    y: bounds?.y,
    minWidth: output ? 640 : 900,
    minHeight: output ? 360 : 600,
    backgroundColor: "#0e0f12",
    title: output ? "Beamloom Projector" : "Beamloom",
    fullscreen: output && Boolean(display),
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  window.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  void window.loadURL(`beamloom://app/index.html${output ? "?projector=1" : ""}`);
  return window;
}

function startUpdates() {
  if (!app.isPackaged || !isSquirrelInstalled()) return;
  const feed = `https://update.electronjs.org/chadakenn/beamloom/win32-x64/${app.getVersion()}`;
  try {
    autoUpdater.setFeedURL({ url: feed });
  } catch {
    return;
  }
  let phase = "idle";
  let version = null;
  let errorMessage = null;
  const send = (next) => {
    phase = next.phase;
    version = next.version ?? version;
    errorMessage = next.message ?? null;
    if (editor && !editor.isDestroyed()) editor.webContents.send("beamloom:update", { phase, version, message: errorMessage });
  };
  autoUpdater.on("error", (error) => {
    if (phase === "downloading") send({ phase: "failed", version, message: error.message });
  });
  autoUpdater.on("update-downloaded", () => {
    send({ phase: "ready", version });
  });
  const probe = () => {
    if (phase === "downloading" || phase === "ready") return;
    const request = https.get(`${feed}/RELEASES`, (response) => {
      if (response.statusCode !== 200) {
        response.resume();
        return;
      }
      const chunks = [];
      response.on("data", (chunk) => chunks.push(chunk));
      response.on("end", () => {
        const body = Buffer.concat(chunks).toString("utf8");
        const found = body.match(/releases\/download\/([^/\s]+)\//)?.[1] ?? null;
        if (!newerRelease(found, app.getVersion())) return;
        send({ phase: "available", version: found });
      });
    });
    request.setTimeout(15000, () => request.destroy());
    request.on("error", () => {});
  };
  ipcMain.handle("beamloom:update-current", (event) => {
    if (event.sender !== editor?.webContents || phase === "idle") return null;
    return { phase, version, message: errorMessage };
  });
  ipcMain.handle("beamloom:update-apply", (event) => {
    if (event.sender !== editor?.webContents) return false;
    if (phase === "ready") {
      autoUpdater.quitAndInstall();
      return true;
    }
    if (phase !== "available" && phase !== "failed") return false;
    send({ phase: "downloading", version });
    try {
      autoUpdater.checkForUpdates();
      return true;
    } catch {
      send({ phase: "failed", version });
      return false;
    }
  });
  autoUpdater.on("update-not-available", () => {
    if (phase === "downloading") send({ phase: "failed", version, message: "The update service did not offer a downloadable installer. Use the latest Setup.exe to reinstall." });
  });
  setTimeout(probe, process.argv.includes("--squirrel-firstrun") ? 15000 : 4000);
  setInterval(probe, 30 * 60 * 1000);
}

ipcMain.handle("beamloom:app-info", (event) => {
  if (event.sender !== editor?.webContents) return null;
  return { version: app.getVersion(), installed: isSquirrelInstalled() };
});
ipcMain.handle("beamloom:installer-page", async (event) => {
  if (event.sender !== editor?.webContents) return false;
  await shell.openExternal("https://github.com/chadakenn/beamloom/releases/latest");
  return true;
});

app.whenReady().then(() => {
  const root = path.join(__dirname, "..", "dist");
  protocol.handle("beamloom", async (request) => {
    const file = fileFromRequest(root, request.url);
    if (!file) return new Response("Not found", { status: 404 });
    try {
      const body = await readFile(file);
      const type = MIME[path.extname(file).toLowerCase()] ?? "application/octet-stream";
      return new Response(body, { headers: { "content-type": type } });
    } catch {
      return new Response("Not found", { status: 404 });
    }
  });
  ipcMain.handle("beamloom:displays", (event) => {
    if (event.sender !== editor?.webContents) return [];
    const primary = screen.getPrimaryDisplay().id;
    return screen.getAllDisplays().map((display, index) => ({
      id: display.id,
      label: `Display ${index + 1}${display.id === primary ? " (main)" : ""}`,
      left: display.bounds.x,
      top: display.bounds.y,
      width: display.bounds.width,
      height: display.bounds.height,
      primary: display.id === primary,
    }));
  });
  ipcMain.handle("beamloom:open-projector", (event, displayId) => {
    if (event.sender !== editor?.webContents) return false;
    const display = Number.isInteger(displayId)
      ? screen.getAllDisplays().find((item) => item.id === displayId)
      : null;
    if (displayId !== null && !display) return false;
    if (projector && !projector.isDestroyed()) projector.close();
    projector = createWindow({ output: true, display });
    projector.on("closed", () => {
      projector = undefined;
    });
    return true;
  });
  ipcMain.handle("beamloom:live-start", async (event) => {
    if (event.sender !== editor?.webContents) return null;
    if (!live) {
      try {
        live = await startLiveServer({ root: path.join(__dirname, "..", "dist") });
      } catch {
        return null;
      }
    }
    return { port: live.port, urls: live.urls };
  });
  ipcMain.handle("beamloom:pi-status", async (event, host) => {
    if (event.sender !== editor?.webContents) return null;
    try { return { ...(await piRequest(host)), viewers: live?.stats().viewers ?? 0 }; }
    catch (error) { return { error: error.message, viewers: live?.stats().viewers ?? 0 }; }
  });
  ipcMain.handle("beamloom:pi-discover", async (event) => {
    if (event.sender !== editor?.webContents) return [];
    return discoverPi();
  });
  ipcMain.handle("beamloom:pi-connect", async (event, host) => {
    if (event.sender !== editor?.webContents || !live) return { error: "Start Pi output first." };
    try {
      const piIp = (await dns.lookup(piAddress(host), { family: 4 })).address;
      const prefix = piIp.split(".").slice(0, 3).join(".");
      const selected = live.urls.find((url) => url.startsWith(`http://${prefix}.`)) ?? live.urls.find((url) => !url.includes("//127.0.0.1:"));
      if (!selected) return { error: "Connect this PC to the same home network as the Pi." };
      await piSetupRequest(host, "/connect", selected);
      return { ok: true, pcUrl: selected };
    } catch (error) { return { error: error.message }; }
  });
  ipcMain.handle("beamloom:pi-check", async (event, host, pcUrl) => {
    if (event.sender !== editor?.webContents || !live || !live.urls.includes(pcUrl)) return { error: "Start Pi output and choose a local PC address." };
    try { return await piSetupRequest(host, "/check", pcUrl); }
    catch (error) { return { error: error.message }; }
  });
  ipcMain.handle("beamloom:pi-update", async (event, host) => {
    if (event.sender !== editor?.webContents) return null;
    try { return await piRequest(host, "POST"); }
    catch (error) { return { error: error.message }; }
  });
  ipcMain.handle("beamloom:pi-show-start", async (event, host) => {
    if (event.sender !== editor?.webContents) return { ok: false, error: "Open this from the Beamloom window." };
    try { return await piPost(host, "/show/start", { "content-length": 0 }); }
    catch (error) { return showResult(error); }
  });
  ipcMain.handle("beamloom:pi-show-project", async (event, host, project) => {
    if (event.sender !== editor?.webContents) return { ok: false, error: "Open this from the Beamloom window." };
    try {
      const body = Buffer.from(JSON.stringify(project));
      if (body.length > 2 * 1024 * 1024) return { ok: false, error: "This project is too large to store." };
      return await piPost(host, "/show/project", { "content-type": "application/json", "content-length": body.length }, body);
    } catch (error) { return showResult(error); }
  });
  ipcMain.handle("beamloom:pi-show-open", (event, id, name, mime, size) => {
    if (event.sender !== editor?.webContents || !SHOW_ID.test(id) || !Number.isInteger(size) || size < 1 || size > 512 * 1024 * 1024) return { ok: false };
    const file = path.join(os.tmpdir(), `beamloom-show-${id}`);
    fs.writeFileSync(file, Buffer.alloc(0));
    showFiles.set(id, { file, name: String(name).slice(0, 80), mime: String(mime), size, written: 0 });
    return { ok: true };
  });
  ipcMain.handle("beamloom:pi-show-write", (event, id, bytes) => {
    const item = event.sender === editor?.webContents ? showFiles.get(id) : null;
    const chunk = Buffer.isBuffer(bytes) ? bytes : Buffer.from(bytes ?? []);
    if (!item || !chunk.length || item.written + chunk.length > item.size) return { ok: false };
    fs.appendFileSync(item.file, chunk);
    item.written += chunk.length;
    return { ok: true };
  });
  ipcMain.handle("beamloom:pi-show-file", async (event, host, id) => {
    const item = event.sender === editor?.webContents ? showFiles.get(id) : null;
    if (!item || item.written !== item.size) return { ok: false, error: "The file upload stopped early." };
    try {
      const result = await piPost(host, `/show/media/${id}`, {
        "content-type": item.mime,
        "content-length": item.size,
        "x-beamloom-name": Buffer.from(item.name, "utf8").toString("base64"),
      }, fs.createReadStream(item.file));
      return result;
    } catch (error) {
      return showResult(error);
    } finally {
      fs.rmSync(item.file, { force: true });
      showFiles.delete(id);
    }
  });
  ipcMain.handle("beamloom:pi-show-finish", async (event, host) => {
    if (event.sender !== editor?.webContents) return { ok: false, error: "Open this from the Beamloom window." };
    try { return await piPost(host, "/show/finish", { "content-length": 0 }); }
    catch (error) { return showResult(error); }
  });
  ipcMain.handle("beamloom:live-stop", async (event) => {
    if (event.sender !== editor?.webContents) return false;
    const stopping = live;
    live = undefined;
    if (stopping) await stopping.stop();
    return true;
  });
  ipcMain.on("beamloom:live-frame", (event, frame) => {
    if (event.sender !== editor?.webContents || !live || !frame || typeof frame !== "object") return;
    live.publish(frame);
  });
  ipcMain.handle("beamloom:live-media", (event, id, mime, bytes) => {
    if (event.sender !== editor?.webContents || !live) return false;
    return live.registerImage(id, mime, bytes);
  });
  ipcMain.handle("beamloom:live-video-begin", (event, id, mime, size) => {
    if (event.sender !== editor?.webContents || !live) return false;
    return live.beginVideo(id, mime, size);
  });
  ipcMain.handle("beamloom:live-video-chunk", (event, id, offset, bytes) => {
    if (event.sender !== editor?.webContents || !live) return false;
    return live.videoChunk(id, offset, bytes);
  });
  ipcMain.handle("beamloom:live-video-finish", (event, id) => {
    if (event.sender !== editor?.webContents || !live) return false;
    return live.finishVideo(id);
  });
  editor = createWindow();
  startUpdates();
  editor.on("closed", () => {
    editor = undefined;
    if (projector && !projector.isDestroyed()) projector.close();
    if (live) {
      void live.stop();
      live = undefined;
    }
  });
  app.on("activate", () => {
    if (!editor) editor = createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
