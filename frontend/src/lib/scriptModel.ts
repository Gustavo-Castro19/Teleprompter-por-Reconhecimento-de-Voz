import type { Block, Program } from "../service/api";

export type PromptWord = {
  display: string;
  /** Índice da primeira palavra do roteiro coberta por este token visual. */
  scriptIndex: number | null;
  /** Exclusivo: fim do intervalo no roteiro (para tokens com hífen). */
  scriptIndexEnd: number | null;
};

export type PromptLine = {
  id: number;
  text: string;
  technical: boolean;
  words: PromptWord[];
  /** Marcador RETRANCA na primeira linha do bloco, se houver. */
  retrancaId?: string;
};

export type PreparedScript = {
  lines: PromptLine[];
  scriptWords: string[];
  markers: RetrancaMarker[];
};

export type RetrancaMarker = {
  id: string;
  title: string;
  pg_index: string;
  startWordIndex: number;
  startLineId: number;
};

const COMMAND_PATTERN = /\{\{[\s\S]*?\}\}/;

export function isCommandText(text: string): boolean {
  return COMMAND_PATTERN.test(text.trim());
}

export function normalizeWord(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{M}+/gu, "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "");
}

export function tokenizeDisplay(text: string): string[] {
  return text.split(/\s+/).filter(Boolean);
}

/** Partes de matching (espaço e hífen) usadas na fala. */
export function tokenizeSpoken(text: string): string[] {
  return text
    .split(/[\s/\-–—]+/)
    .map(normalizeWord)
    .filter(Boolean);
}

function appendBlockLines(
  block: Block,
  lines: PromptLine[],
  scriptWords: string[],
  lineIdStart: number,
  retrancaId?: string,
): number {
  let lineId = lineIdStart;
  let isFirstLine = true;

  for (const subblock of block.subblocks) {
    for (const text of subblock.lines) {
      const technical =
        subblock.type === "technical" || isCommandText(text);
      const displayWords = tokenizeDisplay(text);
      const words: PromptWord[] = displayWords.map((display) => {
        if (technical) {
          return {
            display,
            scriptIndex: null,
            scriptIndexEnd: null,
          };
        }

        const parts = display
          .split(/[/\-–—]+/)
          .map(normalizeWord)
          .filter(Boolean);

        if (parts.length === 0) {
          return {
            display,
            scriptIndex: null,
            scriptIndexEnd: null,
          };
        }

        const scriptIndex = scriptWords.length;
        for (const part of parts) {
          scriptWords.push(part);
        }

        return {
          display,
          scriptIndex,
          scriptIndexEnd: scriptIndex + parts.length,
        };
      });

      lines.push({
        id: lineId++,
        text,
        technical,
        words,
        retrancaId: isFirstLine ? retrancaId : undefined,
      });
      isFirstLine = false;
    }
  }

  return lineId;
}

/** Concatena todos os blocos do programa em um roteiro único com marcadores RETRANCA. */
export function flattenProgram(program: Program): PreparedScript {
  const lines: PromptLine[] = [];
  const scriptWords: string[] = [];
  const markers: RetrancaMarker[] = [];
  let lineId = 0;

  program.blocks.forEach((block, blockIndex) => {
    const id = `${blockIndex}`;
    const startLineId = lineId;
    const startWordIndex = scriptWords.length;
    const title =
      block.program_name?.trim() ||
      program.name ||
      "Retranca sem nome";

    markers.push({
      id,
      title,
      pg_index: block.pg_index ?? "",
      startWordIndex,
      startLineId,
    });

    lineId = appendBlockLines(
      block,
      lines,
      scriptWords,
      lineId,
      id,
    );
  });

  return { lines, scriptWords, markers };
}

export function listRetrancas(program: Program | null): RetrancaMarker[] {
  if (!program) return [];
  return flattenProgram(program).markers;
}
