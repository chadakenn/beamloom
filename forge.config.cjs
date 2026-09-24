module.exports = {
  packagerConfig: {
    name: "Beamloom",
    asar: true,
    executableName: "Beamloom",
  },
  rebuildConfig: {},
  makers: [
    {
      name: "@electron-forge/maker-squirrel",
      config: { name: "Beamloom", setupExe: "Beamloom Setup.exe" },
    },
  ],
};
