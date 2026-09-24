# Beamloom

Original projection-mapping studio.

Beamloom places light on real surfaces. You drop a surface on a 16:9 projector frame, assign a look, and drag the corners until the picture sits on the wall, pier, or object. **Output** sends that frame to the display feeding your projector.

The name, interface, looks, and warp math are written for this project. This is not a copy of any commercial mapping tool. Do not add their assets, presets, or decompiled code.

## What the studio does

- Perspective warp of each surface onto the projector frame
- Looks: tungsten wash, scan loom, lattice, ember lift, halo rings, columns, and gels
- Import your own video files and map them onto a surface. Clips stay on this machine.
- Import a PNG or JPEG and map it the same way. Stills are saved inside the project file.
- Play, pause, unmute, loop, and scrub an imported video. Playback stays on this machine.
- Scenes, opacity, soft edge, normal / add / screen blend, lock, and stack order
- Guides for lining up a facade
- A lineup grid, center cross, and edge ticks for aiming the projector
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

Use **Save** to download a portable `.beamloom` project file, including videos and still images used by its surfaces. Use **Open** to restore that file on another computer. Large videos make the file large; the browser needs enough memory and local storage to import them. Opening a file replaces the current editor project but leaves other imported videos in the browser.

## Windows desktop app

The Electron build opens Beamloom as a desktop app and uses Windows' display list for projector output. A Windows build uses `npm ci` and `npm run make:win`; the installer appears in `out/make/squirrel.windows/x64/`. The **Windows installer** GitHub Actions job also attaches the setup executable to its run. This build is unsigned, so Windows may show a publisher warning until code signing is configured. Keep the source launcher for development; people using the installer do not need Node.js.

## License

MIT. See [LICENSE](LICENSE).
