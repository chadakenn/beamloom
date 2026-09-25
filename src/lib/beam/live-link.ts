import { getMaster, subscribeMaster } from "@/lib/beam/master";
import { activeScene } from "@/lib/beam/project";
import { useEditor } from "@/lib/beam/store";

const listeners = new Set<() => void>();
let running = false;
let blackout = false;
let urls: string[] = [];
let queued = 0;
let masterWatch: (() => void) | null = null;

function notify() {
  listeners.forEach((listener) => listener());
}

function currentFrame() {
  const scene = activeScene(useEditor.getState());
  return {
    blackout,
    master: getMaster(),
    surfaces: scene.surfaces.map((face) => ({
      id: face.id,
      look: face.look,
      gel: face.gel,
      opacity: face.opacity,
      feather: face.feather,
      mask: face.mask,
      brightness: face.brightness,
      contrast: face.contrast,
      saturation: face.saturation,
      blend: face.blend,
      visible: face.visible,
      corners: face.corners,
    })),
  };
}

function schedule() {
  if (!running || queued) return;
  queued = requestAnimationFrame(() => {
    queued = 0;
    if (running) window.beamloomDesktop?.liveFrame?.(currentFrame());
  });
}

useEditor.subscribe(() => schedule());

export function liveRunning() {
  return running;
}

export function liveUrls() {
  return urls;
}

export function subscribeLive(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function setLiveBlackout(value: boolean) {
  blackout = value;
  schedule();
}

export async function startLive() {
  const info = await window.beamloomDesktop?.liveStart?.();
  if (!info?.urls?.length) return null;
  running = true;
  urls = info.urls;
  masterWatch ??= subscribeMaster(schedule);
  schedule();
  notify();
  return info;
}

export async function stopLive() {
  running = false;
  urls = [];
  if (queued) cancelAnimationFrame(queued);
  queued = 0;
  await window.beamloomDesktop?.liveStop?.();
  notify();
}
