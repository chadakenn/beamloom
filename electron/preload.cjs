const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("beamloomDesktop", {
  displays: () => ipcRenderer.invoke("beamloom:displays"),
  openProjector: (displayId) => ipcRenderer.invoke("beamloom:open-projector", displayId ?? null),
  editorReady: () => ipcRenderer.send("beamloom:editor-ready"),
});
