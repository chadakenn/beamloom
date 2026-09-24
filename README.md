# Beamloom

Original projection-mapping studio.

Beamloom places light on real surfaces. You drop a surface on a 16:9 projector frame, assign a look, and drag the corners until the picture sits on the wall, pier, or object. **Output** sends that frame to the display feeding your projector.

The name, interface, looks, and warp math are written for this project. This is not a copy of any commercial mapping tool. Do not add their assets, presets, or decompiled code.

## What the studio does

- Perspective warp of each surface onto the projector frame
- Looks: tungsten wash, scan loom, lattice, ember lift, halo rings, columns, and gels
- Import your own video files and map them onto a surface. Clips stay on this machine.
- Play, pause, unmute, loop, and scrub an imported video. Playback stays on this machine.
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
| `src/lib/beam/clips.ts` | Local video files and playback. |
| `src/lib/beam/displays.ts` | Display list and the projector window. |
| `src/components/studio/` | The editor: looks, frame, inspector. |

**Output** opens a display picker. Where the browser allows it, pick a display and Beamloom opens a separate projector window. Otherwise, open a window and move it onto the projector, or go fullscreen on this display. The projector window follows edits from the editor. Allow popups for Beamloom. Fullscreen inside that window still needs one click there.

A native Windows shell with project files on disk is still later.

## License

MIT. See [LICENSE](LICENSE).
