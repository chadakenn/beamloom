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
- **Layer effects:** Select a surface and click **Add layer on top** to put another effect over exactly the same corners. The new layer starts at 65% opacity with Screen blend; choose a different look or import media, then adjust its opacity and blend in the inspector. Move up/down changes draw order.
- **Line up the projector:** Guides, the lineup grid, center cross, and edge ticks help with placement. With Lineup on, corners snap to 10% grid lines; hold Alt to position freely. **Solo** displays only the selected surface, and **Blackout** immediately cuts the output to black.
- **Use scenes:** Add, rename, duplicate, or drag scene tabs to reorder them. Copy a single surface to another scene using the destination picker in its inspector; this keeps its corner positions and settings. Set a duration for each scene and use **Play show** to loop through the tabs. Set **Fade** from a cut to a two-second transition. **Master** dims every surface together, from 0% to 100%, without changing each surface's own brightness. The projector window follows it.
- **Keep alignments:** Save named presets of surface corner positions across the current scenes. Apply a preset to matching surfaces or update it after adjusting the corners.

Press **?** in the editor to see the available keyboard shortcuts. **Undo** and **Redo** are available in the toolbar. **Reset** asks for confirmation before replacing the current show with the sample project.

## Save and move projects

The editor saves the working project in local browser storage on this computer. Use **Save** to download a portable `.beamloom` file that includes the project and its used imported photos and videos. Use **Open** to load that file on another computer. Keep a copy of the file if the show matters: browser storage is tied to that browser and device.

Large videos produce large project files and need enough memory and local storage during import. Opening a project replaces the current editor project; other previously imported clips on the machine are retained. Alignment presets travel with the project. A newly added surface will not have saved corners in an older preset until you update that preset.

## Set up one Raspberry Pi

Beamloom stays on the Windows PC. The Pi does not run the editor. It opens a page from the PC and fills the Epson with that page, so you can line up one projector. Photos, videos, and a show that keeps playing after the PC is off are later steps.

This is included in Beamloom **0.1.4** and later.

### Which Pi

Use a Pi with a desktop and a normal HDMI path to the projector.

| Pi | Use it for Beamloom? | What to know |
| --- | --- | --- |
| Raspberry Pi 5 | Yes. This is the best choice. | 4 GB of memory or more. Official 27 W USB-C power supply. Two micro-HDMI ports. |
| Raspberry Pi 4 Model B | Yes. | 2 GB can run it. 4 GB is more comfortable. Official 15 W USB-C power supply. Two micro-HDMI ports. |
| Raspberry Pi 400 or 500 | Yes. | These are the keyboard models. The live page is the same. Check whether the HDMI plug on that model is micro-HDMI or full-size HDMI. |
| Raspberry Pi 3 | No for this step. | The desktop is too slow for a fullscreen live page. |
| Pi Zero and Pi Zero 2 W | No. | Not enough for this page. |
| Compute Module | No. | Those need a separate carrier board. This guide is for a normal Pi board. |

![Raspberry Pi 5 with its official cooler](docs/pi/pi-5.jpg)

![Raspberry Pi 4 ports, including the two micro-HDMI sockets and the USB-C power port](docs/pi/pi-4-ports.jpg)

### Which operating system

Use **Raspberry Pi OS (64-bit)** with the desktop. The current image is Debian 13, called Trixie. Do not use **Raspberry Pi OS Lite**. Lite has no desktop, so there is no Chromium window to put on the projector. You do not need Ubuntu or any other system for this step.

Use a microSD card of 32 GB or larger. In [Raspberry Pi Imager](https://www.raspberrypi.com/software/) the choices are:

1. **Device:** Raspberry Pi 5, or Raspberry Pi 4 if that is the board you have.
2. **Operating system:** Raspberry Pi OS (64-bit). Pick the desktop image, not Lite.
3. **Storage:** the microSD card. Leave system drives excluded so you do not erase the PC's disk.
4. Open the Imager settings before you write. Set a username and password. If the Pi will join Wi-Fi, enter that network here. A hostname such as `beamloom` makes the Pi easier to recognize later.

Write the card, wait until Imager says it is safe to remove, then put the card in the Pi.

### Cable the Epson

Pi 4 and Pi 5 do not have a full-size HDMI socket. The two small sockets are micro-HDMI. The Epson has a full-size HDMI input. Use a micro-HDMI to HDMI cable. Plug the small end into the Pi port labeled **HDMI0**, next to the USB-C power port. Plug the large end into the Epson.

![The two micro-HDMI ports on a Pi 4](docs/pi/micro-hdmi-ports.jpg)

![A micro-HDMI plug for the Pi and a full-size HDMI plug for the projector](docs/pi/micro-hdmi-cable.jpg)

On the Epson, choose the HDMI input you plugged into. Power the Pi from its official USB-C supply, not from a weak phone charger. The Pi desktop should appear on the projector. Finish the first-boot questions there. Open Chromium once so you know the browser starts. Raspberry Pi OS with the desktop already includes Chromium.

The PC and the Pi must be on the same network. A cable from the Pi's Ethernet port to the router is steadier than Wi-Fi. Wi-Fi is fine if that is how you set the card.

### Turn on live output

1. Install Beamloom 0.1.4 or later on the PC and open it.
2. Click **Pi** in the show bar. The first time, Windows may ask if Beamloom can use the network. Allow it on private networks. If the Pi stays on "Waiting for the PC", allow inbound TCP port **8751** for private networks in Windows Firewall.
3. The show bar prints an address like `http://192.168.1.20:8751/?player=1`. That address is the PC.
4. On the Pi, open Chromium, paste that address, and press **F11** so it covers the desktop.
5. On the PC, drag a surface corner. The Epson should follow. **Master** and **Blackout** follow too. Built-in looks play on the Pi. An imported photo or video still plays only on the PC.

You can open the same address in a browser on the PC before the Pi is ready. That checks the live page without the projector.

Click **Stop Pi** when you are done. While **Pi** is on, anyone on the same network who opens the address can see the looks. They do not get your photo or video files.

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
