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
- Scenes, opacity, soft edge, brightness, contrast, saturation, normal / add / screen blend, lock, and stack order
- Guides for lining up a facade
- A lineup grid, center cross, and edge ticks for aiming the projector. While it is on, a corner snaps to the nearest 10% line. Hold Alt to place it freely.
- Blackout cuts the projector to black without moving the mapping. Press B, or use the Blackout button. The projector window follows.
- Timed scene playlist with per-scene durations and looping playback. Fade mixes the old scene into the next one, from a cut at 0 up to 2 seconds.
- Named alignment presets that save the corners of matching surfaces in all scenes
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

Set the current scene's duration in seconds beside **Play show**. Playback follows the scene tab order and loops back to the first scene; **Pause** holds the current scene. Type a name such as Office or House and choose **Save preset** to keep corner positions for all current scenes. Choose a preset and **Apply** to restore corners on matching surfaces; **Update** replaces its saved positions. Presets are included in the project file. A newly added surface has no position in older presets until you update them.

## Windows

Install [Node.js LTS](https://nodejs.org/) once. Download this repository, extract it, and double-click **Start Beamloom.bat**. The first run installs dependencies and opens `http://127.0.0.1:4173/`. Leave the command window open. Connect the projector, choose **Extend these displays** in Windows, then click **Output** in Beamloom.

The desktop installer does not need Node.js. From a checkout, `npm ci` and `npm run make:win` write `Beamloom Setup.exe` to `out/make/squirrel.windows/x64/`. The **Windows installer** GitHub Actions job also uploads that file. The build is unsigned, so Windows may warn about the publisher until it is signed. The installer uses the Windows display list for projector output.


## License

MIT. See [LICENSE](LICENSE).
