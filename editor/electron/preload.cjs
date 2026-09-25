const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("beamloomDesktop", {
  displays: () => ipcRenderer.invoke("beamloom:displays"),
  openProjector: (displayId) => ipcRenderer.invoke("beamloom:open-projector", displayId ?? null),
  updateStatus: () => ipcRenderer.invoke("beamloom:update-current"),
  onUpdate: (callback) => {
    const listener = (_event, status) => callback(status);
    ipcRenderer.on("beamloom:update", listener);
    return () => ipcRenderer.removeListener("beamloom:update", listener);
  },
  applyUpdate: () => ipcRenderer.invoke("beamloom:update-apply"),
  liveStart: () => ipcRenderer.invoke("beamloom:live-start"),
  liveStop: () => ipcRenderer.invoke("beamloom:live-stop"),
  liveFrame: (frame) => ipcRenderer.send("beamloom:live-frame", frame),
  liveMedia: (id, mime, bytes) => ipcRenderer.invoke("beamloom:live-media", id, mime, bytes),
  liveVideoBegin: (id, mime, size) => ipcRenderer.invoke("beamloom:live-video-begin", id, mime, size),
  liveVideoChunk: (id, offset, bytes) => ipcRenderer.invoke("beamloom:live-video-chunk", id, offset, bytes),
  liveVideoFinish: (id) => ipcRenderer.invoke("beamloom:live-video-finish", id),
  piStatus: (host) => ipcRenderer.invoke("beamloom:pi-status", host),
  piUpdate: (host) => ipcRenderer.invoke("beamloom:pi-update", host),
});
