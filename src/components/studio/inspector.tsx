import { useEffect, useState } from "react";
import { Copy, Lock, Trash2, Unlock } from "lucide-react";
import { GELS, LOOKS } from "@/lib/beam/looks";
import { listClips, restoreClips, subscribeClips } from "@/lib/beam/clips";
import { selectedSurface, type Blend } from "@/lib/beam/project";
import { useEditor } from "@/lib/beam/store";
import { cn } from "@/lib/cn";

const BLENDS: { id: Blend; label: string }[] = [
  { id: "normal", label: "Normal" },
  { id: "add", label: "Add" },
  { id: "screen", label: "Screen" },
];

export function Inspector() {
  const face = useEditor((s) => selectedSurface(s));
  const patchSurface = useEditor((s) => s.patchSurface);
  const [clipName, setClipName] = useState<string | null>(null);

  useEffect(() => {
    const sync = () => {
      const id = useEditor.getState().selectedId;
      const face = useEditor.getState().scenes.flatMap((scene) => scene.surfaces).find((item) => item.id === id);
      const name = face?.videoId ? listClips().find((clip) => clip.id === face.videoId)?.name ?? null : null;
      setClipName(name);
    };
    void restoreClips().then(sync);
    const stop = subscribeClips(sync);
    return () => {
      stop();
    };
  }, [face?.videoId, face?.id]);
  const removeSurface = useEditor((s) => s.removeSurface);
  const duplicateSurface = useEditor((s) => s.duplicateSurface);

  if (!face) {
    return (
      <div className="flex h-full flex-col justify-between p-4">
        <div>
          <h2 className="font-display text-sm font-semibold text-fg">Surface</h2>
          <p className="mt-2 text-sm text-muted">
            Select a shape on the projector frame, or add one from Looks.
          </p>
        </div>
        <p className="text-xs text-muted">Arrows nudge · Del removes · G guides</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-4 overflow-auto p-4">
      <div>
        <label className="text-xs font-medium text-muted" htmlFor="surface-name">
          Surface
        </label>
        <input
          id="surface-name"
          value={face.name}
          maxLength={40}
          onChange={(event) => patchSurface(face.id, { name: event.target.value })}
          className="mt-1 h-11 w-full rounded-md border border-line bg-bg px-3 text-sm text-fg"
        />
      </div>
      <div>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium text-muted">Opacity</span>
          <span className="text-xs tabular-nums text-fg">{Math.round(face.opacity * 100)}%</span>
        </div>
        <input
          className="opacity-range"
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={face.opacity}
          aria-label="Opacity"
          onChange={(event) => patchSurface(face.id, { opacity: Number(event.target.value) })}
        />
      </div>
      <div>
        <p className="mb-2 text-xs font-medium text-muted">Blend</p>
        <div className="grid grid-cols-3 gap-1">
          {BLENDS.map((blend) => (
            <button
              key={blend.id}
              type="button"
              aria-pressed={face.blend === blend.id}
              onClick={() => patchSurface(face.id, { blend: blend.id })}
              className={cn(
                "h-11 rounded-md border text-sm",
                face.blend === blend.id
                  ? "border-beam bg-beam text-ink"
                  : "border-line text-fg",
              )}
            >
              {blend.label}
            </button>
          ))}
        </div>
      </div>
      <div>
        <p className="mb-2 text-xs font-medium text-muted">Picture</p>
        <p className="text-sm text-fg">
          {face.videoId ? (clipName ?? "Imported video") : LOOKS.find((look) => look.id === face.look)?.name}
        </p>
        {face.videoId ? (
          <button
            type="button"
            onClick={() => patchSurface(face.id, { videoId: null })}
            className="mt-2 h-11 rounded-md border border-line px-3 text-sm text-fg"
          >
            Use the look instead
          </button>
        ) : null}
      </div>
      {face.look === "gel" ? (
        <div>
          <p className="mb-2 text-xs font-medium text-muted">Gel</p>
          <div className="flex flex-wrap gap-2">
            {GELS.map((gel, index) => (
              <button
                key={gel.name}
                type="button"
                aria-label={gel.name}
                aria-pressed={face.gel === index}
                onClick={() => patchSurface(face.id, { gel: index })}
                className={cn(
                  "size-11 rounded-full border-2",
                  face.gel === index ? "border-fg" : "border-transparent",
                )}
                style={{
                  backgroundColor: `rgb(${gel.rgb.map((c) => Math.round(c * 255)).join(" ")})`,
                }}
              />
            ))}
          </div>
        </div>
      ) : null}
      <div>
        <p className="mb-2 text-xs font-medium text-muted">Corners</p>
        <ol className="grid grid-cols-2 gap-2 text-xs tabular-nums text-muted">
          {face.corners.map((corner, index) => (
            <li key={index} className="rounded-md border border-line px-2 py-2">
              {index + 1} · {Math.round(corner.x * 100)} , {Math.round(corner.y * 100)}
            </li>
          ))}
        </ol>
      </div>
      <div className="mt-auto grid grid-cols-3 gap-2">
        <button
          type="button"
          onClick={() => patchSurface(face.id, { locked: !face.locked })}
          className="inline-flex h-11 items-center justify-center gap-1 rounded-md border border-line text-sm text-fg"
        >
          {face.locked ? <Lock className="size-4" /> : <Unlock className="size-4" />}
          {face.locked ? "Locked" : "Lock"}
        </button>
        <button
          type="button"
          onClick={() => duplicateSurface(face.id)}
          className="inline-flex h-11 items-center justify-center gap-1 rounded-md border border-line text-sm text-fg"
        >
          <Copy className="size-4" aria-hidden="true" />
          Copy
        </button>
        <button
          type="button"
          onClick={() => removeSurface(face.id)}
          className="inline-flex h-11 items-center justify-center gap-1 rounded-md border border-line text-sm text-beam"
        >
          <Trash2 className="size-4" aria-hidden="true" />
          Remove
        </button>
      </div>
      <p className="text-xs text-muted">Arrows nudge · Del removes · G guides</p>
    </div>
  );
}
