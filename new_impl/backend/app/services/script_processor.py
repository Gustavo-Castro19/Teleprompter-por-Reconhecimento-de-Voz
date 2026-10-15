import json
import os
import re
from typing import Any
from dataclasses import dataclass

from app.config import get_settings
from app.models import ScriptSegment, VisualLineMeta
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class BlockResult:
    visual_lines: list[str]
    visual_line_types: list[str]
    spoken_lines: list[str]
    spoken_to_visual_map: list[int]
    next_visual_index: int


class ScriptProcessor:
    TECHNICAL_WORDS = (
        "ABRE SOM", "ABRE IMAG", "RODA VT", "RODA IMAGEM", "RODA IMAGENS",
        "VINHETA", "INTERVALO", "LINK NO AR", "IMAGENS//OFF", "GLOBODRONE",
        "LOCUTOR", "MOSAIC", "PROC.", "DEIXA:",
    )

    PAUSE_TRIGGERS = (
        "ABRE SOM VT", "RODA VT", "ABRE SOM LINK", "LINK NO AR", "NARRA VIVO",
        "RODA IMAGEM", "RODA IMAGENS", "IMAGENS NO AR", "GLOBODRONE",
        "VINHETA", "INTERVALO", "ABRE SOM VINHETA",
    )

    SEPARATOR_PATTERN = re.compile(r"^[=\-_/\\ ]+$")
    COMMAND_PATTERN = re.compile(r"^\{\{.*\}\}$")
    BRACE_PATTERN = re.compile(r"^\{.*\}$")
    BRACKET_PATTERN = re.compile(r"^\[.*\]$")
    PAREN_PATTERN = re.compile(r"^\(.*\)$")
    PI_TAG_PATTERN = re.compile(r"<pi\b[^>]*>.*?</pi>", re.IGNORECASE | re.DOTALL)
    CC_TAG_PATTERN = re.compile(r"<cc\b[^>]*>.*?</cc>", re.IGNORECASE | re.DOTALL)
    HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
    MULTI_SPACE_PATTERN = re.compile(r"\s+")

    def __init__(self):
        self.visual_lines: list[str] = []
        self.visual_line_types: list[str] = []
        self.spoken_lines: list[str] = []
        self.spoken_to_visual_map: list[int] = []
        self.segments: list[ScriptSegment] = []
        self.visual_metadata: list[VisualLineMeta] = []

    def ensure_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        return str(value)

    def to_seconds(self, value: Any) -> float:
        try:
            if value is None:
                return 0.0
            text = str(value).strip()
            if not text:
                return 0.0
            return float(text)
        except (ValueError, TypeError):
            return 0.0

    def clean_spaces(self, text: str) -> str:
        return self.MULTI_SPACE_PATTERN.sub(" ", text or "").strip()

    def count_words(self, text: str) -> int:
        text = self.clean_spaces(text)
        if not text:
            return 0
        return len(re.findall(r"[A-Za-zÀ-ÿ0-9]+", text))

    def remove_html_preserve_text(self, text: str) -> str:
        if not text:
            return ""
        text = self.ensure_text(text)
        text = text.replace("\r\r\n", "\n").replace("\r", "\n")
        text = self.HTML_TAG_PATTERN.sub("\n", text)
        return text

    def remove_technical_for_spoken(self, text: str) -> str:
        if not text:
            return ""
        text = self.ensure_text(text)
        text = text.replace("\r\r\n", "\n").replace("\r", "\n")
        text = self.PI_TAG_PATTERN.sub(" ", text)
        text = self.HTML_TAG_PATTERN.sub("\n", text)
        text = self.COMMAND_PATTERN.sub(" ", text)
        text = self.BRACE_PATTERN.sub(" ", text)
        text = self.BRACKET_PATTERN.sub(" ", text)
        text = text.replace("/", " ")
        text = text.replace("=", " ")
        return text

    def is_separator(self, line: str) -> bool:
        if not line:
            return False
        return bool(self.SEPARATOR_PATTERN.fullmatch(line.strip()))

    def is_technical(self, line: str) -> bool:
        if not line:
            return False
        line = line.strip()
        if self.is_separator(line):
            return True
        if self.COMMAND_PATTERN.match(line):
            return True
        if self.BRACE_PATTERN.match(line):
            return True
        if self.BRACKET_PATTERN.match(line):
            return True
        if self.PAREN_PATTERN.match(line):
            return True
        upper = line.upper()
        return any(word in upper for word in self.TECHNICAL_WORDS)

    def is_pause_command(self, line: str) -> bool:
        if not line:
            return False
        upper = line.upper()
        return any(trigger in upper for trigger in self.PAUSE_TRIGGERS)

    def classify_visual_line(self, line: str) -> str:
        if self.is_separator(line):
            return "separador"
        if self.is_pause_command(line):
            return "pausa_tecnica"
        if self.is_technical(line):
            return "tecnico"
        return "fala"

    def is_spoken_line(self, text: str) -> bool:
        if not text:
            return False
        text = text.strip()
        if len(text) < 2:
            return False
        if self.is_technical(text):
            return False
        if self.is_separator(text):
            return False
        if not re.search(r"[A-Za-zÀ-ÿ]", text):
            return False
        return True

    def extract_slug_meta(self, slug: dict) -> dict:
        return {
            "slug_id": slug.get("id") or slug.get("storyId"),
            "title": self.clean_spaces(slug.get("title", "")),
            "page": self.clean_spaces(slug.get("page", "")),
            "item_type": self.clean_spaces(slug.get("itemType", "")),
            "presenter": self.clean_spaces(slug.get("presenter", "")),
            "slug_order": slug.get("order"),
            "speaking_time": self.to_seconds(slug.get("speakingTime")),
            "tape_time": self.to_seconds(slug.get("tapeTime")),
            "total_time": self.to_seconds(slug.get("totalTime")),
            "start_time": slug.get("startTime"),
        }

    def estimate_reading_time(self, text: str, wpm: int | None = None) -> float:
        text = self.clean_spaces(text)
        if not text:
            return 0.0
        if wpm is None:
            wpm = settings.palavras_por_minuto_base
        words = self.count_words(text)
        return (words / wpm) * 60

    def distribute_speaking_time(self, spoken_lines: list[str], speaking_time: float) -> list[float]:
        if not spoken_lines:
            return []
        total_words = sum(self.count_words(line) for line in spoken_lines)
        if speaking_time > 0 and total_words > 0:
            return [
                round((self.count_words(line) / total_words) * speaking_time, 2)
                for line in spoken_lines
            ]
        return [round(self.estimate_reading_time(line), 2) for line in spoken_lines]

    def get_technical_pause(self, meta: dict) -> tuple[float, str]:
        tape_time = meta["tape_time"]
        total_time = meta["total_time"]
        speaking_time = meta["speaking_time"]
        if tape_time > 0:
            return tape_time, "tapeTime_json"
        if speaking_time <= 0 and total_time > 0:
            return total_time, "totalTime_json_sem_fala"
        return 0.0, ""

    def process_text_block(self, raw_text: str, visual_index_start: int) -> BlockResult:
        raw_text = self.ensure_text(raw_text)

        visual_text = self.remove_html_preserve_text(raw_text)
        spoken_text = self.remove_technical_for_spoken(raw_text)

        visual_raw_lines = visual_text.split("\n")
        spoken_raw_lines = spoken_text.split("\n")

        visual_lines: list[str] = []
        visual_types: list[str] = []
        spoken_lines: list[str] = []
        spoken_to_visual: list[int] = []

        visual_idx = visual_index_start

        for line_idx, visual_line in enumerate(visual_raw_lines):
            visual_line = self.clean_spaces(visual_line)
            if not visual_line:
                continue

            visual_lines.append(visual_line)
            visual_types.append(self.classify_visual_line(visual_line))

            current_visual_idx = visual_idx
            visual_idx += 1

            spoken_line = ""
            if line_idx < len(spoken_raw_lines):
                spoken_line = self.clean_spaces(spoken_raw_lines[line_idx])

            if self.is_spoken_line(spoken_line):
                spoken_lines.append(spoken_line)
                spoken_to_visual.append(current_visual_idx)

        return BlockResult(
            visual_lines=visual_lines,
            visual_line_types=visual_types,
            spoken_lines=spoken_lines,
            spoken_to_visual_map=spoken_to_visual,
            next_visual_index=visual_idx,
        )

    def load_script(self) -> tuple[list[str], list[str], list[int]]:
        self.visual_lines = []
        self.visual_line_types = []
        self.spoken_lines = []
        self.spoken_to_visual_map = []
        self.segments = []
        self.visual_metadata = []

        script_path = settings.caminho_roteiro
        if not os.path.isabs(script_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            script_path = os.path.join(base_dir, script_path)
        with open(script_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        visual_index_global = 0
        spoken_index_global = 0

        for slug in data.get("slugs", []):
            meta = self.extract_slug_meta(slug)

            slug_visual_lines: list[str] = []
            slug_visual_types: list[str] = []
            slug_spoken_lines: list[str] = []
            slug_spoken_to_visual: list[int] = []

            has_notes = "notesWithBody" in slug and slug["notesWithBody"]

            if has_notes:
                blocks = []
                for note in slug["notesWithBody"]:
                    texts = note.get("text", [])
                    if isinstance(texts, list):
                        blocks.extend(texts)
                    else:
                        blocks.append(texts)
            else:
                blocks = [slug.get("body", "")]

            for block_text in blocks:
                result = self.process_text_block(block_text, visual_index_global)
                slug_visual_lines.extend(result.visual_lines)
                slug_visual_types.extend(result.visual_line_types)
                slug_spoken_lines.extend(result.spoken_lines)
                slug_spoken_to_visual.extend(result.spoken_to_visual_map)
                visual_index_global = result.next_visual_index

            spoken_times = self.distribute_speaking_time(slug_spoken_lines, meta["speaking_time"])
            pause_duration, pause_reason = self.get_technical_pause(meta)
            pause_applied = False

            for local_idx, visual_line in enumerate(slug_visual_lines):
                visual_idx = len(self.visual_lines) + local_idx
                line_type = slug_visual_types[local_idx] if local_idx < len(slug_visual_types) else "fala"

                line_pause = 0.0
                line_pause_reason = ""

                if not pause_applied and pause_duration > 0 and line_type == "pausa_tecnica":
                    line_pause = pause_duration
                    line_pause_reason = pause_reason
                    pause_applied = True

                self.visual_metadata.append(
                    VisualLineMeta(
                        visual_index=visual_idx,
                        visual_text=visual_line,
                        line_type=line_type,
                        title=meta["title"],
                        page=meta["page"],
                        item_type=meta["item_type"],
                        slug_order=meta["slug_order"],
                        slug_id=meta["slug_id"],
                        speaking_time=meta["speaking_time"],
                        tape_time=meta["tape_time"],
                        total_time=meta["total_time"],
                        duration_seconds=0.0,
                        time_source="json_tecnico" if line_pause > 0 else "sem_tempo",
                        technical_pause_seconds=line_pause,
                        pause_reason=line_pause_reason,
                    )
                )

            for local_idx, spoken_line in enumerate(slug_spoken_lines):
                visual_idx = slug_spoken_to_visual[local_idx]
                visual_text = ""

                if 0 <= visual_idx < visual_index_global:
                    local_offset = visual_idx - len(self.visual_lines)
                    if 0 <= local_offset < len(slug_visual_lines):
                        visual_text = slug_visual_lines[local_offset]

                if not visual_text:
                    visual_text = spoken_line

                line_time = (
                    spoken_times[local_idx]
                    if local_idx < len(spoken_times)
                    else round(self.estimate_reading_time(spoken_line), 2)
                )

                time_source = (
                    "speakingTime_json_distribuido"
                    if meta["speaking_time"] > 0
                    else "estimativa_por_palavras"
                )

                segment_pause = 0.0
                segment_pause_reason = ""

                if pause_duration > 0 and not pause_applied and local_idx == len(slug_spoken_lines) - 1:
                    segment_pause = pause_duration
                    segment_pause_reason = pause_reason

                segment = ScriptSegment(
                    spoken_text=spoken_line,
                    visual_text=visual_text,
                    line_type="fala",
                    spoken_index=spoken_index_global,
                    visual_index=visual_idx,
                    estimated_time=line_time,
                    time_source=time_source,
                    presenter=meta["presenter"],
                    title=meta["title"],
                    page=meta["page"],
                    item_type=meta["item_type"],
                    slug_order=meta["slug_order"],
                    slug_id=meta["slug_id"],
                    speaking_time=meta["speaking_time"],
                    tape_time=meta["tape_time"],
                    total_time=meta["total_time"],
                    start_time=meta["start_time"],
                    pause_after_seconds=segment_pause,
                    pause_reason=segment_pause_reason,
                )

                self.segments.append(segment)
                spoken_index_global += 1

                for vmeta in self.visual_metadata:
                    if vmeta.visual_index == visual_idx:
                        vmeta.duration_seconds = line_time
                        vmeta.time_source = time_source
                        break

            self.visual_lines.extend(slug_visual_lines)
            self.visual_line_types.extend(slug_visual_types)
            self.spoken_lines.extend(slug_spoken_lines)
            self.spoken_to_visual_map.extend(slug_spoken_to_visual)

        logger.info("===== SCRIPT PARSER DIAGNOSTICS =====")
        logger.info(f"Visual lines: {len(self.visual_lines)}")
        logger.info(f"Visual types: {len(self.visual_line_types)}")
        logger.info(f"Spoken lines: {len(self.spoken_lines)}")
        logger.info(f"Mappings: {len(self.spoken_to_visual_map)}")
        logger.info(f"Segments: {len(self.segments)}")

        total_speech = sum(s.estimated_time or 0.0 for s in self.segments)
        total_pause = sum(
            v.technical_pause_seconds or 0.0 for v in self.visual_metadata
        ) + sum(s.pause_after_seconds or 0.0 for s in self.segments)

        logger.info(f"Speech time (s): {round(total_speech, 2)}")
        logger.info(f"Technical/VT time (s): {round(total_pause, 2)}")

        logger.info("First 10 segments with time:")
        for i, seg in enumerate(self.segments[:10]):
            logger.info(f"  {i+1}. {seg.estimated_time}s [{seg.time_source}] - {seg.spoken_text[:60]}")

        logger.info("=====================================")

        return self.spoken_lines, self.visual_lines, self.spoken_to_visual_map