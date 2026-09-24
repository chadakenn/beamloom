import { importVideoFiles, storedClips } from "@/lib/beam/clips";
import { sanitizeProject, type Project } from "@/lib/beam/project";

type PortableClip = { id: string; name: string; data: string };
type PortableProject = { format: "beamloom-project"; version: 1; project: Project; clips: PortableClip[] };

function asDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

export async function saveProjectFile(project: Project): Promise<void> {
  const ids = new Set(
    project.scenes.flatMap((scene) =>
      scene.surfaces.map((face) => face.videoId).filter((id): id is string => Boolean(id)),
    ),
  );
  const stored = ids.size ? await storedClips() : [];
  const clips: PortableClip[] = [];
  for (const id of ids) {
    const clip = stored.find((item) => item.id === id);
    if (!clip) throw new Error("A video used by this project is missing. Restore it before saving.");
    clips.push({ id, name: clip.name, data: await asDataUrl(clip.blob) });
  }
  const payload: PortableProject = { format: "beamloom-project", version: 1, project, clips };
  const blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  const safe = project.name.trim().replace(/[^a-z0-9-_]+/gi, "-").replace(/^-|-$/g, "");
  anchor.download = `${safe || "beamloom"}.beamloom`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export async function openProjectFile(file: File): Promise<Project> {
  let raw: Partial<PortableProject>;
  try {
    raw = JSON.parse(await file.text()) as Partial<PortableProject>;
  } catch {
    throw new Error("This is not a supported Beamloom project file.");
  }
  if (raw.format !== "beamloom-project" || raw.version !== 1 || !Array.isArray(raw.clips)) {
    throw new Error("This is not a supported Beamloom project file.");
  }
  const project = sanitizeProject(raw.project);
  if (!project) throw new Error("The project file contains invalid scenes or surfaces.");
  const ids = new Set(
    project.scenes.flatMap((scene) =>
      scene.surfaces.map((face) => face.videoId).filter((id): id is string => Boolean(id)),
    ),
  );
  const clips = new Map<string, File>();
  for (const clip of raw.clips) {
    if (!clip || typeof clip.id !== "string" || typeof clip.name !== "string" || typeof clip.data !== "string") {
      throw new Error("The project file contains an invalid video.");
    }
    if (!ids.has(clip.id)) continue;
    const mime = /^data:(video\/[\w.+-]+);base64,/.exec(clip.data)?.[1];
    if (!mime) throw new Error("The project file contains an invalid video.");
    const blob = await (await fetch(clip.data)).blob();
    clips.set(clip.id, new File([blob], clip.name, { type: mime }));
  }
  if ([...ids].some((id) => !clips.has(id))) throw new Error("The project file is missing a video used by a surface.");
  const oldIds = [...ids];
  const newIds = await importVideoFiles(oldIds.map((id) => clips.get(id)!));
  if (newIds.length !== oldIds.length) throw new Error("The videos could not be saved in this browser.");
  const remap = new Map(oldIds.map((id, index) => [id, newIds[index]]));
  return {
    ...project,
    scenes: project.scenes.map((scene) => ({
      ...scene,
      surfaces: scene.surfaces.map((surface) => ({
        ...surface,
        videoId: surface.videoId ? (remap.get(surface.videoId) ?? null) : null,
      })),
    })),
  };
}
