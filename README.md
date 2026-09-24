# Beamloom

Original projection-mapping studio.

## Open on Windows

1. Install [Node.js LTS](https://nodejs.org/) once (include npm during installation).
2. Download this repository from GitHub (**Code → Download ZIP**) and extract the ZIP to a folder. Do not run it inside the ZIP.
3. Double-click **Start Beamloom.bat**. On the first run it installs dependencies; later launches reuse them. Leave the command window open while using Beamloom. Your browser opens at `http://127.0.0.1:4173/` when the server is ready.
4. Connect the projector and select **Extend these displays** in Windows display settings. In Beamloom click **Output**, pick the projector, and click **Fullscreen projector** in the output window.

The first run needs internet access. Your projects and imported clips stay in this browser profile; use **Save** to keep a portable copy. To stop the app, close the command window. If Windows asks about network access, local use only needs loopback (`127.0.0.1`).

Developers can use `npm ci`, `npm run dev`, and `npm run build`.

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
| `src/lib/beam/project-file.ts` | Save and open a portable project. |
| `src/lib/beam/displays.ts` | Display list and the projector window. |
| `src/components/studio/` | The editor: looks, frame, inspector. |

**Output** opens a display picker. Where the browser allows it, pick a display and Beamloom opens a separate projector window. Otherwise, open a window and move it onto the projector, or go fullscreen on this display. The projector window follows edits from the editor. Allow popups for Beamloom. Fullscreen inside that window still needs one click there.

Use **Save** to download a portable `.beamloom` project file, including videos used by its surfaces. Use **Open** to restore that file on another computer. Large videos make the file large; the browser needs enough memory and local storage to import them. Opening a file replaces the current editor project but leaves other imported videos in the browser.

The launcher runs a local browser app. A packaged Windows executable is still later.

## License

MIT. See [LICENSE](LICENSE).
