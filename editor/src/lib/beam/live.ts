import type { Corners } from "@/lib/beam/math";
import type { Blend, Mask } from "@/lib/beam/project";
import { type LookId } from "@/lib/beam/looks";

export type LiveSurface = {
  id: string;
  look: LookId;
  gel: number;
  opacity: number;
  feather: number;
  mask: Mask;
  brightness: number;
  contrast: number;
  saturation: number;
  speed: number;
  blend: Blend;
  visible: boolean;
  mediaId?: string;
  mediaPlaying?: boolean;
  mediaTime?: number;
  mediaLoop?: boolean;
  corners: Corners;
};

export type LiveFrame = {
  blackout: boolean;
  alignId?: string;
  master: number;
  surfaces: LiveSurface[];
};

const LOOKS = new Set([
  "wash",
  "scan",
  "lattice",
  "embers",
  "rings",
  "columns",
  "gel",
  "neon",
  "aurora",
  "confetti",
  "prism",
  "tiles",
  "pinwheel",
]);

function numberBetween(value: unknown, fallback: number, min: number, max: number) {
  const next = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(next)) return fallback;
  return Math.min(max, Math.max(min, next));
}

function parseSurface(value: unknown): LiveSurface | null {
  if (!value || typeof value !== "object") return null;
  const face = value as Partial<LiveSurface>;
  if (typeof face.id !== "string" || !LOOKS.has(String(face.look))) return null;
  if (!Array.isArray(face.corners) || face.corners.length !== 4) return null;
  const corners = face.corners.map((point) => {
    if (!point || typeof point !== "object") return null;
    const pt = point as { x?: unknown; y?: unknown };
    if (!Number.isFinite(Number(pt.x)) || !Number.isFinite(Number(pt.y))) return null;
    return { x: Math.max(0, Math.min(1, Number(pt.x))), y: Math.max(0, Math.min(1, Number(pt.y))) };
  });
  if (corners.some((point) => !point)) return null;
  const mask = face.mask === "window" || face.mask === "arch" ? face.mask : "full";
  const blend = face.blend === "add" || face.blend === "screen" ? face.blend : "normal";
  return {
    id: face.id,
    look: face.look as LookId,
    gel: numberBetween(face.gel, 0, 0, 4),
    opacity: numberBetween(face.opacity, 1, 0, 1),
    feather: numberBetween(face.feather, 0, 0, 0.4),
    mask,
    brightness: numberBetween(face.brightness, 0, -1, 1),
    contrast: numberBetween(face.contrast, 1, 0, 2),
    saturation: numberBetween(face.saturation, 1, 0, 2),
    speed: numberBetween(face.speed, 1, 0, 4),
    blend,
    visible: face.visible !== false,
    mediaId: typeof face.mediaId === "string" && /^[a-zA-Z0-9_-]{1,64}$/.test(face.mediaId) ? face.mediaId : undefined,
    ...(typeof face.mediaPlaying === "boolean"
      ? {
          mediaPlaying: face.mediaPlaying,
          mediaTime: numberBetween(face.mediaTime, 0, 0, 24 * 60 * 60),
          mediaLoop: face.mediaLoop === true,
        }
      : {}),
    corners: corners as Corners,
  };
}

export function parseLiveFrame(raw: unknown): LiveFrame | null {
  let value = raw;
  if (typeof raw === "string") {
    try {
      value = JSON.parse(raw);
    } catch {
      return null;
    }
  }
  if (!value || typeof value !== "object") return null;
  const frame = value as Partial<LiveFrame>;
  if (!Array.isArray(frame.surfaces)) return null;
  const surfaces = frame.surfaces.slice(0, 64).map(parseSurface).filter((face): face is LiveSurface => face !== null);
  return {
    blackout: frame.blackout === true,
    alignId: frame.alignId === "" || typeof frame.alignId === "string" && surfaces.some((face) => face.id === frame.alignId) ? frame.alignId : undefined,
    master: numberBetween(frame.master, 1, 0, 1),
    surfaces,
  };
}
