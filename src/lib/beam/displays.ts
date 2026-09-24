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
