import time
from dataclasses import dataclass

from app.config import get_settings
from app.services.aligner import ScriptAligner
from app.services.state_machine import StateMachine, TeleprompterState
from app.utils.logger import EventLogger, get_logger
from app.utils.text_normalizer import get_comparator

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class ScrollDecision:
    should_advance: bool
    target_index: int | None = None
    event_type: str = "next"
    segment = None
    pause_after: float = 0.0
    pause_reason: str = ""
    voice_state: str = "aguardando"


class ScrollController:
    def __init__(
        self,
        state: StateMachine,
        aligner: ScriptAligner,
        socketio,
        room_id: str,
    ):
        self.state = state
        self.aligner = aligner
        self.socketio = socketio
        self.room_id = room_id
        self.comparator = get_comparator()

        self.last_final_text = ""
        self.last_partial_processed = ""

    def get_local_candidates(self) -> list[int]:
        total = len(self.state.spoken_lines)
        current = self.state.current_spoken_index
        candidates = []
        if 0 <= current < total:
            candidates.append(current)
        for offset in range(1, 5):
            nxt = current + offset
            if nxt < total:
                candidates.append(nxt)
        prev = current - 1
        if prev >= 0:
            candidates.append(prev)
        # Deduplicate preserving order
        seen = set()
        uniq = []
        for idx in candidates:
            if idx not in seen:
                seen.add(idx)
                uniq.append(idx)
        return uniq

    def find_best_match(self, text: str) -> tuple[int | None, float, float, float, float]:
        best_idx = None
        best_score = 0.0
        best_sim = 0.0
        best_cov = 0.0
        best_rel = 0.0

        for idx in self.get_local_candidates():
            line = self.state.spoken_lines[idx]
            score, sim, cov, rel = self.comparator.weighted_score(text, line)
            if score > best_score:
                best_score = score
                best_idx = idx
                best_sim = sim
                best_cov = cov
                best_rel = rel

        return best_idx, best_score, best_sim, best_cov, best_rel

    def min_score_for_distance(self, distance: int) -> float | None:
        if distance == -1:
            return 0.82
        if distance == 0:
            return 0.55
        if distance == 1:
            return 0.68
        if distance == 2:
            return 0.82
        if distance == 3:
            return 0.88
        return None

    def get_segment_by_spoken_index(self, idx: int):
        for seg in self.state.segments:
            if seg.spoken_index == idx:
                return seg
        return None

    def segment_to_socket(self, segment) -> dict | None:
        if not segment:
            return None
        return segment.to_frontend()

    def emit_scroll_state(self, state_type: str, reason: str = "", pause_seconds: float = 0.0):
        self.socketio.emit(
            "estado_rolagem",
            {
                "tipo": state_type,
                "motivo": reason,
                "pausaSegundos": round(pause_seconds or 0.0, 2),
                "indiceFalado": self.state.current_spoken_index,
            },
            to=self.room_id,
        )

    def emit_voice_progress(
        self,
        voice_state: str,
        result_type: str,
        recognized_text: str,
        best_idx: int | None,
        score: float,
        coverage: float,
        relevance: float,
        progress: float | None = None,
        recognition_confidence: float = 0.0,
    ):
        visual_idx = None
        if best_idx is not None:
            visual_idx = self.aligner.get_visual_index(best_idx)

        if progress is None and best_idx is not None:
            progress = self.ordered_progress(recognized_text, self.state.spoken_lines[best_idx])
        progress = max(0.0, min(progress or 0.0, 1.0))

        self.socketio.emit(
            "voz_roteiro",
            {
                "estadoVoz": voice_state,
                "tipoResultado": result_type,
                "textoReconhecido": recognized_text,
                "indiceFalado": best_idx,
                "indiceVisual": visual_idx,
                "score": round(score or 0.0, 2),
                "cobertura": round(coverage or 0.0, 2),
                "relevancia": round(relevance or 0.0, 2),
                "progressoEstimado": round(progress, 2),
                "confiancaReconhecimento": round(recognition_confidence or 0.0, 2),
            },
            to=self.room_id,
        )

    def ordered_progress(self, recognized_text: str, script_line: str) -> float:
        """Estimate how far into a line the recognized words have reached."""
        spoken = self.comparator.normalizer.normalize(recognized_text).split()
        script = self.comparator.normalizer.normalize(script_line).split()
        if not spoken or not script:
            return 0.0

        # Transcript updates can revise earlier words, so align the newest
        # recognized window in order and tolerate occasional recognition errors.
        spoken = spoken[-min(len(spoken), 12):]
        matched = 0
        script_index = 0
        for word in spoken:
            for index in range(script_index, len(script)):
                if word == script[index] or self.comparator.similarity(word, script[index]) >= 0.8:
                    matched += 1
                    script_index = index + 1
                    break
        return script_index / len(script) if matched else 0.0

    def enter_improv(self, text: str):
        if not settings.habilitar_improviso if hasattr(settings, 'habilitar_improviso') else True:
            return
        normalized = self.comparator.normalizer.normalize(text)
        if len(normalized.split()) < (settings.min_palavras_improviso if hasattr(settings, 'min_palavras_improviso') else 3):
            return
        if self.state.is_improv():
            self.state.update_improv_tracking(normalized)
            return
        self.state.change_state(TeleprompterState.IMPROV)
        self.state.improv_start_time = time.time()
        self.state.last_improv_text = normalized
        logger.info(f"IMPROVISO detected: {text}")
        self.emit_scroll_state(
            "IMPROVISO",
            "Fala fora do roteiro. Aguardando retorno ao texto."
        )

    def exit_improv(self):
        if self.state.is_improv() or self.state.is_vt_or_link():
            self.state.change_state(TeleprompterState.AUTOMATIC)
            self.emit_scroll_state(
                "AUTOMATICO",
                "Fala voltou ao roteiro. Rolagem retomada."
            )

    def send_command(
        self,
        target_spoken_idx: int,
        event_type: str,
        text: str
    ) -> bool:
        total = len(self.state.spoken_lines)
        target_spoken_idx = min(target_spoken_idx, total)
        target_spoken_idx = max(target_spoken_idx, 0)

        spoken_read = target_spoken_idx - 1
        if event_type == "back":
            spoken_read = target_spoken_idx

        segment = self.get_segment_by_spoken_index(spoken_read)
        pause_after = segment.pause_after_seconds if segment else 0.0
        pause_reason = segment.pause_reason if segment else ""

        self.state.current_spoken_index = target_spoken_idx
        if self.state.spoken_to_visual_map and target_spoken_idx < len(self.state.spoken_to_visual_map):
            self.state.current_visual_index = self.state.spoken_to_visual_map[target_spoken_idx]

        if self.state.current_spoken_index >= total:
            self.state.change_state(TeleprompterState.FINISHED)
        else:
            self.exit_improv()

        self.state.last_advance_time = time.time()
        self.state.discard_buffer = True
        self.state.last_partial_text = ""
        self.state.partial_read_count = 0
        self.state.restart_partial_block = False
        self.last_partial_processed = ""

        visual_idx = self.aligner.get_visual_index(target_spoken_idx)

        payload = {
            "index": visual_idx,
            "type": event_type,
            "text": text,
            "segmento": self.segment_to_socket(segment),
            "pausaAposSegundos": round(pause_after, 2),
            "motivoPausa": pause_reason,
        }
        self.socketio.emit("cmd", payload, to=self.room_id)

        if pause_after > 0:
            self.state.change_state(TeleprompterState.VT_OR_LINK)
            self.emit_scroll_state(
                "VT_OU_LINK",
                pause_reason or "Pausa técnica após fala",
                pause_after
            )

        EventLogger.scroll_event(event_type, target_spoken_idx, visual_idx)
        return True

    def evaluate_final(self, text: str, confidence: float = 0.0) -> ScrollDecision:
        if not self.state.can_evaluate_audio():
            return ScrollDecision(False)

        total = len(self.state.spoken_lines)
        if self.state.current_spoken_index >= total:
            return ScrollDecision(False)

        if self.state.current_spoken_index >= len(self.state.spoken_lines):
            return ScrollDecision(False)
        current_line = self.state.spoken_lines[self.state.current_spoken_index]

        if self.comparator.is_noise(text, current_line):
            return ScrollDecision(False)

        normalized = self.comparator.normalizer.normalize(text)
        if normalized == self.last_final_text:
            return ScrollDecision(False)

        elapsed = time.time() - self.state.last_advance_time
        if elapsed < settings.intervalo_avanco if hasattr(settings, 'intervalo_avanco') else 0.8:
            return ScrollDecision(False)

        self.last_final_text = normalized

        # Browser confidence is sometimes unavailable (reported as 0); only
        # reject a result when the browser supplied a low, non-zero score.
        if 0 < confidence < 0.25:
            self.emit_voice_progress(
                "incerto", "FINAL", text, None, 0.0, 0.0, 0.0,
                recognition_confidence=confidence,
            )
            return ScrollDecision(False)

        best_idx, best_score, best_sim, best_cov, best_rel = self.find_best_match(text)

        logger.info(
            f"FINAL eval: idx={best_idx}, score={best_score:.2f}, "
            f"sim={best_sim:.2f}, cov={best_cov:.2f}, rel={best_rel:.2f}"
        )

        if best_idx is not None and best_score >= (settings.score_minimo_andamento_voz if hasattr(settings, 'score_minimo_andamento_voz') else 0.35):
            self.emit_voice_progress(
                "acompanhando", "FINAL", text, best_idx,
                best_score, best_cov, best_rel,
                self.ordered_progress(text, self.state.spoken_lines[best_idx])
            )

        if best_idx is None:
            self.emit_voice_progress("improviso", "FINAL", text, None, 0.0, 0.0, 0.0)
            self.enter_improv(text)
            return ScrollDecision(False)

        distance = best_idx - self.state.current_spoken_index

        if distance < -1:
            self.emit_voice_progress("improviso", "FINAL", text, best_idx, best_score, best_cov, best_rel)
            self.enter_improv(text)
            return ScrollDecision(False)

        min_threshold = self.min_score_for_distance(distance)

        if min_threshold is None:
            logger.warning(f"Possible jump blocked: distance={distance}")
            self.emit_voice_progress("improviso", "FINAL", text, best_idx, best_score, best_cov, best_rel)
            self.enter_improv(text)
            return ScrollDecision(False)

        if round(best_score, 2) < round(min_threshold, 2):
            logger.info(f"Score below threshold: {best_score:.2f} < {min_threshold:.2f} (dist={distance})")
            self.emit_voice_progress("improviso", "FINAL", text, best_idx, best_score, best_cov, best_rel)
            self.enter_improv(text)
            return ScrollDecision(False)

        # Voice returned to script
        self.emit_voice_progress("retomou", "FINAL", text, best_idx, best_score, best_cov, best_rel)
        self.exit_improv()

        if best_idx == self.state.current_spoken_index:
            return ScrollDecision(True, self.state.current_spoken_index + 1, "next",
                                 self.get_segment_by_spoken_index(self.state.current_spoken_index))

        if best_idx > self.state.current_spoken_index:
            return ScrollDecision(True, best_idx + 1, "next",
                                 self.get_segment_by_spoken_index(best_idx))

        if best_idx == self.state.current_spoken_index - 1:
            return ScrollDecision(True, best_idx, "back",
                                 self.get_segment_by_spoken_index(best_idx))

        return ScrollDecision(False)

    def evaluate_partial(self, text: str, allow_advance: bool = True) -> bool:
        if not self.state.can_evaluate_audio():
            return False

        normalized = self.comparator.normalizer.normalize(text)

        if normalized == self.last_partial_processed:
            return False

        if len(normalized) <= len(self.last_partial_processed) + 2:
            return False

        self.last_partial_processed = normalized

        if self.state.current_spoken_index >= len(self.state.spoken_lines):
            return False
        current_line = self.state.spoken_lines[self.state.current_spoken_index]
        current_normalized = self.comparator.normalizer.normalize(current_line)

        if not self.comparator.has_relevant_word_match(normalized, current_normalized):
            return False

        if len(normalized) < len(self.state.last_partial_text):
            self.state.last_partial_text = normalized
            self.state.partial_read_count = 0
            self.state.restart_partial_block = True
            return False

        self.state.last_partial_text = normalized

        if self.state.restart_partial_block:
            self.state.partial_read_count = 0
            self.state.restart_partial_block = False

        score, sim, cov, rel = self.comparator.weighted_score(text, current_line)

        logger.debug(
            f"PARTIAL eval: score={score:.2f}, sim={sim:.2f}, cov={cov:.2f}, rel={rel:.2f}"
        )

        threshold = settings.score_minimo_andamento_voz if hasattr(settings, 'score_minimo_andamento_voz') else 0.35
        if score >= threshold:
            voice_state = "retomou" if self.state.is_improv() or self.state.is_vt_or_link() else "acompanhando"
            self.emit_voice_progress(
                voice_state, "PARCIAL", text, self.state.current_spoken_index,
                score, cov, rel,
                self.ordered_progress(text, current_line)
            )
            if voice_state == "retomou":
                self.exit_improv()
        else:
            self.emit_voice_progress("improviso", "PARCIAL", text, self.state.current_spoken_index, score, cov, rel)

        if score >= 0.72:
            self.state.partial_read_count += 1
        else:
            self.state.partial_read_count = 0

        if self.state.partial_read_count >= 2:
            self.state.last_partial_text = ""
            self.state.partial_read_count = 0

            if not allow_advance:
                return False

            return self.send_command(
                self.state.current_spoken_index + 1,
                "next",
                current_line
            )

        return False
