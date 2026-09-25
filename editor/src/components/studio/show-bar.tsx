import { useEffect, useState, useSyncExternalStore } from "react";
import { Pause, Play } from "lucide-react";
import { getFadeSeconds, setFadeSeconds, subscribeFade } from "@/lib/beam/fade";
import { getMaster, setMaster, subscribeMaster } from "@/lib/beam/master";
import { liveRunning, liveUrls, startLive, stopLive, subscribeLive } from "@/lib/beam/live-link";
import { activeScene } from "@/lib/beam/project";
import { useEditor } from "@/lib/beam/store";

export function ShowBar() {
  const scene = useEditor((s) => activeScene(s));
  const sceneCount = useEditor((s) => s.scenes.length);
  const playing = useEditor((s) => s.playlistPlaying);
  const setPlaying = useEditor((s) => s.setPlaylistPlaying);
  const setDuration = useEditor((s) => s.setSceneDuration);
  const alignments = useEditor((s) => s.alignments);
  const saveAlignment = useEditor((s) => s.saveAlignment);
  const applyAlignment = useEditor((s) => s.applyAlignment);
  const updateAlignment = useEditor((s) => s.updateAlignment);
  const deleteAlignment = useEditor((s) => s.deleteAlignment);
  const [seconds, setSeconds] = useState(String(scene.durationSeconds));
  const [presetName, setPresetName] = useState("");
  const [selectedPreset, setSelectedPreset] = useState("");
  const [message, setMessage] = useState("");
  const [piHost, setPiHost] = useState(() => localStorage.getItem("beamloom-pi-host") || "beamloom.local");
  const [piStatus, setPiStatus] = useState<Awaited<ReturnType<NonNullable<NonNullable<Window["beamloomDesktop"]>["piStatus"]>>>>(null);
  const [updatingPi, setUpdatingPi] = useState(false);
  const fade = useSyncExternalStore(subscribeFade, getFadeSeconds, () => 0);
  const master = useSyncExternalStore(subscribeMaster, getMaster, () => 1);
  const piOn = useSyncExternalStore(subscribeLive, liveRunning, () => false);
  const piUrls = useSyncExternalStore(subscribeLive, liveUrls, () => [] as string[]);

  useEffect(() => setSeconds(String(scene.durationSeconds)), [scene.id, scene.durationSeconds]);
  useEffect(() => {
    localStorage.setItem("beamloom-pi-host", piHost);
    if (!window.beamloomDesktop?.piStatus) return;
    let active = true;
    const refresh = () => { void window.beamloomDesktop?.piStatus?.(piHost).then((status) => { if (active) setPiStatus(status); }); };
    refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => { active = false; window.clearInterval(timer); };
  }, [piHost]);

  async function updatePi() {
    if (!window.confirm(`Update the Beamloom player on ${piHost}? Its output may briefly disconnect.`)) return;
    setUpdatingPi(true);
    const result = await window.beamloomDesktop?.piUpdate?.(piHost);
    setUpdatingPi(false);
    setMessage(result?.error ?? (result?.started ? "Pi update started; watch its status below." : "Pi update is already running."));
  }
  useEffect(() => {
    if (selectedPreset && !alignments.some((preset) => preset.id === selectedPreset)) {
      setSelectedPreset(alignments[0]?.id ?? "");
    }
  }, [alignments, selectedPreset]);

  function commitSeconds() {
    const value = Number(seconds);
    if (Number.isFinite(value) && seconds.trim()) setDuration(scene.id, value);
    setSeconds(String(useEditor.getState().scenes.find((item) => item.id === scene.id)?.durationSeconds ?? 10));
  }

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-line bg-panel px-3 py-1.5 text-sm text-fg" aria-label="Show and alignment controls">
      <button type="button" disabled={sceneCount < 2} onClick={() => setPlaying(!playing)} className="inline-flex h-10 shrink-0 items-center gap-1 rounded-md border border-line px-3 disabled:opacity-40" aria-label={playing ? "Pause scene playlist" : "Play scene playlist"}>
        {playing ? <Pause className="size-4" aria-hidden="true" /> : <Play className="size-4" aria-hidden="true" />}
        {playing ? "Pause" : "Play show"}
      </button>
      <label className="flex shrink-0 items-center gap-1 text-muted">
        <span>{scene.name}:</span>
        <input type="number" min="1" max="3600" step="1" value={seconds} onChange={(event) => setSeconds(event.target.value)} onBlur={commitSeconds} onKeyDown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); }} aria-label="Scene duration in seconds" className="h-10 w-16 rounded-md border border-line bg-bg px-2 text-fg" />
        <span>sec</span>
      </label>
      <label className="flex shrink-0 items-center gap-2 text-muted">
        <span>Fade</span>
        <input
          className="h-10 w-24"
          type="range"
          min={0}
          max={2}
          step={0.1}
          value={fade}
          aria-label="Scene fade"
          onChange={(event) => setFadeSeconds(Number(event.target.value))}
        />
        <span className="w-10 tabular-nums text-fg">{fade === 0 ? "Cut" : `${fade.toFixed(1)}s`}</span>
      </label>
      <label className="flex shrink-0 items-center gap-2 text-muted">
        <span>Master</span>
        <input
          className="h-10 w-24"
          type="range"
          min={0}
          max={100}
          step={1}
          value={Math.round(master * 100)}
          aria-label="Master brightness"
          onChange={(event) => setMaster(Number(event.target.value) / 100)}
        />
        <span className="w-10 tabular-nums text-fg">{Math.round(master * 100)}%</span>
      </label>
      <button
        type="button"
        disabled={!window.beamloomDesktop?.liveStart}
        onClick={() => void (piOn ? stopLive() : startLive())}
        className="inline-flex h-10 shrink-0 items-center rounded-md border border-line px-3 disabled:opacity-40"
        aria-pressed={piOn}
      >
        {piOn ? "Stop Pi" : "Pi"}
      </button>
      {piOn && piUrls[0] ? (
        <span className="shrink-0 text-xs text-muted" role="status">
          On the Pi, open {piUrls[0]}
        </span>
      ) : null}
      {window.beamloomDesktop?.piStatus && (
        <details className="relative shrink-0">
          <summary className="cursor-pointer rounded-md border border-line px-3 py-2" aria-label="Pi link and update controls">
            {piStatus?.error || !piStatus ? "Pi offline" : `Pi online · ${piStatus.latencyMs} ms · ${piStatus.viewers ? `${piStatus.viewers} live viewer${piStatus.viewers === 1 ? "" : "s"}` : "no live viewer"}`}
          </summary>
          <div className="absolute left-0 top-full z-30 mt-2 w-80 rounded-md border border-line bg-panel p-3 shadow-xl">
            <label htmlFor="pi-host" className="block">Pi address</label>
            <input id="pi-host" value={piHost} onChange={(event) => { setPiHost(event.target.value.trim()); setPiStatus(null); }} className="mt-1 w-full rounded border border-line bg-bg p-2" placeholder="beamloom.local" />
            <p className="mt-2 text-xs text-muted" role="status">{piStatus?.error ?? (piStatus ? `Response time: ${piStatus.latencyMs} ms. ${piStatus.update ? `Player: ${piStatus.update.state}${piStatus.update.message ? ` — ${piStatus.update.message}` : ""}` : "Reflash once with the new Pi image to enable remote updates."}` : "Checking Pi...")}</p>
            <button type="button" disabled={!!piStatus?.error || !piStatus?.update || updatingPi || piStatus.update?.state === "downloading"} onClick={() => void updatePi()} className="mt-2 rounded border border-line px-3 py-2 disabled:opacity-40">{updatingPi ? "Starting..." : "Update Pi player"}</button>
            {message && <p className="mt-2 text-xs" role="status">{message}</p>}
          </div>
        </details>
      )}
      <details className="relative ml-auto shrink-0">
        <summary className="flex h-10 cursor-pointer list-none items-center rounded-md border border-line px-3 text-fg marker:hidden">
          Alignment presets
        </summary>
        <div className="absolute right-0 top-full z-30 mt-2 flex w-[min(90vw,34rem)] flex-wrap items-center gap-2 rounded-md border border-line bg-panel p-3 shadow-xl">
      <label className="sr-only" htmlFor="alignment-select">Alignment preset</label>
      <select id="alignment-select" value={selectedPreset} onChange={(event) => { setSelectedPreset(event.target.value); setMessage(""); }} className="h-10 min-w-28 shrink-0 rounded-md border border-line bg-bg px-2" aria-label="Alignment preset">
        <option value="">Presets</option>
        {alignments.map((preset) => <option key={preset.id} value={preset.id}>{preset.name}</option>)}
      </select>
      <button type="button" disabled={!selectedPreset} onClick={() => setMessage(applyAlignment(selectedPreset) ? "Alignment applied" : "No matching surfaces in this project")} className="h-10 shrink-0 rounded-md border border-line px-2 disabled:opacity-40">Apply</button>
      <button type="button" disabled={!selectedPreset} onClick={() => { updateAlignment(selectedPreset); setMessage("Alignment updated"); }} className="h-10 shrink-0 rounded-md border border-line px-2 disabled:opacity-40">Update</button>
      <button type="button" disabled={!selectedPreset} onClick={() => { deleteAlignment(selectedPreset); setSelectedPreset(""); setMessage("Preset removed"); }} className="h-10 shrink-0 rounded-md border border-line px-2 disabled:opacity-40">Remove</button>
      <form className="flex shrink-0 items-center gap-1" onSubmit={(event) => { event.preventDefault(); if (saveAlignment(presetName)) { const preset = useEditor.getState().alignments.at(-1); setSelectedPreset(preset?.id ?? ""); setPresetName(""); setMessage("Alignment saved"); } else setMessage("Use a unique name (up to 24 presets)"); }}>
        <input value={presetName} onChange={(event) => setPresetName(event.target.value)} maxLength={40} placeholder="Office or House" aria-label="New alignment preset name" className="h-10 w-36 rounded-md border border-line bg-bg px-2 text-fg placeholder:text-muted" />
        <button type="submit" className="h-10 rounded-md border border-line px-2">Save preset</button>
      </form>
      {message ? <span role="status" className="shrink-0 text-xs text-beam">{message}</span> : null}
        </div>
      </details>
    </div>
  );
}
