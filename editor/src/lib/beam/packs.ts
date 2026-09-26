import type { LookId } from "@/lib/beam/looks";
import type { Blend, Mask, Project, Surface } from "@/lib/beam/project";

type Role = "window" | "door" | "garage" | "trim" | "wall";

type Style = {
  look: LookId;
  gel: number;
  speed: number;
  opacity: number;
  mask: Mask;
  brightness: number;
  blend: Blend;
};

type PackScene = {
  name: string;
  durationSeconds: number;
  roles: Record<Role, Style>;
};

export type Pack = {
  id: string;
  name: string;
  blurb: string;
  scenes: PackScene[];
};

function style(look: LookId, gel: number, extra?: Partial<Style>): Style {
  return { look, gel, speed: 1, opacity: 1, mask: "full", brightness: 0, blend: "normal", ...extra };
}

function scene(name: string, roles: Record<Role, Style>): PackScene {
  return { name, durationSeconds: 12, roles };
}

export const PACKS: Pack[] = [
  {
    id: "halloween",
    name: "Halloween",
    blurb: "Pumpkin glow, flicker, and a haunted window",
    scenes: [
      scene("Jack-o'-lantern", {
        window: style("embers", 0, { speed: 1.2, mask: "window" }),
        door: style("gel", 0, { speed: 0.6 }),
        garage: style("wash", 0, { brightness: -0.25, speed: 0.4 }),
        trim: style("scan", 0, { speed: 0.5 }),
        wall: style("wash", 0, { brightness: -0.15, speed: 0.5 }),
      }),
      scene("Flicker", {
        window: style("embers", 2, { speed: 2.2, mask: "window" }),
        door: style("gel", 2),
        garage: style("columns", 0, { speed: 0.4, opacity: 0.65 }),
        trim: style("gel", 0, { opacity: 0.8 }),
        wall: style("embers", 0, { speed: 1.4, opacity: 0.8 }),
      }),
      scene("Haunted glass", {
        window: style("aurora", 3, { speed: 0.45, mask: "window" }),
        door: style("neon", 4, { speed: 0.7 }),
        garage: style("pinwheel", 4, { speed: 0.35, opacity: 0.7 }),
        trim: style("scan", 4, { speed: 0.4 }),
        wall: style("aurora", 4, { speed: 0.4, opacity: 0.75 }),
      }),
      scene("Witching hour", {
        window: style("confetti", 4, { speed: 1.1, mask: "window" }),
        door: style("rings", 2, { speed: 0.8 }),
        garage: style("gel", 4, { opacity: 0.45 }),
        trim: style("pinwheel", 2, { speed: 0.5 }),
        wall: style("rings", 4, { speed: 0.6, opacity: 0.7 }),
      }),
    ],
  },
  {
    id: "christmas",
    name: "Christmas",
    blurb: "Warm eaves, colored lights, and a quiet night",
    scenes: [
      scene("Warm eaves", {
        window: style("gel", 1, { mask: "window", speed: 0.4 }),
        door: style("gel", 2),
        garage: style("wash", 0, { brightness: -0.15, speed: 0.3 }),
        trim: style("scan", 0, { speed: 0.45 }),
        wall: style("wash", 0, { speed: 0.3 }),
      }),
      scene("Colored lights", {
        window: style("tiles", 1, { speed: 1, mask: "window" }),
        door: style("gel", 2),
        garage: style("prism", 1, { speed: 0.4 }),
        trim: style("confetti", 0, { speed: 0.8 }),
        wall: style("tiles", 2, { speed: 0.7, opacity: 0.85 }),
      }),
      scene("Candy glow", {
        window: style("columns", 2, { speed: 0.7, mask: "window" }),
        door: style("gel", 1),
        garage: style("tiles", 2, { speed: 0.6 }),
        trim: style("pinwheel", 2, { speed: 0.4 }),
        wall: style("prism", 2, { speed: 0.35, opacity: 0.8 }),
      }),
      scene("Silent night", {
        window: style("gel", 1, { mask: "window", speed: 0.25, brightness: -0.05 }),
        door: style("gel", 2, { opacity: 0.85 }),
        garage: style("wash", 1, { speed: 0.2, brightness: -0.3 }),
        trim: style("aurora", 3, { speed: 0.25, opacity: 0.55 }),
        wall: style("wash", 1, { speed: 0.2, brightness: -0.1 }),
      }),
    ],
  },
];

export function surfaceRole(name: string): Role {
  const text = name.toLowerCase();
  if (/window|bay|glass|pane/.test(text)) return "window";
  if (/door/.test(text)) return "door";
  if (/garage/.test(text)) return "garage";
  if (/trim|roof|eave|pier|column|sill/.test(text)) return "trim";
  return "wall";
}

function starterHouse(): Surface[] {
  const face = (name: string, corners: Surface["corners"]): Surface => ({
    id: name,
    name,
    look: "wash",
    gel: 0,
    opacity: 1,
    feather: 0,
    mask: "full",
    brightness: 0,
    contrast: 1,
    saturation: 1,
    speed: 1,
    blend: "normal",
    visible: true,
    locked: false,
    videoId: null,
    corners,
  });
  return [
    face("Left window", [{ x: 0.12, y: 0.28 }, { x: 0.32, y: 0.28 }, { x: 0.32, y: 0.52 }, { x: 0.12, y: 0.52 }]),
    face("Right window", [{ x: 0.68, y: 0.28 }, { x: 0.88, y: 0.28 }, { x: 0.88, y: 0.52 }, { x: 0.68, y: 0.52 }]),
    face("Front door", [{ x: 0.42, y: 0.4 }, { x: 0.58, y: 0.4 }, { x: 0.58, y: 0.78 }, { x: 0.42, y: 0.78 }]),
    face("Garage", [{ x: 0.08, y: 0.58 }, { x: 0.36, y: 0.58 }, { x: 0.36, y: 0.88 }, { x: 0.08, y: 0.88 }]),
    face("Eave trim", [{ x: 0.08, y: 0.16 }, { x: 0.92, y: 0.16 }, { x: 0.92, y: 0.24 }, { x: 0.08, y: 0.24 }]),
  ];
}

export function applyPack(project: Project, packId: string): Project {
  const pack = PACKS.find((item) => item.id === packId);
  if (!pack) return project;
  const current = project.scenes.find((scene) => scene.id === project.activeSceneId) ?? project.scenes[0];
  const bases = current && current.surfaces.length > 0 ? current.surfaces : starterHouse();
  let seq = project.seq;
  const added = pack.scenes.map((recipe) => {
    seq += 1;
    const id = `scene-${seq}`;
    return {
      id,
      name: recipe.name,
      durationSeconds: recipe.durationSeconds,
      surfaces: bases.map((face) => {
        seq += 1;
        const role = surfaceRole(face.name);
        return { ...face, id: `surf-${seq}`, videoId: null, locked: false, ...recipe.roles[role] };
      }),
    };
  });
  return {
    ...project,
    seq,
    scenes: [...project.scenes, ...added],
    activeSceneId: added[0]?.id ?? project.activeSceneId,
    selectedId: added[0]?.surfaces[0]?.id ?? project.selectedId,
  };
}
