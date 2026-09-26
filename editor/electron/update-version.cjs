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

module.exports = { newerRelease };
