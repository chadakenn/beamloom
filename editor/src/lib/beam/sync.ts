export type SyncAssignment = { universe: number; channel: number };
export type SyncColor = { rgb: [number, number, number]; brightness: number };

export function validSync(value: unknown): SyncAssignment | undefined {
  if (!value || typeof value !== "object") return undefined;
  const raw = value as Partial<SyncAssignment>;
  if (!Number.isInteger(raw.universe) || !Number.isInteger(raw.channel) ||
    raw.universe! < 1 || raw.universe! > 63999 || raw.channel! < 1 || raw.channel! > 509) return undefined;
  return { universe: raw.universe!, channel: raw.channel! };
}

const values = new Map<number, Uint8Array>();
let lastFrameAt = 0;
const MATRIX_WIDTH = 256;
const MATRIX_HEIGHT = 144;
let matrixCanvas: HTMLCanvasElement | undefined;
let matrixAt = 0;

function paintMatrix(pixels: Uint8Array, width: number, height: number) {
  if ((width !== 128 && width !== MATRIX_WIDTH) || (height !== 72 && height !== MATRIX_HEIGHT) || pixels.length !== width * height * 3) return;
  matrixCanvas ??= document.createElement("canvas");
  if (matrixCanvas.width !== width || matrixCanvas.height !== height) {
    matrixCanvas.width = width;
    matrixCanvas.height = height;
  }
  const context = matrixCanvas.getContext("2d", { alpha: false });
  if (!context) return;
  const image = context.createImageData(width, height);
  const rgba = image.data;
  const count = width * height;
  for (let index = 0, pixel = 0; index < count; index += 1, pixel += 4) {
    const source = index * 3;
    rgba[pixel] = pixels[source];
    rgba[pixel + 1] = pixels[source + 1];
    rgba[pixel + 2] = pixels[source + 2];
    rgba[pixel + 3] = 255;
  }
  context.putImageData(image, 0, 0);
  matrixAt = Date.now();
}

export function receiveSync(raw: unknown) {
  if (raw instanceof ArrayBuffer) {
    const bytes = new Uint8Array(raw);
    if (bytes.length < 4) return;
    paintMatrix(bytes.subarray(4), (bytes[0] << 8) | bytes[1], (bytes[2] << 8) | bytes[3]);
    return;
  }
  if (typeof raw !== "string" || raw.length > 200000) return;
  try {
    const frame = JSON.parse(raw) as { universes?: Record<string, string>; matrix?: string; matrixWidth?: number; matrixHeight?: number };
    if (!frame.universes || typeof frame.universes !== "object" || Array.isArray(frame.universes)) return;
    const next = new Map<number, Uint8Array>();
    for (const [id, encoded] of Object.entries(frame.universes).slice(0, 32)) {
      const universe = Number(id);
      if (!Number.isInteger(universe) || universe < 0 || universe > 63999 || typeof encoded !== "string" || encoded.length > 700) continue;
      const binary = atob(encoded);
      const data = new Uint8Array(binary.length);
      for (let index = 0; index < binary.length; index += 1) data[index] = binary.charCodeAt(index);
      if (data.length === 512) next.set(universe, data);
    }
    values.clear();
    next.forEach((data, universe) => values.set(universe, data));
    lastFrameAt = Date.now();
    if (typeof frame.matrix === "string") {
      const binary = atob(frame.matrix);
      const pixels = new Uint8Array(binary.length);
      for (let index = 0; index < binary.length; index += 1) pixels[index] = binary.charCodeAt(index);
      paintMatrix(pixels, frame.matrixWidth ?? 128, frame.matrixHeight ?? 72);
    }
  } catch { /* Ignore invalid channel frames. */ }
}

export function syncColor(assignment: SyncAssignment | undefined): SyncColor | undefined {
  if (!assignment || Date.now() - lastFrameAt > 5000) return undefined;
  const data = values.get(assignment.universe);
  if (!data) return undefined;
  const offset = assignment.channel - 1;
  return {
    rgb: [data[offset] / 255, data[offset + 1] / 255, data[offset + 2] / 255],
    brightness: data[offset + 3] / 255,
  };
}

export function syncMatrix(): HTMLCanvasElement | undefined {
  return Date.now() - matrixAt < 5000 ? matrixCanvas : undefined;
}

export function clearSync() { values.clear(); lastFrameAt = 0; matrixAt = 0; matrixCanvas = undefined; }
