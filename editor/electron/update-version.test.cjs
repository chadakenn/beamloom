const { test } = require("node:test");
const assert = require("node:assert/strict");
const { githubRelease, newerRelease, releasesListing } = require("./update-version.cjs");

test("only newer published releases trigger an update", () => {
  assert.equal(newerRelease("0.1.9", "0.1.8"), true);
  assert.equal(newerRelease("0.2.0", "0.1.99"), true);
  assert.equal(newerRelease("0.1.8", "0.1.8"), false);
  assert.equal(newerRelease("0.1.7", "0.1.8"), false);
  assert.equal(newerRelease("bad", "0.1.8"), false);
});

test("a GitHub release supplies the Windows package", () => {
  const release = githubRelease(JSON.stringify({
    tag_name: "v0.1.21",
    assets: [
      { name: "Beamloom-0.1.21-full.nupkg", browser_download_url: "https://github.com/chadakenn/beamloom/releases/download/0.1.21/Beamloom-0.1.21-full.nupkg" },
      { name: "RELEASES", browser_download_url: "https://github.com/chadakenn/beamloom/releases/download/0.1.21/RELEASES" },
    ],
  }));
  assert.equal(release.version, "0.1.21");
  assert.equal(release.nupkgName, "Beamloom-0.1.21-full.nupkg");
  assert.equal(githubRelease(JSON.stringify({ tag_name: "0.1.21", assets: [] })), null);
  assert.equal(githubRelease("{"), null);
});

test("the update listing points Squirrel at the GitHub package", () => {
  const listing = releasesListing("\uFEFF0C86106560904E4CCCC5997CE1E5377F8B9D1E9D Beamloom-0.1.21-full.nupkg 157873143\n", "Beamloom-0.1.21-full.nupkg", "https://github.com/chadakenn/beamloom/releases/download/0.1.21/Beamloom-0.1.21-full.nupkg");
  assert.equal(listing, "0C86106560904E4CCCC5997CE1E5377F8B9D1E9D https://github.com/chadakenn/beamloom/releases/download/0.1.21/Beamloom-0.1.21-full.nupkg 157873143\n");
  assert.equal(releasesListing("abc file 1", "file", "https://example.com/file"), null);
});
