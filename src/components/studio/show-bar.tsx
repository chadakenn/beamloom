import { useEffect, useState } from "react";
import { Pause, Play } from "lucide-react";
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

  useEffect(() => setSeconds(String(scene.durationSeconds)), [scene.id, scene.durationSeconds]);
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
    <div className="flex shrink-0 items-center gap-2 overflow-x-auto border-b border-line bg-panel px-3 py-1.5 text-sm text-fg" aria-label="Show and alignment controls">
      <button type="button" disabled={sceneCount < 2} onClick={() => setPlaying(!playing)} className="inline-flex h-10 shrink-0 items-center gap-1 rounded-md border border-line px-3 disabled:opacity-40" aria-label={playing ? "Pause scene playlist" : "Play scene playlist"}>
        {playing ? <Pause className="size-4" aria-hidden="true" /> : <Play className="size-4" aria-hidden="true" />}
        {playing ? "Pause" : "Play show"}
      </button>
      <label className="flex shrink-0 items-center gap-1 text-muted">
        <span>{scene.name}:</span>
        <input type="number" min="1" max="3600" step="1" value={seconds} onChange={(event) => setSeconds(event.target.value)} onBlur={commitSeconds} onKeyDown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); }} aria-label="Scene duration in seconds" className="h-10 w-16 rounded-md border border-line bg-bg px-2 text-fg" />
        <span>sec</span>
      </label>
      <span className="mx-1 h-7 w-px shrink-0 bg-line" aria-hidden="true" />
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
  );
}
