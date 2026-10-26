import re
import json
import unicodedata
from rapidfuzz import fuzz
from app.config import get_settings, CONFIG

settings = get_settings()


def _load_stop_words() -> set[str]:
    """Load stop words from JSON config file, fallback to built-in PT-BR."""
    path = CONFIG.get("stop_words_path", "")
    if path:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Default to pt-BR if available, else first language
            lang = data.get("pt-BR") or next(iter(data.values()), [])
            return set(lang)
        except Exception:
            pass
    # Built-in PT-BR fallback
    return {
        "a", "o", "e", "de", "do", "da", "dos", "das",
        "em", "no", "na", "nos", "nas", "um", "uma",
        "para", "pra", "com", "por", "que", "se",
        "ao", "as", "os", "ou", "e", "é",
    }


class TextNormalizer:
    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return ""
        text = text.lower().strip()
        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        text = re.sub(r"[-/]", " ", text)
        text = re.sub(r"[^a-z0-9\s]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def similarity(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return fuzz.ratio(a, b) / 100.0


class TextComparator:
    def __init__(self):
        self.normalizer = TextNormalizer()
        self.weak_words = _load_stop_words()

    def similarity(self, a: str, b: str) -> float:
        a_n = self.normalizer.normalize(a)
        b_n = self.normalizer.normalize(b)
        if not a_n or not b_n:
            return 0.0
        return fuzz.ratio(a_n, b_n) / 100.0

    def token_coverage(self, spoken: str, script_line: str) -> float:
        spoken_n = self.normalizer.normalize(spoken)
        script_n = self.normalizer.normalize(script_line)
        spoken_words = spoken_n.split()
        script_words = script_n.split()
        if not spoken_words or not script_words:
            return 0.0
        script_set = set(script_words)
        matches = sum(1 for w in spoken_words if w in script_set)
        return matches / max(len(script_words), 1)

    def relevant_word_score(self, spoken: str, script_line: str) -> float:
        spoken_n = self.normalizer.normalize(spoken)
        script_n = self.normalizer.normalize(script_line)
        spoken_words = {w for w in spoken_n.split() if w not in self.weak_words}
        script_words = {w for w in script_n.split() if w not in self.weak_words}
        if not script_words:
            return 0.0
        matches = 0
        for w in script_words:
            if w in spoken_words:
                matches += 1
                continue
            for sw in spoken_words:
                if self.similarity(w, sw) >= 0.72:
                    matches += 1
                    break
        return matches / len(script_words)

    def has_relevant_word_match(self, spoken: str, script_line: str) -> bool:
        spoken_n = self.normalizer.normalize(spoken)
        script_n = self.normalizer.normalize(script_line)
        spoken_words = {w for w in spoken_n.split() if w not in self.weak_words and len(w) >= 3}
        script_words = {w for w in script_n.split() if w not in self.weak_words and len(w) >= 3}
        if not spoken_words or not script_words:
            return False
        return bool(spoken_words.intersection(script_words))

    def is_noise(self, text: str, current_line: str) -> bool:
        normalized = self.normalizer.normalize(text)
        if not normalized:
            return True
        if len(normalized) < 4:
            return True
        words = normalized.split()
        if len(words) == 1:
            return not self.has_relevant_word_match(normalized, current_line)
        return False

    def weighted_score(self, spoken: str, script_line: str) -> tuple[float, float, float, float]:
        sim = self.similarity(spoken, script_line)
        cov = self.token_coverage(spoken, script_line)
        rel = self.relevant_word_score(spoken, script_line)
        score = (sim * 0.45) + (cov * 0.30) + (rel * 0.25)
        return score, sim, cov, rel


def get_comparator() -> TextComparator:
    return TextComparator()