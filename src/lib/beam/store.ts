import { create } from "zustand";
import type { LookId } from "@/lib/beam/looks";
import { clamp01, translateCorners, type Corners } from "@/lib/beam/math";
import {
  activeScene,
  demoProject,
  offsetCorners,
  sanitizeProject,
  STORAGE_KEY,
  type Blend,
  type Project,
  type Surface,
} from "@/lib/beam/project";

type EditorState = Project & {
  output: boolean;
  armedLook: LookId;
  replace: (project: Project) => void;
  setName: (name: string) => void;
  setScene: (id: string) => void;
  addScene: () => void;
  removeScene: (id: string) => void;
  select: (id: string | null) => void;
  addSurface: () => void;
  removeSurface: (id: string) => void;
  duplicateSurface: (id: string) => void;
  patchSurface: (id: string, patch: Partial<Surface>) => void;
  setCorner: (id: string, index: number, x: number, y: number) => void;
  moveSurface: (id: string, origin: Corners, dx: number, dy: number) => void;
  nudge: (dx: number, dy: number) => void;
  reorder: (id: string, dir: -1 | 1) => void;
  setGuides: (guides: boolean) => void;
  setOutput: (output: boolean) => void;
  setArmedLook: (look: LookId) => void;
  reset: () => void;
};

function mapSceneSurfaces(
  project: Project,
  sceneId: string,
  fn: (surfaces: Surface[]) => Surface[],
): Project {
  return {
    ...project,
    scenes: project.scenes.map((scene) =>
      scene.id === sceneId ? { ...scene, surfaces: fn(scene.surfaces) } : scene,
    ),
  };
}

function freshCorners(index: number): Corners {
  const o = (index % 4) * 0.035;
  return [
    { x: 0.32 + o, y: 0.26 + o },
    { x: 0.68 + o, y: 0.24 + o },
    { x: 0.72, y: 0.72 },
    { x: 0.28, y: 0.7 },
  ];
}

export const useEditor = create<EditorState>((set, get) => ({
  ...demoProject(),
  output: false,
  armedLook: "wash",
  replace: (project) => set({ ...project, output: false }),
  setName: (name) => set({ name: name.slice(0, 48) }),
  setScene: (id) => {
    const scene = get().scenes.find((item) => item.id === id);
    if (!scene) return;
    set({
      activeSceneId: id,
      selectedId: scene.surfaces.some((face) => face.id === get().selectedId)
        ? get().selectedId
        : (scene.surfaces[0]?.id ?? null),
    });
  },
  addScene: () => {
    const seq = get().seq + 1;
    const id = `scene-${seq}`;
    const faceId = `surf-${seq}`;
    const scene = {
      id,
      name: `Scene ${get().scenes.length + 1}`,
      surfaces: [
        {
          id: faceId,
          name: "Surface 1",
          look: get().armedLook,
          gel: 0,
          opacity: 1,
          blend: "normal" as Blend,
          visible: true,
          locked: false,
          corners: freshCorners(0),
        },
      ],
    };
    set({
      seq,
      scenes: [...get().scenes, scene],
      activeSceneId: id,
      selectedId: faceId,
    });
  },
  removeScene: (id) => {
    const scenes = get().scenes.filter((scene) => scene.id !== id);
    if (scenes.length === 0) return;
    const activeSceneId = get().activeSceneId === id ? scenes[0].id : get().activeSceneId;
    const scene = scenes.find((item) => item.id === activeSceneId) ?? scenes[0];
    set({
      scenes,
      activeSceneId: scene.id,
      selectedId: scene.surfaces[0]?.id ?? null,
    });
  },
  select: (id) => set({ selectedId: id }),
  addSurface: () => {
    const scene = activeScene(get());
    const seq = get().seq + 1;
    const id = `surf-${seq}`;
    const face: Surface = {
      id,
      name: `Surface ${scene.surfaces.length + 1}`,
      look: get().armedLook,
      gel: 0,
      opacity: 1,
      blend: "normal",
      visible: true,
      locked: false,
      corners: freshCorners(scene.surfaces.length),
    };
    set({
      ...mapSceneSurfaces(get(), scene.id, (surfaces) => [...surfaces, face]),
      seq,
      selectedId: id,
    });
  },
  removeSurface: (id) => {
    const scene = activeScene(get());
    const surfaces = scene.surfaces.filter((face) => face.id !== id);
    set({
      ...mapSceneSurfaces(get(), scene.id, () => surfaces),
      selectedId: get().selectedId === id ? (surfaces.at(-1)?.id ?? null) : get().selectedId,
    });
  },
  duplicateSurface: (id) => {
    const scene = activeScene(get());
    const source = scene.surfaces.find((face) => face.id === id);
    if (!source) return;
    const seq = get().seq + 1;
    const copy: Surface = {
      ...source,
      id: `surf-${seq}`,
      name: `${source.name} copy`.slice(0, 40),
      locked: false,
      corners: offsetCorners(source.corners),
    };
    const index = scene.surfaces.findIndex((face) => face.id === id);
    const surfaces = [...scene.surfaces];
    surfaces.splice(index + 1, 0, copy);
    set({
      ...mapSceneSurfaces(get(), scene.id, () => surfaces),
      seq,
      selectedId: copy.id,
    });
  },
  patchSurface: (id, patch) => {
    const scene = activeScene(get());
    set(
      mapSceneSurfaces(get(), scene.id, (surfaces) =>
        surfaces.map((face) => (face.id === id ? { ...face, ...patch, id: face.id } : face)),
      ),
    );
  },
  setCorner: (id, index, x, y) => {
    const scene = activeScene(get());
    set(
      mapSceneSurfaces(get(), scene.id, (surfaces) =>
        surfaces.map((face) => {
          if (face.id !== id || face.locked) return face;
          const corners = face.corners.map((corner, i) =>
            i === index ? { x: clamp01(x), y: clamp01(y) } : corner,
          ) as Corners;
          return { ...face, corners };
        }),
      ),
    );
  },
  moveSurface: (id, origin, dx, dy) => {
    const scene = activeScene(get());
    const face = scene.surfaces.find((item) => item.id === id);
    if (!face || face.locked) return;
    const corners = translateCorners(origin, dx, dy);
    set(
      mapSceneSurfaces(get(), scene.id, (surfaces) =>
        surfaces.map((item) => (item.id === id ? { ...item, corners } : item)),
      ),
    );
  },
  nudge: (dx, dy) => {
    const id = get().selectedId;
    if (!id) return;
    const scene = activeScene(get());
    const face = scene.surfaces.find((item) => item.id === id);
    if (!face || face.locked) return;
    get().moveSurface(id, face.corners, dx, dy);
  },
  reorder: (id, dir) => {
    const scene = activeScene(get());
    const index = scene.surfaces.findIndex((face) => face.id === id);
    const next = index + dir;
    if (index < 0 || next < 0 || next >= scene.surfaces.length) return;
    const surfaces = [...scene.surfaces];
    const [item] = surfaces.splice(index, 1);
    surfaces.splice(next, 0, item);
    set(mapSceneSurfaces(get(), scene.id, () => surfaces));
  },
  setGuides: (guides) => set({ guides }),
  setOutput: (output) => set({ output }),
  setArmedLook: (look) => {
    const id = get().selectedId;
    set({ armedLook: look });
    if (id) get().patchSurface(id, { look });
  },
  reset: () => {
    set({ ...demoProject(), output: false, armedLook: "wash" });
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* private mode */
    }
  },
}));

export function snapshot(state: EditorState): Project {
  return {
    name: state.name,
    scenes: state.scenes,
    activeSceneId: state.activeSceneId,
    selectedId: state.selectedId,
    guides: state.guides,
    seq: state.seq,
  };
}

export function loadStoredProject(): Project | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { version?: number; project?: unknown };
    if (parsed.version !== 1) return null;
    return sanitizeProject(parsed.project);
  } catch {
    return null;
  }
}

export function saveStoredProject(project: Project) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, project }));
  } catch {
    /* quota / private mode */
  }
}
