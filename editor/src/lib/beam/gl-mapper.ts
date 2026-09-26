import { lookKind, type LookId } from "@/lib/beam/looks";
import { invertHomography, squareToQuad, type Corners } from "@/lib/beam/math";
import type { Blend, Mask } from "@/lib/beam/project";

export type DrawFace = {
  corners: Corners;
  look: LookId;
  gel: [number, number, number];
  opacity: number;
  feather: number;
  mask: Mask;
  brightness: number;
  contrast: number;
  saturation: number;
  speed: number;
  blend: Blend;
  visible: boolean;
  source: TexImageSource | null;
};

const VERT = `#version 300 es
layout(location=0) in vec2 aClip;
void main() {
  gl_Position = vec4(aClip, 0.0, 1.0);
}`;

const FRAG = `#version 300 es
precision highp float;
out vec4 frag;
uniform mat3 uInv;
uniform vec2 uRes;
uniform float uTime;
uniform float uOpacity;
uniform float uFeather;
uniform int uMask;
uniform float uBrightness;
uniform float uMaster;
uniform float uContrast;
uniform float uSaturation;
uniform int uKind;
uniform vec3 uGel;
uniform sampler2D uVideo;
uniform int uHasVideo;

float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}
float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

void main() {
  vec2 px = vec2(gl_FragCoord.x, uRes.y - gl_FragCoord.y);
  vec3 h = uInv * vec3(px, 1.0);
  vec2 uv = h.xy / h.z;
  vec3 col = vec3(0.0);

  if (uHasVideo == 1) {
    col = texture(uVideo, uv).rgb;
  } else if (uKind == 0) {
    float n = noise(uv * 2.4 + vec2(uTime * 0.04, uTime * 0.02));
    float m = noise(uv * 5.0 - vec2(uTime * 0.05, 0.0));
    col = mix(vec3(0.18, 0.05, 0.015), vec3(0.98, 0.72, 0.28), smoothstep(0.15, 0.9, n + uv.y * 0.15));
    col += vec3(1.0, 0.82, 0.45) * pow(m, 5.0) * 0.55;
    col *= 0.72 + 0.28 * smoothstep(0.9, 0.2, length(uv - vec2(0.5, 0.45)));
  } else if (uKind == 1) {
    float thread = smoothstep(0.035, 0.0, abs(fract(uv.y * 22.0) - 0.5) - 0.47);
    float by = fract(uTime * 0.11);
    float beam = exp(-pow((uv.y - by) * 14.0, 2.0));
    float vert = smoothstep(0.02, 0.0, abs(fract(uv.x * 40.0) - 0.5) - 0.48);
    col = vec3(0.96, 0.78, 0.42) * (thread * 0.28 + vert * 0.12) + vec3(1.0, 0.9, 0.62) * beam;
    col += vec3(0.12, 0.05, 0.02);
  } else if (uKind == 2) {
    float gx = smoothstep(0.025, 0.0, abs(fract(uv.x * 8.0)));
    float gy = smoothstep(0.03, 0.0, abs(fract(uv.y * 5.0)));
    float grid = max(gx, gy);
    float cell = hash(floor(uv * vec2(8.0, 5.0)));
    float glow = 0.35 + 0.65 * (0.5 + 0.5 * sin(uTime * 1.4 + cell * 6.2));
    col = vec3(0.93, 0.88, 0.74) * grid * glow;
    col += vec3(0.95, 0.55, 0.16) * gx * gy;
  } else if (uKind == 3) {
    col = vec3(0.07, 0.025, 0.015);
    for (int i = 0; i < 10; i++) {
      float fi = float(i);
      float sx = hash(vec2(fi, 1.7));
      float sp = 0.05 + hash(vec2(fi, 9.2)) * 0.14;
      float sy = fract(hash(vec2(fi, 3.1)) - uTime * sp);
      float d = length((uv - vec2(sx, sy)) * vec2(1.0, 1.7));
      float spark = exp(-d * 46.0);
      col += vec3(1.0, 0.46, 0.12) * spark;
    }
  } else if (uKind == 4) {
    float r = length((uv - 0.5) * vec2(1.15, 1.0));
    float ring = smoothstep(0.018, 0.0, abs(fract(r * 7.0 - uTime * 0.28) - 0.06));
    float core = exp(-r * 3.2);
    col = mix(vec3(0.03, 0.05, 0.06), vec3(0.78, 0.9, 0.86), ring);
    col += vec3(0.95, 0.78, 0.4) * core * 0.45;
  } else if (uKind == 5) {
    float lanes = 8.0;
    float lane = floor(uv.x * lanes);
    float h = 0.22 + 0.72 * (0.5 + 0.5 * sin(uTime * 1.8 + lane * 1.15));
    float inside = step(fract(uv.x * lanes), 0.72);
    float bar = step(1.0 - h, uv.y) * inside;
    col = vec3(0.98, 0.58, 0.16) * bar;
    col += vec3(0.2, 0.08, 0.03) * inside * (1.0 - bar) * 0.35;
  } else if (uKind == 7) {
    float ribbon = sin(uv.x * 12.0 + sin(uv.y * 9.0 + uTime * 0.65) * 2.0 - uTime * 0.9);
    float ripple = sin(uv.y * 13.0 - uv.x * 7.0 + uTime * 0.7);
    float glow = pow(0.5 + 0.5 * ribbon, 5.0);
    col = mix(vec3(0.12, 0.015, 0.24), vec3(0.98, 0.07, 0.52), 0.5 + 0.5 * ripple);
    col = mix(col, vec3(0.05, 0.94, 0.98), 0.5 + 0.5 * sin(uv.x * 6.0 - uTime * 0.4));
    col *= 0.22 + 0.9 * glow;
  } else if (uKind == 8) {
    float wave = sin(uv.x * 9.0 + uTime * 0.55 + sin(uv.x * 3.0 - uTime * 0.3) * 1.5);
    float band = exp(-pow((uv.y - 0.5 - wave * 0.22) * 5.0, 2.0));
    float second = exp(-pow((uv.y - 0.48 + wave * 0.2) * 7.0, 2.0));
    col = vec3(0.006, 0.04, 0.09);
    col += vec3(0.02, 0.95, 0.55) * band * (0.5 + 0.5 * sin(uv.x * 6.0 + uTime * 0.4));
    col += vec3(0.64, 0.12, 0.98) * second * 0.85;
    col += vec3(0.08, 0.32, 0.9) * (band + second) * 0.25;
  } else if (uKind == 9) {
    col = vec3(0.025, 0.012, 0.09);
    for (int i = 0; i < 25; i++) {
      float fi = float(i);
      float x = hash(vec2(fi, 4.1));
      float y = fract(hash(vec2(fi, 8.3)) + uTime * (0.08 + hash(vec2(fi, 2.1)) * 0.08));
      vec2 delta = (uv - vec2(x, y)) * vec2(1.0, 1.5);
      float spark = exp(-dot(delta, delta) * 2200.0);
      vec3 hue = 0.5 + 0.5 * cos(6.28318 * (hash(vec2(fi, 7.2)) + vec3(0.0, 0.33, 0.67)));
      col += hue * spark * 1.6;
    }
  } else if (uKind == 10) {
    float band = fract(uv.x * 1.4 + uv.y * 0.45 - uTime * 0.12);
    vec3 hue = 0.55 + 0.45 * cos(6.28318 * (band + vec3(0.0, 0.33, 0.67)));
    float sweep = exp(-pow(fract(uv.x + uv.y * 0.25 - uTime * 0.18) - 0.5, 2.0) * 18.0);
    col = hue * (0.28 + sweep);
  } else if (uKind == 11) {
    vec2 cell = floor(uv * vec2(8.0, 5.0));
    float n = hash(cell);
    float phase = 0.5 + 0.5 * sin(uTime * 1.7 + n * 6.28318);
    vec3 hue = 0.55 + 0.45 * cos(6.28318 * (n + vec3(0.0, 0.33, 0.67)));
    col = hue * (0.12 + 0.95 * phase * phase);
  } else if (uKind == 12) {
    vec2 p = uv - 0.5;
    float ang = atan(p.y, p.x);
    float arm = pow(0.5 + 0.5 * sin(ang * 3.0 - uTime * 1.3), 10.0);
    float spin = fract(ang / 6.28318 + uTime * 0.08);
    vec3 hue = 0.55 + 0.45 * cos(6.28318 * (spin + vec3(0.0, 0.33, 0.67)));
    float fade = 1.0 - smoothstep(0.15, 0.72, length(p * vec2(1.2, 1.0)));
    col = vec3(0.02, 0.01, 0.05) + hue * arm * fade;
    col += vec3(1.0, 0.95, 0.9) * exp(-length(p) * 8.0) * 0.35;
  } else if (uKind == 13) {
    vec2 bone = uv;
    bone.x += 0.035 * sin(uTime * 1.3 + uv.y * 4.0);
    vec2 s = bone - vec2(0.5, 0.74);
    float skull = smoothstep(0.155, 0.13, length(s * vec2(1.2, 1.0)));
    float eyeL = smoothstep(0.034, 0.02, length(s - vec2(-0.045, 0.02)));
    float eyeR = smoothstep(0.034, 0.02, length(s - vec2(0.045, 0.02)));
    float jaw = smoothstep(0.018, 0.0, abs(s.y + 0.09)) * step(abs(s.x), 0.055);
    float ribs = 0.0;
    for (int i = 0; i < 5; i++) {
      float y = 0.46 - float(i) * 0.07;
      ribs += smoothstep(0.014, 0.0, abs(bone.y - y)) * smoothstep(0.18, 0.04, abs(bone.x - 0.5));
    }
    float spine = smoothstep(0.012, 0.0, abs(bone.x - 0.5)) * step(bone.y, 0.52) * step(0.14, bone.y);
    float lit = clamp(skull - eyeL - eyeR + jaw + ribs + spine, 0.0, 1.0);
    col = vec3(0.015, 0.01, 0.02) + vec3(0.95, 0.91, 0.8) * lit;
  } else if (uKind == 14) {
    col = vec3(0.012, 0.016, 0.03);
    for (int i = 0; i < 3; i++) {
      float fi = float(i);
      float rise = fract(0.15 + fi * 0.28 + uTime * (0.06 + fi * 0.015));
      vec2 g = uv - vec2(0.22 + fi * 0.28, rise);
      float body = exp(-dot(g * vec2(2.4, 1.15), g * vec2(2.4, 1.15)) * 16.0);
      float tail = exp(-pow((uv.x - g.x - uv.x) * 8.0, 2.0));
      col += vec3(0.78, 0.92, 0.84) * body * (0.55 + 0.45 * sin(uTime * 1.5 + fi));
      col += vec3(0.55, 0.75, 0.7) * smoothstep(0.35, 0.0, abs(uv.x - (0.22 + fi * 0.28))) * smoothstep(rise, rise - 0.25, uv.y) * 0.25;
    }
  } else if (uKind == 15) {
    col = vec3(0.02, 0.018, 0.015);
    float web = max(smoothstep(0.012, 0.0, abs(fract(uv.x * 7.0) - 0.5) - 0.47), smoothstep(0.012, 0.0, abs(fract(uv.y * 5.0) - 0.5) - 0.47));
    col += vec3(0.55, 0.52, 0.45) * web * 0.45;
    for (int i = 0; i < 4; i++) {
      float fi = float(i);
      vec2 c = vec2(0.18 + hash(vec2(fi, 1.3)) * 0.64, fract(hash(vec2(fi, 4.4)) - uTime * (0.07 + fi * 0.02)));
      vec2 d = uv - c;
      float body = exp(-dot(d, d) * 900.0);
      float legs = exp(-abs(abs(d.x) - abs(d.y)) * 40.0) * exp(-dot(d, d) * 80.0);
      col += vec3(0.92, 0.9, 0.82) * clamp(body + legs * 0.65, 0.0, 1.0);
    }
  } else if (uKind == 16) {
    vec2 q = (uv - vec2(0.5, 0.48)) * vec2(1.15, 1.0);
    float face = smoothstep(0.42, 0.36, length(q));
    float eye = smoothstep(0.07, 0.045, length(q - vec2(-0.12, 0.08))) + smoothstep(0.07, 0.045, length(q - vec2(0.12, 0.08)));
    float mouth = smoothstep(0.05, 0.02, abs(q.y + 0.12)) * step(abs(q.x), 0.16) * step(-0.2, q.y);
    float flicker = 0.82 + 0.18 * sin(uTime * 6.0 + uv.x * 12.0);
    col = vec3(0.02, 0.008, 0.0) + vec3(0.98, 0.48, 0.05) * face * (1.0 - clamp(eye + mouth, 0.0, 1.0)) * flicker;
  } else if (uKind == 17) {
    float travel = fract(uTime * 0.07);
    vec2 q = uv - vec2(travel, 0.48);
    float hat = step(abs(q.x) * 2.6, 0.16 - q.y) * step(0.0, q.y) * step(q.y, 0.16);
    float head = smoothstep(0.055, 0.04, length(q - vec2(0.0, -0.02)));
    float robe = smoothstep(0.015, 0.0, abs(q.x) - 0.028) * step(-0.32, q.y) * step(q.y, 0.0);
    col = vec3(0.015, 0.02, 0.012) + vec3(0.72, 0.95, 0.55) * clamp(hat + head + robe, 0.0, 1.0);
  } else {
    col = uGel;
    float sheen = 0.08 * sin(uv.y * 18.0 + uTime * 0.6);
    col += sheen;
  }

  if (uHasVideo == 0) {
    float grain = (hash(gl_FragCoord.xy + fract(uTime) * 80.0) - 0.5) * 0.035;
    col += grain;
  }
  col += uBrightness;
  col = (col - 0.5) * uContrast + 0.5;
  float luma = dot(col, vec3(0.2126, 0.7152, 0.0722));
  col = mix(vec3(luma), col, uSaturation);
  col = clamp(col, 0.0, 1.0);
  float edge = min(min(uv.x, 1.0 - uv.x), min(uv.y, 1.0 - uv.y));
  if (uMask == 1) {
    float inset = 0.08;
    float bar = 0.035;
    float frame = min(min(uv.x - inset, 1.0 - inset - uv.x), min(uv.y - inset, 1.0 - inset - uv.y));
    float mullion = min(abs(uv.x - 0.5), abs(uv.y - 0.5)) - bar;
    edge = min(frame, mullion);
  } else if (uMask == 2) {
    float side = min(uv.x, 1.0 - uv.x);
    float bottom = 1.0 - uv.y;
    if (uv.y >= 0.5) edge = min(side, bottom);
    else edge = 0.5 - length(uv - vec2(0.5, 0.5));
  }
  float soft = uFeather > 0.001 ? smoothstep(0.0, uFeather, edge) : step(0.0, edge);
  float a = clamp(uOpacity, 0.0, 1.0) * soft * clamp(uMaster, 0.0, 1.0);
  frag = vec4(col * a, a);
}`;

export type Mapper = {
  resize: (cssWidth: number, cssHeight: number, dpr: number) => void;
  draw: (faces: DrawFace[], time: number, master?: number) => void;
  destroy: () => void;
};

export function createMapper(canvas: HTMLCanvasElement): Mapper | null {
  const gl = canvas.getContext("webgl2", {
    alpha: false,
    antialias: true,
    premultipliedAlpha: true,
  });
  if (!gl) return null;

  const program = gl.createProgram();
  if (!program) return null;
  const vs = compile(gl, gl.VERTEX_SHADER, VERT);
  const fs = compile(gl, gl.FRAGMENT_SHADER, FRAG);
  if (!vs || !fs) return null;
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.bindAttribLocation(program, 0, "aClip");
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    console.error(gl.getProgramInfoLog(program));
    return null;
  }

  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, 12 * 4, gl.DYNAMIC_DRAW);
  gl.enableVertexAttribArray(0);
  gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  gl.useProgram(program);

  const loc = {
    inv: gl.getUniformLocation(program, "uInv"),
    res: gl.getUniformLocation(program, "uRes"),
    time: gl.getUniformLocation(program, "uTime"),
    opacity: gl.getUniformLocation(program, "uOpacity"),
    feather: gl.getUniformLocation(program, "uFeather"),
    mask: gl.getUniformLocation(program, "uMask"),
    brightness: gl.getUniformLocation(program, "uBrightness"),
    master: gl.getUniformLocation(program, "uMaster"),
    contrast: gl.getUniformLocation(program, "uContrast"),
    saturation: gl.getUniformLocation(program, "uSaturation"),
    kind: gl.getUniformLocation(program, "uKind"),
    gel: gl.getUniformLocation(program, "uGel"),
    video: gl.getUniformLocation(program, "uVideo"),
    hasVideo: gl.getUniformLocation(program, "uHasVideo"),
  };
  const clip = new Float32Array(12);
  const texture = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texImage2D(
    gl.TEXTURE_2D,
    0,
    gl.RGBA,
    1,
    1,
    0,
    gl.RGBA,
    gl.UNSIGNED_BYTE,
    new Uint8Array([0, 0, 0, 255]),
  );
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.uniform1i(loc.video, 0);
  let width = 2;
  let height = 2;

  return {
    resize(cssWidth, cssHeight, dpr) {
      const w = Math.max(2, Math.round(cssWidth * dpr));
      const h = Math.max(2, Math.round(cssHeight * dpr));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
      width = w;
      height = h;
      gl.viewport(0, 0, w, h);
    },
    draw(faces, time, master = 1) {
      gl.viewport(0, 0, width, height);
      gl.clearColor(0, 0, 0, 1);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.useProgram(program);
      gl.uniform2f(loc.res, width, height);
      gl.uniform1f(loc.master, Math.max(0, Math.min(1, master)));
      for (const face of faces) {
        if (!face.visible || face.opacity <= 0.001) continue;
        const pace = face.source ? 1 : Math.max(0, Math.min(4, face.speed));
        gl.uniform1f(loc.time, time * pace);
        const px = face.corners.map((c) => ({ x: c.x * width, y: c.y * height }));
        const forward = squareToQuad(px[0], px[1], px[2], px[3]);
        if (!forward) continue;
        const inv = invertHomography(forward);
        if (!inv) continue;
        writeClip(clip, face.corners);
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferSubData(gl.ARRAY_BUFFER, 0, clip);
        gl.uniformMatrix3fv(loc.inv, false, inv);
        gl.uniform1f(loc.opacity, face.opacity);
        gl.uniform1f(loc.feather, face.feather);
        gl.uniform1i(loc.mask, face.mask === "window" ? 1 : face.mask === "arch" ? 2 : 0);
        gl.uniform1f(loc.brightness, face.brightness);
        gl.uniform1f(loc.contrast, face.contrast);
        gl.uniform1f(loc.saturation, face.saturation);
        gl.uniform1i(loc.kind, lookKind(face.look));
        gl.uniform3f(loc.gel, face.gel[0], face.gel[1], face.gel[2]);
        const source = face.source;
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, texture);
        if (source) {
          try {
            gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, source);
            gl.uniform1i(loc.hasVideo, 1);
          } catch {
            gl.uniform1i(loc.hasVideo, 0);
          }
        } else {
          gl.uniform1i(loc.hasVideo, 0);
        }
        gl.enable(gl.BLEND);
        if (face.blend === "add") gl.blendFunc(gl.ONE, gl.ONE);
        else if (face.blend === "screen") gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_COLOR);
        else gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
        gl.drawArrays(gl.TRIANGLES, 0, 6);
      }
    },
    destroy() {
      gl.deleteTexture(texture);
      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
      gl.deleteShader(vs);
      gl.deleteShader(fs);
    },
  };
}

function writeClip(out: Float32Array, corners: Corners) {
  const order = [0, 1, 2, 0, 2, 3];
  for (let i = 0; i < 6; i++) {
    const c = corners[order[i]];
    out[i * 2] = c.x * 2 - 1;
    out[i * 2 + 1] = 1 - c.y * 2;
  }
}

function compile(gl: WebGL2RenderingContext, type: number, source: string) {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    console.error(gl.getShaderInfoLog(shader));
    gl.deleteShader(shader);
    return null;
  }
  return shader;
}
