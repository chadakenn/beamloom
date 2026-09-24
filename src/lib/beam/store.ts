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
  type AlignmentPreset,
  type Project,
  type Surface,
} from "@/lib/beam/project";

type EditorState = Project & {
  canUndo: boolean;
  canRedo: boolean;
  undo: () => void;
  redo: () => void;
  beginHistoryGroup: () => void;
  endHistoryGroup: () => void;
  output: boolean;
  armedLook: LookId;
  armedVideoId: string | null;
  playlistPlaying: boolean;
  setPlaylistPlaying: (playing: boolean) => void;
  advanceScene: () => void;
  setSceneDuration: (id: string, seconds: number) => void;
  saveAlignment: (name: string) => boolean;
  applyAlignment: (id: string) => boolean;
  updateAlignment: (id: string) => void;
  deleteAlignment: (id: string) => void;
  replace: (project: Project) => void;
  setName: (name: string) => void;
  setScene: (id: string) => void;
  renameScene: (id: string, name: string) => void;
  duplicateScene: (id: string) => void;
  reorderScene: (sourceId: string, targetId: string, after: boolean) => void;
  addScene: () => void;
  removeScene: (id: string) => void;
  select: (id: string | null) => void;
  addSurface: () => void;
  removeSurface: (id: string) => void;
  duplicateSurface: (id: string) => void;
  copySurfaceToScene: (id: string, sceneId: string) => void;
  patchSurface: (id: string, patch: Partial<Surface>) => void;
  setCorner: (id: string, index: number, x: number, y: number) => void;
  moveSurface: (id: string, origin: Corners, dx: number, dy: number) => void;
  nudge: (dx: number, dy: number) => void;
  reorder: (id: string, dir: -1 | 1) => void;
  setGuides: (guides: boolean) => void;
  setOutput: (output: boolean) => void;
  setArmedLook: (look: LookId) => void;
  assignVideo: (videoId: string) => void;
  clearVideo: (videoId: string) => void;
  reset: () => void;
};

const HISTORY_LIMIT = 100;
const past: Project[] = [];
const future: Project[] = [];
let groupStart: Project | null = null;
let restoring = false;

function changed(a: Project, b: Project) {
  return a.scenes !== b.scenes || a.name !== b.name || a.alignments !== b.alignments;
}

function finishGroup() {
  if (!groupStart) return;
  const start = groupStart;
  groupStart = null;
  if (changed(start, snapshot(useEditor.getState()))) {
    past.push(start);
    if (past.length > HISTORY_LIMIT) past.shift();
    future.length = 0;
    useEditor.setState({ canUndo: true, canRedo: false });
  }
}

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

function captureAlignment(project: Project): AlignmentPreset["scenes"] {
  return project.scenes.map((scene) => ({
    sceneId: scene.id,
    surfaces: scene.surfaces.map((face) => ({
      surfaceId: face.id,
      corners: face.corners.map((corner) => ({ ...corner })) as Corners,
    })),
  }));
}

export const useEditor = create<EditorState>((set, get) => ({
  ...demoProject(),
  canUndo: false,
  canRedo: false,
  undo: () => {
    finishGroup();
    const previous = past.pop();
    if (!previous) return;
    future.push(snapshot(get()));
    restoring = true;
    try { set({ ...previous, canUndo: past.length > 0, canRedo: true }); }
    finally { restoring = false; }
  },
  redo: () => {
    finishGroup();
    const next = future.pop();
    if (!next) return;
    past.push(snapshot(get()));
    if (past.length > HISTORY_LIMIT) past.shift();
    restoring = true;
    try { set({ ...next, canUndo: true, canRedo: future.length > 0 }); }
    finally { restoring = false; }
  },
  beginHistoryGroup: () => { if (!groupStart) groupStart = snapshot(get()); },
  endHistoryGroup: finishGroup,
  output: false,
  armedLook: "wash",
  armedVideoId: null,
  playlistPlaying: false,
  replace: (project) => {
    past.length = 0;
    future.length = 0;
    groupStart = null;
    restoring = true;
    try {
      set({ ...project, output: false, playlistPlaying: false, canUndo: false, canRedo: false });
    } finally {
      restoring = false;
    }
  },
  setPlaylistPlaying: (playing) => set({ playlistPlaying: playing && get().scenes.length > 1 }),
  advanceScene: () => {
    const scenes = get().scenes;
    const index = scenes.findIndex((scene) => scene.id === get().activeSceneId);
    const next = scenes[(index + 1) % scenes.length];
    if (next) get().setScene(next.id);
  },
  setSceneDuration: (id, seconds) => {
    if (!Number.isFinite(seconds)) return;
    set({
      scenes: get().scenes.map((scene) =>
        scene.id === id
          ? { ...scene, durationSeconds: Math.max(1, Math.min(3600, Math.round(seconds))) }
          : scene,
      ),
    });
  },
  saveAlignment: (name) => {
    const trimmed = name.trim().slice(0, 40);
    if (
      !trimmed ||
      get().alignments.length >= 24 ||
      get().alignments.some((preset) => preset.name.toLowerCase() === trimmed.toLowerCase())
    ) {
      return false;
    }
    set({
      alignments: [...get().alignments, { id: crypto.randomUUID(), name: trimmed, scenes: captureAlignment(get()) }],
    });
    return true;
  },
  applyAlignment: (id) => {
    const preset = get().alignments.find((item) => item.id === id);
    if (!preset) return false;
    let matches = 0;
    const scenes = get().scenes.map((scene) => {
      const saved = preset.scenes.find((entry) => entry.sceneId === scene.id);
      if (!saved) return scene;
      return {
        ...scene,
        surfaces: scene.surfaces.map((face) => {
          const corners = saved.surfaces.find((item) => item.surfaceId === face.id)?.corners;
          if (!corners) return face;
          matches++;
          return { ...face, corners: corners.map((corner) => ({ ...corner })) as Corners };
        }),
      };
    });
    if (matches) set({ scenes });
    return matches > 0;
  },
  updateAlignment: (id) =>
    set({
      alignments: get().alignments.map((preset) =>
        preset.id === id ? { ...preset, scenes: captureAlignment(get()) } : preset,
      ),
    }),
  deleteAlignment: (id) => set({ alignments: get().alignments.filter((preset) => preset.id !== id) }),
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
  renameScene: (id, name) => {
    const trimmed = name.trim().slice(0, 32);
    if (!trimmed || !get().scenes.some((scene) => scene.id === id && scene.name !== trimmed)) return;
    set({ scenes: get().scenes.map((scene) => scene.id === id ? { ...scene, name: trimmed } : scene) });
  },
  duplicateScene: (id) => {
    const scenes = get().scenes;
    const index = scenes.findIndex((scene) => scene.id === id);
    if (index < 0) return;
    const source = scenes[index];
    let seq = get().seq + 1;
    const sceneId = `scene-${seq}`;
    const surfaces = source.surfaces.map((face) => ({
      ...face,
      id: `surf-${++seq}`,
      corners: face.corners.map((corner) => ({ ...corner })) as Corners,
    }));
    const copy = { ...source, id: sceneId, name: `${source.name} copy`.slice(0, 32), surfaces };
    set({
      seq,
      scenes: [...scenes.slice(0, index + 1), copy, ...scenes.slice(index + 1)],
      activeSceneId: sceneId,
      selectedId: surfaces[source.surfaces.findIndex((face) => face.id === get().selectedId)]?.id ?? surfaces[0]?.id ?? null,
    });
  },
  reorderScene: (sourceId, targetId, after) => {
    const scenes = get().scenes;
    const sourceIndex = scenes.findIndex((scene) => scene.id === sourceId);
    const targetIndex = scenes.findIndex((scene) => scene.id === targetId);
    if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return;
    const reordered = [...scenes];
    const [source] = reordered.splice(sourceIndex, 1);
    const insertAt = reordered.findIndex((scene) => scene.id === targetId) + (after ? 1 : 0);
    reordered.splice(insertAt, 0, source);
    if (reordered.every((scene, index) => scene === scenes[index])) return;
    set({ scenes: reordered });
  },
  addScene: () => {
    const seq = get().seq + 1;
    const id = `scene-${seq}`;
    const faceId = `surf-${seq}`;
    const scene = {
      id,
      name: `Scene ${get().scenes.length + 1}`,
      durationSeconds: 10,
      surfaces: [
        {
          id: faceId,
          name: "Surface 1",
          look: get().armedLook,
          videoId: get().armedVideoId,
          gel: 0,
          opacity: 1,
          feather: 0,
          mask: "full" as const,
          brightness: 0,
          contrast: 1,
          saturation: 1,
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
      playlistPlaying: get().playlistPlaying && scenes.length > 1,
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
      videoId: get().armedVideoId,
      gel: 0,
      opacity: 1,
      feather: 0,
      mask: "full",
      brightness: 0,
      contrast: 1,
      saturation: 1,
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
  copySurfaceToScene: (id, sceneId) => {
    const project = get();
    if (sceneId === project.activeSceneId || !project.scenes.some((scene) => scene.id === sceneId)) return;
    const source = activeScene(project).surfaces.find((face) => face.id === id);
    if (!source) return;
    const seq = project.seq + 1;
    const copy: Surface = {
      ...structuredClone(source),
      id: `surf-${seq}`,
      name: `${source.name} copy`.slice(0, 40),
    };
    set({
      ...mapSceneSurfaces(project, sceneId, (surfaces) => [...surfaces, copy]),
      seq,
      activeSceneId: sceneId,
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
    set({ armedLook: look, armedVideoId: null });
    if (id) get().patchSurface(id, { look, videoId: null });
  },
  assignVideo: (videoId) => {
    const id = get().selectedId;
    set({ armedVideoId: videoId });
    if (id) get().patchSurface(id, { videoId });
  },
  clearVideo: (videoId) => {
    set({
      armedVideoId: get().armedVideoId === videoId ? null : get().armedVideoId,
      scenes: get().scenes.map((scene) => ({
        ...scene,
        surfaces: scene.surfaces.map((face) =>
          face.videoId === videoId ? { ...face, videoId: null } : face,
        ),
      })),
    });
  },
  reset: () => {
    set({ ...demoProject(), output: false, playlistPlaying: false, armedLook: "wash", armedVideoId: null });
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* private mode */
    }
  },
}));

useEditor.subscribe((state, previous) => {
  if (restoring || !changed(state, previous) || groupStart) return;
  past.push(snapshot(previous));
  if (past.length > HISTORY_LIMIT) past.shift();
  future.length = 0;
  useEditor.setState({ canUndo: true, canRedo: false });
});

export function snapshot(state: EditorState): Project {
  return {
    name: state.name,
    scenes: state.scenes,
    activeSceneId: state.activeSceneId,
    selectedId: state.selectedId,
    guides: state.guides,
    seq: state.seq,
    alignments: state.alignments,
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
