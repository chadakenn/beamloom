import { useEffect, useRef, useState } from "react";
import { Crosshair, Download, FolderOpen, Grid2x2, Monitor, Plus, RotateCcw, X } from "lucide-react";
import { LOOKS } from "@/lib/beam/looks";
import { CLIP_CHANGE_KEY, restoreClips, syncClips } from "@/lib/beam/clips";
import { openProjectFile, saveProjectFile } from "@/lib/beam/project-file";
import { connectedDisplays, openProjector, type Display } from "@/lib/beam/displays";
import { activeScene, STORAGE_KEY } from "@/lib/beam/project";
import { loadStoredProject, saveStoredProject, snapshot, useEditor } from "@/lib/beam/store";
import { cn } from "@/lib/cn";
import { Inspector } from "@/components/studio/inspector";
import { Library } from "@/components/studio/library";
import { Stage } from "@/components/studio/stage";

type Dock = "looks" | "adjust";
const LINEUP_KEY = "beamloom.lineup.v1";

export function Studio() {
  const name = useEditor((s) => s.name);
  const scenes = useEditor((s) => s.scenes);
  const activeSceneId = useEditor((s) => s.activeSceneId);
  const guides = useEditor((s) => s.guides);
  const output = useEditor((s) => s.output);
  const setName = useEditor((s) => s.setName);
  const setScene = useEditor((s) => s.setScene);
  const addScene = useEditor((s) => s.addScene);
  const setGuides = useEditor((s) => s.setGuides);
  const setOutput = useEditor((s) => s.setOutput);
  const reset = useEditor((s) => s.reset);
  const nudge = useEditor((s) => s.nudge);
  const removeSurface = useEditor((s) => s.removeSurface);
  const setArmedLook = useEditor((s) => s.setArmedLook);
  const selectedId = useEditor((s) => s.selectedId);
  const [dock, setDock] = useState<Dock>("looks");
  const [chrome, setChrome] = useState(true);
  const [ready, setReady] = useState(false);
  const [picker, setPicker] = useState(false);
  const [displays, setDisplays] = useState<Display[] | null>(null);
  const [displayError, setDisplayError] = useState("");
  const [projectorWindow, setProjectorWindow] = useState(false);
  const [covering, setCovering] = useState(false);
  const projectorRef = useRef(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const [fileBusy, setFileBusy] = useState(false);
  const [fileMessage, setFileMessage] = useState("");
  const [lineup, setLineup] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);

  function toggleLineup() {
    const next = !lineup;
    setLineup(next);
    try {
      localStorage.setItem(LINEUP_KEY, next ? "1" : "0");
    } catch {
      /* the overlay still shows in this window */
    }
  }

  useEffect(() => {
    try {
      setLineup(localStorage.getItem(LINEUP_KEY) === "1");
    } catch {
      /* ignore */
    }
    const sync = (event: StorageEvent) => {
      if (event.key === LINEUP_KEY) setLineup(event.newValue === "1");
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, []);

  useEffect(() => {
    const isProjector = new URLSearchParams(window.location.search).has("projector");
    projectorRef.current = isProjector;
    setProjectorWindow(isProjector);
    void restoreClips();
    const stored = loadStoredProject();
    if (stored) useEditor.getState().replace(stored);
    if (isProjector) setOutput(true);
    setReady(true);
    return useEditor.subscribe((state) => {
      if (!projectorRef.current) saveStoredProject(snapshot(state));
    });
  }, [setOutput]);

  useEffect(() => {
    if (!projectorWindow) return;
    const sync = (event: StorageEvent) => {
      if (event.key === CLIP_CHANGE_KEY) {
        void syncClips();
        return;
      }
      if (event.key !== STORAGE_KEY || !event.newValue) return;
      const stored = loadStoredProject();
      if (stored) useEditor.getState().replace(stored);
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, [projectorWindow]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable;
      if (event.key === "Escape" && shortcutsOpen) {
        setShortcutsOpen(false);
        return;
      }
      if (event.key === "Escape" && picker) {
        setPicker(false);
        return;
      }
      if (event.key === "Escape" && useEditor.getState().output && !projectorRef.current) {
        setOutput(false);
        if (document.fullscreenElement) void document.exitFullscreen();
        return;
      }
      if (typing) return;
      if (event.key === "?" && !projectorRef.current) {
        event.preventDefault();
        setShortcutsOpen((open) => !open);
        return;
      }
      if (shortcutsOpen) return;
      const step = event.shiftKey ? 0.02 : 0.006;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        nudge(-step, 0);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        nudge(step, 0);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        nudge(0, -step);
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        nudge(0, step);
      } else if (event.key === "Delete" || event.key === "Backspace") {
        const id = useEditor.getState().selectedId;
        if (id) {
          event.preventDefault();
          removeSurface(id);
        }
      } else if (event.key === "g" || event.key === "G") {
        setGuides(!useEditor.getState().guides);
      } else if ((event.key === "f" || event.key === "F") && !projectorRef.current) {
        void enterOutput();
      } else if (event.key >= "1" && event.key <= "7") {
        const look = LOOKS[Number(event.key) - 1];
        if (look) setArmedLook(look.id);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [nudge, picker, removeSurface, setArmedLook, setGuides, setOutput, shortcutsOpen]);

  useEffect(() => {
    const onFull = () => {
      const active = Boolean(document.fullscreenElement);
      setCovering(active);
      if (!active && !projectorRef.current) setOutput(false);
    };
    document.addEventListener("fullscreenchange", onFull);
    return () => document.removeEventListener("fullscreenchange", onFull);
  }, [setOutput]);

  useEffect(() => {
    if (!output) return;
    setChrome(true);
    let timer = window.setTimeout(() => setChrome(false), 1800);
    const wake = () => {
      setChrome(true);
      window.clearTimeout(timer);
      timer = window.setTimeout(() => setChrome(false), 1800);
    };
    window.addEventListener("pointermove", wake);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("pointermove", wake);
    };
  }, [output]);

  async function enterOutput() {
    setOutput(true);
    const node = document.getElementById("beamloom-output");
    if (!node) return;
    try {
      await node.requestFullscreen();
    } catch {
      /* iframe preview stays in the in-app output frame */
    }
  }

  async function chooseDisplay() {
    setPicker(true);
    setDisplayError("");
    try {
      setDisplays(await connectedDisplays());
    } catch {
      setDisplays(null);
      setDisplayError("Display access was denied. You can still move the projector window manually.");
    }
  }

  async function launch(display?: Display) {
    if (!(await openProjector(display))) {
      setDisplayError("The browser blocked the projector window. Allow popups for Beamloom and try again.");
      return;
    }
    setPicker(false);
  }

  async function saveFile() {
    setFileBusy(true);
    setFileMessage("");
    try {
      await saveProjectFile(snapshot(useEditor.getState()));
      setFileMessage("Saved the project file.");
    } catch (error) {
      setFileMessage(error instanceof Error ? error.message : "Could not save the project.");
    } finally {
      setFileBusy(false);
    }
  }

  async function openFile(file: File) {
    setFileBusy(true);
    setFileMessage("");
    try {
      const project = await openProjectFile(file);
      useEditor.getState().replace(project);
      setFileMessage(`Opened ${project.name}`);
    } catch (error) {
      setFileMessage(error instanceof Error ? error.message : "Could not open the project.");
    } finally {
      setFileBusy(false);
    }
  }

  const scene = useEditor((s) => activeScene(s));

  return (
    <div id="beamloom-output" className="relative flex h-dvh flex-col bg-bg text-fg">
      {output ? null : (
        <header className="flex h-14 shrink-0 items-center gap-2 border-b border-line px-3">
          <div className="flex items-center gap-2 pr-1">
            <span className="grid size-8 place-items-center rounded-md bg-beam text-ink" aria-hidden="true">
              <span className="block h-3 w-3 rotate-45 border-2 border-ink" />
            </span>
            <span className="font-display text-lg font-semibold leading-none">Beamloom</span>
          </div>
          <input
            aria-label="Project name"
            value={name}
            maxLength={48}
            onChange={(event) => setName(event.target.value)}
            className="hidden h-11 min-w-0 flex-1 rounded-md bg-transparent px-2 text-sm text-fg sm:block"
          />
          <div className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto sm:flex-none">
            {scenes.map((item) => (
              <button
                key={item.id}
                type="button"
                aria-pressed={item.id === activeSceneId}
                onClick={() => setScene(item.id)}
                className={cn(
                  "h-11 shrink-0 rounded-md px-3 text-sm",
                  item.id === activeSceneId ? "bg-panel text-fg" : "text-muted",
                )}
              >
                {item.name}
              </button>
            ))}
            <button
              type="button"
              aria-label="Add scene"
              onClick={addScene}
              className="inline-flex size-11 shrink-0 items-center justify-center text-muted"
            >
              <Plus className="size-4" aria-hidden="true" />
            </button>
          </div>
          <button
            type="button"
            aria-pressed={guides}
            onClick={() => setGuides(!guides)}
            className={cn(
              "inline-flex size-11 items-center justify-center rounded-md border",
              guides ? "border-beam text-beam" : "border-line text-muted",
            )}
            aria-label={guides ? "Hide guides" : "Show guides"}
          >
            <Crosshair className="size-4" aria-hidden="true" />
          </button>
          <button
            type="button"
            aria-pressed={lineup}
            onClick={toggleLineup}
            className={cn(
              "inline-flex h-11 items-center gap-2 rounded-md border px-2 text-sm",
              lineup ? "border-beam text-beam" : "border-line text-muted",
            )}
            aria-label={lineup ? "Turn lineup off" : "Turn lineup on"}
          >
            <Grid2x2 className="size-4" aria-hidden="true" />
            <span className="hidden xl:inline">Lineup</span>
          </button>
          <button
            type="button"
            onClick={() => setShortcutsOpen(true)}
            className="inline-flex size-11 items-center justify-center rounded-md border border-line text-lg font-medium text-muted"
            aria-label="Keyboard shortcuts"
            title="Keyboard shortcuts (?)"
          >
            ?
          </button>
          <button
            type="button"
            onClick={reset}
            className="inline-flex size-11 items-center justify-center rounded-md border border-line text-muted"
            aria-label="Reset to the facade study"
          >
            <RotateCcw className="size-4" aria-hidden="true" />
          </button>
          <input
            ref={fileInput}
            type="file"
            accept=".beamloom,application/json"
            className="sr-only"
            aria-label="Select Beamloom project file"
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (file) void openFile(file);
            }}
          />
          <button
            type="button"
            disabled={fileBusy}
            onClick={() => fileInput.current?.click()}
            className="inline-flex h-11 items-center gap-1 rounded-md border border-line px-2 text-sm text-fg disabled:opacity-50"
            aria-label="Open project file"
          >
            <FolderOpen className="size-4" aria-hidden="true" />
            <span className="hidden xl:inline">Open</span>
          </button>
          <button
            type="button"
            disabled={fileBusy}
            onClick={() => void saveFile()}
            className="inline-flex h-11 items-center gap-1 rounded-md border border-line px-2 text-sm text-fg disabled:opacity-50"
            aria-label="Save project file"
          >
            <Download className="size-4" aria-hidden="true" />
            <span className="hidden xl:inline">Save</span>
          </button>
          <button
            type="button"
            onClick={() => void chooseDisplay()}
            className="inline-flex h-11 items-center gap-2 rounded-md bg-beam px-3 text-sm font-medium text-ink"
          >
            <Monitor className="size-4" aria-hidden="true" />
            <span className="hidden sm:inline">Output</span>
          </button>
        </header>
      )}
      {shortcutsOpen && !output ? <ShortcutCard onClose={() => setShortcutsOpen(false)} /> : null}
      {fileMessage && !output ? (
        <div role="status" className="absolute bottom-3 left-3 z-30 max-w-sm rounded-md border border-line bg-panel px-3 py-2 text-sm text-fg">
          {fileMessage}
          <button type="button" onClick={() => setFileMessage("")} className="ml-3 h-11 text-muted" aria-label="Dismiss message">
            Close
          </button>
        </div>
      ) : null}

      {picker && !output ? (
        <div
          className="absolute inset-0 z-30 grid place-items-center bg-black/70 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Choose projector display"
        >
          <div className="w-full max-w-md rounded-lg border border-line bg-panel p-5 text-fg">
            <h2 className="font-display text-xl">Choose output display</h2>
            <p className="mt-2 text-sm text-muted">Open a separate projector window. Your editor stays here.</p>
            {displays?.map((display, index) => (
              <button
                key={`${display.left}:${display.top}:${index}`}
                type="button"
                onClick={() => void launch(display)}
                className="mt-3 block min-h-11 w-full rounded-md border border-line p-3 text-left text-sm"
              >
                {display.label}
                {display.primary ? " (main display)" : ""} · {display.width} × {display.height}
              </button>
            ))}
            {displayError ? (
              <p role="alert" className="mt-3 text-sm text-beam">
                {displayError}
              </p>
            ) : null}
            <button
              type="button"
              onClick={() => void launch()}
              className="mt-3 block min-h-11 w-full rounded-md border border-line p-3 text-left text-sm"
            >
              Open window to move manually
            </button>
            <button
              type="button"
              onClick={() => {
                setPicker(false);
                void enterOutput();
              }}
              className="mt-3 block min-h-11 w-full rounded-md border border-line p-3 text-left text-sm"
            >
              Fullscreen on this display
            </button>
            <button type="button" onClick={() => setPicker(false)} className="mt-3 h-11 text-sm text-muted">
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      <div className={cn("flex min-h-0 flex-1", output ? "flex-col" : "flex-col lg:flex-row")}>
        {output ? null : (
          <aside className="hidden w-64 shrink-0 overflow-auto border-r border-line bg-panel lg:block">
            <Library />
          </aside>
        )}
        <main className={cn("relative min-w-0", output ? "min-h-0 flex-1" : "aspect-video shrink-0 lg:aspect-auto lg:min-h-0 lg:flex-1")}>
          <Stage edit={!output} lineup={lineup} />
        </main>
        {output ? null : (
          <aside className="hidden w-80 shrink-0 overflow-auto border-l border-line bg-panel lg:block">
            <Inspector />
          </aside>
        )}
        {output ? null : (
          <section className="flex min-h-0 flex-1 flex-col border-t border-line bg-panel lg:hidden">
            <div className="flex shrink-0 border-b border-line">
              <DockTab current={dock} id="looks" label="Looks" onSelect={setDock} />
              <DockTab current={dock} id="adjust" label="Adjust" onSelect={setDock} />
            </div>
            <div className="min-h-0 flex-1 overflow-auto">
              {dock === "looks" ? <Library /> : <Inspector />}
            </div>
          </section>
        )}
      </div>

      {output && chrome ? (
        <div className="pointer-events-none absolute inset-x-0 top-0 z-20 flex justify-end p-3">
          {projectorWindow && !covering ? (
            <button
              type="button"
              onClick={() => void document.getElementById("beamloom-output")?.requestFullscreen()}
              className="pointer-events-auto mr-2 inline-flex h-11 items-center rounded-md bg-beam px-3 text-sm font-medium text-ink"
            >
              Fullscreen projector
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => {
              if (projectorWindow) {
                window.close();
                return;
              }
              setOutput(false);
              if (document.fullscreenElement) void document.exitFullscreen();
            }}
            className="pointer-events-auto inline-flex h-11 items-center gap-2 rounded-md bg-panel px-3 text-sm text-fg"
          >
            <X className="size-4" aria-hidden="true" />
            Close output
          </button>
        </div>
      ) : null}
      <span className="sr-only">
        {ready ? `${scene.name}, ${scene.surfaces.length} surfaces` : "Loading project"}
        {selectedId ? "" : ""}
      </span>
    </div>
  );
}

function ShortcutCard({ onClose }: { onClose: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);

  return (
    <dialog
      ref={dialogRef}
      onCancel={onClose}
      onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}
      aria-labelledby="shortcut-title"
      className="max-h-[85dvh] w-[min(92vw,28rem)] overflow-y-auto rounded-lg border border-line bg-panel p-5 text-fg shadow-2xl backdrop:bg-black/75"
    >
      <div className="flex items-center justify-between gap-4">
        <h2 id="shortcut-title" className="font-display text-xl font-semibold">Keyboard shortcuts</h2>
        <button type="button" onClick={onClose} className="inline-flex size-11 items-center justify-center rounded-md border border-line" aria-label="Close shortcuts"><X className="size-4" aria-hidden="true" /></button>
      </div>
      <dl className="mt-3 space-y-2 text-sm">
        <Shortcut keys="Arrow keys" action="Nudge selected surface" />
        <Shortcut keys="Shift + Arrow keys" action="Nudge farther" />
        <Shortcut keys="Delete / Backspace" action="Remove selected surface" />
        <Shortcut keys="G" action="Toggle editor guides" />
        <Shortcut keys="F" action="Fullscreen output on this display" />
        {LOOKS.map((look, index) => <Shortcut key={look.id} keys={String(index + 1)} action={look.name} />)}
        <Shortcut keys="?" action="Show or hide this card" />
        <Shortcut keys="Esc" action="Close card, picker, or output" />
      </dl>
      <p className="mt-4 text-xs text-muted">Shortcuts pause while you type in a field.</p>
    </dialog>
  );
}

function Shortcut({ keys, action }: { keys: string; action: string }) {
  return <div className="flex items-center justify-between gap-3 border-b border-line py-1"><dt>{action}</dt><dd className="shrink-0 rounded border border-line px-2 py-1 font-mono text-xs text-beam">{keys}</dd></div>;
}

function DockTab({
  current,
  id,
  label,
  onSelect,
}: {
  current: Dock;
  id: Dock;
  label: string;
  onSelect: (id: Dock) => void;
}) {
  const active = current === id;
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={() => onSelect(id)}
      className={cn(
        "h-11 flex-1 text-sm",
        active ? "text-beam" : "text-muted",
      )}
    >
      {label}
    </button>
  );
}
