import { useCallback, useEffect, useRef, useState } from "react";
import Header from "./components/layout/Header";
import { OnAirTeleprompter } from "./components/OnAirTeleprompter";
import {
  OperatorScriptPanel,
  type OperatorScrollSync,
} from "./components/OperatorScriptPanel";
import { ProgramList } from "./components/ProgramList";
import { useScriptFollow } from "./hooks/useScriptFollow";
import { useSpeechCapture } from "./hooks/useSpeechCapture";
import { useSlugs } from "./hooks/useSlugs";
import {
  ON_AIR_CHANNEL,
  openOnAirWindow,
  publishOnAirState,
  publishOperatorScroll,
  type OnAirMessage,
  type OnAirSyncState,
} from "./lib/onAirChannel";
import type { RetrancaMarker } from "./lib/scriptModel";
import {
  loadTeleprompterLayout,
  saveTeleprompterLayout,
  type TeleprompterLayout,
} from "./lib/teleprompterLayout";

function App() {
  const programs = useSlugs();
  const activeProgram = programs[0] ?? null;

  const [activeRetrancaId, setActiveRetrancaId] = useState<string | null>(
    null,
  );
  const [anchorWordIndex, setAnchorWordIndex] = useState(0);
  const [operatorFocusLineId, setOperatorFocusLineId] = useState<number | null>(
    null,
  );
  const [operatorScrollRatio, setOperatorScrollRatio] = useState(0);
  const [operatorMode, setOperatorMode] = useState(false);
  const [onAirPoppedOut, setOnAirPoppedOut] = useState(false);
  const [layout, setLayout] = useState<TeleprompterLayout>(() =>
    loadTeleprompterLayout(),
  );

  const popoutRef = useRef<Window | null>(null);
  const onAirPoppedOutRef = useRef(onAirPoppedOut);
  onAirPoppedOutRef.current = onAirPoppedOut;

  const {
    status,
    error,
    transcript,
    clearTranscript,
    toggle,
    isSupported,
  } = useSpeechCapture();

  const listening = status === "listening" || status === "reconnecting";

  const { lines, cursor, improvising, markers } = useScriptFollow(
    activeProgram,
    transcript,
    anchorWordIndex,
  );

  const buildSyncState = useCallback(
    (poppedOut: boolean): OnAirSyncState => ({
      cursor,
      improvising,
      activeRetrancaId,
      operatorFocusLineId,
      operatorScrollRatio,
      listening,
      operatorMode,
      layout,
      poppedOut,
    }),
    [
      cursor,
      improvising,
      activeRetrancaId,
      operatorFocusLineId,
      operatorScrollRatio,
      listening,
      operatorMode,
      layout,
    ],
  );

  useEffect(() => {
    setActiveRetrancaId(null);
    setAnchorWordIndex(0);
    clearTranscript();
  }, [activeProgram, clearTranscript]);

  // Estado completo (sem martelar localStorage a cada frame de scroll).
  useEffect(() => {
    publishOnAirState(buildSyncState(onAirPoppedOut));
  }, [
    cursor,
    improvising,
    activeRetrancaId,
    operatorFocusLineId,
    listening,
    operatorMode,
    layout,
    onAirPoppedOut,
    // operatorScrollRatio propositalmente fora — usa publishOperatorScroll
  ]);

  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return;

    const channel = new BroadcastChannel(ON_AIR_CHANNEL);
    channel.onmessage = (event: MessageEvent<OnAirMessage>) => {
      const message = event.data;
      if (message.type === "popout-closed") {
        setOnAirPoppedOut(false);
        popoutRef.current = null;
      }
      if (message.type === "request-state") {
        publishOnAirState(buildSyncState(onAirPoppedOutRef.current));
      }
    };

    return () => channel.close();
  }, [buildSyncState]);

  useEffect(() => {
    function onFocus() {
      if (popoutRef.current && popoutRef.current.closed) {
        setOnAirPoppedOut(false);
        popoutRef.current = null;
      }
    }

    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  const handleScrollSync = useCallback((sync: OperatorScrollSync) => {
    setOperatorFocusLineId(sync.lineId);
    setOperatorScrollRatio(sync.ratio);
    if (onAirPoppedOutRef.current) {
      publishOperatorScroll(sync.ratio);
    }
  }, []);

  function handleSelectStart() {
    setActiveRetrancaId(null);
    setAnchorWordIndex(0);
    clearTranscript();
  }

  function handleSelect(marker: RetrancaMarker) {
    setActiveRetrancaId(marker.id);
    setAnchorWordIndex(marker.startWordIndex);
    clearTranscript();
  }

  function handleLayoutChange(next: TeleprompterLayout) {
    setLayout(next);
    saveTeleprompterLayout(next);
  }

  function handlePopOut() {
    const win = openOnAirWindow();
    if (!win) return;
    popoutRef.current = win;
    setOnAirPoppedOut(true);
    publishOnAirState(buildSyncState(true));
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <Header
        listening={listening}
        reconnecting={status === "reconnecting"}
        speechError={error}
        transcript={transcript}
        isSpeechSupported={isSupported}
        onToggleCapture={toggle}
        layout={layout}
        onLayoutChange={handleLayoutChange}
        operatorMode={operatorMode}
        onOperatorModeChange={setOperatorMode}
      />

      <div className="flex min-h-0 flex-1">
        <ProgramList
          markers={markers}
          selectedId={activeRetrancaId}
          onSelect={handleSelect}
          onSelectStart={handleSelectStart}
        />

        <OperatorScriptPanel
          lines={lines}
          cursor={cursor}
          layout={layout}
          activeRetrancaId={activeRetrancaId}
          onScrollSync={handleScrollSync}
        />

        <OnAirTeleprompter
          lines={lines}
          cursor={cursor}
          improvising={improvising}
          listening={listening}
          operatorMode={operatorMode}
          layout={layout}
          activeRetrancaId={activeRetrancaId}
          operatorScrollRatio={operatorScrollRatio}
          poppedOut={onAirPoppedOut}
          onPopOut={handlePopOut}
        />
      </div>
    </div>
  );
}

export default App;
