import { useEffect, useState } from "react";
import { Crosshair, Monitor, Plus, RotateCcw, X } from "lucide-react";
import { LOOKS } from "@/lib/beam/looks";
import { connectedDisplays, openProjector, type Display } from "@/lib/beam/displays";
import { activeScene } from "@/lib/beam/project";
import { loadStoredProject, saveStoredProject, snapshot, useEditor } from "@/lib/beam/store";
import { cn } from "@/lib/cn";
import { Inspector } from "@/components/studio/inspector";
import { Library } from "@/components/studio/library";
import { Stage } from "@/components/studio/stage";

type Dock = "looks" | "adjust";

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
  const projectorWindow = new URLSearchParams(window.location.search).has("projector");
  const [picker, setPicker] = useState(false);
  const [displays, setDisplays] = useState<Display[] | null>(null);
  const [displayError, setDisplayError] = useState("");

  useEffect(() => {
    const stored = loadStoredProject();
    if (stored) useEditor.getState().replace(stored);
    if (projectorWindow) setOutput(true);
    setReady(true);
    return useEditor.subscribe((state) => {
      if (!projectorWindow) saveStoredProject(snapshot(state));
    });
  }, []);

  useEffect(() => {
    if (!projectorWindow) return;
    const sync = (event: StorageEvent) => {
      if (event.key !== "beamloom.project.v1" || !event.newValue) return;
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
      if (event.key === "Escape" && useEditor.getState().output && !projectorWindow) {
        setOutput(false);
        if (document.fullscreenElement) void document.exitFullscreen();
        return;
      }
      if (typing) return;
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
      } else if ((event.key === "f" || event.key === "F") && !projectorWindow) {
        void enterOutput();
      } else if (event.key >= "1" && event.key <= "7") {
        const look = LOOKS[Number(event.key) - 1];
        if (look) setArmedLook(look.id);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [nudge, removeSurface, setArmedLook, setGuides, setOutput]);

  useEffect(() => {
    const onFull = () => {
      if (!document.fullscreenElement && !projectorWindow) setOutput(false);
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

  function launch(display?: Display) {
    if (!openProjector(display)) {
      setDisplayError("The browser blocked the projector window. Allow popups for Beamloom and try again.");
      return;
    }
    setPicker(false);
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
            onClick={reset}
            className="inline-flex size-11 items-center justify-center rounded-md border border-line text-muted"
            aria-label="Reset to the facade study"
          >
            <RotateCcw className="size-4" aria-hidden="true" />
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

      {picker && !output ? (
        <div className="absolute inset-0 z-30 grid place-items-center bg-black/70 p-4" role="dialog" aria-modal="true" aria-label="Choose projector display">
          <div className="w-full max-w-md rounded-lg border border-line bg-panel p-5 text-fg">
            <h2 className="font-display text-xl">Choose output display</h2>
            <p className="mt-2 text-sm text-muted">Open a separate projector window. Your editor stays here.</p>
            {displays?.map((display, index) => (
              <button key={`${display.left}:${display.top}:${index}`} type="button" onClick={() => launch(display)} className="mt-3 block w-full rounded-md border border-line p-3 text-left text-sm hover:border-beam">
                {display.label} {display.primary ? "(main display)" : ""} · {display.width} × {display.height}
              </button>
            ))}
            {displayError ? <p role="alert" className="mt-3 text-sm text-beam">{displayError}</p> : null}
            <button type="button" onClick={() => launch()} className="mt-3 block w-full rounded-md border border-line p-3 text-left text-sm">Open window to move manually</button>
            <button type="button" onClick={() => { setPicker(false); void enterOutput(); }} className="mt-3 block w-full rounded-md border border-line p-3 text-left text-sm">Fullscreen on this display</button>
            <button type="button" onClick={() => setPicker(false)} className="mt-3 text-sm text-muted">Cancel</button>
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
          <Stage edit={!output} />
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
          {projectorWindow && !document.fullscreenElement ? <button type="button" onClick={() => void document.getElementById("beamloom-output")?.requestFullscreen()} className="pointer-events-auto mr-2 rounded-md bg-beam px-3 text-sm text-ink">Fullscreen projector</button> : null}
          <button
            type="button"
            onClick={() => {
              if (projectorWindow) { window.close(); return; }
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
