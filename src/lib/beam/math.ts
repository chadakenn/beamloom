export type Pt = { x: number; y: number };

export type Corners = [Pt, Pt, Pt, Pt];

/**
 * Column-major 3×3 mapping the unit square (TL, TR, BR, BL) onto a quad.
 * Layout matches WebGL's uniformMatrix3fv.
 */
export function squareToQuad(tl: Pt, tr: Pt, br: Pt, bl: Pt): Float32Array | null {
  const x0 = tl.x;
  const y0 = tl.y;
  const x1 = tr.x;
  const y1 = tr.y;
  const x2 = br.x;
  const y2 = br.y;
  const x3 = bl.x;
  const y3 = bl.y;
  const dx1 = x1 - x2;
  const dy1 = y1 - y2;
  const dx2 = x3 - x2;
  const dy2 = y3 - y2;
  const sx = x0 - x1 + x2 - x3;
  const sy = y0 - y1 + y2 - y3;
  const det = dx1 * dy2 - dx2 * dy1;
  if (!Number.isFinite(det) || Math.abs(det) < 1e-8) return null;
  const g = (sx * dy2 - dx2 * sy) / det;
  const h = (dx1 * sy - sx * dy1) / det;
  return new Float32Array([
    x1 - x0 + g * x1,
    y1 - y0 + g * y1,
    g,
    x3 - x0 + h * x3,
    y3 - y0 + h * y3,
    h,
    x0,
    y0,
    1,
  ]);
}

/** Invert a column-major 3×3. Returns column-major, or null if singular. */
export function invertHomography(m: Float32Array): Float32Array | null {
  const a00 = m[0];
  const a01 = m[3];
  const a02 = m[6];
  const a10 = m[1];
  const a11 = m[4];
  const a12 = m[7];
  const a20 = m[2];
  const a21 = m[5];
  const a22 = m[8];

  const c00 = a11 * a22 - a12 * a21;
  const c01 = a12 * a20 - a10 * a22;
  const c02 = a10 * a21 - a11 * a20;
  const c10 = a02 * a21 - a01 * a22;
  const c11 = a00 * a22 - a02 * a20;
  const c12 = a01 * a20 - a00 * a21;
  const c20 = a01 * a12 - a02 * a11;
  const c21 = a02 * a10 - a00 * a12;
  const c22 = a00 * a11 - a01 * a10;

  const det = a00 * c00 + a01 * c01 + a02 * c02;
  if (!Number.isFinite(det) || Math.abs(det) < 1e-10) return null;
  const inv = 1 / det;
  return new Float32Array([
    c00 * inv,
    c01 * inv,
    c02 * inv,
    c10 * inv,
    c11 * inv,
    c12 * inv,
    c20 * inv,
    c21 * inv,
    c22 * inv,
  ]);
}

export function applyHomography(m: Float32Array, x: number, y: number): Pt {
  const w = m[2] * x + m[5] * y + m[8];
  return {
    x: (m[0] * x + m[3] * y + m[6]) / w,
    y: (m[1] * x + m[4] * y + m[7]) / w,
  };
}

export function clamp01(n: number): number {
  if (n < 0) return 0;
  if (n > 1) return 1;
  return n;
}

export function translateCorners(corners: Corners, dx: number, dy: number): Corners {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const c of corners) {
    minX = Math.min(minX, c.x);
    minY = Math.min(minY, c.y);
    maxX = Math.max(maxX, c.x);
    maxY = Math.max(maxY, c.y);
  }
  const adx = Math.min(Math.max(dx, -minX), 1 - maxX);
  const ady = Math.min(Math.max(dy, -minY), 1 - maxY);
  return corners.map((c) => ({ x: c.x + adx, y: c.y + ady })) as Corners;
}
