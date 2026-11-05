import type { TeleprompterLayout } from "./teleprompterLayout";

export const ON_AIR_CHANNEL = "teleprompter-on-air";
export const ON_AIR_STORAGE_KEY = "teleprompter-on-air-state";

export type OnAirSyncState = {
  cursor: number;
  improvising: boolean;
  activeRetrancaId: string | null;
  operatorFocusLineId: number | null;
  /** Progresso de scroll do operador (0–1), espelhado no Ao ar. */
  operatorScrollRatio: number;
  listening: boolean;
  operatorMode: boolean;
  layout: TeleprompterLayout;
  poppedOut: boolean;
};

export type OnAirMessage =
  | { type: "state"; payload: OnAirSyncState }
  | { type: "operator-scroll"; ratio: number }
  | { type: "popout-closed" }
  | { type: "request-state" };

export function publishOnAirState(state: OnAirSyncState) {
  const message: OnAirMessage = { type: "state", payload: state };
  try {
    localStorage.setItem(ON_AIR_STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* ignore quota */
  }

  if (typeof BroadcastChannel !== "undefined") {
    const channel = new BroadcastChannel(ON_AIR_CHANNEL);
    channel.postMessage(message);
    channel.close();
  }
}

/** Scroll contínuo do operador → popout (sem localStorage a 60fps). */
export function publishOperatorScroll(ratio: number) {
  if (typeof BroadcastChannel === "undefined") return;
  const channel = new BroadcastChannel(ON_AIR_CHANNEL);
  channel.postMessage({
    type: "operator-scroll",
    ratio,
  } satisfies OnAirMessage);
  channel.close();
}

export function openOnAirWindow(): Window | null {
  const url = `${window.location.origin}${window.location.pathname}?onair=1`;
  // Sem noopener: a janela principal precisa de `closed` para restaurar o preview.
  return window.open(url, "teleprompter-on-air");
}
