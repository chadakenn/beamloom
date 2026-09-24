import { useEffect, useRef, useState } from "react";
import { Copy, Lock, Pause, Play, Repeat, Trash2, Unlock, Volume2, VolumeX } from "lucide-react";
import { GELS, LOOKS } from "@/lib/beam/looks";
import {
  clipTransport,
  listClips,
  restoreClips,
  seekClip,
  setClipLoop,
  setClipMuted,
  setClipPlaying,
  subscribeClips,
  type ClipKind,
} from "@/lib/beam/clips";
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
  const setCorner = useEditor((s) => s.setCorner);
  const [clipInfo, setClipInfo] = useState<{ name: string; kind: ClipKind } | null>(null);

  useEffect(() => {
    const sync = () => {
      const id = useEditor.getState().selectedId;
      const current = useEditor
        .getState()
        .scenes.flatMap((scene) => scene.surfaces)
        .find((item) => item.id === id);
      const clip = current?.videoId ? listClips().find((item) => item.id === current.videoId) : undefined;
      setClipInfo(clip ? { name: clip.name, kind: clip.kind } : null);
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
        <p className="text-xs text-muted">Arrows nudge · Del removes · G guides · B blackout</p>
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
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium text-muted">Soft edge</span>
          <span className="text-xs tabular-nums text-fg">{Math.round(face.feather * 100)}%</span>
        </div>
        <input
          className="opacity-range"
          type="range"
          min={0}
          max={0.4}
          step={0.01}
          value={face.feather}
          aria-label="Soft edge"
          onChange={(event) => patchSurface(face.id, { feather: Number(event.target.value) })}
        />
      </div>
      <ColorSlider
        label="Brightness"
        value={face.brightness}
        min={-1}
        max={1}
        text={`${face.brightness > 0 ? "+" : ""}${Math.round(face.brightness * 100)}`}
        onChange={(value) => patchSurface(face.id, { brightness: value })}
      />
      <ColorSlider
        label="Contrast"
        value={face.contrast}
        min={0}
        max={2}
        text={`${Math.round(face.contrast * 100)}%`}
        onChange={(value) => patchSurface(face.id, { contrast: value })}
      />
      <ColorSlider
        label="Saturation"
        value={face.saturation}
        min={0}
        max={2}
        text={`${Math.round(face.saturation * 100)}%`}
        onChange={(value) => patchSurface(face.id, { saturation: value })}
      />
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
                face.blend === blend.id ? "border-beam bg-beam text-ink" : "border-line text-fg",
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
          {face.videoId ? (clipInfo?.name ?? "Imported picture") : LOOKS.find((look) => look.id === face.look)?.name}
        </p>
        {face.videoId && clipInfo?.kind === "video" ? <VideoTransport videoId={face.videoId} /> : null}
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
      {face.look === "gel" && !face.videoId ? (
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
        <p className="mb-2 text-xs text-muted">Position in % of the projector frame</p>
        <ol className="grid grid-cols-2 gap-2 text-xs tabular-nums text-muted">
          {face.corners.map((corner, index) => {
            const place = cornerPlaces(face.corners)[index];
            const cornerName = `Corner ${index + 1} ${place}`;
            return (
              <li key={`${face.id}-${index}`} className="rounded-md border border-line p-2">
                <span className="mb-1 block font-medium">
                  Corner {index + 1}
                  <span className="font-normal text-muted"> · {place}</span>
                </span>
                <div className="grid grid-cols-2 gap-1">
                  <CornerNumber
                    label={`${cornerName} X`}
                    value={corner.x * 100}
                    disabled={face.locked}
                    onCommit={(value) => setCorner(face.id, index, value / 100, corner.y)}
                  />
                  <CornerNumber
                    label={`${cornerName} Y`}
                    value={corner.y * 100}
                    disabled={face.locked}
                    onCommit={(value) => setCorner(face.id, index, corner.x, value / 100)}
                  />
                </div>
              </li>
            );
          })}
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

function ColorSlider({
  label,
  value,
  min,
  max,
  text,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  text: string;
  onChange: (value: number) => void;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-medium text-muted">{label}</span>
        <span className="text-xs tabular-nums text-fg">{text}</span>
      </div>
      <input
        className="opacity-range"
        type="range"
        min={min}
        max={max}
        step={0.01}
        value={value}
        aria-label={label}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </div>
  );
}

function cornerPlaces(corners: { x: number; y: number }[]): string[] {
  const ids = [0, 1, 2, 3];
  const byY = [...ids].sort((a, b) => corners[a].y - corners[b].y || a - b);
  const top = byY.slice(0, 2).sort((a, b) => corners[a].x - corners[b].x || a - b);
  const bottom = byY.slice(2).sort((a, b) => corners[a].x - corners[b].x || a - b);
  const places = ["", "", "", ""];
  places[top[0]] = "Top left";
  places[top[1]] = "Top right";
  places[bottom[0]] = "Bottom left";
  places[bottom[1]] = "Bottom right";
  return places;
}

function CornerNumber({
  label,
  value,
  disabled,
  onCommit,
}: {
  label: string;
  value: number;
  disabled: boolean;
  onCommit: (value: number) => void;
}) {
  const display = Math.round(value * 10) / 10;
  const [draft, setDraft] = useState(String(display));
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (!focused || disabled) setDraft(String(display));
  }, [display, focused, disabled]);

  function commit() {
    setFocused(false);
    const parsed = Number(draft);
    if (draft.trim() === "" || !Number.isFinite(parsed)) {
      setDraft(String(display));
      return;
    }
    const bounded = Math.max(0, Math.min(100, parsed));
    onCommit(bounded);
    setDraft(String(Math.round(bounded * 10) / 10));
  }

  return (
    <label className="flex items-center gap-1">
      <span className="sr-only">{label}</span>
      <span aria-hidden="true">{label.endsWith("X") ? "X" : "Y"}</span>
      <input
        type="number"
        min="0"
        max="100"
        step="0.1"
        inputMode="decimal"
        aria-label={label}
        disabled={disabled}
        value={draft}
        onFocus={() => setFocused(true)}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") event.currentTarget.blur();
        }}
        className="h-11 min-w-0 w-full rounded-md border border-line bg-bg px-2 text-sm text-fg disabled:opacity-50"
      />
    </label>
  );
}

function VideoTransport({ videoId }: { videoId: string }) {
  const [transport, setTransport] = useState(() => clipTransport(videoId));
  const dragging = useRef(false);

  useEffect(() => {
    const read = () => {
      if (!dragging.current) setTransport(clipTransport(videoId));
    };
    read();
    const timer = window.setInterval(read, 200);
    return () => window.clearInterval(timer);
  }, [videoId]);

  if (!transport) return null;
  const duration = transport.duration || 0;

  return (
    <div className="mt-2 flex flex-col gap-2">
      <p className="text-xs font-medium text-muted">Playback</p>
      <div className="flex gap-1">
        <button
          type="button"
          onClick={() => {
            setClipPlaying(videoId, transport.paused);
            setTransport(clipTransport(videoId));
          }}
          className="inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-md border border-line text-sm text-fg"
        >
          {transport.paused ? <Play className="size-4" aria-hidden="true" /> : <Pause className="size-4" aria-hidden="true" />}
          {transport.paused ? "Play" : "Pause"}
        </button>
        <button
          type="button"
          aria-pressed={!transport.muted}
          onClick={() => {
            setClipMuted(videoId, !transport.muted);
            setTransport(clipTransport(videoId));
          }}
          className={cn(
            "inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-md border text-sm",
            transport.muted ? "border-line text-fg" : "border-beam text-beam",
          )}
        >
          {transport.muted ? <VolumeX className="size-4" aria-hidden="true" /> : <Volume2 className="size-4" aria-hidden="true" />}
          {transport.muted ? "Sound" : "On"}
        </button>
        <button
          type="button"
          aria-pressed={transport.loop}
          onClick={() => {
            setClipLoop(videoId, !transport.loop);
            setTransport(clipTransport(videoId));
          }}
          className={cn(
            "inline-flex size-11 items-center justify-center rounded-md border",
            transport.loop ? "border-beam text-beam" : "border-line text-muted",
          )}
          aria-label={transport.loop ? "Turn loop off" : "Loop this video"}
        >
          <Repeat className="size-4" aria-hidden="true" />
        </button>
      </div>
      <input
        className="opacity-range"
        type="range"
        min={0}
        max={duration || 0}
        step={0.01}
        value={Math.min(transport.current, duration || 0)}
        aria-label="Video position"
        disabled={duration <= 0}
        onPointerDown={() => {
          dragging.current = true;
        }}
        onPointerUp={() => {
          dragging.current = false;
          setTransport(clipTransport(videoId));
        }}
        onChange={(event) => {
          const time = Number(event.target.value);
          seekClip(videoId, time);
          setTransport((current) => (current ? { ...current, current: time } : current));
        }}
      />
      <p className="text-xs tabular-nums text-muted">
        {clock(transport.current)} / {clock(duration)}
      </p>
    </div>
  );
}

function clock(seconds: number) {
  const whole = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(whole / 60);
  const remain = whole % 60;
  return `${minutes}:${remain.toString().padStart(2, "0")}`;
}
