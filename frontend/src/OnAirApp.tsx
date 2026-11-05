import { useEffect, useMemo, useState } from "react";
import { OnAirTeleprompter } from "./components/OnAirTeleprompter";
import { useSlugs } from "./hooks/useSlugs";
import { flattenProgram } from "./lib/scriptModel";
import {
  ON_AIR_CHANNEL,
  ON_AIR_STORAGE_KEY,
  type OnAirMessage,
  type OnAirSyncState,
} from "./lib/onAirChannel";
import {
  DEFAULT_LAYOUT,
  type TeleprompterLayout,
} from "./lib/teleprompterLayout";

function readStoredState(): OnAirSyncState | null {
  try {
    const raw = localStorage.getItem(ON_AIR_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as OnAirSyncState) : null;
  } catch {
    return null;
  }
}

const DEFAULT_SYNC: OnAirSyncState = {
  cursor: 0,
  improvising: false,
  activeRetrancaId: null,
  operatorFocusLineId: null,
  operatorScrollRatio: 0,
  listening: false,
  operatorMode: false,
  layout: DEFAULT_LAYOUT,
  poppedOut: true,
};

export default function OnAirApp() {
  const programs = useSlugs();
  const activeProgram = programs[0] ?? null;
  const prepared = useMemo(
    () =>
      activeProgram
        ? flattenProgram(activeProgram)
        : { lines: [], scriptWords: [], markers: [] },
    [activeProgram],
  );

  const [sync, setSync] = useState<OnAirSyncState>(() => {
    const stored = readStoredState();
    return stored
      ? { ...DEFAULT_SYNC, ...stored, operatorScrollRatio: stored.operatorScrollRatio ?? 0 }
      : DEFAULT_SYNC;
  });

  useEffect(() => {
    function apply(message: OnAirMessage) {
      if (message.type === "state") {
        setSync({
          ...DEFAULT_SYNC,
          ...message.payload,
          operatorScrollRatio: message.payload.operatorScrollRatio ?? 0,
        });
      }
      if (message.type === "operator-scroll") {
        setSync((prev) =>
          prev.operatorScrollRatio === message.ratio
            ? prev
            : { ...prev, operatorScrollRatio: message.ratio },
        );
      }
    }

    function onStorage(event: StorageEvent) {
      if (event.key !== ON_AIR_STORAGE_KEY || !event.newValue) return;
      try {
        const payload = JSON.parse(event.newValue) as OnAirSyncState;
        setSync({
          ...DEFAULT_SYNC,
          ...payload,
          operatorScrollRatio: payload.operatorScrollRatio ?? 0,
        });
      } catch {
        /* ignore */
      }
    }

    let channel: BroadcastChannel | null = null;
    if (typeof BroadcastChannel !== "undefined") {
      channel = new BroadcastChannel(ON_AIR_CHANNEL);
      channel.onmessage = (event: MessageEvent<OnAirMessage>) => {
        apply(event.data);
      };
      channel.postMessage({ type: "request-state" } satisfies OnAirMessage);
    }

    window.addEventListener("storage", onStorage);

    return () => {
      window.removeEventListener("storage", onStorage);
      channel?.close();
    };
  }, []);

  useEffect(() => {
    function notifyClosed() {
      if (typeof BroadcastChannel !== "undefined") {
        const channel = new BroadcastChannel(ON_AIR_CHANNEL);
        channel.postMessage({ type: "popout-closed" } satisfies OnAirMessage);
        channel.close();
      }
    }

    window.addEventListener("beforeunload", notifyClosed);
    return () => {
      window.removeEventListener("beforeunload", notifyClosed);
      notifyClosed();
    };
  }, []);

  const layout: TeleprompterLayout = sync.layout ?? DEFAULT_LAYOUT;

  return (
    <div className="flex h-full min-h-0 flex-col bg-black text-d_font">
      <OnAirTeleprompter
        lines={prepared.lines}
        cursor={sync.cursor}
        improvising={sync.improvising}
        listening={sync.listening}
        operatorMode={Boolean(sync.operatorMode)}
        layout={layout}
        activeRetrancaId={sync.activeRetrancaId}
        operatorScrollRatio={sync.operatorScrollRatio}
        fillWindow
      />
    </div>
  );
}
