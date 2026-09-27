import type { Corners, Pt } from "@/lib/beam/math";
import { outlineToScreen } from "@/lib/beam/outline";

const KEY = "beamloom.align.v1";
const listeners = new Set<() => void>();
let enabled = false;
let listening = false;

function listen() {
  if (listening || typeof window === "undefined") return;
  listening = true;
  try { enabled = localStorage.getItem(KEY) === "1"; } catch { /* Session-only alignment. */ }
  window.addEventListener("storage", (event) => {
    if (event.key !== KEY) return;
    enabled = event.newValue === "1";
    listeners.forEach((listener) => listener());
  });
}

export function getAlign() {
  listen();
  return enabled;
}

export function setAlign(next: boolean) {
  listen();
  if (enabled === next) return;
  enabled = next;
  try { localStorage.setItem(KEY, next ? "1" : "0"); } catch { /* Keep current window working. */ }
  listeners.forEach((listener) => listener());
}

export function subscribeAlign(listener: () => void) {
  listen();
  listeners.add(listener);
  return () => listeners.delete(listener);
}

// Draw over a black projector frame. The marks are inside the selected quad only.
export function drawAlignment(canvas: HTMLCanvasElement, corners: Corners | null, master = 1, outline?: Pt[]) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const { width, height } = canvas;
  ctx.clearRect(0, 0, width, height);
  if (!corners || master <= 0) return;
  const points = outlineToScreen(corners, outline).map(({ x, y }) => ({ x: x * width, y: y * height }));
  ctx.save();
  ctx.globalAlpha = master;
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (const point of points.slice(1)) ctx.lineTo(point.x, point.y);
  ctx.closePath();
  ctx.fillStyle = "#e8dc35";
  ctx.fill();
  ctx.lineJoin = "round";
  ctx.lineWidth = Math.max(3, Math.min(width, height) * 0.006);
  ctx.strokeStyle = "#ffffff";
  ctx.stroke();
  if (!outline) {
    ctx.beginPath();
    ctx.moveTo((points[0].x + points[3].x) / 2, (points[0].y + points[3].y) / 2);
    ctx.lineTo((points[1].x + points[2].x) / 2, (points[1].y + points[2].y) / 2);
    ctx.moveTo((points[0].x + points[1].x) / 2, (points[0].y + points[1].y) / 2);
    ctx.lineTo((points[2].x + points[3].x) / 2, (points[2].y + points[3].y) / 2);
    ctx.strokeStyle = "#242025";
    ctx.lineWidth = Math.max(2, Math.min(width, height) * 0.003);
    ctx.stroke();
  }
  for (const point of points) {
    ctx.beginPath();
    ctx.arc(point.x, point.y, Math.max(7, Math.min(width, height) * 0.012), 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.strokeStyle = "#242025";
    ctx.stroke();
  }
  ctx.restore();
}
