const { test } = require("node:test");
const assert = require("node:assert/strict");
const { squirrelInstall } = require("./squirrel.cjs");

test("Squirrel installation and update refresh Windows shortcuts", () => {
  for (const event of ["--squirrel-install", "--squirrel-updated"]) {
    let command;
    const run = (exe, args) => {
      command = { exe, args };
      return { on() {}, unref() {} };
    };
    assert.equal(squirrelInstall("/Beamloom/app-0.1.8/Beamloom.exe", [event], "win32", run), true);
    assert.equal(command.exe, "/Beamloom/Update.exe");
    assert.deepEqual(command.args, ["--createShortcut=Beamloom.exe"]);
  }
  assert.equal(squirrelInstall("/Beamloom/app-0.1.8/Beamloom.exe", ["--squirrel-firstrun"], "win32"), false);
});
