const { app, BrowserWindow, ipcMain, net, protocol, screen } = require("electron");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

protocol.registerSchemesAsPrivileged([{ scheme: "beamloom", privileges: { standard: true, secure: true, supportFetchAPI: true, stream: true } }]);

let editor;
let projector;

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

app.whenReady().then(() => {
  const root = path.join(__dirname, "..", "dist");
  protocol.handle("beamloom", (request) => {
    const pathname = new URL(request.url).pathname;
    const file = path.resolve(root, `.${pathname}`);
    if (!file.startsWith(root + path.sep) || !path.extname(file)) {
      return new Response("Not found", { status: 404 });
    }
    return net.fetch(pathToFileURL(file).href);
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
    projector.on("closed", () => { projector = undefined; });
    return true;
  });
  editor = createWindow();
  editor.on("closed", () => { editor = undefined; if (projector && !projector.isDestroyed()) projector.close(); });
  app.on("activate", () => { if (!editor) editor = createWindow(); });
});

app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
