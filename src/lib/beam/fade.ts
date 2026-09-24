const FADE_KEY = "beamloom.fade.v1";

const listeners = new Set<() => void>();
let seconds = 0;
let loaded = false;

function clampFade(value: number) {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(2, Math.round(value * 10) / 10));
}

function ensureFade() {
  if (loaded || typeof window === "undefined") return;
  loaded = true;
  seconds = clampFade(Number(localStorage.getItem(FADE_KEY)));
  window.addEventListener("storage", (event) => {
    if (event.key !== FADE_KEY) return;
    seconds = clampFade(Number(event.newValue));
    listeners.forEach((listener) => listener());
  });
}

export function getFadeSeconds() {
  ensureFade();
  return seconds;
}

export function setFadeSeconds(value: number) {
  ensureFade();
  seconds = clampFade(value);
  try {
    localStorage.setItem(FADE_KEY, String(seconds));
  } catch {
    /* this window still fades */
  }
  listeners.forEach((listener) => listener());
}

export function subscribeFade(listener: () => void) {
  ensureFade();
  listeners.add(listener);
  return () => listeners.delete(listener);
}
