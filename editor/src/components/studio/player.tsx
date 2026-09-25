import { useEffect, useRef, useState } from "react";
import { createMapper, type DrawFace } from "@/lib/beam/gl-mapper";
import { parseLiveFrame, type LiveFrame, type LiveSurface } from "@/lib/beam/live";
import { gelRgb } from "@/lib/beam/looks";

function drawFaces(frame: LiveFrame): DrawFace[] {
  if (frame.blackout) return [];
  return frame.surfaces.map((face: LiveSurface) => ({
    corners: face.corners,
    look: face.look,
    gel: gelRgb(face.gel),
    opacity: face.opacity,
    feather: face.feather,
    mask: face.mask,
    brightness: face.brightness,
    contrast: face.contrast,
    saturation: face.saturation,
    blend: face.blend,
    visible: face.visible,
    source: null,
  }));
}

export function Player() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [waiting, setWaiting] = useState(true);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const mapper = createMapper(canvas);
    let frame: LiveFrame | null = null;
    let socket: WebSocket | null = null;
    let retry = 0;
    let stopped = false;
    const fit = () => mapper?.resize(window.innerWidth, window.innerHeight, Math.min(window.devicePixelRatio || 1, 2));
    fit();
    window.addEventListener("resize", fit);
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    const loop = (now: number) => {
      mapper?.draw(frame ? drawFaces(frame) : [], reduced ? 0 : now / 1000, frame?.master ?? 1);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    const connect = () => {
      if (stopped) return;
      const next = new WebSocket(`ws://${window.location.host}/live`);
      socket = next;
      next.onopen = () => setWaiting(false);
      next.onmessage = (event) => {
        const parsed = parseLiveFrame(event.data);
        if (parsed) frame = parsed;
      };
      next.onclose = () => {
        setWaiting(true);
        if (!stopped) retry = window.setTimeout(connect, 2000);
      };
    };
    connect();
    return () => {
      stopped = true;
      window.clearTimeout(retry);
      cancelAnimationFrame(raf);
      socket?.close();
      mapper?.destroy();
      window.removeEventListener("resize", fit);
    };
  }, []);

  return (
    <div className="relative h-dvh w-screen overflow-hidden bg-black">
      <canvas ref={canvasRef} className="block h-full w-full" />
      {waiting ? <p className="absolute bottom-4 left-4 text-sm text-white/70">Waiting for the PC</p> : null}
    </div>
  );
}
