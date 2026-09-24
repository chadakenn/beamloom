const MASTER_KEY = "beamloom.master.v1";

const listeners = new Set<() => void>();
let level = 1;
let loaded = false;

function clampMaster(value: number) {
  if (!Number.isFinite(value)) return 1;
  return Math.max(0, Math.min(1, Math.round(value * 100) / 100));
}

function ensureMaster() {
  if (loaded || typeof window === "undefined") return;
  loaded = true;
  const stored = localStorage.getItem(MASTER_KEY);
  level = stored === null ? 1 : clampMaster(Number(stored));
  window.addEventListener("storage", (event) => {
    if (event.key !== MASTER_KEY) return;
    level = event.newValue === null ? 1 : clampMaster(Number(event.newValue));
    listeners.forEach((listener) => listener());
  });
}

export function getMaster() {
  ensureMaster();
  return level;
}

export function setMaster(value: number) {
  ensureMaster();
  level = clampMaster(value);
  try {
    localStorage.setItem(MASTER_KEY, String(level));
  } catch {
    /* this window still dims */
  }
  listeners.forEach((listener) => listener());
}

export function subscribeMaster(listener: () => void) {
  ensureMaster();
  listeners.add(listener);
  return () => listeners.delete(listener);
}
