"""Matching de roteiro com duas janelas deslizantes (tracking + recovery)."""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz.distance import Levenshtein

PHRASE_WINDOW = 4
RECOVERY_SCORE = 2.2
DIVERGE_SCORE = 0.9
MAX_JUMP = 4
LOOKBACK = 6
LOOKAHEAD = 14
IMPROV_LOOKAHEAD = 40
DISTANCE_PENALTY = 0.35
HYSTERESIS_TICKS = 2


@dataclass
class FollowState:
    cursor: int = 0
    improvising: bool = False


@dataclass
class FollowResult:
    state: FollowState
    status_changed: bool
    previous_improvising: bool


class ScriptMatcher:
    """Janela de tracking + janela de recuperação de improviso."""

    def __init__(self) -> None:
        self._diverge_streak = 0
        self._recover_streak = 0

    def reset(self) -> None:
        self._diverge_streak = 0
        self._recover_streak = 0

    def follow(
        self,
        script_words: list[str],
        spoken_words: list[str],
        previous: FollowState,
    ) -> FollowResult:
        if not script_words or not spoken_words:
            return FollowResult(previous, False, previous.improvising)

        cursor = previous.cursor
        improvising = previous.improvising
        previous_improvising = improvising

        if len(spoken_words) < PHRASE_WINDOW:
            last = spoken_words[-1]
            if not improvising and cursor < len(script_words):
                exact = word_similarity(script_words[cursor], last)
                nxt = (
                    word_similarity(script_words[cursor + 1], last)
                    if cursor + 1 < len(script_words)
                    else 0.0
                )
                if exact >= 0.72:
                    cursor += 1
                elif nxt >= 0.72:
                    cursor += 2
            state = FollowState(cursor=cursor, improvising=improvising)
            return FollowResult(state, False, previous_improvising)

        spoken4 = spoken_words[-PHRASE_WINDOW:]

        # Janela 1 — tracking local (ou recovery curto em improviso)
        local_from = max(0, cursor - LOOKBACK)
        local_to = min(
            len(script_words) - PHRASE_WINDOW,
            cursor + (IMPROV_LOOKAHEAD if improvising else LOOKAHEAD),
        )
        index, score = best_script_window(
            script_words,
            spoken4,
            local_from,
            local_to,
            prefer_near=cursor,
        )

        # Janela 2 — recovery ampliado se ainda fraco em improviso
        if improvising and score < RECOVERY_SCORE:
            g_index, g_score = best_script_window(
                script_words,
                spoken4,
                0,
                None,
                prefer_near=cursor,
            )
            if g_score > score or (
                g_score == score
                and g_index >= 0
                and abs(g_index - cursor) < abs(index - cursor)
            ):
                index, score = g_index, g_score

        if (
            not improvising
            and index >= 0
            and score >= RECOVERY_SCORE
            and index > cursor + MAX_JUMP
        ):
            near_to = min(len(script_words) - PHRASE_WINDOW, cursor + MAX_JUMP)
            n_index, n_score = best_script_window(
                script_words,
                spoken4,
                max(0, cursor - LOOKBACK),
                near_to,
                prefer_near=cursor,
            )
            near_competitive = n_index >= 0 and (
                n_score >= RECOVERY_SCORE * 0.85 or n_score >= score - 0.3
            )
            if near_competitive:
                index, score = n_index, n_score
            else:
                self._diverge_streak = 0
                self._recover_streak = 0
                state = FollowState(cursor=cursor, improvising=improvising)
                return FollowResult(state, False, previous_improvising)

        if score >= RECOVERY_SCORE and index >= 0:
            self._diverge_streak = 0
            self._recover_streak += 1
            if not improvising or self._recover_streak >= HYSTERESIS_TICKS:
                target = index + PHRASE_WINDOW
                if target > cursor:
                    cursor = clamp_cursor_step(cursor, target)
                improvising = False
                self._recover_streak = 0
        elif score < DIVERGE_SCORE:
            self._recover_streak = 0
            self._diverge_streak += 1
            if improvising or self._diverge_streak >= HYSTERESIS_TICKS:
                improvising = True
                self._diverge_streak = 0
        else:
            self._diverge_streak = 0
            self._recover_streak = 0

        state = FollowState(cursor=cursor, improvising=improvising)
        return FollowResult(
            state=state,
            status_changed=improvising != previous_improvising,
            previous_improvising=previous_improvising,
        )


def word_similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0

    shorter = min(len(a), len(b))
    longer = max(len(a), len(b))

    if shorter >= 3 and (a.startswith(b) or b.startswith(a)):
        ratio = shorter / longer
        if ratio >= 0.55:
            return 0.7 + 0.25 * ratio

    if abs(len(a) - len(b)) > 2:
        return 0.0

    dist = Levenshtein.distance(a, b)
    if dist == 1:
        return 0.72
    if dist == 2 and shorter >= 5:
        return 0.45
    return 0.0


def positional_score(a: list[str], b: list[str]) -> float:
    n = min(len(a), len(b))
    return sum(word_similarity(a[i], b[i]) for i in range(n))


def best_script_window(
    script_words: list[str],
    spoken4: list[str],
    from_index: int,
    to_index: int | None,
    prefer_near: int | None = None,
) -> tuple[int, float]:
    best_index = -1
    best_score = -1.0
    best_adjusted = float("-inf")

    if len(spoken4) < PHRASE_WINDOW or len(script_words) < PHRASE_WINDOW:
        return best_index, best_score

    start = max(0, from_index)
    last = min(
        len(script_words) - PHRASE_WINDOW,
        len(script_words) - PHRASE_WINDOW if to_index is None else to_index,
    )
    if start > last:
        return best_index, best_score

    anchor = prefer_near if prefer_near is not None else start
    span = max(1, last - start)

    for i in range(start, last + 1):
        window = script_words[i : i + PHRASE_WINDOW]
        score = positional_score(spoken4, window)
        adjusted = score - (abs(i - anchor) / span) * DISTANCE_PENALTY
        if adjusted > best_adjusted or (
            adjusted == best_adjusted
            and best_index >= 0
            and abs(i - anchor) < abs(best_index - anchor)
        ):
            best_index = i
            best_score = score
            best_adjusted = adjusted

    return best_index, best_score


def clamp_cursor_step(
    previous_cursor: int,
    target_cursor: int,
    max_jump: int = MAX_JUMP,
) -> int:
    if target_cursor <= previous_cursor:
        return previous_cursor
    delta = target_cursor - previous_cursor
    if delta > max_jump:
        return previous_cursor + max_jump
    return target_cursor
