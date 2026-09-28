import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { liveMediaNote, liveRunning, liveUrls, startLive, stopLive, subscribeLive } from "@/lib/beam/live-link";
import { sendShowToPi } from "@/lib/beam/send-show";

type PiStatus = Awaited<ReturnType<NonNullable<NonNullable<Window["beamloomDesktop"]>["piStatus"]>>>;
const KNOWN_PIS_KEY = "beamloom-known-pis";

export function ConnectionsPage() {
  const [piMessage, setPiMessage] = useState("");
  const [piHost, setPiHost] = useState(() => localStorage.getItem("beamloom-pi-host") || "beamloom.local");
  const [piStatus, setPiStatus] = useState<PiStatus>(null);
  const [updatingPi, setUpdatingPi] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [sendingShow, setSendingShow] = useState(false);
  const [foundPis, setFoundPis] = useState<{ host: string; wifi: { mode: string; ssid: string } }[]>([]);
  const [testResult, setTestResult] = useState<"ok" | "failed" | null>(null);
  const [clockOn, setClockOn] = useState(false);
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [afterSunset, setAfterSunset] = useState("20");
  const [clockStart, setClockStart] = useState("");
  const [clockEnd, setClockEnd] = useState("23:00");
  const [savingClock, setSavingClock] = useState(false);
  const clockDirty = useRef(false);
  const [addressDraft, setAddressDraft] = useState("");
  const [knownHosts, setKnownHosts] = useState<string[]>(() => {
    try {
      const saved: unknown = JSON.parse(localStorage.getItem(KNOWN_PIS_KEY) || "[]");
      return Array.isArray(saved) ? saved.filter((host): host is string => typeof host === "string" && host.length > 0 && host.length < 256).slice(0, 24) : [];
    } catch { return []; }
  });
  const [deviceStatuses, setDeviceStatuses] = useState<Record<string, PiStatus>>({});
  const piOn = useSyncExternalStore(subscribeLive, liveRunning, () => false);
  const mediaNote = useSyncExternalStore(subscribeLive, liveMediaNote, () => "");
  const piUrls = useSyncExternalStore(subscribeLive, liveUrls, () => [] as string[]);
  const piSubnet = piHost.match(/^(\d+\.\d+\.\d+)\./)?.[1];
  const suggestedPiUrl = piUrls.find((url) => piSubnet && url.startsWith(`http://${piSubnet}.`)) ?? piUrls.find((url) => !url.includes("//127.0.0.1:"));

  useEffect(() => {
    localStorage.setItem("beamloom-pi-host", piHost);
    if (!window.beamloomDesktop?.piStatus) return;
    let active = true;
    const refresh = () => { void window.beamloomDesktop?.piStatus?.(piHost).then((status) => { if (active) setPiStatus(status); }); };
    refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => { active = false; window.clearInterval(timer); };
  }, [piHost]);
  useEffect(() => { localStorage.setItem(KNOWN_PIS_KEY, JSON.stringify(knownHosts)); }, [knownHosts]);

  useEffect(() => {
    const clock = piStatus?.clock;
    if (!clock || clockDirty.current) return;
    setClockOn(clock.enabled);
    setLatitude(clock.latitude == null ? "" : String(clock.latitude));
    setLongitude(clock.longitude == null ? "" : String(clock.longitude));
    setAfterSunset(String(clock.afterSunset));
    setClockStart(clock.start || "");
    setClockEnd(clock.end);
  }, [piStatus]);

  useEffect(() => {
    if (!window.beamloomDesktop?.piDiscover) return;
    let active = true;
    let running = false;
    const scan = async () => {
      if (running) return;
      running = true;
      try {
        const found = await window.beamloomDesktop?.piDiscover?.() ?? [];
        if (!active) return;
        setFoundPis(found);
        setKnownHosts((current) => [...new Set([...current, ...found.map((item) => item.host)])].slice(-24));
        setPiHost((current) => {
          if (found.some((item) => item.host === current)) return current;
          return current === "beamloom.local" && found.length ? found[0].host : current;
        });
      } finally {
        running = false;
      }
    };
    void scan();
    const timer = window.setInterval(() => void scan(), 20000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

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
    const found = await window.beamloomDesktop?.piDiscover?.() ?? [];
    setFoundPis(found);
    setKnownHosts((current) => [...new Set([...current, ...found.map((item) => item.host)])].slice(-24));
    setPiHost((current) => found.some((item) => item.host === current) ? current : current === "beamloom.local" && found.length ? found[0].host : current);
    setPiMessage(found.length ? `Found ${found.length} Beamloom Pi${found.length === 1 ? "" : "s"}.` : "No Pi found. Check Wi-Fi or enter the Pi's address below.");
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
    setSendingShow(true);
    try {
      setPiMessage(await sendShowToPi(piHost, setPiMessage));
    } catch (error) {
      setPiMessage(error instanceof Error ? error.message : "The Pi could not store the show.");
    } finally {
      setSendingShow(false);
    }
  }

  async function saveClock(enabled = clockOn) {
    setSavingClock(true);
    const result = await window.beamloomDesktop?.piSchedule?.(piHost, {
      enabled,
      latitude: latitude.trim() === "" ? Number.NaN : Number(latitude),
      longitude: longitude.trim() === "" ? Number.NaN : Number(longitude),
      afterSunset: Number(afterSunset),
      start: clockStart.trim(),
      end: clockEnd,
    });
    setSavingClock(false);
    clockDirty.current = false;
    setClockOn(enabled);
    setPiMessage(result?.error?.includes("store a show") ? "Update the Pi player, then save the clock again." : result?.error || (enabled ? result?.clock?.note || "Clock is on." : "Clock is off."));
    if (result?.ok) setPiStatus(await window.beamloomDesktop?.piStatus?.(piHost) ?? null);
  }

  async function testPi() {
    if (!suggestedPiUrl) return;
    const result = await window.beamloomDesktop?.piCheck?.(piHost, suggestedPiUrl);
    setTestResult(result?.ok ? "ok" : "failed");
    setPiMessage(result?.ok ? "The Pi can reach this PC." : result?.error || "The Pi could not reach this PC.");
  }

  const hosts = [...new Set([...foundPis.map((found) => found.host), ...knownHosts, ...(piHost === "beamloom.local" && foundPis.length ? [] : [piHost])].filter(Boolean))];
  useEffect(() => {
    if (!window.beamloomDesktop?.piStatus || !hosts.length) return;
    let active = true;
    const check = async () => {
      const statuses = await Promise.all(hosts.map(async (host) => {
        try { return [host, await window.beamloomDesktop?.piStatus?.(host) ?? null] as const; }
        catch { return [host, null] as const; }
      }));
      if (active) setDeviceStatuses(Object.fromEntries(statuses));
    };
    void check();
    const timer = window.setInterval(() => void check(), 15000);
    return () => { active = false; window.clearInterval(timer); };
  }, [hosts.join("|")]);

  function selectPi(host: string) {
    clockDirty.current = false;
    setPiHost(host);
    setPiStatus(null);
    setPiMessage("");
    setTestResult(null);
  }

  return (
    <section className="flex min-h-0 flex-1 flex-col overflow-auto bg-bg px-4 py-5 text-fg lg:px-8" aria-labelledby="connections-title">
      <div className="mx-auto w-full max-w-7xl">
        <div className="mb-6">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-beam">Devices</p>
          <h1 id="connections-title" className="font-display text-2xl font-semibold">Connections</h1>
          <p className="mt-1 text-sm text-muted">Pick a Pi to set up its picture, stored show, clock, and updates.</p>
        </div>
        <div className="grid gap-5 lg:grid-cols-[17rem_minmax(0,1fr)]">
          <aside className="rounded-xl border border-line bg-panel p-4" aria-label="Discovered Pi players">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-semibold">Pi players</h2>
              <button type="button" disabled={discovering} onClick={() => void findPis()} className="rounded-md border border-line px-3 py-2 text-sm disabled:opacity-40">{discovering ? "Searching…" : "Search again"}</button>
            </div>
            <p className="mt-2 text-xs text-muted">Beamloom scans your network automatically. You can also enter an address below.</p>
            <div className="mt-4 space-y-2">
              {hosts.map((host) => {
                const status = host === piHost ? piStatus : deviceStatuses[host];
                const found = foundPis.find((item) => item.host === host);
                const online = !!status && !status.error;
                return <button key={host} type="button" aria-current={host === piHost ? "true" : undefined} onClick={() => selectPi(host)} className={`w-full rounded-lg border p-3 text-left ${host === piHost ? "border-beam bg-beam/10" : "border-line hover:border-beam/70"}`}>
                  <span className="flex items-center gap-2"><span className={`size-2 shrink-0 rounded-full ${online ? "bg-emerald-400" : "bg-muted"}`} aria-hidden="true" /><strong className="min-w-0 truncate text-sm">{host}</strong></span>
                  <span className="mt-1 block text-xs text-muted">{online ? `Online · ${status.latencyMs} ms${status.viewers ? ` · ${status.viewers} live viewer${status.viewers === 1 ? "" : "s"}` : ""}` : status ? "Offline" : "Checking…"}{found?.wifi.ssid ? ` · ${found.wifi.ssid}` : ""}</span>
                </button>;
              })}
            </div>
            <form className="mt-5 border-t border-line pt-4" onSubmit={(event) => { event.preventDefault(); const host = addressDraft.trim(); if (host) { setKnownHosts((current) => [...new Set([...current, host])].slice(-24)); selectPi(host); setAddressDraft(""); } }}>
              <label htmlFor="pi-address" className="text-sm font-medium">Add by address</label>
              <div className="mt-2 flex gap-2"><input id="pi-address" value={addressDraft} onChange={(event) => setAddressDraft(event.target.value)} placeholder="192.168.1.157" className="min-w-0 flex-1 rounded-md border border-line bg-bg px-3 py-2 text-sm" /><button type="submit" disabled={!addressDraft.trim()} className="rounded-md bg-beam px-3 py-2 text-sm font-medium text-ink disabled:opacity-40">Select</button></div>
            </form>
          </aside>
          <div className="min-w-0 space-y-5">
            <section className="rounded-xl border border-line bg-panel p-5" aria-label="Selected Pi connection">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div><p className="text-xs uppercase tracking-widest text-muted">Selected Pi</p><h2 className="mt-1 font-display text-xl font-semibold">{piHost}</h2><p className="mt-1 text-sm text-muted">{piStatus?.error || !piStatus ? "Offline or checking…" : `Online · ${piStatus.latencyMs} ms · ${piStatus.viewers ?? 0} live viewers`}</p></div>
                <a href={`http://${piHost}/`} target="_blank" rel="noreferrer" className="rounded-md border border-line px-3 py-2 text-sm text-fg">Open Pi settings</a>
              </div>
              {knownHosts.includes(piHost) && !foundPis.some((item) => item.host === piHost) ? <button type="button" onClick={() => { setKnownHosts((current) => current.filter((host) => host !== piHost)); selectPi(foundPis[0]?.host || "beamloom.local"); }} className="mt-3 text-xs text-muted underline">Forget this Pi</button> : null}
              <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" disabled={!window.beamloomDesktop?.liveStart} onClick={() => void (piOn ? stopLive() : startLive())} className="mt-3 rounded border border-line px-3 py-2 disabled:opacity-40">{piOn ? "Stop PC output" : "Start PC output"}</button>

            <button type="button" disabled={connecting} onClick={() => void connectPi()} className="mt-3 rounded bg-amber-400 px-3 py-2 text-black disabled:opacity-40">{connecting ? "Connecting…" : "Connect this Pi"}</button>
            <button type="button" disabled={sendingShow || !!piStatus?.error} onClick={() => void sendShow()} className="mt-3 rounded border border-line px-3 py-2 disabled:opacity-40">{sendingShow ? "Sending show…" : "Send show"}</button>
            <button type="button" disabled={!!piStatus?.error} onClick={() => void window.beamloomDesktop?.piPlayMode?.(piHost, "show").then((result) => setPiMessage(result?.ok ? "The Pi is switching to the stored show. The picture may blink, then it keeps playing after this PC closes." : result?.error || "The Pi could not switch to the stored show."))} className="mt-3 rounded border border-line px-3 py-2 disabled:opacity-40">Play stored show</button>
            <button type="button" disabled={!!piStatus?.error} onClick={() => void window.beamloomDesktop?.piPlayMode?.(piHost, "auto").then((result) => setPiMessage(result?.ok ? "The Pi will follow this PC, and play the stored show when the PC is off." : result?.error || "The Pi could not follow this PC."))} className="mt-3 rounded border border-line px-3 py-2 disabled:opacity-40">Follow this PC</button>
            <button type="button" disabled={!piOn || !suggestedPiUrl || !!piStatus?.error} onClick={() => void testPi()} className="mt-3 rounded border border-line px-3 py-2 disabled:opacity-40">Test connection</button>
              </div>
              {piOn && suggestedPiUrl ? <p className="mt-3 break-all text-xs text-muted">PC live address: {suggestedPiUrl}</p> : null}
              {piOn && mediaNote ? <p className="mt-2 text-xs text-amber-400" role="status">{mediaNote}</p> : null}
            </section>
            <section className="rounded-xl border border-line bg-panel p-5" aria-label="FPP remote status">
              <h2 className="font-display text-lg font-semibold">FPP remote</h2>
              {piStatus?.syncShow?.showId ? (
                <p className="mt-2 text-sm" role="status"><span className="text-beam">Matched:</span> {piStatus.syncShow.sequence} → {piStatus.syncShow.showName} · {piStatus.syncShow.action === "play" ? "Playing" : piStatus.syncShow.action === "hold" ? "Paused" : "Stopped"}{typeof piStatus.syncShow.elapsed === "number" ? ` · ${piStatus.syncShow.elapsed.toFixed(1)}s` : ""}</p>
              ) : piStatus?.syncShow?.action === "waiting" ? (
                <p className="mt-2 text-sm text-amber-400" role="status">{piStatus.syncShow.reason === "ambiguous" ? "More than one enabled show matches" : "No enabled stored show matches"} {piStatus.syncShow.sequence}. Name a Beamloom show after that sequence, send it to this Pi, and enable it in the Pi playlist.</p>
              ) : (
                <p className="mt-2 text-sm text-muted" role="status">{piStatus?.error ? "Pi offline." : "Waiting for an FPP sequence."}</p>
              )}
              <p className="mt-2 text-xs text-muted">The Pi matches the FPP sequence filename (without .fseq) to a stored Beamloom show name. The show and its videos stay on the Pi.</p>
              {piStatus?.syncShow?.action && piStatus.screen !== "/play" ? <p className="mt-2 text-xs text-amber-400">The Pi is displaying PC output. Select Play stored show or Follow this PC to let FPP take over.</p> : null}
            </section>
            <section className="rounded-xl border border-line bg-panel p-5" aria-label="Dusk clock">
              <h2 className="font-display text-lg font-semibold">Dusk clock</h2>
              <p className="mt-1 text-xs text-muted">After you send a show, the Pi starts it at the time you type, or at sunset if you leave the start time blank. It stops at the time you type. The PC can be off.</p>
              {piStatus?.clock ? <p className="mt-1 text-xs" role="status">{piStatus.clock.enabled ? piStatus.clock.note || "Clock is on." : "Clock is off."} Pi time {piStatus.clock.now}.</p> : null}
              <div className="mt-2 flex gap-2" role="group" aria-label="Pi clock">
                <button type="button" aria-pressed={!clockOn} disabled={savingClock || !!piStatus?.error} onClick={() => void saveClock(false)} className={`rounded px-3 py-2 text-xs disabled:opacity-40 ${clockOn ? "border border-line" : "bg-amber-400 text-black"}`}>Off</button>
                <button type="button" aria-pressed={clockOn} disabled={!!piStatus?.error} onClick={() => { clockDirty.current = true; setClockOn(true); }} className={`rounded px-3 py-2 text-xs disabled:opacity-40 ${clockOn ? "bg-amber-400 text-black" : "border border-line"}`}>On</button>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <label className="text-xs">Start at<input value={clockStart} onChange={(event) => { clockDirty.current = true; setClockStart(event.target.value); }} className="mt-1 w-full rounded border border-line bg-bg p-2" placeholder="18:30 or blank for sunset" /></label>
                <label className="text-xs">Stop at<input value={clockEnd} onChange={(event) => { clockDirty.current = true; setClockEnd(event.target.value); }} className="mt-1 w-full rounded border border-line bg-bg p-2" placeholder="23:00" /></label>
                <label className="text-xs">Latitude, for sunset<input value={latitude} onChange={(event) => { clockDirty.current = true; setLatitude(event.target.value); }} className="mt-1 w-full rounded border border-line bg-bg p-2" inputMode="decimal" placeholder="40.71" /></label>
                <label className="text-xs">Longitude, for sunset<input value={longitude} onChange={(event) => { clockDirty.current = true; setLongitude(event.target.value); }} className="mt-1 w-full rounded border border-line bg-bg p-2" inputMode="decimal" placeholder="-74.01" /></label>
                <label className="text-xs">Minutes after sunset<input value={afterSunset} onChange={(event) => { clockDirty.current = true; setAfterSunset(event.target.value); }} className="mt-1 w-full rounded border border-line bg-bg p-2" inputMode="numeric" /></label>
              </div>
              <button type="button" disabled={savingClock || !!piStatus?.error || !clockOn} onClick={() => void saveClock(true)} className="mt-2 rounded border border-line px-3 py-2 disabled:opacity-40">{savingClock ? "Saving…" : "Save clock"}</button>
            </section>
            <section className="rounded-xl border border-line bg-panel p-5" aria-label="Pi health and updates">
              <h2 className="font-display text-lg font-semibold">Health and updates</h2>
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
            <p className="mt-2 text-xs text-muted">For network and display settings, open the Pi settings page above.</p>
            <details className="mt-3 text-xs text-muted">
              <summary className="cursor-pointer text-fg">First-time setup guide</summary>
              <ol className="mt-2 list-decimal space-y-1 pl-4">
                <li>Connect the Pi to a screen and power it on.</li>
                <li>If it shows a Beamloom setup network, join that Wi-Fi using password <strong>beamloom</strong>, then open <strong>http://192.168.4.1/</strong> and enter your home Wi-Fi.</li>
                <li>Put this PC back on the same home network. Beamloom fills in the Pi it finds. If more than one appears, select it. If none appear, find its IP in your router and enter it above.</li>
                <li>Click <strong>Connect this Pi</strong>. The checklist shows what still needs attention. Allow Beamloom on private networks if Windows asks.</li>
              </ol>
            </details>
            </section>
          </div>
        </div>
      </div>
    </section>
  );
}
