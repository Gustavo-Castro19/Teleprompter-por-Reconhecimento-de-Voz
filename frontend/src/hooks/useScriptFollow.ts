import { useEffect, useMemo, useState } from "react";
import {
  flattenProgram,
  tokenizeSpoken,
  type PromptLine,
  type RetrancaMarker,
} from "../lib/scriptModel";
import {
  followSpokenScript,
  type FollowState,
} from "../lib/speechScriptMatcher";
import type { Program } from "../service/api";

/** Evita reprocessar transcript enorme a cada interim. */
const SPOKEN_TAIL = 32;

export function useScriptFollow(
  program: Program | null,
  transcript: string,
  anchorWordIndex: number,
): FollowState & {
  scriptWords: string[];
  lines: PromptLine[];
  markers: RetrancaMarker[];
} {
  const prepared = useMemo(
    () =>
      program
        ? flattenProgram(program)
        : { lines: [], scriptWords: [], markers: [] },
    [program],
  );

  const [follow, setFollow] = useState<FollowState>({
    cursor: 0,
    improvising: false,
  });

  useEffect(() => {
    const cursor = Math.max(
      0,
      Math.min(anchorWordIndex, Math.max(prepared.scriptWords.length, 0)),
    );
    setFollow({ cursor, improvising: false });
  }, [program, anchorWordIndex, prepared.scriptWords.length]);

  useEffect(() => {
    if (!transcript.trim()) return;

    const spoken = tokenizeSpoken(transcript).slice(-SPOKEN_TAIL);
    setFollow((previous) =>
      followSpokenScript(prepared.scriptWords, spoken, previous),
    );
  }, [prepared.scriptWords, transcript]);

  return {
    ...follow,
    scriptWords: prepared.scriptWords,
    lines: prepared.lines,
    markers: prepared.markers,
  };
}
