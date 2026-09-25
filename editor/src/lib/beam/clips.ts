export type ClipKind = "video" | "image";

export type Clip = {
  id: string;
  name: string;
  url: string;
  kind: ClipKind;
  video: HTMLVideoElement | null;
  image: HTMLImageElement | null;
};

type StoredClip = { id: string; name: string; blob: Blob };

const DB_NAME = "beamloom";
const STORE = "videos";
export const CLIP_CHANGE_KEY = "beamloom.clips.changed";

let clips: Clip[] = [];
const listeners = new Set<() => void>();
let restorePromise: Promise<void> | null = null;

function emit() {
  for (const listener of listeners) listener();
}

export function listClips(): Clip[] {
  return clips;
}

export async function storedClips(): Promise<StoredClip[]> {
  await restoreClips();
  return idbAll();
}

export async function syncClips(): Promise<void> {
  await restoreClips();
  const records = await idbAll();
  for (const record of records) {
    if (!clips.some((clip) => clip.id === record.id)) mountClip(record);
  }
  emit();
}

export function getClipVideo(id: string | null): HTMLVideoElement | null {
  if (!id) return null;
  return clips.find((clip) => clip.id === id)?.video ?? null;
}

export function getClipSource(id: string | null): TexImageSource | null {
  const clip = id ? clips.find((item) => item.id === id) : undefined;
  if (!clip) return null;
  if (clip.kind === "image") {
    const image = clip.image;
    if (!image || !image.complete || image.naturalWidth === 0) return null;
    return image;
  }
  const video = clip.video;
  if (!video || video.readyState < 2 || video.videoWidth === 0) return null;
  return video;
}

export function mediaFile(file: File): File | null {
  if (file.type.startsWith("video/")) return file;
  if (file.type === "image/png" || file.type === "image/jpeg") return file;
  if (file.type && file.type !== "application/octet-stream") return null;
  const name = file.name.toLowerCase();
  if (name.endsWith(".png")) return new File([file], file.name, { type: "image/png" });
  if (name.endsWith(".jpg") || name.endsWith(".jpeg")) return new File([file], file.name, { type: "image/jpeg" });
  return null;
}

export function subscribeClips(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function restoreClips() {
  if (!restorePromise) restorePromise = loadAll();
  return restorePromise;
}

export async function importVideoFiles(files: File[]): Promise<string[]> {
  const ids: string[] = [];
  for (const file of files) {
    const media = mediaFile(file);
    if (!media) continue;
    const id = crypto.randomUUID();
    const name = media.name.slice(0, 80) || (media.type.startsWith("image/") ? "Image" : "Video");
    await idbPut({ id, name, blob: media });
    mountClip({ id, name, blob: media });
    ids.push(id);
  }
  if (ids.length > 0) {
    emit();
    try {
      localStorage.setItem(CLIP_CHANGE_KEY, crypto.randomUUID());
    } catch {
      /* private mode */
    }
  }
  return ids;
}

export async function removeClip(id: string) {
  const clip = clips.find((item) => item.id === id);
  if (!clip) return;
  if (clip.video) {
    clip.video.pause();
    held.delete(id);
    clip.video.remove();
  }
  URL.revokeObjectURL(clip.url);
  clips = clips.filter((item) => item.id !== id);
  await idbDelete(id);
  emit();
}

const held = new Set<string>();

export function clipTransport(id: string | null) {
  const clip = id ? clips.find((item) => item.id === id) : undefined;
  if (!clip?.video) return null;
  const duration = Number.isFinite(clip.video.duration) ? clip.video.duration : 0;
  return {
    name: clip.name,
    paused: clip.video.paused,
    muted: clip.video.muted,
    loop: clip.video.loop,
    current: clip.video.currentTime || 0,
    duration,
  };
}

export function setClipPlaying(id: string, playing: boolean) {
  const video = getClipVideo(id);
  if (!video) return;
  if (playing) {
    held.delete(id);
    void video.play().catch(() => undefined);
  } else {
    held.add(id);
    video.pause();
  }
}

export function setClipMuted(id: string, muted: boolean) {
  const video = getClipVideo(id);
  if (!video) return;
  video.muted = muted;
  if (!muted && !held.has(id) && video.paused) void video.play().catch(() => undefined);
}

export function setClipLoop(id: string, loop: boolean) {
  const video = getClipVideo(id);
  if (!video) return;
  video.loop = loop;
}

export function seekClip(id: string, time: number) {
  const video = getClipVideo(id);
  if (!video || !Number.isFinite(video.duration)) return;
  const next = Math.max(0, Math.min(video.duration, time));
  if (Number.isFinite(next)) video.currentTime = next;
}

export function resumeClips() {
  for (const clip of clips) {
    if (!clip.video || held.has(clip.id) || !clip.video.paused) continue;
    void clip.video.play().catch(() => undefined);
  }
}

function mountClip(record: StoredClip) {
  const url = URL.createObjectURL(record.blob);
  const kind: ClipKind = record.blob.type === "image/png" || record.blob.type === "image/jpeg" ? "image" : "video";
  if (kind === "image") {
    const image = new Image();
    image.src = url;
    image.decoding = "async";
    clips = [...clips.filter((item) => item.id !== record.id), { id: record.id, name: record.name, url, kind, video: null, image }];
    image.addEventListener("load", emit, { once: true });
    return;
  }
  const video = document.createElement("video");
  video.src = url;
  video.muted = true;
  video.loop = true;
  video.playsInline = true;
  video.preload = "auto";
  video.dataset.beamClip = record.id;
  video.style.cssText = "position:fixed;width:2px;height:2px;opacity:0;pointer-events:none";
  document.body.appendChild(video);
  const start = () => {
    void video.play().catch(() => undefined);
  };
  if (video.readyState >= 2) start();
  else video.addEventListener("loadeddata", start, { once: true });
  clips = [...clips.filter((item) => item.id !== record.id), { id: record.id, name: record.name, url, kind, video, image: null }];
}

async function loadAll() {
  if (typeof indexedDB === "undefined") return;
  const records = await idbAll();
  for (const record of records) mountClip(record);
  emit();
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: "id" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function idbPut(record: StoredClip) {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).put(record);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

async function idbDelete(id: string) {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

async function idbAll(): Promise<StoredClip[]> {
  const db = await openDb();
  const records = await new Promise<StoredClip[]>((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const request = tx.objectStore(STORE).getAll();
    request.onsuccess = () => resolve(request.result as StoredClip[]);
    request.onerror = () => reject(request.error);
  });
  db.close();
  return records;
}
