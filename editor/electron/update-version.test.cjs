const { test } = require("node:test");
const assert = require("node:assert/strict");
const { newerRelease } = require("./update-version.cjs");

test("only newer published releases trigger an update", () => {
  assert.equal(newerRelease("0.1.9", "0.1.8"), true);
  assert.equal(newerRelease("0.2.0", "0.1.99"), true);
  assert.equal(newerRelease("0.1.8", "0.1.8"), false);
  assert.equal(newerRelease("0.1.7", "0.1.8"), false);
  assert.equal(newerRelease("bad", "0.1.8"), false);
});
