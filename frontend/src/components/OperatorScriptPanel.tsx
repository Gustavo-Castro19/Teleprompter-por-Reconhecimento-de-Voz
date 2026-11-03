import { useEffect, useRef, useState } from "react";
import {
  alignTopToPointer,
  POINTER_RATIO,
  pointerPads,
} from "../lib/alignToPointer";
import type { PromptLine } from "../lib/scriptModel";
import type { TeleprompterLayout } from "../lib/teleprompterLayout";
import { ScriptLines } from "./ScriptLines";

export type OperatorScrollSync = {
  lineId: number | null;
  ratio: number;
};

type OperatorScriptPanelProps = {
  lines: PromptLine[];
  cursor: number;
  layout: TeleprompterLayout;
  activeRetrancaId: string | null;
  onScrollSync: (sync: OperatorScrollSync) => void;
};

function findFocusLineId(scroller: HTMLElement): number | null {
  const mid =
    scroller.getBoundingClientRect().top +
    scroller.clientHeight * POINTER_RATIO;
  const nodes = scroller.querySelectorAll<HTMLElement>("[data-line-id]");
  let best: { id: number; dist: number } | null = null;

  for (const node of nodes) {
    const rect = node.getBoundingClientRect();
    const center = rect.top + rect.height / 2;
    const dist = Math.abs(center - mid);
    const id = Number(node.dataset.lineId);
    if (Number.isNaN(id)) continue;
    if (!best || dist < best.dist) {
      best = { id, dist };
    }
  }

  return best?.id ?? null;
}

function scrollRatio(scroller: HTMLElement): number {
  const max = scroller.scrollHeight - scroller.clientHeight;
  if (max <= 0) return 0;
  return Math.min(1, Math.max(0, scroller.scrollTop / max));
}

export function OperatorScriptPanel({
  lines,
  cursor,
  layout,
  activeRetrancaId,
  onScrollSync,
}: OperatorScriptPanelProps) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const lastRetrancaRef = useRef<string | null | undefined>(undefined);
  const lastScriptLenRef = useRef(0);
  const rafRef = useRef<number | null>(null);
  const [pads, setPads] = useState({ top: 0, bottom: 0 });

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
  }, [lines.length]);

  useEffect(() => {
    const scroller = scrollerRef.current;
    if (!scroller || lines.length === 0 || pads.top <= 0) return;

    const scriptChanged = lastScriptLenRef.current !== lines.length;
    if (!scriptChanged && activeRetrancaId === lastRetrancaRef.current) {
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

    alignTopToPointer(scroller, target);
    requestAnimationFrame(() => {
      alignTopToPointer(scroller, target);
      onScrollSync({
        lineId: findFocusLineId(scroller),
        ratio: scrollRatio(scroller),
      });
    });
  }, [activeRetrancaId, lines.length, pads.top, onScrollSync]);

  useEffect(() => {
    const scroller = scrollerRef.current;
    if (!scroller) return;

    function emitSync() {
      rafRef.current = null;
      if (!scrollerRef.current) return;
      onScrollSync({
        lineId: findFocusLineId(scrollerRef.current),
        ratio: scrollRatio(scrollerRef.current),
      });
    }

    function onScroll() {
      if (rafRef.current !== null) return;
      rafRef.current = requestAnimationFrame(emitSync);
    }

    scroller.addEventListener("scroll", onScroll, { passive: true });
    emitSync();

    return () => {
      scroller.removeEventListener("scroll", onScroll);
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [onScrollSync, lines.length]);

  const pointerTop = `${POINTER_RATIO * 100}%`;

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col border-r border-current/20">
      <header className="flex shrink-0 items-center justify-between border-b border-current/15 px-4 py-2">
        <h2 className="text-sm font-semibold">Operador</h2>
        <p className="text-xs opacity-70">Scroll livre</p>
      </header>
      <div className="relative min-h-0 flex-1">
        <div
          ref={scrollerRef}
          className="scrollbar-sm absolute inset-0 overflow-y-auto px-6 py-4 pl-10"
        >
          <div
            className="mx-auto max-w-2xl leading-relaxed"
            style={{
              fontFamily: layout.fontFamily || undefined,
              fontSize: `${Math.max(16, Math.round(layout.fontSizePx * 0.7))}px`,
              textAlign: layout.textAlign,
              color: layout.colorNormal || undefined,
            }}
          >
            <div
              className="shrink-0"
              style={{ height: pads.top }}
              aria-hidden="true"
            />
            <ScriptLines lines={lines} cursor={cursor} layout={layout} />
            <div
              className="shrink-0"
              style={{ height: pads.bottom }}
              aria-hidden="true"
            />
          </div>
        </div>
        {layout.pointerColor ? (
          <div
            className="pointer-events-none absolute left-2 z-10 -translate-y-1/2"
            style={{ top: pointerTop, color: layout.pointerColor }}
            aria-hidden="true"
          >
            <svg
              width="24"
              height="28"
              viewBox="0 0 28 32"
              className="drop-shadow"
            >
              <polygon points="0,0 28,16 0,32" fill="currentColor" />
            </svg>
          </div>
        ) : null}
      </div>
    </section>
  );
}
