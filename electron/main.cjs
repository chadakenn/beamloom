const { app, BrowserWindow, autoUpdater, ipcMain, protocol, screen } = require("electron");
const { readFile } = require("node:fs/promises");
const https = require("node:https");
const path = require("node:path");

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
  if (!app.isPackaged || process.platform !== "win32") return;
  const feed = `https://update.electronjs.org/chadakenn/beamloom/win32-x64/${app.getVersion()}`;
  try {
    autoUpdater.setFeedURL({ url: feed });
  } catch {
    return;
  }
  let phase = "idle";
  let version = null;
  const send = (next) => {
    phase = next.phase;
    version = next.version ?? version;
    if (editor && !editor.isDestroyed()) editor.webContents.send("beamloom:update", { phase, version });
  };
  autoUpdater.on("error", () => {
    if (phase === "downloading") send({ phase: "failed", version });
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
        if (!found || found === app.getVersion()) return;
        send({ phase: "available", version: found });
      });
    });
    request.setTimeout(15000, () => request.destroy());
    request.on("error", () => {});
  };
  ipcMain.handle("beamloom:update-current", (event) => {
    if (event.sender !== editor?.webContents || phase === "idle") return null;
    return { phase, version };
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
  setTimeout(probe, 4000);
  setInterval(probe, 30 * 60 * 1000);
}

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
  editor = createWindow();
  startUpdates();
  editor.on("closed", () => {
    editor = undefined;
    if (projector && !projector.isDestroyed()) projector.close();
  });
  app.on("activate", () => {
    if (!editor) editor = createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
