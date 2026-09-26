const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");

function squirrelInstall(execPath, argv = process.argv, platform = process.platform, run = spawn) {
  if (platform !== "win32") return false;
  const event = argv.find((arg) => arg.startsWith("--squirrel-"));
  if (!event || event === "--squirrel-firstrun") return false;
  const action = {
    "--squirrel-install": "--createShortcut",
    "--squirrel-updated": "--createShortcut",
    "--squirrel-uninstall": "--removeShortcut",
  }[event];
  if (action) {
    const updateExe = path.resolve(path.dirname(execPath), "..", "Update.exe");
    const child = run(updateExe, [`${action}=${path.basename(execPath)}`], { detached: true, stdio: "ignore" });
    child.on("error", () => {});
    child.unref();
  }
  return true;
}

function isSquirrelInstalled(execPath = process.execPath, platform = process.platform) {
  if (platform !== "win32") return false;
  const folder = path.dirname(execPath);
  return /^app-\d+\.\d+\.\d+(?:-[a-z0-9.-]+)?$/i.test(path.basename(folder)) &&
    fs.existsSync(path.join(path.dirname(folder), "Update.exe"));
}

module.exports = { squirrelInstall, isSquirrelInstalled };
