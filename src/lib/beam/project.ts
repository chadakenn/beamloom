import { gelRgb, type LookId } from "@/lib/beam/looks";
import { translateCorners, type Corners, type Pt } from "@/lib/beam/math";

export type Blend = "normal" | "add" | "screen";

export type Surface = {
  id: string;
  name: string;
  look: LookId;
  gel: number;
  opacity: number;
  feather: number;
  blend: Blend;
  visible: boolean;
  locked: boolean;
  videoId: string | null;
  corners: Corners;
};

export type Scene = {
  id: string;
  name: string;
  surfaces: Surface[];
};

export type Project = {
  name: string;
  scenes: Scene[];
  activeSceneId: string;
  selectedId: string | null;
  guides: boolean;
  seq: number;
};

export const STORAGE_KEY = "beamloom.project.v1";

function surface(
  id: string,
  name: string,
  look: LookId,
  corners: Corners,
  extra?: Partial<Surface>,
): Surface {
  return {
    id,
    name,
    look,
    gel: 0,
    opacity: 1,
    feather: 0,
    blend: "normal",
    visible: true,
    locked: false,
    videoId: null,
    corners,
    ...extra,
  };
}

export function demoProject(): Project {
  return {
    name: "Facade study",
    seq: 8,
    guides: true,
    selectedId: "bay",
    activeSceneId: "facade",
    scenes: [
      {
        id: "facade",
        name: "Facade",
        surfaces: [
          surface("pier-l", "Left pier", "columns", [
            { x: 0.06, y: 0.18 },
            { x: 0.2, y: 0.16 },
            { x: 0.2, y: 0.8 },
            { x: 0.05, y: 0.84 },
          ]),
          surface("pier-r", "Right pier", "columns", [
            { x: 0.8, y: 0.16 },
            { x: 0.94, y: 0.18 },
            { x: 0.95, y: 0.84 },
            { x: 0.8, y: 0.8 },
          ]),
          surface("bay", "Main bay", "lattice", [
            { x: 0.22, y: 0.18 },
            { x: 0.78, y: 0.16 },
            { x: 0.8, y: 0.64 },
            { x: 0.2, y: 0.66 },
          ]),
          surface(
            "sill",
            "Sill",
            "wash",
            [
              { x: 0.16, y: 0.68 },
              { x: 0.84, y: 0.66 },
              { x: 0.92, y: 0.92 },
              { x: 0.08, y: 0.94 },
            ],
            { blend: "add", opacity: 0.92 },
          ),
        ],
      },
      {
        id: "object",
        name: "Object",
        surfaces: [
          surface("crate", "Crate face", "rings", [
            { x: 0.28, y: 0.2 },
            { x: 0.7, y: 0.28 },
            { x: 0.74, y: 0.6 },
            { x: 0.24, y: 0.56 },
          ]),
          surface(
            "spill",
            "Floor spill",
            "embers",
            [
              { x: 0.18, y: 0.62 },
              { x: 0.8, y: 0.58 },
              { x: 0.94, y: 0.92 },
              { x: 0.06, y: 0.9 },
            ],
            { blend: "add" },
          ),
        ],
      },
    ],
  };
}

export function activeScene(project: Project): Scene {
  return project.scenes.find((scene) => scene.id === project.activeSceneId) ?? project.scenes[0];
}

export function selectedSurface(project: Project): Surface | null {
  const scene = activeScene(project);
  return scene.surfaces.find((surface) => surface.id === project.selectedId) ?? null;
}

function isPt(value: unknown): value is Pt {
  if (!value || typeof value !== "object") return false;
  const pt = value as Pt;
  return Number.isFinite(pt.x) && Number.isFinite(pt.y);
}

function isLook(value: unknown): value is LookId {
  return (
    value === "wash" ||
    value === "scan" ||
    value === "lattice" ||
    value === "embers" ||
    value === "rings" ||
    value === "columns" ||
    value === "gel"
  );
}

export function sanitizeProject(value: unknown): Project | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Partial<Project>;
  if (!Array.isArray(raw.scenes) || raw.scenes.length === 0) return null;
  const scenes: Scene[] = [];
  for (const scene of raw.scenes) {
    if (!scene || typeof scene !== "object") return null;
    const s = scene as Scene;
    if (typeof s.id !== "string" || typeof s.name !== "string" || !Array.isArray(s.surfaces)) {
      return null;
    }
    const surfaces: Surface[] = [];
    for (const item of s.surfaces) {
      if (!item || typeof item !== "object") return null;
      const face = item as Surface;
      if (typeof face.id !== "string" || typeof face.name !== "string") return null;
      if (!isLook(face.look) || !Array.isArray(face.corners) || face.corners.length !== 4) return null;
      if (!face.corners.every(isPt)) return null;
      const blend: Blend =
        face.blend === "add" || face.blend === "screen" ? face.blend : "normal";
      surfaces.push({
        id: face.id,
        name: face.name.slice(0, 40),
        look: face.look,
        gel: Math.max(0, Math.min(4, Math.round(face.gel) || 0)),
        opacity: Math.max(0, Math.min(1, Number(face.opacity) || 0)),
        feather: Math.max(0, Math.min(0.4, Number(face.feather) || 0)),
        blend,
        visible: face.visible !== false,
        locked: face.locked === true,
        videoId:
          typeof face.videoId === "string" && face.videoId.length > 0 && face.videoId.length < 80
            ? face.videoId
            : null,
        corners: face.corners.map((c) => ({
          x: Math.max(0, Math.min(1, c.x)),
          y: Math.max(0, Math.min(1, c.y)),
        })) as Corners,
      });
    }
    scenes.push({ id: s.id, name: s.name.slice(0, 32), surfaces });
  }
  const activeSceneId = scenes.some((scene) => scene.id === raw.activeSceneId)
    ? (raw.activeSceneId as string)
    : scenes[0].id;
  const current = scenes.find((scene) => scene.id === activeSceneId) ?? scenes[0];
  const selectedId = current.surfaces.some((face) => face.id === raw.selectedId)
    ? (raw.selectedId ?? null)
    : (current.surfaces[0]?.id ?? null);
  return {
    name: typeof raw.name === "string" && raw.name.trim() ? raw.name.slice(0, 48) : "Untitled",
    scenes,
    activeSceneId,
    selectedId,
    guides: raw.guides !== false,
    seq: Number.isFinite(raw.seq) ? Number(raw.seq) : 1,
  };
}

export function drawGel(index: number): [number, number, number] {
  return gelRgb(index);
}

export function offsetCorners(corners: Corners, amount = 0.03): Corners {
  return translateCorners(corners, amount, amount);
}
