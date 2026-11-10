import { useCallback, useEffect, useRef, useState } from "react";
import {
  alignTopToPointer,
  cancelScrollTracker,
  createScrollTracker,
  POINTER_RATIO,
  pointerPads,
  trackAlignToPointer,
} from "../lib/alignToPointer";
import type { PromptLine } from "../lib/scriptModel";
import type { TeleprompterLayout } from "../lib/teleprompterLayout";
import { ScriptLines } from "./ScriptLines";

type OnAirTeleprompterProps = {
  lines: PromptLine[];
  cursor: number;
  improvising: boolean;
  listening: boolean;
  operatorMode: boolean;
  layout: TeleprompterLayout;
  activeRetrancaId: string | null;
  /** Progresso 0–1 do scroll do operador; drive a rolagem em modo operador. */
  operatorScrollRatio: number;
  poppedOut?: boolean;
  fillWindow?: boolean;
  onPopOut?: () => void;
};

export function OnAirTeleprompter({
  lines,
  cursor,
  improvising,
  listening,
  operatorMode,
  layout,
  activeRetrancaId,
  operatorScrollRatio,
  poppedOut = false,
  fillWindow = false,
  onPopOut,
}: OnAirTeleprompterProps) {
  const frameRef = useRef<HTMLDivElement>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const scrollTrackerRef = useRef(createScrollTracker());
  const lastScrolledCursorRef = useRef<number | null>(null);
  const lastRetrancaRef = useRef<string | null | undefined>(undefined);
  const lastScriptLenRef = useRef(0);
  const operatorScrollRafRef = useRef<number | null>(null);

  useEffect(() => {
    const tracker = scrollTrackerRef.current;
    return () => cancelScrollTracker(tracker);
  }, []);

  const [fullscreen, setFullscreen] = useState(false);
  const [pads, setPads] = useState({ top: 0, bottom: 0 });

  const updateFullscreenState = useCallback(() => {
    setFullscreen(document.fullscreenElement === frameRef.current);
  }, []);

  useEffect(() => {
    document.addEventListener("fullscreenchange", updateFullscreenState);
    return () => {
      document.removeEventListener("fullscreenchange", updateFullscreenState);
    };
  }, [updateFullscreenState]);

  useEffect(() => {
    const scroller = scrollerRef.current;
    if (!scroller) return;

    function measure() {
      if (!scroller) return;
      setPads(pointerPads(scroller.clientHeight));
    }

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(scroller);
    return () => observer.disconnect();
  }, [fullscreen, fillWindow, lines.length, poppedOut]);

  useEffect(() => {
    const scroller = scrollerRef.current;
    if (!scroller || lines.length === 0 || pads.top <= 0) return;

    const scriptChanged = lastScriptLenRef.current !== lines.length;
    if (
      !scriptChanged &&
      activeRetrancaId === lastRetrancaRef.current
    ) {
      return;
    }

    lastScriptLenRef.current = lines.length;
    lastRetrancaRef.current = activeRetrancaId;

    const target = activeRetrancaId
      ? scroller.querySelector<HTMLElement>(
          `[data-retranca-id="${activeRetrancaId}"]`,
        )
      : scroller.querySelector<HTMLElement>("[data-script-line]");

    if (!target) return;

    cancelScrollTracker(scrollTrackerRef.current);
    alignTopToPointer(scroller, target);
    requestAnimationFrame(() => {
      alignTopToPointer(scroller, target);
      lastScrolledCursorRef.current = null;
    });
  }, [activeRetrancaId, lines.length, pads.top]);

  // Follow por voz: tracking contínuo (desligado em modo operador).
  useEffect(() => {
    if (operatorMode) return;
    if (lastScrolledCursorRef.current === cursor) return;

    const scroller = scrollerRef.current;
    const current = scroller?.querySelector<HTMLElement>(
      '[data-current-word="true"]',
    );
    if (!scroller || !current) return;

    lastScrolledCursorRef.current = cursor;
    trackAlignToPointer(scrollTrackerRef.current, scroller, current);
  }, [cursor, improvising, lines.length, operatorMode]);

  // Modo operador: suaviza o scroll espelhado do operador.
  useEffect(() => {
    if (!operatorMode) {
      return;
    }

    const scroller = scrollerRef.current;
    if (!scroller) return;

    cancelScrollTracker(scrollTrackerRef.current);
    const max = scroller.scrollHeight - scroller.clientHeight;
    const target = max > 0 ? operatorScrollRatio * max : 0;
    const step = () => {
      const delta = target - scroller.scrollTop;
      if (Math.abs(delta) < 0.5) {
        scroller.scrollTop = target;
        operatorScrollRafRef.current = null;
        return;
      }
      scroller.scrollTop += delta * 0.2;
      operatorScrollRafRef.current = requestAnimationFrame(step);
    };

    operatorScrollRafRef.current = requestAnimationFrame(step);
    return () => {
      if (operatorScrollRafRef.current !== null) {
        cancelAnimationFrame(operatorScrollRafRef.current);
        operatorScrollRafRef.current = null;
      }
    };
  }, [operatorMode, operatorScrollRatio, lines.length, pads.top]);

  async function toggleFullscreen() {
    if (!frameRef.current) return;
    try {
      if (document.fullscreenElement === frameRef.current) {
        await document.exitFullscreen();
      } else {
        await frameRef.current.requestFullscreen();
      }
    } catch {
      /* ignore */
    }
  }

  const statusText = poppedOut
    ? "Exibido em janela externa"
    : operatorMode
      ? "Controle manual (operador)"
      : improvising
        ? "Interpretação: aguardando volta ao roteiro"
        : listening
          ? "Sincronizado (fala + operador)"
          : "Aguardando captura";

  const pointerTop = `${POINTER_RATIO * 100}%`;

  return (
    <section
      className={`flex min-h-0 min-w-0 flex-col ${
        fillWindow ? "h-full flex-1" : "flex-1"
      }`}
    >
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-current/15 px-4 py-2">
        <div>
          <h2 className="text-sm font-semibold">Ao ar</h2>
          <p className="text-xs opacity-70" role="status">
            {statusText}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {!fillWindow && onPopOut && (
            <button
              type="button"
              className="rounded-md border border-current/25 px-3 py-1.5 text-sm hover:bg-black/5 dark:hover:bg-white/10"
              onClick={onPopOut}
            >
              Destacar janela
            </button>
          )}
          <button
            type="button"
            className="rounded-md border border-current/25 px-3 py-1.5 text-sm hover:bg-black/5 dark:hover:bg-white/10"
            onClick={() => void toggleFullscreen()}
          >
            {fullscreen ? "Sair da tela cheia" : "Tela cheia 4:3"}
          </button>
        </div>
      </header>

      {poppedOut && !fillWindow ? (
        <div className="flex flex-1 items-center justify-center px-4 text-center text-sm opacity-70">
          Teleprompter ao ar aberto em outra janela.
        </div>
      ) : (
        <div
          ref={frameRef}
          className="flex min-h-0 flex-1 items-center justify-center bg-black p-3"
          onDoubleClick={() => {
            if (!fillWindow && onPopOut) onPopOut();
          }}
          title={
            fillWindow
              ? undefined
              : "Clique duas vezes para destacar em janela separada"
          }
        >
          <div
            className="relative min-h-0 w-full overflow-hidden bg-bg_white text-w_font shadow-2xl dark:bg-bg_dark dark:text-d_font"
            style={{
              aspectRatio: fillWindow ? undefined : "4 / 3",
              height: fillWindow ? "100%" : undefined,
              maxHeight: "100%",
              maxWidth: fillWindow
                ? "min(100vw, calc(100vh * 4 / 3))"
                : undefined,
            }}
          >
            <div
              ref={scrollerRef}
              className="scrollbar-none absolute inset-0 overflow-y-auto px-8 sm:px-12"
            >
              <div
                className="mx-auto flex w-full max-w-3xl flex-col leading-relaxed"
                style={{
                  fontFamily: layout.fontFamily || undefined,
                  fontSize: `${layout.fontSizePx}px`,
                  textAlign: layout.textAlign,
                  color: layout.colorNormal || undefined,
                }}
              >
                <div
                  className="shrink-0"
                  style={{ height: pads.top }}
                  aria-hidden="true"
                />
                <div>
                  <ScriptLines lines={lines} cursor={cursor} layout={layout} />
                </div>
                <div
                  className="shrink-0"
                  style={{ height: pads.bottom }}
                  aria-hidden="true"
                />
              </div>
            </div>

            {layout.pointerColor ? (
              <div
                className="pointer-events-none absolute left-3 z-10 -translate-y-1/2"
                style={{ top: pointerTop, color: layout.pointerColor }}
                aria-hidden="true"
              >
                <svg
                  width="32"
                  height="36"
                  viewBox="0 0 28 32"
                  className="drop-shadow"
                >
                  <polygon points="0,0 28,16 0,32" fill="currentColor" />
                </svg>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </section>
  );
}
