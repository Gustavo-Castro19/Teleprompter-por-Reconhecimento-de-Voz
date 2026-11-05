/** Fração da altura do viewport onde fica o ponteiro (altura dos olhos). */
export const POINTER_RATIO = 0.38;

/** Lerp por frame — mais baixo = mais inércia, menos “pulo” a cada palavra. */
export const SCROLL_LERP = 0.12;

/** Teto de px/frame quando o alvo salta longe (evita teleporte residual). */
const SCROLL_MAX_PX_PER_FRAME = 24;

const SCROLL_EPSILON_PX = 0.5;

export type ScrollRafRef = { current: number | null };

/** Tracker contínuo: atualiza o alvo sem cancelar o loop rAF. */
export type ScrollTracker = {
  raf: ScrollRafRef;
  target: { current: HTMLElement | null };
  scroller: { current: HTMLElement | null };
  ratio: number;
  lerp: number;
};

export function createScrollTracker(
  ratio: number = POINTER_RATIO,
  lerp: number = SCROLL_LERP,
): ScrollTracker {
  return {
    raf: { current: null },
    target: { current: null },
    scroller: { current: null },
    ratio,
    lerp,
  };
}

/** Alinha o topo do elemento com a linha do ponteiro no scroller (instantâneo). */
export function alignTopToPointer(
  scroller: HTMLElement,
  target: HTMLElement,
  ratio: number = POINTER_RATIO,
) {
  const scrollerRect = scroller.getBoundingClientRect();
  const targetRect = target.getBoundingClientRect();
  const pointerY = scrollerRect.top + scrollerRect.height * ratio;
  scroller.scrollTop += targetRect.top - pointerY;
}

function stopTracker(tracker: ScrollTracker) {
  if (tracker.raf.current !== null) {
    cancelAnimationFrame(tracker.raf.current);
    tracker.raf.current = null;
  }
}

/**
 * Aponta o tracker para um novo alvo. Se o loop já estiver rodando, só troca o alvo;
 * senão inicia um único rAF contínuo.
 */
export function trackAlignToPointer(
  tracker: ScrollTracker,
  scroller: HTMLElement,
  target: HTMLElement,
) {
  tracker.scroller.current = scroller;
  tracker.target.current = target;

  if (tracker.raf.current !== null) return;

  const step = () => {
    const scrollerEl = tracker.scroller.current;
    const targetEl = tracker.target.current;

    if (
      !scrollerEl?.isConnected ||
      !targetEl?.isConnected
    ) {
      tracker.raf.current = null;
      return;
    }

    const scrollerRect = scrollerEl.getBoundingClientRect();
    const targetRect = targetEl.getBoundingClientRect();
    const pointerY =
      scrollerRect.top + scrollerRect.height * tracker.ratio;
    const delta = targetRect.top - pointerY;

    if (Math.abs(delta) < SCROLL_EPSILON_PX) {
      scrollerEl.scrollTop += delta;
      tracker.raf.current = null;
      return;
    }

    const stepPx = Math.sign(delta) * Math.min(
      Math.abs(delta) * tracker.lerp,
      SCROLL_MAX_PX_PER_FRAME,
    );
    // Garante progresso mínimo de ~1px para não “grudar” em deltas pequenos.
    const moved =
      Math.abs(stepPx) < 1 ? Math.sign(delta) * Math.min(1, Math.abs(delta)) : stepPx;
    scrollerEl.scrollTop += moved;
    tracker.raf.current = requestAnimationFrame(step);
  };

  tracker.raf.current = requestAnimationFrame(step);
}

/** Cancela o loop e limpa o alvo (ex.: troca de retranca / unmount). */
export function cancelScrollTracker(tracker: ScrollTracker) {
  stopTracker(tracker);
  tracker.target.current = null;
}

/**
 * Compat: inicia alinhamento suave. Preferir trackAlignToPointer para follow contínuo.
 * Ainda cancela o frame anterior (uso pontual).
 */
export function smoothAlignTopToPointer(
  scroller: HTMLElement,
  target: HTMLElement,
  rafRef: ScrollRafRef,
  ratio: number = POINTER_RATIO,
  lerp: number = SCROLL_LERP,
) {
  if (rafRef.current !== null) {
    cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
  }

  const step = () => {
    if (!scroller.isConnected || !target.isConnected) {
      rafRef.current = null;
      return;
    }

    const scrollerRect = scroller.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    const pointerY = scrollerRect.top + scrollerRect.height * ratio;
    const delta = targetRect.top - pointerY;

    if (Math.abs(delta) < SCROLL_EPSILON_PX) {
      scroller.scrollTop += delta;
      rafRef.current = null;
      return;
    }

    const stepPx = Math.sign(delta) * Math.min(
      Math.abs(delta) * lerp,
      SCROLL_MAX_PX_PER_FRAME,
    );
    const moved =
      Math.abs(stepPx) < 1 ? Math.sign(delta) * Math.min(1, Math.abs(delta)) : stepPx;
    scroller.scrollTop += moved;
    rafRef.current = requestAnimationFrame(step);
  };

  rafRef.current = requestAnimationFrame(step);
}

export function pointerPads(scrollerHeight: number, ratio: number = POINTER_RATIO) {
  return {
    top: scrollerHeight * ratio,
    bottom: scrollerHeight * (1 - ratio),
  };
}
