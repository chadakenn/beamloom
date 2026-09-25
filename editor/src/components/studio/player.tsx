import { useEffect, useRef, useState } from "react";
import { createMapper, type DrawFace } from "@/lib/beam/gl-mapper";
import { parseLiveFrame, type LiveFrame, type LiveSurface } from "@/lib/beam/live";
import { gelRgb } from "@/lib/beam/looks";

function drawFaces(frame: LiveFrame, images: Map<string, HTMLImageElement>): DrawFace[] {
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
    source: face.mediaId ? images.get(face.mediaId) ?? null : null,
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
    const images = new Map<string, HTMLImageElement>();
    const loading = new Set<string>();
    let mediaEpoch = 0;
    const loadImages = (current: LiveFrame) => {
      for (const face of current.surfaces) {
        const id = face.mediaId;
        if (!id || images.has(id) || loading.has(id)) continue;
        loading.add(id);
        const epoch = mediaEpoch;
        const image = new Image();
        image.onload = () => {
          if (!stopped && epoch === mediaEpoch && image.naturalWidth > 0) images.set(id, image);
          if (epoch === mediaEpoch) loading.delete(id);
        };
        image.onerror = () => { if (epoch === mediaEpoch) loading.delete(id); };
        image.src = `/media/${id}`;
      }
    };
    const fit = () => mapper?.resize(window.innerWidth, window.innerHeight, Math.min(window.devicePixelRatio || 1, 2));
    fit();
    window.addEventListener("resize", fit);
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    const loop = (now: number) => {
      mapper?.draw(frame ? drawFaces(frame, images) : [], reduced ? 0 : now / 1000, frame?.master ?? 1);
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
        if (parsed) {
          frame = parsed;
          loadImages(parsed);
        }
      };
      next.onclose = () => {
        mediaEpoch += 1;
        images.clear();
        loading.clear();
        frame = null;
        setWaiting(true);
        if (!stopped) retry = window.setTimeout(connect, 2000);
      };
    };
    connect();
    return () => {
      stopped = true;
      mediaEpoch += 1;
      images.clear();
      loading.clear();
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
