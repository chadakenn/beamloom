import { storedClips } from "@/lib/beam/clips";
import { snapshot, useEditor } from "@/lib/beam/store";

export async function sendShowToPi(host: string, onProgress?: (message: string) => void): Promise<string> {
  const desktop = window.beamloomDesktop;
  if (!desktop?.piShowStart || !desktop.piShowProject || !desktop.piShowOpen || !desktop.piShowWrite || !desktop.piShowFile || !desktop.piShowFinish) {
    throw new Error("Send to Pi works in the installed Beamloom app.");
  }
  onProgress?.("Sending the show to the Pi…");
  const project = snapshot(useEditor.getState());
  const used = new Set(project.scenes.flatMap((scene) => scene.surfaces.map((face) => face.videoId).filter((id): id is string => Boolean(id))));
  const media = (await storedClips()).filter((clip) => used.has(clip.id));
  const allowed = new Set(["image/png", "image/jpeg", "video/mp4", "video/webm", "video/quicktime"]);
  for (const clip of media) {
    if (clip.blob.size > 512 * 1024 * 1024 || !allowed.has(clip.blob.type)) {
      throw new Error(`${clip.name} is over 512 MB or is not a PNG, JPEG, MP4, WebM, or MOV.`);
    }
  }
  const started = await desktop.piShowStart(host);
  if (!started?.ok) throw new Error(started?.error || "The Pi could not store the show.");
  const savedProject = await desktop.piShowProject(host, project);
  if (!savedProject?.ok) throw new Error(savedProject?.error || "The Pi could not store the project.");
  for (const clip of media) {
    onProgress?.(`Sending ${clip.name}…`);
    const opened = await desktop.piShowOpen(clip.id, clip.name, clip.blob.type, clip.blob.size);
    if (!opened?.ok) throw new Error(opened?.error || `Could not send ${clip.name}.`);
    let offset = 0;
    while (offset < clip.blob.size) {
      const bytes = new Uint8Array(await clip.blob.slice(offset, offset + 1024 * 1024).arrayBuffer());
      const wrote = await desktop.piShowWrite(clip.id, bytes);
      if (!wrote?.ok) throw new Error(wrote?.error || `Could not send ${clip.name}.`);
      offset += bytes.length;
    }
    const filed = await desktop.piShowFile(host, clip.id);
    if (!filed?.ok) throw new Error(filed?.error || `Could not send ${clip.name}.`);
  }
  const finished = await desktop.piShowFinish(host);
  if (!finished?.ok) throw new Error(finished?.error || "The Pi could not store the show.");
  const count = finished.show?.files ?? media.length;
  return `Saved ${finished.show?.name || project.name} on the Pi${count ? `, with ${count} file${count === 1 ? "" : "s"}` : ""}. It is in the playlist. Open the Playlist tab on the Pi page to choose which shows loop.`;
}
