import { useEffect, useRef } from "react";
import { gelRgb } from "@/lib/beam/looks";
import { getClipSource } from "@/lib/beam/clips";
import { createMapper, type DrawFace, type Mapper } from "@/lib/beam/gl-mapper";
import type { Corners } from "@/lib/beam/math";
import { activeScene, type Surface } from "@/lib/beam/project";
import { useEditor } from "@/lib/beam/store";

const VIEW_W = 1600;
const VIEW_H = 900;

export function Stage({ edit, lineup }: { edit: boolean; lineup: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mapperRef = useRef<Mapper | null>(null);
  const dragRef = useRef<
    | { type: "corner"; id: string; index: number }
    | { type: "move"; id: string; startX: number; startY: number; corners: Corners }
    | null
  >(null);
  const guides = useEditor((s) => s.guides);
  const selectedId = useEditor((s) => s.selectedId);
  const scene = useEditor((s) => activeScene(s));
  const select = useEditor((s) => s.select);
  const setCorner = useEditor((s) => s.setCorner);
  const moveSurface = useEditor((s) => s.moveSurface);

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
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(bay);
    let raf = 0;
    const loop = (now: number) => {
      const state = useEditor.getState();
      const current = activeScene(state);
      const faces: DrawFace[] = current.surfaces.map((face) => ({
        corners: face.corners,
        look: face.look,
        gel: gelRgb(face.gel),
        opacity: face.opacity,
        blend: face.blend,
        visible: face.visible,
        source: getClipSource(face.videoId),
      }));
      mapper?.draw(faces, reduced ? 0 : now / 1000);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
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
      if (drag.type === "corner") setCorner(drag.id, drag.index, point.x, point.y);
      else moveSurface(drag.id, drag.corners, point.x - drag.startX, point.y - drag.startY);
    };
    const up = () => {
      dragRef.current = null;
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
  }, [moveSurface, setCorner]);

  function beginMove(event: React.PointerEvent, face: Surface) {
    if (!edit || face.locked) {
      select(face.id);
      return;
    }
    event.preventDefault();
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
                const points = face.corners
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
                      select(selected.id);
                      dragRef.current = { type: "corner", id: selected.id, index };
                    }}
                  >
                    <span className="size-3.5 rounded-full border-2 border-beam bg-fg" />
                  </button>
                ))
              : null}
          </div>
        ) : null}
        {lineup ? <LineupOverlay /> : null}
        {edit && scene.surfaces.length === 0 ? (
          <p className="pointer-events-none absolute inset-0 flex items-center justify-center px-6 text-center text-sm text-muted">
            Add a surface, then drag its corners until the light sits on the real object.
          </p>
        ) : null}
      </div>
    </div>
  );
}

function LineupOverlay() {
  return (
    <svg
      className="pointer-events-none absolute inset-0 z-20 h-full w-full"
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <g fill="none" stroke="#fff" strokeOpacity="0.85" strokeWidth="1.5" vectorEffect="non-scaling-stroke">
        <rect x="1" y="1" width={VIEW_W - 2} height={VIEW_H - 2} />
        {Array.from({ length: 9 }, (_, i) => (
          <g key={i}>
            <line x1={((i + 1) * VIEW_W) / 10} y1="0" x2={((i + 1) * VIEW_W) / 10} y2={VIEW_H} strokeOpacity="0.5" />
            <line x1="0" y1={((i + 1) * VIEW_H) / 10} x2={VIEW_W} y2={((i + 1) * VIEW_H) / 10} strokeOpacity="0.5" />
          </g>
        ))}
        <line x1={VIEW_W / 2 - 42} y1={VIEW_H / 2} x2={VIEW_W / 2 + 42} y2={VIEW_H / 2} strokeWidth="3" />
        <line x1={VIEW_W / 2} y1={VIEW_H / 2 - 42} x2={VIEW_W / 2} y2={VIEW_H / 2 + 42} strokeWidth="3" />
        {Array.from({ length: 9 }, (_, i) => (
          <g key={`tick-${i}`} strokeWidth="3">
            <line x1={((i + 1) * VIEW_W) / 10} y1="0" x2={((i + 1) * VIEW_W) / 10} y2="18" />
            <line x1={((i + 1) * VIEW_W) / 10} y1={VIEW_H - 18} x2={((i + 1) * VIEW_W) / 10} y2={VIEW_H} />
            <line x1="0" y1={((i + 1) * VIEW_H) / 10} x2="18" y2={((i + 1) * VIEW_H) / 10} />
            <line x1={VIEW_W - 18} y1={((i + 1) * VIEW_H) / 10} x2={VIEW_W} y2={((i + 1) * VIEW_H) / 10} />
          </g>
        ))}
      </g>
    </svg>
  );
}
