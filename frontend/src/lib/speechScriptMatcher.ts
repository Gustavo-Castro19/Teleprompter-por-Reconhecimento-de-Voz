const PHRASE_WINDOW = 4;
/** Score fuzzy (0–4) para recuperar / sair de improviso. */
const RECOVERY_SCORE = 2.2;
/** Só improvisa com match claramente péssimo — tolerância maior no roteiro. */
const DIVERGE_SCORE = 0.9;
/** Limite de avanço do cursor por passo (evita saltos abruptos). */
const MAX_JUMP = 4;
/** Janela local preferida em torno do cursor. */
const LOOKBACK = 6;
const LOOKAHEAD = 14;
/** Em improviso, busca um pouco mais à frente antes de varrer o roteiro todo. */
const IMPROV_LOOKAHEAD = 40;
/** Penalidade máxima no score por distância ao cursor (0–0.35). */
const DISTANCE_PENALTY = 0.35;
/** Ticks seguidos exigidos para entrar/sair de improviso (anti-flicker ASR). */
const HYSTERESIS_TICKS = 2;

export type FollowState = {
  cursor: number;
  improvising: boolean;
};

export const INITIAL_FOLLOW_STATE: FollowState = {
  cursor: 0,
  improvising: false,
};

/** Histerese de improviso — módulo único (um teleprompter por app). */
let divergeStreak = 0;
let recoverStreak = 0;

export function resetFollowHysteresis() {
  divergeStreak = 0;
  recoverStreak = 0;
}

/** Distância de edição (Levenshtein) limitada — palavras curtas / ASR. */
function editDistance(a: string, b: string): number {
  if (a === b) return 0;
  const m = a.length;
  const n = b.length;
  if (m === 0) return n;
  if (n === 0) return m;

  let prev = new Array<number>(n + 1);
  let curr = new Array<number>(n + 1);
  for (let j = 0; j <= n; j++) prev[j] = j;

  for (let i = 1; i <= m; i++) {
    curr[0] = i;
    for (let j = 1; j <= n; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      curr[j] = Math.min(
        prev[j] + 1,
        curr[j - 1] + 1,
        prev[j - 1] + cost,
      );
    }
    [prev, curr] = [curr, prev];
  }
  return prev[n];
}

/** Similaridade 0–1 entre tokens (exato, prefixo parcial ou 1–2 edições). */
export function wordSimilarity(a: string, b: string): number {
  if (a === b) return 1;
  if (!a || !b) return 0;

  const shorter = Math.min(a.length, b.length);
  const longer = Math.max(a.length, b.length);

  // ASR interim costuma truncar: "teleprom" ≈ "teleprompter"
  if (shorter >= 3 && (a.startsWith(b) || b.startsWith(a))) {
    const ratio = shorter / longer;
    if (ratio >= 0.55) return 0.7 + 0.25 * ratio;
  }

  if (Math.abs(a.length - b.length) > 2) return 0;

  const dist = editDistance(a, b);
  if (dist === 1) return 0.72;
  if (dist === 2 && shorter >= 5) return 0.45;
  return 0;
}

/** Score fuzzy posicional (máx ≈ PHRASE_WINDOW). Mantém export do nome legado. */
export function positionalScore(a: string[], b: string[]): number {
  const n = Math.min(a.length, b.length);
  let score = 0;
  for (let i = 0; i < n; i++) {
    score += wordSimilarity(a[i], b[i]);
  }
  return score;
}

export function bestScriptWindow(
  scriptWords: string[],
  spoken4: string[],
  fromIndex: number,
  toIndex?: number,
  /** Em empate / ranking, prefere a janela mais próxima deste índice (cursor). */
  preferNear?: number,
): { index: number; score: number } {
  let best = { index: -1, score: -1, adjusted: -Infinity };

  if (spoken4.length < PHRASE_WINDOW || scriptWords.length < PHRASE_WINDOW) {
    return { index: best.index, score: best.score };
  }

  const start = Math.max(0, fromIndex);
  const last = Math.min(
    scriptWords.length - PHRASE_WINDOW,
    toIndex ?? scriptWords.length - PHRASE_WINDOW,
  );

  if (start > last) return { index: best.index, score: best.score };

  const anchor = preferNear ?? start;
  const span = Math.max(1, last - start);

  for (let i = start; i <= last; i++) {
    const window = scriptWords.slice(i, i + PHRASE_WINDOW);
    const score = positionalScore(spoken4, window);
    // Matches distantes precisam ser bem melhores para vencer.
    const adjusted =
      score - (Math.abs(i - anchor) / span) * DISTANCE_PENALTY;

    if (
      adjusted > best.adjusted ||
      (adjusted === best.adjusted &&
        best.index >= 0 &&
        Math.abs(i - anchor) < Math.abs(best.index - anchor))
    ) {
      best = { index: i, score, adjusted };
    }
  }

  return { index: best.index, score: best.score };
}

/** Cursor monotônico: só avança (até maxJump); nunca recua. */
function clampCursorStep(
  previousCursor: number,
  targetCursor: number,
  maxJump: number = MAX_JUMP,
): number {
  if (targetCursor <= previousCursor) return previousCursor;
  const delta = targetCursor - previousCursor;
  if (delta > maxJump) return previousCursor + maxJump;
  return targetCursor;
}

/**
 * Acompanha o roteiro com métrica fuzzy de 4 palavras:
 * score >= RECOVERY → no roteiro / recupera; score < DIVERGE → improvisa;
 * entre os dois → mantém estado. Improviso exige HYSTERESIS_TICKS consecutivos.
 */
export function followSpokenScript(
  scriptWords: string[],
  spokenWords: string[],
  previous: FollowState = INITIAL_FOLLOW_STATE,
): FollowState {
  if (scriptWords.length === 0 || spokenWords.length === 0) {
    return previous;
  }

  let { cursor, improvising } = previous;

  // Com menos de 4 palavras: avanço simples sem togglear improviso.
  if (spokenWords.length < PHRASE_WINDOW) {
    const last = spokenWords[spokenWords.length - 1];
    if (!improvising && cursor < scriptWords.length) {
      const exact = wordSimilarity(scriptWords[cursor], last);
      const next =
        cursor + 1 < scriptWords.length
          ? wordSimilarity(scriptWords[cursor + 1], last)
          : 0;

      if (exact >= 0.72) {
        cursor += 1;
      } else if (next >= 0.72) {
        cursor += 2;
      }
    }

    console.log("[follow]", { score: null, cursor, improvising, mode: "warmup" });
    return { cursor, improvising };
  }

  const spoken4 = spokenWords.slice(-PHRASE_WINDOW);

  // Preferência forte por busca local; global só se improviso + match local fraco.
  const localFrom = Math.max(0, cursor - LOOKBACK);
  const localTo = Math.min(
    scriptWords.length - PHRASE_WINDOW,
    cursor + (improvising ? IMPROV_LOOKAHEAD : LOOKAHEAD),
  );

  let { index, score } = bestScriptWindow(
    scriptWords,
    spoken4,
    localFrom,
    localTo,
    cursor,
  );

  if (improvising && score < RECOVERY_SCORE) {
    const global = bestScriptWindow(scriptWords, spoken4, 0, undefined, cursor);
    if (
      global.score > score ||
      (global.score === score &&
        global.index >= 0 &&
        Math.abs(global.index - cursor) < Math.abs(index - cursor))
    ) {
      index = global.index;
      score = global.score;
    }
  }

  // Fora de improviso: rejeita salto futuro se o match próximo não for competitivo.
  if (
    !improvising &&
    index >= 0 &&
    score >= RECOVERY_SCORE &&
    index > cursor + MAX_JUMP
  ) {
    const nearTo = Math.min(
      scriptWords.length - PHRASE_WINDOW,
      cursor + MAX_JUMP,
    );
    const near = bestScriptWindow(
      scriptWords,
      spoken4,
      Math.max(0, cursor - LOOKBACK),
      nearTo,
      cursor,
    );
    const nearCompetitive =
      near.index >= 0 &&
      (near.score >= RECOVERY_SCORE * 0.85 || near.score >= score - 0.3);

    if (nearCompetitive) {
      index = near.index;
      score = near.score;
    } else {
      // Mantém cursor — não rastejar em direção a uma frase falsa à frente.
      divergeStreak = 0;
      recoverStreak = 0;
      console.log("[follow]", {
        score,
        windowIndex: index,
        cursor,
        improvising,
        mode: "reject-far",
      });
      return { cursor, improvising };
    }
  }

  if (score >= RECOVERY_SCORE && index >= 0) {
    divergeStreak = 0;
    recoverStreak += 1;
    if (!improvising || recoverStreak >= HYSTERESIS_TICKS) {
      const target = index + PHRASE_WINDOW;
      // Match atrás do cursor (frase já lida / ASR revisado): fica no roteiro, sem recuar.
      if (target > cursor) {
        cursor = clampCursorStep(cursor, target);
      }
      improvising = false;
      recoverStreak = 0;
    }
  } else if (score < DIVERGE_SCORE) {
    recoverStreak = 0;
    divergeStreak += 1;
    if (improvising || divergeStreak >= HYSTERESIS_TICKS) {
      improvising = true;
      divergeStreak = 0;
    }
  } else {
    // Faixa intermediária → mantém; zera streaks parciais.
    divergeStreak = 0;
    recoverStreak = 0;
  }

  console.log("[follow]", { score, windowIndex: index, cursor, improvising });
  return { cursor, improvising };
}
