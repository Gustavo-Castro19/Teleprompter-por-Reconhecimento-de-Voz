import { SpeechCaptureButton } from "../SpeechCaptureButton";
import { OperatorModeToggle } from "../OperatorModeToggle";
import File from "../menu/File";
import LayoutMenu from "../menu/Layout";
import Settings from "../menu/Settings";
import type { TeleprompterLayout } from "../../lib/teleprompterLayout";

type HeaderProps = {
  listening: boolean;
  reconnecting?: boolean;
  speechError: string | null;
  transcript: string;
  isSpeechSupported: boolean;
  onToggleCapture: () => void;
  layout: TeleprompterLayout;
  onLayoutChange: (next: TeleprompterLayout) => void;
  operatorMode: boolean;
  onOperatorModeChange: (enabled: boolean) => void;
};

function Header({
  listening,
  reconnecting = false,
  speechError,
  transcript,
  isSpeechSupported,
  onToggleCapture,
  layout,
  onLayoutChange,
  operatorMode,
  onOperatorModeChange,
}: HeaderProps) {
  return (
    <header className="flex flex-wrap items-center gap-5 border-b border-current/20 p-4">
      <File />
      <Settings />
      <LayoutMenu layout={layout} onLayoutChange={onLayoutChange} />
      <SpeechCaptureButton
        listening={listening}
        reconnecting={reconnecting}
        error={speechError}
        transcript={transcript}
        isSupported={isSpeechSupported}
        onToggle={onToggleCapture}
      />
      <div className="ml-auto">
        <OperatorModeToggle
          enabled={operatorMode}
          onChange={onOperatorModeChange}
        />
      </div>
    </header>
  );
}

export default Header;
