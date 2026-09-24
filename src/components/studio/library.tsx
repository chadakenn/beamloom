import { useEffect, useRef, useState } from "react";
import { Eye, EyeOff, Film, Image as ImageIcon, Plus, Trash2 } from "lucide-react";
import { importVideoFiles, listClips, mediaFile, removeClip, restoreClips, resumeClips, subscribeClips, type Clip } from "@/lib/beam/clips";
import { GELS, LOOKS, type LookId } from "@/lib/beam/looks";
import { activeScene } from "@/lib/beam/project";
import { useEditor } from "@/lib/beam/store";
import { cn } from "@/lib/cn";

export function Library() {
  const scene = useEditor((s) => activeScene(s));
  const selectedId = useEditor((s) => s.selectedId);
  const armedLook = useEditor((s) => s.armedLook);
  const setArmedLook = useEditor((s) => s.setArmedLook);
  const assignVideo = useEditor((s) => s.assignVideo);
  const clearVideo = useEditor((s) => s.clearVideo);
  const select = useEditor((s) => s.select);
  const addSurface = useEditor((s) => s.addSurface);
  const patchSurface = useEditor((s) => s.patchSurface);
  const reorder = useEditor((s) => s.reorder);
  const clips = useClipList();

  return (
    <div className="flex h-full flex-col gap-4 p-3">
      <VideoShelf
        clips={clips}
        selectedVideoId={scene.surfaces.find((face) => face.id === selectedId)?.videoId ?? null}
        onAssign={assignVideo}
        onRemove={async (id) => {
          await removeClip(id);
          clearVideo(id);
        }}
      />
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-display text-sm font-semibold tracking-wide text-fg">Looks</h2>
        <button
          type="button"
          onClick={addSurface}
          className="inline-flex h-11 items-center gap-1.5 rounded-md bg-beam px-3 text-sm font-medium text-ink"
        >
          <Plus className="size-4" aria-hidden="true" />
          Surface
        </button>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {LOOKS.map((look) => {
          const active = armedLook === look.id;
          return (
            <button
              key={look.id}
              type="button"
              aria-pressed={active}
              onClick={() => setArmedLook(look.id)}
              className={cn(
                "overflow-hidden rounded-md border text-left",
                active ? "border-beam" : "border-line",
              )}
            >
              <LookThumb kind={look.kind} />
              <span className="block px-2 py-1.5 text-xs font-medium text-fg">{look.name}</span>
            </button>
          );
        })}
      </div>
      <div className="mt-1 flex items-center justify-between">
        <h2 className="font-display text-sm font-semibold tracking-wide text-fg">Stack</h2>
        <p className="text-xs text-muted">Top draws last</p>
      </div>
      <ul className="flex flex-col gap-1">
        {[...scene.surfaces].reverse().map((face) => {
          const active = face.id === selectedId;
          return (
            <li key={face.id}>
              <div
                className={cn(
                  "flex items-center gap-1 rounded-md border pr-1",
                  active ? "border-beam bg-panel" : "border-transparent",
                )}
              >
                <button
                  type="button"
                  onClick={() => select(face.id)}
                  className="flex h-11 min-w-0 flex-1 items-center gap-2 px-2 text-left"
                >
                  <LookDot
                    look={face.look}
                    gel={face.gel}
                    media={clips.find((clip) => clip.id === face.videoId)?.kind}
                  />
                  <span className="truncate text-sm text-fg">{face.name}</span>
                </button>
                <button
                  type="button"
                  aria-label={face.visible ? `Hide ${face.name}` : `Show ${face.name}`}
                  onClick={() => patchSurface(face.id, { visible: !face.visible })}
                  className="inline-flex size-11 items-center justify-center text-muted"
                >
                  {face.visible ? (
                    <Eye className="size-4" aria-hidden="true" />
                  ) : (
                    <EyeOff className="size-4" aria-hidden="true" />
                  )}
                </button>
              </div>
            </li>
          );
        })}
      </ul>
      {selectedId ? (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => reorder(selectedId, 1)}
            className="h-11 flex-1 rounded-md border border-line text-sm text-fg"
          >
            Forward
          </button>
          <button
            type="button"
            onClick={() => reorder(selectedId, -1)}
            className="h-11 flex-1 rounded-md border border-line text-sm text-fg"
          >
            Back
          </button>
        </div>
      ) : null}
    </div>
  );
}

function useClipList() {
  const [clips, setClips] = useState<Clip[]>([]);
  useEffect(() => {
    let alive = true;
    void restoreClips().then(() => {
      if (alive) setClips(listClips());
    });
    const stop = subscribeClips(() => setClips(listClips()));
    return () => {
      alive = false;
      stop();
    };
  }, []);
  return clips;
}

function VideoShelf({
  clips,
  selectedVideoId,
  onAssign,
  onRemove,
}: {
  clips: Clip[];
  selectedVideoId: string | null;
  onAssign: (id: string) => void;
  onRemove: (id: string) => void;
}) {
  const [note, setNote] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const resume = () => resumeClips();
    window.addEventListener("pointerdown", resume);
    return () => window.removeEventListener("pointerdown", resume);
  }, []);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-display text-sm font-semibold tracking-wide text-fg">Your media</h2>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="inline-flex h-11 items-center gap-1.5 rounded-md border border-line px-3 text-sm text-fg"
        >
          <ImageIcon className="size-4" aria-hidden="true" />
          Import
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="video/*,image/png,image/jpeg,.png,.jpg,.jpeg"
          multiple
          className="sr-only"
          onChange={(event) => {
            const files = [...(event.target.files ?? [])];
            event.target.value = "";
            if (files.length === 0) return;
            const pictures = files.filter((file) => mediaFile(file));
            if (pictures.length === 0) {
              setNote("Use a video, PNG, or JPEG.");
              return;
            }
            setNote(null);
            void importVideoFiles(pictures).then((ids) => {
              if (ids[0]) onAssign(ids[0]);
            });
          }}
        />
      </div>
      <p className="text-xs text-muted">Video, PNG, or JPEG. Files stay on this machine.</p>
      {note ? <p className="text-xs text-beam">{note}</p> : null}
      {clips.length === 0 ? null : (
        <ul className="flex flex-col gap-2">
          {clips.map((clip) => {
            const active = clip.id === selectedVideoId;
            return (
              <li key={clip.id} className={cn("overflow-hidden rounded-md border", active ? "border-beam" : "border-line")}>
                <button type="button" onClick={() => onAssign(clip.id)} className="block w-full text-left" aria-pressed={active}>
                  {clip.kind === "image" ? (
                    <img src={clip.url} alt="" className="aspect-video w-full object-cover bg-bg" />
                  ) : (
                    <video
                      src={clip.url}
                      muted
                      playsInline
                      preload="metadata"
                      className="aspect-video w-full bg-bg"
                      aria-hidden="true"
                    />
                  )}
                  <span className="block truncate px-2 py-1.5 text-xs font-medium text-fg">{clip.name}</span>
                </button>
                <button
                  type="button"
                  aria-label={`Remove ${clip.name}`}
                  onClick={() => onRemove(clip.id)}
                  className="inline-flex h-11 w-full items-center justify-center gap-1 border-t border-line text-sm text-muted"
                >
                  <Trash2 className="size-4" aria-hidden="true" />
                  Remove
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function LookDot({
  look,
  gel,
  media,
}: {
  look: LookId;
  gel: number;
  media?: "video" | "image";
}) {
  if (media === "image") {
    return <ImageIcon className="size-3.5 shrink-0 text-beam" aria-hidden="true" />;
  }
  if (media === "video") {
    return <Film className="size-3.5 shrink-0 text-beam" aria-hidden="true" />;
  }
  const kind = LOOKS.find((item) => item.id === look)?.kind ?? 0;
  const rgb = look === "gel" ? GELS[gel]?.rgb ?? GELS[0].rgb : accentFor(kind);
  return (
    <span
      className="size-3 shrink-0 rounded-full"
      style={{ backgroundColor: `rgb(${rgb.map((c) => Math.round(c * 255)).join(" ")})` }}
      aria-hidden="true"
    />
  );
}

function accentFor(kind: number): [number, number, number] {
  if (kind === 7) return [0.98, 0.07, 0.52];
  if (kind === 8) return [0.02, 0.95, 0.55];
  if (kind === 9) return [0.9, 0.85, 0.2];
  if (kind === 1) return [0.96, 0.78, 0.42];
  if (kind === 2) return [0.93, 0.88, 0.74];
  if (kind === 3) return [1, 0.46, 0.12];
  if (kind === 4) return [0.78, 0.9, 0.86];
  if (kind === 5) return [0.98, 0.58, 0.16];
  return [0.98, 0.72, 0.28];
}

function LookThumb({ kind }: { kind: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    const paint = (now: number) => {
      const t = reduced ? 1.2 : now / 1000;
      const w = canvas.width;
      const h = canvas.height;
      ctx.fillStyle = "#070708";
      ctx.fillRect(0, 0, w, h);
      if (kind === 0) {
        const g = ctx.createRadialGradient(w * 0.5, h * 0.4, 8, w * 0.5, h * 0.5, w * 0.6);
        g.addColorStop(0, "#f2c36a");
        g.addColorStop(1, "#3a1608");
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, w, h);
      } else if (kind === 1) {
        ctx.strokeStyle = "rgba(245, 206, 130, 0.7)";
        ctx.lineWidth = 1;
        for (let y = 4; y < h; y += 6) {
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(w, y);
          ctx.stroke();
        }
        const by = ((t * 0.11) % 1) * h;
        ctx.fillStyle = "rgba(255, 230, 170, 0.85)";
        ctx.fillRect(0, by - 2, w, 4);
      } else if (kind === 2) {
        ctx.strokeStyle = "rgba(236, 224, 190, 0.85)";
        ctx.lineWidth = 1;
        for (let x = 0; x <= w; x += w / 8) {
          ctx.beginPath();
          ctx.moveTo(x, 0);
          ctx.lineTo(x, h);
          ctx.stroke();
        }
        for (let y = 0; y <= h; y += h / 5) {
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(w, y);
          ctx.stroke();
        }
      } else if (kind === 3) {
        for (let i = 0; i < 10; i++) {
          const x = ((Math.sin(i * 12.3) * 0.5 + 0.5) * w);
          const y = ((1 - ((t * (0.08 + (i % 4) * 0.03) + i * 0.17) % 1)) * h);
          ctx.fillStyle = "rgba(255, 120, 40, 0.9)";
          ctx.beginPath();
          ctx.arc(x, y, 2.2, 0, Math.PI * 2);
          ctx.fill();
        }
      } else if (kind === 4) {
        ctx.strokeStyle = "rgba(190, 230, 220, 0.9)";
        ctx.lineWidth = 1.5;
        const shift = (t * 8) % 14;
        for (let r = 6 + shift; r < w; r += 14) {
          ctx.beginPath();
          ctx.arc(w / 2, h / 2, r, 0, Math.PI * 2);
          ctx.stroke();
        }
      } else if (kind === 5) {
        const lanes = 8;
        for (let i = 0; i < lanes; i++) {
          const bh = 0.25 + 0.7 * (0.5 + 0.5 * Math.sin(t * 1.8 + i));
          ctx.fillStyle = "#f0942a";
          const bw = w / lanes * 0.7;
          const x = (w / lanes) * i + 2;
          ctx.fillRect(x, h - h * bh, bw, h * bh);
        }
      } else if (kind === 7 || kind === 8) {
        const g = ctx.createLinearGradient(0, h * (0.3 + Math.sin(t) * 0.2), w, h);
        g.addColorStop(0, kind === 7 ? "#ff36ad" : "#062448");
        g.addColorStop(0.5, kind === 7 ? "#6846ff" : "#02e1a8");
        g.addColorStop(1, kind === 7 ? "#02d9ef" : "#b24cff");
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, w, h);
        ctx.globalAlpha = 0.5;
        ctx.fillStyle = "#fff";
        ctx.fillRect(0, h * (0.5 + Math.sin(t) * 0.2), w, 2);
        ctx.globalAlpha = 1;
      } else if (kind === 9) {
        const colors = ["#ff4a80", "#ffe43b", "#15dcff", "#8aff62", "#bc70ff"];
        for (let i = 0; i < 40; i++) {
          ctx.fillStyle = colors[i % colors.length];
          ctx.fillRect((i * 71) % w, (i * 37 + t * 13) % h, 4, 3);
        }
      } else {
        ctx.fillStyle = "#e29a28";
        ctx.fillRect(0, 0, w, h);
      }
      if (!reduced) raf = requestAnimationFrame(paint);
    };
    canvas.width = 160;
    canvas.height = 90;
    raf = requestAnimationFrame(paint);
    return () => cancelAnimationFrame(raf);
  }, [kind]);
  return <canvas ref={ref} className="block aspect-video w-full bg-bg" aria-hidden="true" />;
}
