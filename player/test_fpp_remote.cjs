const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const html = fs.readFileSync(path.join(__dirname, "play.html"), "utf8");
const code = html.match(/async function pollClock\(\) \{[\s\S]*?\n\}\n\nfunction fit/);
assert.ok(code, "Pi clock handler exists");

async function receive(syncShow) {
  const opened = [];
  const context = {
    clock: null, clockAt: 0, switching: false, showPos: 0,
    playing: [{ id: "christmas" }, { id: "halloween" }],
    performance: { now: () => 1234 },
    fetch: async () => ({ json: async () => ({ syncShow }) }),
    openShow: async (index) => { opened.push(index); context.showPos = index; },
  };
  vm.createContext(context);
  vm.runInContext(code[0].replace(/\nfunction fit$/, ""), context);
  await context.pollClock();
  return { opened, clock: context.clock, showPos: context.showPos };
}

(async () => {
  const match = await receive({ action: "play", showId: "halloween", sequence: "Halloween.fseq", elapsed: 12 });
  assert.deepEqual(match.opened, [1]);
  assert.equal(match.showPos, 1);
  assert.equal(match.clock.elapsed, 12);
  const missing = await receive({ action: "waiting", sequence: "Unknown.fseq", reason: "missing" });
  assert.deepEqual(missing.opened, []);
  assert.equal(missing.clock.action, "waiting");
  const disabled = await receive({ action: "play", showId: "disabled", sequence: "Disabled.fseq", elapsed: 1 });
  assert.deepEqual(disabled.opened, []);
  assert.equal(disabled.clock.action, "waiting");
  console.log("FPP remote show selection checks passed.");
})().catch((error) => { console.error(error); process.exitCode = 1; });
