import { applyHomography, invertHomography, squareToQuad, type Corners, type Pt } from "@/lib/beam/math";

export const MAX_OUTLINE_POINTS = 16;
export const RECT_OUTLINE: Pt[] = [
  { x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }, { x: 0, y: 1 },
];

export function validOutline(value: unknown): Pt[] | undefined {
  if (!Array.isArray(value) || value.length < 3 || value.length > MAX_OUTLINE_POINTS) return undefined;
  if (!value.every((point) => point && typeof point.x === "number" && typeof point.y === "number" &&
    Number.isFinite(point.x) && Number.isFinite(point.y))) return undefined;
  return value.map((point: Pt) => ({ x: Math.max(0, Math.min(1, point.x)), y: Math.max(0, Math.min(1, point.y)) }));
}

export function outlineToScreen(corners: Corners, outline: Pt[] | undefined): Pt[] {
  if (!outline) return corners;
  const matrix = squareToQuad(...corners);
  return matrix ? outline.map(({ x, y }) => applyHomography(matrix, x, y)) : corners;
}

export function screenToOutline(corners: Corners, point: Pt): Pt | null {
  const matrix = squareToQuad(...corners);
  const inverse = matrix && invertHomography(matrix);
  if (!inverse) return null;
  const uv = applyHomography(inverse, point.x, point.y);
  if (!Number.isFinite(uv.x) || !Number.isFinite(uv.y)) return null;
  return { x: Math.max(0, Math.min(1, uv.x)), y: Math.max(0, Math.min(1, uv.y)) };
}
