# Beamloom

Beamloom is a projection mapping studio for Windows. Add a surface to a projector frame, place its four corners over a wall, window, or other feature, and give it a built-in look, photo, or video. The separate projector window follows changes you make in the editor.

## Get started on Windows

**Desktop installer:** Download `Beamloom Setup.exe` from the latest [GitHub release](https://github.com/chadakenn/beamloom/releases), or from the `Beamloom-Windows-Installer` artifact on a completed **Windows installer** run. This version does not require Node.js. The installer is unsigned, so Windows may display a publisher warning. Connect your projector and set Windows to **Extend these displays**, then use **Output** in Beamloom to choose the display.

An installed copy checks for a newer release a few seconds after it opens, then again every 30 minutes. When one exists, a bar at the top of the editor offers **Update**. The download starts only after you click it, and **Restart** appears when it is ready. The project saved on this computer stays put. `Start Beamloom.bat` does not update itself. The first install of a build that shows this bar still has to be done by hand.

**From source:** Install [Node.js LTS](https://nodejs.org/) (version 22 or newer), download and extract this repository, and double-click `Start Beamloom.bat`. The first launch installs dependencies and opens `http://127.0.0.1:4173/`. Keep the command window open while using Beamloom. If the browser cannot pick the projector automatically, open the output window, move it to the projector display, and make it fullscreen. Allow popups; fullscreen may need a click inside the output window.

For a quick office test, start with one projector or a second display. Add a surface, choose a look, drag its corners to fit something in the image, then try **Lineup** and **Blackout** before building a longer show.

## Build a show

- **Map surfaces:** Drag the four corners or enter their positions as percentages in the inspector. Choose a built-in look, import a PNG/JPEG, or import a video. Imported videos support play/pause, sound, loop, and scrubbing.
- **Shape the output:** Choose Full, Window, or Arch masking; adjust that surface's soft edge, opacity, brightness, contrast, saturation, and blend mode. Lock a surface to prevent accidental corner moves, or change its stacking order. Window and Arch use fixed mask shapes within the quad.
- **Line up the projector:** Guides, the lineup grid, center cross, and edge ticks help with placement. With Lineup on, corners snap to 10% grid lines; hold Alt to position freely. **Solo** displays only the selected surface, and **Blackout** immediately cuts the output to black.
- **Use scenes:** Add, rename, duplicate, or drag scene tabs to reorder them. Copy a single surface to another scene using the destination picker in its inspector; this keeps its corner positions and settings. Set a duration for each scene and use **Play show** to loop through the tabs. Set **Fade** from a cut to a two-second transition. **Master** dims every surface together, from 0% to 100%, without changing each surface's own brightness. The projector window follows it.
- **Keep alignments:** Save named presets of surface corner positions across the current scenes. Apply a preset to matching surfaces or update it after adjusting the corners.

Press **?** in the editor to see the available keyboard shortcuts. **Undo** and **Redo** are available in the toolbar. **Reset** asks for confirmation before replacing the current show with the sample project.

## Save and move projects

The editor saves the working project in local browser storage on this computer. Use **Save** to download a portable `.beamloom` file that includes the project and its used imported photos and videos. Use **Open** to load that file on another computer. Keep a copy of the file if the show matters: browser storage is tied to that browser and device.

Large videos produce large project files and need enough memory and local storage during import. Opening a project replaces the current editor project; other previously imported clips on the machine are retained. Alignment presets travel with the project. A newly added surface will not have saved corners in an older preset until you update that preset.

## Set up one Raspberry Pi

Beamloom stays on the Windows PC. The Pi does not run the editor. It opens a page from the PC and shows that page on the Epson. This is for lining up one projector. Photos, videos, and a show that keeps playing after the PC is turned off are not part of this step yet.

This is not in the 0.1.3 installer. Use a build published after this change.

### What you need

- A Raspberry Pi 4 or Pi 5, its power supply, and a microSD card.
- A monitor cable from the Pi to the Epson. Use the HDMI port on the Pi and the HDMI input on the projector.
- The PC and the Pi on the same home network. Ethernet is steadier than Wi-Fi, but either works.

### Prepare the Pi

1. On the PC, install [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2. Choose **Raspberry Pi OS (64-bit)**, the desktop version, and write it to the microSD card. In Imager's settings, set a username and password. If the Pi will use Wi-Fi, enter that network here too.
3. Put the card in the Pi, connect the Epson's HDMI input, and power the Pi on.
4. On the Epson, select the HDMI input that the Pi is plugged into. You should see the Raspberry Pi desktop on the projector. Finish the first-boot questions on that desktop.
5. Open Chromium on the Pi once, so you know the browser is there. Raspberry Pi OS desktop includes it.

### Turn on live output

1. Install and open Beamloom on the PC.
2. The first time you click **Pi**, Windows may ask whether Beamloom can use the network. Allow it on private networks. If the Pi stays on "Waiting for the PC", allow inbound TCP port **8751** for private networks in Windows Firewall.
3. In Beamloom's show bar, click **Pi**. The bar shows an address like `http://192.168.1.20:8751/?player=1`. That address is the PC, not the Pi.
4. On the Pi, open Chromium and go to that exact address. Press **F11** so the page fills the projector.
5. On the PC, drag a surface corner. The projector should follow. **Master** and **Blackout** follow too. Built-in looks play on the Pi. An imported photo or video still plays only on the PC.

You can open the same address in a browser on the PC before the Pi is ready. That checks the live page without the projector.

Click **Stop Pi** when you are finished. While **Pi** is on, anyone on the same network who opens the address can see the looks. They do not get your photo or video files.

A second Pi, copying the show onto the Pi, and playback with the PC switched off are later steps.

## Develop from source

```bash
npm ci
npm run dev
```

The development server listens on `http://127.0.0.1:4173/`. Run `npm run build` to type-check and build the web app. On Windows, `npm run make:win` builds the desktop installer in `out/make/squirrel.windows/x64/`. The **Windows installer** workflow can also be started manually in GitHub Actions; it uploads the installer as an artifact. **Publish Windows release** uploads that installer, `RELEASES`, and the `.nupkg` to a GitHub Release. The release tag must be the version in `package.json`, such as `0.1.1`, with no `v` in front.

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
