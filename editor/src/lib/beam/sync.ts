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

export function receiveSync(raw: unknown) {
  if (typeof raw !== "string" || raw.length > 60000) return;
  try {
    const frame = JSON.parse(raw) as { universes?: Record<string, string> };
    if (!frame.universes || typeof frame.universes !== "object" || Array.isArray(frame.universes)) return;
    const next = new Map<number, Uint8Array>();
    for (const [id, encoded] of Object.entries(frame.universes).slice(0, 32)) {
      const universe = Number(id);
      if (!Number.isInteger(universe) || universe < 0 || universe > 63999 || typeof encoded !== "string" || encoded.length > 700) continue;
      const data = Uint8Array.from(atob(encoded), (char) => char.charCodeAt(0));
      if (data.length === 512) next.set(universe, data);
    }
    values.clear();
    next.forEach((data, universe) => values.set(universe, data));
    lastFrameAt = Date.now();
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

export function clearSync() { values.clear(); lastFrameAt = 0; }
