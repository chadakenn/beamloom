export const LOOKS = [
  { id: "wash", name: "Tungsten wash", kind: 0, blurb: "Slow warm field" },
  { id: "scan", name: "Scan loom", kind: 1, blurb: "Thread and sweep" },
  { id: "lattice", name: "Lattice", kind: 2, blurb: "Alignment grid" },
  { id: "embers", name: "Ember lift", kind: 3, blurb: "Rising sparks" },
  { id: "rings", name: "Halo rings", kind: 4, blurb: "Pulse from center" },
  { id: "columns", name: "Columns", kind: 5, blurb: "Facade bars" },
  { id: "gel", name: "Gel", kind: 6, blurb: "Flat color" },
  { id: "neon", name: "Neon flow", kind: 7, blurb: "Moving neon ribbons" },
  { id: "aurora", name: "Aurora", kind: 8, blurb: "Waves of green and violet" },
  { id: "confetti", name: "Confetti", kind: 9, blurb: "Bright falling sparks" },
  { id: "prism", name: "Prism sweep", kind: 10, blurb: "A rainbow band crossing the quad" },
  { id: "tiles", name: "Hue tiles", kind: 11, blurb: "A grid of flashing colors" },
  { id: "pinwheel", name: "Pinwheel", kind: 12, blurb: "Colored arms turning from the center" },
] as const;

export type LookId = (typeof LOOKS)[number]["id"];

export const GELS: { name: string; rgb: [number, number, number] }[] = [
  { name: "Amber", rgb: [0.95, 0.62, 0.16] },
  { name: "Bone", rgb: [0.93, 0.9, 0.84] },
  { name: "Crimson", rgb: [0.72, 0.08, 0.12] },
  { name: "Signal", rgb: [0.1, 0.62, 0.55] },
  { name: "Violet", rgb: [0.42, 0.22, 0.72] },
];

export function lookKind(id: LookId): number {
  return LOOKS.find((look) => look.id === id)?.kind ?? 0;
}

export function gelRgb(index: number): [number, number, number] {
  return GELS[index]?.rgb ?? GELS[0].rgb;
}
