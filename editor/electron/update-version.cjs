function newerRelease(candidate, current) {
  const parts = (value) => /^\d+\.\d+\.\d+$/.test(value) ? value.split(".").map(Number) : null;
  const next = parts(candidate);
  const running = parts(current);
  if (!next || !running) return false;
  for (let index = 0; index < 3; index += 1) {
    if (next[index] !== running[index]) return next[index] > running[index];
  }
  return false;
}

function githubRelease(body) {
  let data;
  try {
    data = JSON.parse(body);
  } catch {
    return null;
  }
  if (!data || typeof data !== "object") return null;
  const version = typeof data.tag_name === "string" ? data.tag_name.replace(/^v/, "") : "";
  if (!/^\d+\.\d+\.\d+$/.test(version) || !Array.isArray(data.assets)) return null;
  const nupkg = data.assets.find((asset) => asset && typeof asset.name === "string" && asset.name.endsWith(".nupkg"));
  const notes = data.assets.find((asset) => asset && asset.name === "RELEASES");
  if (!nupkg || !notes || !assetUrl(nupkg.browser_download_url) || !assetUrl(notes.browser_download_url)) return null;
  return { version, nupkgName: nupkg.name, nupkgUrl: nupkg.browser_download_url, releasesUrl: notes.browser_download_url };
}

function assetUrl(value) {
  if (typeof value !== "string") return false;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname === "github.com" && url.pathname.startsWith("/chadakenn/beamloom/releases/download/");
  } catch {
    return false;
  }
}

function releasesListing(text, nupkgName, nupkgUrl) {
  if (!assetUrl(nupkgUrl) || typeof nupkgName !== "string" || !nupkgName.endsWith(".nupkg")) return null;
  const row = String(text).replace(/^\uFEFF/, "").split(/\r?\n/).find((line) => line.trim().split(/\s+/)[1] === nupkgName);
  if (!row) return null;
  const [sha, , size] = row.trim().split(/\s+/);
  if (!/^[A-Fa-f0-9]{40}$/.test(sha) || !/^\d+$/.test(size)) return null;
  return `${sha.toUpperCase()} ${nupkgUrl} ${size}\n`;
}

module.exports = { newerRelease, githubRelease, releasesListing };
