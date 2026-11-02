import { useCallback, useEffect, useRef, useState } from "react";
import type { PromptLine } from "../lib/scriptModel";
import type { TeleprompterLayout } from "../lib/teleprompterLayout";

type TeleprompterProps = {
  lines: PromptLine[];
  cursor: number;
  improvising: boolean;
  operatorMode: boolean;
  layout: TeleprompterLayout;
  activeRetrancaId?: string | null;
};

/** Alinha o topo do elemento com a linha do ponteiro (centro vertical). */
function alignTopToPointer(scroller: HTMLElement, target: HTMLElement) {
  const scrollerRect = scroller.getBoundingClientRect();
  const targetRect = target.getBoundingClientRect();
  const pointerY = scrollerRect.top + scrollerRect.height / 2;
  scroller.scrollTop += targetRect.top - pointerY;
}

export function Teleprompter({
  lines,
  cursor,
  improvising,
  operatorMode,
  layout,
  activeRetrancaId = null,
}: TeleprompterProps) {
  const frameRef = useRef<HTMLDivElement>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const lastScrolledCursorRef = useRef<number | null>(null);
  const lastRetrancaRef = useRef<string | null | undefined>(undefined);
  const [fullscreen, setFullscreen] = useState(false);
  const [viewportPad, setViewportPad] = useState(0);

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
      setViewportPad(scroller.clientHeight / 2);
    }

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(scroller);
    return () => observer.disconnect();
  }, [fullscreen, lines.length]);

  const cursorRef = useRef(cursor);
  cursorRef.current = cursor;

  useEffect(() => {
    const scroller = scrollerRef.current;
    if (!scroller || lines.length === 0 || viewportPad <= 0) return;

    lastRetrancaRef.current = activeRetrancaId;

    const target = activeRetrancaId
      ? scroller.querySelector<HTMLElement>(
          `[data-retranca-id="${activeRetrancaId}"]`,
        )
      : scroller.querySelector<HTMLElement>("[data-script-line]");

    if (!target) return;

    alignTopToPointer(scroller, target);
    requestAnimationFrame(() => {
      alignTopToPointer(scroller, target);
      lastScrolledCursorRef.current = cursorRef.current;
    });
  }, [activeRetrancaId, lines, viewportPad]);

  useEffect(() => {
    if (operatorMode || improvising) return;
    if (lastScrolledCursorRef.current === cursor) return;

    const scroller = scrollerRef.current;
    const current = scroller?.querySelector<HTMLElement>(
      '[data-current-word="true"]',
    );
    if (!scroller || !current) return;

    lastScrolledCursorRef.current = cursor;
    alignTopToPointer(scroller, current);
  }, [cursor, improvising, lines, operatorMode]);

  async function toggleFullscreen() {
    if (!frameRef.current) return;

    try {
      if (document.fullscreenElement === frameRef.current) {
        await document.exitFullscreen();
      } else {
        await frameRef.current.requestFullscreen();
      }
    } catch {
      /* o navegador pode recusar o fullscreen */
    }
  }

  return (
    <section className="flex w-full max-w-5xl flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs opacity-70" role="status">
          {improvising
            ? "Interpretação: aguardando volta ao roteiro"
            : "Acompanhando o roteiro"}
        </p>
        <button
          type="button"
          className="rounded-md border border-current/25 px-3 py-1.5 text-sm hover:bg-black/5 dark:hover:bg-white/10"
          onClick={() => void toggleFullscreen()}
        >
          {fullscreen ? "Sair da tela cheia" : "Tela cheia 4:3"}
        </button>
      </div>

      <div
        ref={frameRef}
        className={`flex items-center justify-center bg-black ${
          fullscreen ? "h-full w-full" : ""
        }`}
      >
        <div
          className="relative w-full overflow-hidden bg-bg_white text-w_font shadow-2xl dark:bg-bg_dark dark:text-d_font"
          style={{
            aspectRatio: "4 / 3",
            maxHeight: fullscreen ? "100vh" : "min(78vh, 48rem)",
            maxWidth: fullscreen
              ? "min(100vw, calc(100vh * 4 / 3))"
              : undefined,
          }}
        >
          <div
            ref={scrollerRef}
            className={`h-full w-full px-8 sm:px-12 ${
              operatorMode
                ? "overflow-y-auto scrollbar-sm"
                : "overflow-y-hidden"
            }`}
          >
            <div
              className="mx-auto flex min-h-full w-full max-w-3xl flex-col leading-relaxed"
              style={{
                fontFamily: layout.fontFamily || undefined,
                fontSize: `${layout.fontSizePx}px`,
                textAlign: layout.textAlign,
                color: layout.colorNormal || undefined,
              }}
            >
              <div
                className="shrink-0"
                style={{ height: viewportPad }}
                aria-hidden="true"
              />
              <div>
                {lines.length === 0 ? (
                  <p className="text-base opacity-60">
                    Importe um roteiro para exibir o texto completo.
                  </p>
                ) : (
                  lines.map((line) => (
                    <p
                      key={line.id}
                      className="mb-5"
                      data-script-line=""
                      data-retranca-id={line.retrancaId}
                    >
                      <span
                        className={
                          line.technical
                            ? "bg-white px-2 py-0.5 text-black"
                            : ""
                        }
                      >
                        {line.words.map((word, index) => {
                          const start = word.scriptIndex;
                          const end = word.scriptIndexEnd;
                          const isCurrent =
                            start !== null &&
                            end !== null &&
                            cursor >= start &&
                            cursor < end;
                          const isSpoken = end !== null && end <= cursor;

                          return (
                            <span
                              key={`${line.id}-${index}`}
                              data-current-word={isCurrent ? "true" : undefined}
                              style={
                                line.technical
                                  ? undefined
                                  : isSpoken
                                    ? {
                                        color: layout.colorSpoken,
                                        opacity: 0.7,
                                      }
                                    : isCurrent
                                      ? {
                                          backgroundColor: layout.colorCurrent,
                                          color: layout.colorCurrentFg,
                                        }
                                      : undefined
                              }
                            >
                              {word.display}
                              {index < line.words.length - 1 ? " " : ""}
                            </span>
                          );
                        })}
                      </span>
                    </p>
                  ))
                )}
              </div>
              <div
                className="shrink-0"
                style={{ height: viewportPad }}
                aria-hidden="true"
              />
            </div>
          </div>

          <div
            className="pointer-events-none absolute top-1/2 left-3 z-10 -translate-y-1/2"
            aria-hidden="true"
          >
            <svg
              width="32"
              height="36"
              viewBox="0 0 28 32"
              className="drop-shadow"
            >
              <polygon
                points="0,0 28,16 0,32"
                fill="currentColor"
                className="text-red-600 dark:text-red-400"
              />
            </svg>
          </div>
        </div>
      </div>
    </section>
  );
}
