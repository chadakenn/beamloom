import { getMaster, subscribeMaster } from "@/lib/beam/master";
import { listClips, subscribeClips } from "@/lib/beam/clips";
import { activeScene } from "@/lib/beam/project";
import { useEditor } from "@/lib/beam/store";

const listeners = new Set<() => void>();
let running = false;
let blackout = false;
let urls: string[] = [];
let queued = 0;
let masterWatch: (() => void) | null = null;
const registeredImages = new Set<string>();
const registeringImages = new Set<string>();
let imageSession = 0;
const MAX_IMAGE_BYTES = 25 * 1024 * 1024;

async function registerImages() {
  const session = imageSession;
  for (const clip of listClips()) {
    if (clip.kind !== "image" || registeredImages.has(clip.id) || registeringImages.has(clip.id)) continue;
    registeringImages.add(clip.id);
    void (async () => {
      try {
        const blob = await (await fetch(clip.url)).blob();
        if (blob.size > MAX_IMAGE_BYTES || (blob.type !== "image/png" && blob.type !== "image/jpeg")) return;
        const bytes = new Uint8Array(await blob.arrayBuffer());
        if (!running || session !== imageSession) return;
        if (await window.beamloomDesktop?.liveMedia?.(clip.id, blob.type, bytes)) {
          if (running && session === imageSession) {
            registeredImages.add(clip.id);
            schedule();
          }
        }
      } catch {
        // A missing or oversized image leaves its built-in look on the Pi.
      } finally {
        if (session === imageSession) registeringImages.delete(clip.id);
      }
    })();
  }
}

function notify() {
  listeners.forEach((listener) => listener());
}

function currentFrame() {
  const scene = activeScene(useEditor.getState());
  const imageIds = new Set(listClips().filter((clip) => clip.kind === "image").map((clip) => clip.id));
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
      mediaId: face.videoId && registeredImages.has(face.videoId) && imageIds.has(face.videoId) ? face.videoId : undefined,
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
subscribeClips(() => { if (running) void registerImages(); });

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
  imageSession += 1;
  registeredImages.clear();
  registeringImages.clear();
  urls = info.urls;
  void registerImages();
  masterWatch ??= subscribeMaster(schedule);
  schedule();
  notify();
  return info;
}

export async function stopLive() {
  running = false;
  imageSession += 1;
  registeredImages.clear();
  registeringImages.clear();
  urls = [];
  if (queued) cancelAnimationFrame(queued);
  queued = 0;
  await window.beamloomDesktop?.liveStop?.();
  notify();
}
