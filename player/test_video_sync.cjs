const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const html = fs.readFileSync(require("node:path").join(__dirname, "play.html"), "utf8");
const code = html.match(/function syncStoredVideos\(scene, now\) \{[\s\S]*?\n\}\nfunction sceneNow/);
assert.ok(code, "stored video sync function exists");

function run(action, time, current, duration = 10) {
  const video = {
    readyState: 2, duration, currentTime: current, paused: false, seeking: false,
    pause() { this.paused = true; },
    play() { this.paused = false; return Promise.resolve(); },
  };
  const context = { clock: { action }, sceneStarted: 1000, videos: new Map([["clip1", video]]) };
  vm.createContext(context);
  vm.runInContext(code[0].replace(/\nfunction sceneNow$/, "") + "\nsyncStoredVideos({surfaces:[{videoId:'clip1'}]}, " + time + ");", context);
  return video;
}

assert.equal(run("play", 6300, 0).currentTime, 5.3, "starting mid-scene seeks to FPP time");
assert.equal(run("hold", 7300, 0).paused, true, "FPP hold pauses at its position");
assert.ok(Math.abs(run("play", 13300, 0).currentTime - 2.3) < 0.001, "looping video wraps at its duration");
assert.equal(run("play", 6300, 5.15).currentTime, 5.15, "small drift does not cause repeated seeks");
console.log("Stored video sync checks passed.");
