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
});
