// Type-check Electron's CommonJS files for undefined names before packaging.
// Other checkJs diagnostics need a separate typing pass as these files gain JSDoc.
const { spawnSync } = require("node:child_process");
const path = require("node:path");
const tsc = path.join(__dirname, "..", "node_modules", "typescript", "bin", "tsc");
const files = ["main.cjs", "live.cjs", "preload.cjs"].map((file) => path.join(__dirname, "..", "electron", file));
const result = spawnSync(process.execPath, [tsc, "--ignoreConfig", "--allowJs", "--checkJs", "--noEmit",
  "--strict", "false", "--target", "es2022", "--module", "nodenext", "--moduleResolution", "nodenext",
  "--skipLibCheck", "--types", "node", ...files], { encoding: "utf8" });
if (result.error) throw result.error;
const undefinedNames = (result.stdout + result.stderr).split(/\r?\n/).filter((line) => /error TS(?:2304|2552):/.test(line));
if (undefinedNames.length) {
  process.stderr.write(undefinedNames.join("\n") + "\n");
  process.exitCode = 1;
} else if (result.status === null) {
  process.stderr.write(result.stderr || "Electron check did not complete.\n");
  process.exitCode = 1;
} else {
  process.stdout.write("Electron names checked.\n");
}
