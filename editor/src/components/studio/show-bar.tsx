import { useEffect, useState, useSyncExternalStore } from "react";
import { Pause, Play } from "lucide-react";
import { getFadeSeconds, setFadeSeconds, subscribeFade } from "@/lib/beam/fade";
import { getMaster, setMaster, subscribeMaster } from "@/lib/beam/master";
import { storedClips } from "@/lib/beam/clips";
import { liveMediaNote, liveRunning, liveUrls, startLive, stopLive, subscribeLive } from "@/lib/beam/live-link";
import { activeScene } from "@/lib/beam/project";
import { snapshot, useEditor } from "@/lib/beam/store";

export function ShowBar() {
  const scene = useEditor((s) => activeScene(s));
  const sceneCount = useEditor((s) => s.scenes.length);
  const mediaNote = useSyncExternalStore(subscribeLive, liveMediaNote, () => "");
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
  const [piMessage, setPiMessage] = useState("");
  const [piHost, setPiHost] = useState(() => localStorage.getItem("beamloom-pi-host") || "beamloom.local");
  const [piStatus, setPiStatus] = useState<Awaited<ReturnType<NonNullable<NonNullable<Window["beamloomDesktop"]>["piStatus"]>>>>(null);
  const [updatingPi, setUpdatingPi] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [sendingShow, setSendingShow] = useState(false);
  const [foundPis, setFoundPis] = useState<{ host: string; wifi: { mode: string; ssid: string } }[]>([]);
  const [testResult, setTestResult] = useState<"ok" | "failed" | null>(null);
  const fade = useSyncExternalStore(subscribeFade, getFadeSeconds, () => 0);
  const master = useSyncExternalStore(subscribeMaster, getMaster, () => 1);
  const piOn = useSyncExternalStore(subscribeLive, liveRunning, () => false);
  const piUrls = useSyncExternalStore(subscribeLive, liveUrls, () => [] as string[]);
  const piSubnet = piHost.match(/^(\d+\.\d+\.\d+)\./)?.[1];
  const suggestedPiUrl = piUrls.find((url) => piSubnet && url.startsWith(`http://${piSubnet}.`)) ?? piUrls.find((url) => !url.includes("//127.0.0.1:"));

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
    const available = piStatus?.update?.available;
    const version = piStatus?.update?.version ?? "the current player";
    if (!available) return;
    if (!window.confirm(`Update the Beamloom player on ${piHost} to ${available}? It is running ${version}. The picture may go dark for a few seconds.`)) return;
    setUpdatingPi(true);
    const result = await window.beamloomDesktop?.piUpdate?.(piHost);
    setUpdatingPi(false);
    setPiMessage(result?.error ?? (result?.started ? `Update to ${available} started.` : "Pi update is already running."));
  }
  async function findPis() {
    setDiscovering(true);
    setPiMessage("Searching this PC's local network…");
    if (!liveRunning()) await startLive();
    const found = await window.beamloomDesktop?.piDiscover?.() ?? [];
    setFoundPis(found);
    setPiMessage(found.length ? `Found ${found.length} Beamloom Pi${found.length === 1 ? "" : "s"}. Select one below.` : "No Pi found. Check Wi-Fi or enter the Pi's address below.");
    setDiscovering(false);
  }

  async function connectPi() {
    setConnecting(true);
    setPiMessage("Checking whether the Pi can reach this PC…");
    if (!liveRunning() && !await startLive()) {
      setPiMessage("Could not start Pi output on this PC.");
      setConnecting(false);
      return;
    }
    const result = await window.beamloomDesktop?.piConnect?.(piHost);
    setTestResult(result?.ok ? "ok" : "failed");
    setPiMessage(result?.ok ? `Connected. The Pi saved ${result.pcUrl}. Its picture should appear now.` : result?.error || "Could not connect the Pi.");
    if (result?.ok) setPiStatus(await window.beamloomDesktop?.piStatus?.(piHost) ?? null);
    setConnecting(false);
  }

  async function sendShow() {
    const desktop = window.beamloomDesktop;
    if (!desktop?.piShowStart || !desktop.piShowProject || !desktop.piShowOpen || !desktop.piShowWrite || !desktop.piShowFile || !desktop.piShowFinish) return;
    setSendingShow(true);
    setPiMessage("Sending the show to the Pi…");
    try {
      const project = snapshot(useEditor.getState());
      const used = new Set(project.scenes.flatMap((scene) => scene.surfaces.map((face) => face.videoId).filter((id): id is string => Boolean(id))));
      const media = (await storedClips()).filter((clip) => used.has(clip.id));
      const allowed = new Set(["image/png", "image/jpeg", "video/mp4", "video/webm", "video/quicktime"]);
      for (const clip of media) {
        if (clip.blob.size > 512 * 1024 * 1024 || !allowed.has(clip.blob.type)) {
          throw new Error(`${clip.name} is over 512 MB or is not a PNG, JPEG, MP4, WebM, or MOV.`);
        }
      }
      const started = await desktop.piShowStart(piHost);
      if (!started?.ok) throw new Error(started?.error || "The Pi could not store the show.");
      const savedProject = await desktop.piShowProject(piHost, project);
      if (!savedProject?.ok) throw new Error(savedProject?.error || "The Pi could not store the project.");
      for (const clip of media) {
        setPiMessage(`Sending ${clip.name}…`);
        const opened = await desktop.piShowOpen(clip.id, clip.name, clip.blob.type, clip.blob.size);
        if (!opened?.ok) throw new Error(opened?.error || `Could not send ${clip.name}.`);
        let offset = 0;
        while (offset < clip.blob.size) {
          const bytes = new Uint8Array(await clip.blob.slice(offset, offset + 1024 * 1024).arrayBuffer());
          const wrote = await desktop.piShowWrite(clip.id, bytes);
          if (!wrote?.ok) throw new Error(wrote?.error || `Could not send ${clip.name}.`);
          offset += bytes.length;
        }
        const filed = await desktop.piShowFile(piHost, clip.id);
        if (!filed?.ok) throw new Error(filed?.error || `Could not send ${clip.name}.`);
      }
      const finished = await desktop.piShowFinish(piHost);
      if (!finished?.ok) throw new Error(finished?.error || "The Pi could not store the show.");
      const count = finished.show?.files ?? media.length;
      setPiMessage(`Saved ${finished.show?.name || project.name} on the Pi, with ${count} file${count === 1 ? "" : "s"}. The Pi cannot play this copy by itself yet.`);
    } catch (error) {
      setPiMessage(error instanceof Error ? error.message : "The Pi could not store the show.");
    } finally {
      setSendingShow(false);
    }
  }

  async function testPi() {
    if (!suggestedPiUrl) return;
    const result = await window.beamloomDesktop?.piCheck?.(piHost, suggestedPiUrl);
    setTestResult(result?.ok ? "ok" : "failed");
    setPiMessage(result?.ok ? "The Pi can reach this PC." : result?.error || "The Pi could not reach this PC.");
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
      {piOn && suggestedPiUrl ? (
        <span className="shrink-0 text-xs text-muted" role="status">
          Enter on the Pi settings page: {suggestedPiUrl}
        </span>
      ) : null}
      {piOn && !suggestedPiUrl && <span className="text-xs text-amber-400" role="status">Connect this PC to the same home Wi-Fi as the Pi to get its address.</span>}
      {piOn && mediaNote ? (
        <span className="text-xs text-amber-400" role="status">{mediaNote}</span>
      ) : null}
      {window.beamloomDesktop?.piStatus && (
        <details className="relative shrink-0">
          <summary className="cursor-pointer rounded-md border border-line px-3 py-2" aria-label="Pi link and update controls">
            {piStatus?.error || !piStatus ? "Pi offline" : `Pi online · ${piStatus.latencyMs} ms · ${piStatus.viewers ? `${piStatus.viewers} live viewer${piStatus.viewers === 1 ? "" : "s"}` : "no live viewer"}`}
          </summary>
          <div className="absolute left-0 top-full z-30 mt-2 w-[min(90vw,28rem)] rounded-md border border-line bg-panel p-3 shadow-xl">
            <h3 className="font-semibold">Set up Pi output</h3>
            <p className="mt-1 text-xs text-muted">Keep this PC and the Pi on the same home network. Find your Pi, then connect it to the picture from this app.</p>
            <button type="button" disabled={discovering} onClick={() => void findPis()} className="mt-3 rounded border border-line px-3 py-2 disabled:opacity-40">{discovering ? "Searching…" : "Find my Pi"}</button>
            {foundPis.length > 0 && <div className="mt-2 flex flex-wrap gap-2">{foundPis.map((found) => <button key={found.host} type="button" onClick={() => { setPiHost(found.host); setPiMessage(""); setTestResult(null); }} className="rounded border border-line px-2 py-1 text-xs">{found.host}{found.wifi.ssid ? ` · ${found.wifi.ssid}` : ""}</button>)}</div>}
            <label htmlFor="pi-host" className="block">Pi address</label>
            <input id="pi-host" value={piHost} onChange={(event) => { setPiHost(event.target.value.trim()); setPiStatus(null); setTestResult(null); }} className="mt-1 w-full rounded border border-line bg-bg p-2" placeholder="beamloom.local" />
            <p className="mt-2 text-xs text-muted">Find this address in your router if beamloom.local does not work. The Pi and PC should be on the same home network.</p>
            {piOn && suggestedPiUrl && <p className="mt-2 break-all text-xs">PC address to enter at <strong>http://{piHost}/</strong>: {suggestedPiUrl}</p>}
            <button type="button" disabled={connecting} onClick={() => void connectPi()} className="mt-3 rounded bg-amber-400 px-3 py-2 text-black disabled:opacity-40">{connecting ? "Connecting…" : "Connect this Pi"}</button>
            <button type="button" disabled={sendingShow || !!piStatus?.error} onClick={() => void sendShow()} className="ml-2 mt-3 rounded border border-line px-3 py-2 disabled:opacity-40">{sendingShow ? "Sending show…" : "Send show"}</button>
            <button type="button" disabled={!piOn || !suggestedPiUrl || !!piStatus?.error} onClick={() => void testPi()} className="ml-2 mt-3 rounded border border-line px-3 py-2 disabled:opacity-40">Test connection</button>
            <ol className="mt-4 space-y-1 text-xs" aria-label="Pi setup checklist">
              <li>{piStatus && !piStatus.error ? "✓" : "○"} Pi found on your network</li>
              <li>{piOn ? "✓" : "○"} Pi output running on this PC</li>
              <li>{testResult === "ok" ? "✓" : "○"} Pi can reach this PC</li>
              <li>{piStatus?.display?.state === "active" ? "✓" : "○"} Pi display running{piStatus?.display && piStatus.display.state !== "active" ? ` (${piStatus.display.state})` : ""}</li>
              <li>{(piStatus?.viewers ?? 0) > 0 ? "✓" : "○"} Live picture on the Pi</li>
            </ol>
            {piStatus?.display?.state !== "active" && piStatus?.display?.message && <p className="mt-2 max-h-28 overflow-auto whitespace-pre-wrap text-xs text-amber-400">{piStatus.display.message}</p>}
            <p className="mt-2 text-xs text-muted" role="status">{piStatus?.error ?? (piStatus ? `Response time: ${piStatus.latencyMs} ms. ${piStatus.update ? (piStatus.update.message ? piStatus.update.message : piStatus.update.available ? `Player ${piStatus.update.version}. Release ${piStatus.update.available} is ready.` : `Player ${piStatus.update.version} matches the published release.`) : "This card has no player updater. Build a new image before flashing."}` : "Checking Pi...")}</p>
            <button type="button" disabled={!!piStatus?.error || !piStatus?.update?.available || updatingPi || piStatus.update?.state === "checking" || piStatus.update?.state === "downloading" || piStatus.update?.state === "restarting"} onClick={() => void updatePi()} className="mt-2 rounded border border-line px-3 py-2 disabled:opacity-40">{updatingPi ? "Starting..." : piStatus?.update?.available ? `Update Pi player to ${piStatus.update.available}` : "Update Pi player"}</button>
            {piMessage && <p className="mt-2 text-xs" role="status">{piMessage}</p>}
            <p className="mt-2 text-xs text-muted">Need the full steps? Open the Pi settings page at <strong>http://{piHost}/</strong>.</p>
            <details className="mt-3 text-xs text-muted">
              <summary className="cursor-pointer text-fg">First-time setup guide</summary>
              <ol className="mt-2 list-decimal space-y-1 pl-4">
                <li>Connect the Pi to a screen and power it on.</li>
                <li>If it shows a Beamloom setup network, join that Wi-Fi using password <strong>beamloom</strong>, then open <strong>http://192.168.4.1/</strong> and enter your home Wi-Fi.</li>
                <li>Put this PC back on the same home network, click <strong>Find my Pi</strong>, and select it. If it does not appear, find its IP in your router and enter it above.</li>
                <li>Click <strong>Connect this Pi</strong>. The checklist shows what still needs attention. Allow Beamloom on private networks if Windows asks.</li>
              </ol>
            </details>
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
