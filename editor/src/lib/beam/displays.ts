export type Display = {
  id?: number;
  label: string;
  left: number;
  top: number;
  width: number;
  height: number;
  primary: boolean;
};

type ScreenDetail = {
  label?: string;
  isPrimary?: boolean;
  availLeft: number;
  availTop: number;
  availWidth: number;
  availHeight: number;
};

type ScreenDetails = { screens: ScreenDetail[] };

declare global {
  interface Window {
    beamloomDesktop?: {
      displays: () => Promise<Display[]>;
      openProjector: (displayId: number | null) => Promise<boolean>;
      updateStatus?: () => Promise<{ phase: "available" | "downloading" | "ready" | "failed"; version: string | null } | null>;
      onUpdate?: (callback: (status: { phase: "available" | "downloading" | "ready" | "failed"; version: string | null }) => void) => () => void;
      applyUpdate?: () => Promise<boolean>;
      liveStart?: () => Promise<{ port: number; urls: string[] } | null>;
      liveStop?: () => Promise<boolean>;
      liveFrame?: (frame: unknown) => void;
      liveMedia?: (id: string, mime: string, bytes: Uint8Array) => Promise<boolean>;
      piStatus?: (host: string) => Promise<{ error?: string; latencyMs?: number; viewers?: number; update?: { state: string; version?: string; available?: string | null; message?: string } } | null>;
      piUpdate?: (host: string) => Promise<{ error?: string; started?: boolean; current?: boolean } | null>;
    };
  }
}

export async function connectedDisplays(): Promise<Display[] | null> {
  if (window.beamloomDesktop) return window.beamloomDesktop.displays();
  const browser = window as Window & { getScreenDetails?: () => Promise<ScreenDetails> };
  if (!browser.getScreenDetails) return null;
  const details = await browser.getScreenDetails();
  return details.screens.map((screen, index) => ({
    label: screen.label || `Display ${index + 1}`,
    left: screen.availLeft,
    top: screen.availTop,
    width: screen.availWidth,
    height: screen.availHeight,
    primary: Boolean(screen.isPrimary),
  }));
}

export async function openProjector(display?: Display): Promise<boolean> {
  if (window.beamloomDesktop) return window.beamloomDesktop.openProjector(display?.id ?? null);
  const url = new URL(window.location.href);
  url.searchParams.set("projector", "1");
  const features = display
    ? `popup=yes,left=${Math.round(display.left)},top=${Math.round(display.top)},width=${Math.round(display.width)},height=${Math.round(display.height)}`
    : "popup=yes,width=1280,height=720";
  return Boolean(window.open(url.href, "beamloom-projector", features));
}
