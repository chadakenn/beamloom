# Beamloom

Beamloom is a projection mapping studio for Windows. Add a surface to a projector frame, place its four corners over a wall, window, or other feature, and give it a built-in look, photo, or video. The separate projector window follows changes you make in the editor.

## Get started on Windows

**Desktop installer:** Download the `Beamloom-Windows-Installer` artifact from a completed **Windows installer** GitHub Actions run, extract it, and run `Beamloom Setup.exe`. This version does not require Node.js. The installer is unsigned, so Windows may display a publisher warning. Connect your projector and set Windows to **Extend these displays**, then use **Output** in Beamloom to choose the display.

**From source:** Install [Node.js LTS](https://nodejs.org/) (version 22 or newer), download and extract this repository, and double-click `Start Beamloom.bat`. The first launch installs dependencies and opens `http://127.0.0.1:4173/`. Keep the command window open while using Beamloom. If the browser cannot pick the projector automatically, open the output window, move it to the projector display, and make it fullscreen. Allow popups; fullscreen may need a click inside the output window.

For a quick office test, start with one projector or a second display. Add a surface, choose a look, drag its corners to fit something in the image, then try **Lineup** and **Blackout** before building a longer show.

## Build a show

- **Map surfaces:** Drag the four corners or enter their positions as percentages in the inspector. Choose a built-in look, import a PNG/JPEG, or import a video. Imported videos support play/pause, sound, loop, and scrubbing.
- **Shape the output:** Choose Full, Window, or Arch masking; adjust the shared soft edge, opacity, brightness, contrast, saturation, and blend mode. Lock a surface to prevent accidental corner moves, or change its stacking order. Window and Arch use fixed mask shapes within the quad.
- **Line up the projector:** Guides, the lineup grid, center cross, and edge ticks help with placement. With Lineup on, corners snap to 10% grid lines; hold Alt to position freely. **Solo** displays only the selected surface, and **Blackout** immediately cuts the output to black.
- **Use scenes:** Add, rename, duplicate, or drag scene tabs to reorder them. Copy a single surface to another scene using the destination picker in its inspector; this keeps its corner positions and settings. Set a duration for each scene and use **Play show** to loop through the tabs. Set **Fade** from a cut to a two-second transition.
- **Keep alignments:** Save named presets of surface corner positions across the current scenes. Apply a preset to matching surfaces or update it after adjusting the corners.

Press **?** in the editor to see the available keyboard shortcuts. **Undo** and **Redo** are available in the toolbar. **Reset** asks for confirmation before replacing the current show with the sample project.

## Save and move projects

The editor saves the working project in local browser storage on this computer. Use **Save** to download a portable `.beamloom` file that includes the project and its used imported photos and videos. Use **Open** to load that file on another computer. Keep a copy of the file if the show matters: browser storage is tied to that browser and device.

Large videos produce large project files and need enough memory and local storage during import. Opening a project replaces the current editor project; other previously imported clips on the machine are retained. Alignment presets travel with the project. A newly added surface will not have saved corners in an older preset until you update that preset.

## Pi projector players: planned direction

The goal is to edit shows on a Windows PC and use a Raspberry Pi at each projector. **Live setup** would send changes from the PC to the projector while adjusting surfaces. **Show playback** would transfer the show and media to the Pi for local playback without requiring the PC to stay connected. Multiple Pi players would eventually stay in sync, with the PC providing controls and status. These Pi modes are a design goal; they are not part of the current Windows app.

## Develop from source

```bash
npm ci
npm run dev
```

The development server listens on `http://127.0.0.1:4173/`. Run `npm run build` to type-check and build the web app. On Windows, `npm run make:win` builds the desktop installer in `out/make/squirrel.windows/x64/`. The **Windows installer** workflow can also be started manually in GitHub Actions; it uploads the installer as an artifact.

| Path | Purpose |
| --- | --- |
| `src/lib/beam/project.ts` | Project, scenes, surfaces, and saved project data |
| `src/lib/beam/store.ts` | Editor actions and undo history |
| `src/lib/beam/gl-mapper.ts` | WebGL rendering, quad mapping, and masks |
| `src/lib/beam/clips.ts` | Imported media and playback |
| `src/lib/beam/project-file.ts` | Portable project save/open |
| `src/lib/beam/displays.ts` | Projector display selection |
| `src/components/studio/` | Editor, projector frame, and inspector |
| `electron/` | Windows desktop window and display integration |

Beamloom's interface, looks, and mapping code are original to this project. Do not add assets, presets, or decompiled code from commercial mapping tools.

## License

MIT. See [LICENSE](LICENSE).
