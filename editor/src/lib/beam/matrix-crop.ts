export type MatrixCrop = { column: number; row: number; width: number; height: number };

// Missing crop means the entire incoming matrix, including older saved projects.
export function validMatrixCrop(value: unknown): MatrixCrop | undefined {
  if (!value || typeof value !== "object") return undefined;
  const crop = value as Record<string, unknown>;
  const numbers = [crop.column, crop.row, crop.width, crop.height];
  if (numbers.some((number) => typeof number !== "number" || !Number.isInteger(number))) return undefined;
  const [column, row, width, height] = numbers as number[];
  if (column < 1 || column > 256 || row < 1 || row > 144 || width < 1 || width > 256 || height < 1 || height > 144) return undefined;
  return { column, row, width, height };
}

export function matrixCropRect(crop: MatrixCrop | undefined, width: number, height: number): [number, number, number, number] {
  if (!crop) return [0, 0, 1, 1];
  const left = Math.min(width - 1, crop.column - 1);
  const top = Math.min(height - 1, crop.row - 1);
  return [left / width, top / height, Math.min(crop.width, width - left) / width, Math.min(crop.height, height - top) / height];
}
