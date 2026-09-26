import { useEffect, useRef, useSyncExternalStore } from "react";
import { gelRgb } from "@/lib/beam/looks";
import { getClipSource } from "@/lib/beam/clips";
import { drawAlignment, getAlign, subscribeAlign } from "@/lib/beam/align";
import { getFadeSeconds, subscribeFade } from "@/lib/beam/fade";
import { getMaster, subscribeMaster } from "@/lib/beam/master";
import { getSolo, subscribeSolo, toggleSolo } from "@/lib/beam/solo";
import { createMapper, type DrawFace, type Mapper } from "@/lib/beam/gl-mapper";
import type { Corners } from "@/lib/beam/math";
import { MAX_OUTLINE_POINTS, outlineToScreen, screenToOutline } from "@/lib/beam/outline";
import { activeScene, type Surface } from "@/lib/beam/project";
import { useEditor } from "@/lib/beam/store";

const VIEW_W = 1600;
const VIEW_H = 900;

export function Stage({ edit, lineup, blackout }: { edit: boolean; lineup: boolean; blackout: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const alignCanvasRef = useRef<HTMLCanvasElement>(null);
  const mapperRef = useRef<Mapper | null>(null);
  const blackoutRef = useRef(blackout);
  blackoutRef.current = blackout;
  const dragRef = useRef<
    | { type: "corner"; id: string; index: number }
    | { type: "outline"; id: string; index: number }
    | { type: "move"; id: string; startX: number; startY: number; corners: Corners }
    | null
  >(null);
  const guides = useEditor((s) => s.guides);
  const selectedId = useEditor((s) => s.selectedId);
  const scene = useEditor((s) => activeScene(s));
  const select = useEditor((s) => s.select);
  const setCorner = useEditor((s) => s.setCorner);
  const setOutlinePoint = useEditor((s) => s.setOutlinePoint);
  const addOutlinePoint = useEditor((s) => s.addOutlinePoint);
  const moveSurface = useEditor((s) => s.moveSurface);
  const beginHistoryGroup = useEditor((s) => s.beginHistoryGroup);
  const endHistoryGroup = useEditor((s) => s.endHistoryGroup);
  const fadeSeconds = useSyncExternalStore(subscribeFade, getFadeSeconds, () => 0);
  const fadeRef = useRef(fadeSeconds);
  fadeRef.current = fadeSeconds;
  const solo = useSyncExternalStore(subscribeSolo, getSolo, () => false);
  const soloRef = useRef(solo);
  soloRef.current = solo;
  const master = useSyncExternalStore(subscribeMaster, getMaster, () => 1);
  const masterRef = useRef(master);
  masterRef.current = master;
  const align = useSyncExternalStore(subscribeAlign, getAlign, () => false);
  const alignRef = useRef(align);
  alignRef.current = align;

  useEffect(() => {
    const canvas = canvasRef.current;
    const bay = canvas?.parentElement;
    if (!canvas || !bay) return;
    const mapper = createMapper(canvas);
    mapperRef.current = mapper;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const fit = () => {
      const rect = bay.getBoundingClientRect();
      mapper?.resize(rect.width, rect.height, Math.min(window.devicePixelRatio || 1, 2));
      const overlay = alignCanvasRef.current;
      if (overlay) {
        overlay.width = Math.round(rect.width * Math.min(window.devicePixelRatio || 1, 2));
        overlay.height = Math.round(rect.height * Math.min(window.devicePixelRatio || 1, 2));
      }
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(bay);
    let raf = 0;
    let shownId: string | null = null;
    let fading: { id: string; started: number } | null = null;
    const loop = (now: number) => {
      const state = useEditor.getState();
      const current = activeScene(state);
      const fadeMs = reduced ? 0 : fadeRef.current * 1000;
      if (shownId === null) shownId = current.id;
      else if (shownId !== current.id) {
        fading = fadeMs > 0 ? { id: shownId, started: now } : null;
        shownId = current.id;
      }
      const soloId = soloRef.current ? state.selectedId : null;
      let faces = sceneFaces(current, soloId);
      if (fading) {
        const amount = fadeMs <= 0 ? 1 : Math.min(1, (now - fading.started) / fadeMs);
        const previous = state.scenes.find((scene) => scene.id === fading?.id);
        if (previous && amount < 1) {
          faces = [...scaledFaces(sceneFaces(previous, soloId), 1 - amount), ...scaledFaces(faces, amount)];
        } else fading = null;
      }
      const aligning = alignRef.current && !blackoutRef.current;
      mapper?.draw(blackoutRef.current || aligning ? [] : faces, reduced ? 0 : now / 1000, masterRef.current);
      const chosen = current.surfaces.find((face) => face.id === state.selectedId);
      if (alignCanvasRef.current) drawAlignment(alignCanvasRef.current, aligning ? chosen?.corners ?? null : null, masterRef.current, chosen?.outline);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.isContentEditable;
      if (typing || event.metaKey || event.ctrlKey || event.altKey) return;
      if (event.key === "s" || event.key === "S") {
        event.preventDefault();
        toggleSolo();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
      window.removeEventListener("keydown", onKey);
      mapper?.destroy();
      mapperRef.current = null;
    };
  }, []);

  function normFromEvent(event: React.PointerEvent | PointerEvent) {
    const canvas = canvasRef.current;
    const rect = canvas?.getBoundingClientRect();
    if (!rect || rect.width === 0 || rect.height === 0) return { x: 0, y: 0 };
    return {
      x: (event.clientX - rect.left) / rect.width,
      y: (event.clientY - rect.top) / rect.height,
    };
  }

  useEffect(() => {
    const move = (event: PointerEvent) => {
      const drag = dragRef.current;
      if (!drag) return;
      const point = normFromEvent(event);
      const snapped =
        drag.type === "corner"
          ? {
              x: snapLine(point.x, lineup, event.altKey),
              y: snapLine(point.y, lineup, event.altKey),
            }
          : point;
      if (drag.type === "corner") setCorner(drag.id, drag.index, snapped.x, snapped.y);
      else if (drag.type === "outline") {
        const face = activeScene(useEditor.getState()).surfaces.find((item) => item.id === drag.id);
        const uv = face && screenToOutline(face.corners, snapped);
        if (uv) setOutlinePoint(drag.id, drag.index, uv.x, uv.y);
      } else moveSurface(drag.id, drag.corners, point.x - drag.startX, point.y - drag.startY);
    };
    const up = () => {
      if (dragRef.current) endHistoryGroup();
      dragRef.current = null;
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
    };
  }, [endHistoryGroup, lineup, moveSurface, setCorner, setOutlinePoint]);

  function beginMove(event: React.PointerEvent, face: Surface) {
    if (!edit || face.locked) {
      select(face.id);
      return;
    }
    event.preventDefault();
    beginHistoryGroup();
    select(face.id);
    const point = normFromEvent(event);
    dragRef.current = {
      type: "move",
      id: face.id,
      startX: point.x,
      startY: point.y,
      corners: face.corners.map((c) => ({ ...c })) as Corners,
    };
  }

  const selected = scene.surfaces.find((face) => face.id === selectedId) ?? null;

  return (
    <div className="projector-bay absolute inset-0 grid place-items-center">
      <div className="projector-fit overflow-hidden rounded-md border border-line bg-bg">
        <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" aria-label="Projector frame" />
        <canvas ref={alignCanvasRef} className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true" />
        {edit ? (
          <div className="absolute inset-0 touch-none">
            <svg
              className="absolute inset-0 h-full w-full"
              viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
              preserveAspectRatio="none"
            >
              {guides ? (
                <g className="pointer-events-none text-line" stroke="currentColor" fill="none">
                  {[1, 2].map((step) => (
                    <g key={step}>
                      <line
                        x1={(VIEW_W / 3) * step}
                        y1="0"
                        x2={(VIEW_W / 3) * step}
                        y2={VIEW_H}
                        vectorEffect="non-scaling-stroke"
                      />
                      <line
                        x1="0"
                        y1={(VIEW_H / 3) * step}
                        x2={VIEW_W}
                        y2={(VIEW_H / 3) * step}
                        vectorEffect="non-scaling-stroke"
                      />
                    </g>
                  ))}
                </g>
              ) : null}
              {scene.surfaces.map((face) => {
                const active = face.id === selectedId;
                const points = outlineToScreen(face.corners, face.outline)
                  .map((c) => `${c.x * VIEW_W},${c.y * VIEW_H}`)
                  .join(" ");
                return (
                  <polygon
                    key={face.id}
                    points={points}
                    fill="white"
                    fillOpacity={face.visible ? 0.02 : 0}
                    stroke={active ? "var(--color-beam)" : "var(--color-fg)"}
                    strokeOpacity={face.visible ? (active ? 1 : 0.45) : 0.2}
                    strokeWidth={active ? 2.5 : 1.25}
                    vectorEffect="non-scaling-stroke"
                    className={face.locked ? "cursor-default" : "cursor-move"}
                    onPointerDown={(event) => beginMove(event, face)}
                  />
                );
              })}
            </svg>
            {selected && !selected.locked
              ? selected.corners.map((corner, index) => (
                  <button
                    key={`${selected.id}-${index}`}
                    type="button"
                    aria-label={`Corner ${index + 1} of ${selected.name}`}
                    className="absolute z-10 flex size-11 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full"
                    style={{ left: `${corner.x * 100}%`, top: `${corner.y * 100}%` }}
                    onPointerDown={(event) => {
                      event.stopPropagation();
                      event.preventDefault();
                      beginHistoryGroup();
                      select(selected.id);
                      dragRef.current = { type: "corner", id: selected.id, index };
                    }}
                  >
                    <span className="size-3.5 rounded-full border-2 border-beam bg-fg" />
                  </button>
                ))
              : null}
            {selected && !selected.locked && selected.outline ? outlineToScreen(selected.corners, selected.outline).map((point, index) => (
              <button
                key={`${selected.id}-outline-${index}`}
                type="button"
                aria-label={`Outline point ${index + 1} of ${selected.name}`}
                title={`Drag outline point ${index + 1}; remove it in the inspector`}
                className="absolute z-20 flex size-9 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full"
                style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%` }}
                onPointerDown={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  beginHistoryGroup();
                  dragRef.current = { type: "outline", id: selected.id, index };
                }}
              ><span className="size-3 rounded-full border-2 border-black bg-yellow-300" /></button>
            )) : null}
            {selected && !selected.locked && (selected.outline?.length ?? 4) < MAX_OUTLINE_POINTS ? outlineToScreen(selected.corners, selected.outline).map((point, index, all) => {
              const next = all[(index + 1) % all.length];
              return (
                <button
                  key={`${selected.id}-add-${index}`}
                  type="button"
                  aria-label={`Add outline point between ${index + 1} and ${(index + 1) % all.length + 1}`}
                  title="Add a point on this edge"
                  className="absolute z-20 flex size-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-yellow-300 bg-bg/80 text-yellow-300"
                  style={{ left: `${(point.x + next.x) * 50}%`, top: `${(point.y + next.y) * 50}%` }}
                  onClick={() => addOutlinePoint(selected.id, index)}
                >+</button>
              );
            }) : null}
          </div>
        ) : null}
        {lineup && !blackout && !align ? <LineupOverlay /> : null}
        {edit && scene.surfaces.length === 0 ? (
          <p className="pointer-events-none absolute inset-0 flex items-center justify-center px-6 text-center text-sm text-muted">
            Add a surface, then drag its corners until the light sits on the real object.
          </p>
        ) : null}
      </div>
    </div>
  );
}

function sceneFaces(scene: { surfaces: Surface[] }, soloId: string | null): DrawFace[] {
  const surfaces = soloId ? scene.surfaces.filter((face) => face.id === soloId) : scene.surfaces;
  return surfaces.map((face) => ({
    corners: face.corners,
    outline: face.outline,
    look: face.look,
    gel: gelRgb(face.gel),
    opacity: face.opacity,
    feather: face.feather,
    mask: face.mask,
    brightness: face.brightness,
    contrast: face.contrast,
    saturation: face.saturation,
    speed: face.speed,
    blend: face.blend,
    visible: face.visible,
    source: getClipSource(face.videoId),
  }));
}

function scaledFaces(faces: DrawFace[], amount: number): DrawFace[] {
  return faces.map((face) => ({ ...face, opacity: face.opacity * amount }));
}

function snapLine(value: number, lineup: boolean, bypass: boolean) {
  if (!lineup || bypass) return value;
  const nearest = Math.round(value * 10) / 10;
  return Math.abs(nearest - value) <= 0.02 ? nearest : value;
}

function LineupOverlay() {
  return (
    <svg
      className="pointer-events-none absolute inset-0 z-20 h-full w-full"
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <LineupMarks ink="#000" gridOpacity={0.9} fine={4} heavy={6} />
      <LineupMarks ink="#fff" gridOpacity={0.92} fine={1.5} heavy={3} />
    </svg>
  );
}

function LineupMarks({
  ink,
  gridOpacity,
  fine,
  heavy,
}: {
  ink: string;
  gridOpacity: number;
  fine: number;
  heavy: number;
}) {
  return (
    <g fill="none" stroke={ink} strokeWidth={fine} vectorEffect="non-scaling-stroke">
      <rect x="1" y="1" width={VIEW_W - 2} height={VIEW_H - 2} />
      {Array.from({ length: 9 }, (_, i) => (
        <g key={i} strokeOpacity={gridOpacity}>
          <line x1={((i + 1) * VIEW_W) / 10} y1="0" x2={((i + 1) * VIEW_W) / 10} y2={VIEW_H} />
          <line x1="0" y1={((i + 1) * VIEW_H) / 10} x2={VIEW_W} y2={((i + 1) * VIEW_H) / 10} />
        </g>
      ))}
      <g strokeWidth={heavy}>
        <line x1={VIEW_W / 2 - 42} y1={VIEW_H / 2} x2={VIEW_W / 2 + 42} y2={VIEW_H / 2} />
        <line x1={VIEW_W / 2} y1={VIEW_H / 2 - 42} x2={VIEW_W / 2} y2={VIEW_H / 2 + 42} />
        {Array.from({ length: 9 }, (_, i) => (
          <g key={`tick-${i}`}>
            <line x1={((i + 1) * VIEW_W) / 10} y1="0" x2={((i + 1) * VIEW_W) / 10} y2="18" />
            <line x1={((i + 1) * VIEW_W) / 10} y1={VIEW_H - 18} x2={((i + 1) * VIEW_W) / 10} y2={VIEW_H} />
            <line x1="0" y1={((i + 1) * VIEW_H) / 10} x2="18" y2={((i + 1) * VIEW_H) / 10} />
            <line x1={VIEW_W - 18} y1={((i + 1) * VIEW_H) / 10} x2={VIEW_W} y2={((i + 1) * VIEW_H) / 10} />
          </g>
        ))}
      </g>
    </g>
  );
}
