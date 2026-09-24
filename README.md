# Beamloom

Original projection-mapping studio.

Beamloom places light on real surfaces. You drop a surface on a 16:9 projector frame, assign a look, and drag the corners until the picture sits on the wall, pier, or object. **Output** sends that frame fullscreen to the display feeding your projector.

The name, interface, looks, and warp math are written for this project. This is not a copy of any commercial mapping tool. Do not add their assets, presets, or decompiled code.

## What the studio does

- Perspective warp of each surface onto the projector frame
- Looks: tungsten wash, scan loom, lattice, ember lift, halo rings, columns, and gels
- Scenes, opacity, normal / add / screen blend, lock, and stack order
- Guides for lining up a facade
- Projects saved in the browser on this machine

## Source

| Path | Role |
| --- | --- |
| `src/lib/beam/gl-mapper.ts` | WebGL projector. Homography fills each quad. |
| `src/lib/beam/math.ts` | Unit-square to quad, and back. |
| `src/lib/beam/project.ts` | Scenes, surfaces, and the facade study. |
| `src/lib/beam/store.ts` | Editor state. |
| `src/components/studio/` | The editor: looks, frame, inspector. |

**Output** opens a display picker in browsers supporting the Window Management API (for example, Chromium with display permission). Pick a display to open a separate projector window, then click **Fullscreen projector** in that window. Browsers without display access offer a window you can move to the projector manually. The editor and projector window share project edits through browser storage. Allow popups for Beamloom and use the same browser profile for both windows. A native Windows shell with project files on disk is still future work.

## License

MIT. See [LICENSE](LICENSE).
