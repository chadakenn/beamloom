import { getMaster, subscribeMaster } from "@/lib/beam/master";
import { clipTransport, listClips, subscribeClips } from "@/lib/beam/clips";
import { activeScene } from "@/lib/beam/project";
import { useEditor } from "@/lib/beam/store";

const listeners = new Set<() => void>();
let running = false;
let blackout = false;
let urls: string[] = [];
let queued = 0;
let masterWatch: (() => void) | null = null;
const registeredImages = new Set<string>();
const registeredVideos = new Set<string>();
const registering = new Set<string>();
const rejectedVideos = new Set<string>();
let mediaSession = 0;
let mediaClock = 0;
const MAX_IMAGE_BYTES = 25 * 1024 * 1024;
const MAX_VIDEO_BYTES = 512 * 1024 * 1024;
const VIDEO_CHUNK = 1024 * 1024;
const VIDEO_TYPES = new Set(["video/mp4", "video/webm", "video/quicktime"]);

function rejectVideo(id: string, session: number) {
  if (session !== mediaSession) return;
  rejectedVideos.add(id);
  notify();
}

async function registerVideos() {
  const session = mediaSession;
  for (const clip of listClips()) {
    if (clip.kind !== "video" || registeredVideos.has(clip.id) || registering.has(clip.id)) continue;
    registering.add(clip.id);
    void (async () => {
      try {
        const blob = await (await fetch(clip.url)).blob();
        if (!running || session !== mediaSession) return;
        if (blob.size > MAX_VIDEO_BYTES || blob.size < 12 || !VIDEO_TYPES.has(blob.type)) {
          rejectVideo(clip.id, session);
          return;
        }
        const started = await window.beamloomDesktop?.liveVideoBegin?.(clip.id, blob.type, blob.size);
        if (!running || session !== mediaSession) return;
        if (started === "ready") {
          registeredVideos.add(clip.id);
          schedule();
          return;
        }
        if (started !== "started") {
          rejectVideo(clip.id, session);
          return;
        }
        let offset = 0;
        while (offset < blob.size) {
          const bytes = new Uint8Array(await blob.slice(offset, offset + VIDEO_CHUNK).arrayBuffer());
          if (!running || session !== mediaSession) return;
          if (!(await window.beamloomDesktop?.liveVideoChunk?.(clip.id, offset, bytes))) {
            rejectVideo(clip.id, session);
            return;
          }
          offset += bytes.length;
        }
        if (!running || session !== mediaSession) return;
        if (await window.beamloomDesktop?.liveVideoFinish?.(clip.id)) {
          registeredVideos.add(clip.id);
          rejectedVideos.delete(clip.id);
          schedule();
          notify();
        } else rejectVideo(clip.id, session);
      } catch {
        rejectVideo(clip.id, session);
      } finally {
        if (session === mediaSession) registering.delete(clip.id);
      }
    })();
  }
}

async function registerImages() {
  const session = mediaSession;
  for (const clip of listClips()) {
    if (clip.kind !== "image" || registeredImages.has(clip.id) || registering.has(clip.id)) continue;
    registering.add(clip.id);
    void (async () => {
      try {
        const blob = await (await fetch(clip.url)).blob();
        if (blob.size > MAX_IMAGE_BYTES || (blob.type !== "image/png" && blob.type !== "image/jpeg")) return;
        const bytes = new Uint8Array(await blob.arrayBuffer());
        if (!running || session !== mediaSession) return;
        if (await window.beamloomDesktop?.liveMedia?.(clip.id, blob.type, bytes)) {
          if (running && session === mediaSession) {
            registeredImages.add(clip.id);
            schedule();
          }
        }
      } catch {
        // A missing or oversized image leaves its built-in look on the Pi.
      } finally {
        if (session === mediaSession) registering.delete(clip.id);
      }
    })();
  }
}

function registerMedia() {
  void registerImages();
  void registerVideos();
}

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
      speed: face.speed,
      blend: face.blend,
      visible: face.visible,
      ...mediaFields(face.videoId),
      corners: face.corners,
    })),
  };
}

function mediaFields(videoId: string | null) {
  if (!videoId) return {};
  if (registeredImages.has(videoId)) return { mediaId: videoId };
  if (!registeredVideos.has(videoId)) return {};
  const transport = clipTransport(videoId);
  return {
    mediaId: videoId,
    mediaPlaying: transport ? !transport.paused : false,
    mediaTime: transport?.current ?? 0,
    mediaLoop: transport?.loop ?? true,
  };
}

function sceneUsesVideo() {
  return activeScene(useEditor.getState()).surfaces.some((face) => face.videoId && registeredVideos.has(face.videoId));
}

function schedule() {
  if (!running || queued) return;
  queued = requestAnimationFrame(() => {
    queued = 0;
    if (running) window.beamloomDesktop?.liveFrame?.(currentFrame());
  });
}

useEditor.subscribe(() => schedule());
subscribeClips(() => { if (running) registerMedia(); });

export function liveMediaNote() {
  return rejectedVideos.size > 0
    ? "A video is over 512 MB or is not an MP4, WebM, or MOV. The Pi is showing that surface's colored look."
    : "";
}

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
  mediaSession += 1;
  registeredImages.clear();
  registeredVideos.clear();
  registering.clear();
  rejectedVideos.clear();
  urls = info.urls;
  registerMedia();
  masterWatch ??= subscribeMaster(schedule);
  if (!mediaClock) mediaClock = window.setInterval(() => { if (running && sceneUsesVideo()) schedule(); }, 250);
  schedule();
  notify();
  return info;
}

export async function stopLive() {
  running = false;
  mediaSession += 1;
  registeredImages.clear();
  registeredVideos.clear();
  registering.clear();
  rejectedVideos.clear();
  urls = [];
  if (mediaClock) window.clearInterval(mediaClock);
  mediaClock = 0;
  if (queued) cancelAnimationFrame(queued);
  queued = 0;
  await window.beamloomDesktop?.liveStop?.();
  notify();
}
