const SOLO_KEY = "beamloom.solo.v1";

const listeners = new Set<() => void>();
let solo = false;
let loaded = false;

function ensureSolo() {
  if (loaded || typeof window === "undefined") return;
  loaded = true;
  solo = localStorage.getItem(SOLO_KEY) === "1";
  window.addEventListener("storage", (event) => {
    if (event.key !== SOLO_KEY) return;
    solo = event.newValue === "1";
    listeners.forEach((listener) => listener());
  });
}

export function getSolo() {
  ensureSolo();
  return solo;
}

export function setSolo(next: boolean) {
  ensureSolo();
  solo = next;
  try {
    localStorage.setItem(SOLO_KEY, next ? "1" : "0");
  } catch {
    /* this window still solos */
  }
  listeners.forEach((listener) => listener());
}

export function toggleSolo() {
  setSolo(!getSolo());
}

export function subscribeSolo(listener: () => void) {
  ensureSolo();
  listeners.add(listener);
  return () => listeners.delete(listener);
}
