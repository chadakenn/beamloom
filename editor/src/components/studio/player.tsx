import { useEffect, useRef, useState } from "react";
import { createMapper, type DrawFace } from "@/lib/beam/gl-mapper";
import { parseLiveFrame, type LiveFrame, type LiveSurface } from "@/lib/beam/live";
import { gelRgb } from "@/lib/beam/looks";

function drawFaces(frame: LiveFrame, images: Map<string, HTMLImageElement>, videos: Map<string, HTMLVideoElement>): DrawFace[] {
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
    speed: face.speed ?? 1,
    blend: face.blend,
    visible: face.visible,
    source: sourceFor(face, images, videos),
  }));
}

function sourceFor(face: LiveSurface, images: Map<string, HTMLImageElement>, videos: Map<string, HTMLVideoElement>) {
  if (!face.mediaId) return null;
  if (face.mediaPlaying !== undefined) {
    const video = videos.get(face.mediaId);
    if (!video || video.readyState < 2 || video.videoWidth === 0) return null;
    return video;
  }
  return images.get(face.mediaId) ?? null;
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
    const videos = new Map<string, HTMLVideoElement>();
    const loading = new Set<string>();
    const failed = new Set<string>();
    let mediaEpoch = 0;
    const dropVideos = () => {
      for (const video of videos.values()) {
        video.pause();
        video.removeAttribute("src");
        video.load();
        video.remove();
      }
      videos.clear();
    };
    const loadImages = (current: LiveFrame) => {
      for (const face of current.surfaces) {
        const id = face.mediaId;
        if (!id || face.mediaPlaying !== undefined || images.has(id) || loading.has(id) || failed.has(id)) continue;
        loading.add(id);
        const epoch = mediaEpoch;
        const image = new Image();
        image.onload = () => {
          if (!stopped && epoch === mediaEpoch && image.naturalWidth > 0) images.set(id, image);
          if (epoch === mediaEpoch) loading.delete(id);
        };
        image.onerror = () => {
          if (epoch === mediaEpoch) {
            failed.add(id);
            loading.delete(id);
          }
        };
        image.src = `/media/${id}`;
      }
    };
    const applyVideos = (current: LiveFrame) => {
      for (const face of current.surfaces) {
        const id = face.mediaId;
        if (!id || face.mediaPlaying === undefined || failed.has(id)) continue;
        let video = videos.get(id);
        if (!video) {
          const epoch = mediaEpoch;
          video = document.createElement("video");
          video.muted = true;
          video.playsInline = true;
          video.preload = "auto";
          video.loop = face.mediaLoop === true;
          video.style.cssText = "position:fixed;width:2px;height:2px;opacity:0;pointer-events:none";
          document.body.appendChild(video);
          videos.set(id, video);
          video.onerror = () => {
            if (epoch !== mediaEpoch) return;
            failed.add(id);
            videos.delete(id);
            video?.remove();
          };
          video.src = `/media/${id}`;
        }
        if (!video || video.readyState < 1) continue;
        video.loop = face.mediaLoop === true;
        if (typeof face.mediaTime === "number" && Math.abs(video.currentTime - face.mediaTime) > 0.4) video.currentTime = face.mediaTime;
        if (face.mediaPlaying && video.paused) void video.play().catch(() => undefined);
        else if (!face.mediaPlaying && !video.paused) video.pause();
      }
    };
    const fit = () => mapper?.resize(window.innerWidth, window.innerHeight, Math.min(window.devicePixelRatio || 1, 2));
    fit();
    window.addEventListener("resize", fit);
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    const loop = (now: number) => {
      mapper?.draw(frame ? drawFaces(frame, images, videos) : [], reduced ? 0 : now / 1000, frame?.master ?? 1);
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
          applyVideos(parsed);
        }
      };
      next.onclose = () => {
        mediaEpoch += 1;
        images.clear();
        loading.clear();
        failed.clear();
        dropVideos();
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
      failed.clear();
      dropVideos();
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
