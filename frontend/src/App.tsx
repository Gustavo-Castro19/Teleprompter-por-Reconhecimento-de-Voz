import { useEffect, useState } from "react";
import Header from "./components/layout/Header";
import { ProgramList } from "./components/ProgramList";
import { Teleprompter } from "./components/Teleprompter";
import { useScriptFollow } from "./hooks/useScriptFollow";
import { useSpeechCapture } from "./hooks/useSpeechCapture";
import { useSlugs } from "./hooks/useSlugs";
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
  const [operatorMode, setOperatorMode] = useState(false);
  const [layout, setLayout] = useState<TeleprompterLayout>(() =>
    loadTeleprompterLayout(),
  );

  const {
    status,
    error,
    transcript,
    clearTranscript,
    toggle,
    isSupported,
  } = useSpeechCapture();

  const { lines, cursor, improvising, markers } = useScriptFollow(
    activeProgram,
    transcript,
    anchorWordIndex,
  );

  useEffect(() => {
    setActiveRetrancaId(null);
    setAnchorWordIndex(0);
    clearTranscript();
  }, [activeProgram, clearTranscript]);

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

  return (
    <div className="flex h-full min-h-0 flex-col">
      <Header
        listening={status === "listening"}
        reconnecting={status === "reconnecting"}
        speechError={error}
        transcript={transcript}
        isSpeechSupported={isSupported}
        onToggleCapture={toggle}
        operatorMode={operatorMode}
        onOperatorModeChange={setOperatorMode}
        layout={layout}
        onLayoutChange={handleLayoutChange}
      />

      <div className="flex min-h-0 flex-1">
        <ProgramList
          markers={markers}
          selectedId={activeRetrancaId}
          onSelect={handleSelect}
          onSelectStart={handleSelectStart}
        />

        <main className="flex min-w-0 flex-1 items-center justify-center px-6 py-6 lg:px-10">
          <Teleprompter
            lines={lines}
            cursor={cursor}
            improvising={improvising}
            operatorMode={operatorMode}
            layout={layout}
            activeRetrancaId={activeRetrancaId}
          />
        </main>
      </div>
    </div>
  );
}

export default App;
