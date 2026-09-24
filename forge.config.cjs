module.exports = {
  packagerConfig: {
    name: "Beamloom",
    asar: true,
    executableName: "Beamloom",
    icon: "electron/beamloom",
  },
  rebuildConfig: {},
  makers: [
    {
      name: "@electron-forge/maker-squirrel",
      config: {
        name: "Beamloom",
        setupExe: "Beamloom Setup.exe",
        setupIcon: "electron/beamloom.ico",
      },
    },
  ],
};
