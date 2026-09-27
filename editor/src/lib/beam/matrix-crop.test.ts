import assert from "node:assert/strict";
import { matrixCropRect, validMatrixCrop } from "./matrix-crop.ts";

assert.deepEqual(matrixCropRect(undefined, 256, 144), [0, 0, 1, 1]);
assert.deepEqual(matrixCropRect({ column: 65, row: 37, width: 64, height: 36 }, 256, 144), [0.25, 0.25, 0.25, 0.25]);
assert.deepEqual(matrixCropRect({ column: 120, row: 70, width: 64, height: 36 }, 128, 72), [119 / 128, 69 / 72, 9 / 128, 3 / 72]);
assert.equal(validMatrixCrop({ column: 0, row: 1, width: 10, height: 10 }), undefined);
assert.equal(validMatrixCrop({ column: 1.5, row: 1, width: 10, height: 10 }), undefined);
