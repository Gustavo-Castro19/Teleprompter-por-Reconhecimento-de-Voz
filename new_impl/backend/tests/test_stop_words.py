import pytest
import tempfile
import json
from pathlib import Path
from app.utils.text_normalizer import TextComparator, _load_stop_words
from app.config import CONFIG


class TestStopWords:
    def test_default_pt_br_stop_words(self):
        """Test that default PT-BR stop words are loaded when no config file."""
        # Temporarily clear the stop_words_path
        original = CONFIG.get("stop_words_path", "")
        CONFIG["stop_words_path"] = ""

        try:
            comp = TextComparator()
            # Check common PT-BR stop words are in weak_words
            assert "a" in comp.weak_words
            assert "o" in comp.weak_words
            assert "de" in comp.weak_words
            assert "do" in comp.weak_words
            assert "da" in comp.weak_words
            assert "em" in comp.weak_words
            assert "para" in comp.weak_words
            assert "com" in comp.weak_words
            assert "por" in comp.weak_words
            assert "que" in comp.weak_words
        finally:
            CONFIG["stop_words_path"] = original

    def test_custom_stop_words_file(self):
        """Test loading stop words from custom JSON file."""
        # Create temp file with custom stop words
        custom_words = {"pt-BR": ["custom1", "custom2", "a", "o"]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(custom_words, f)
            temp_path = f.name

        try:
            original = CONFIG.get("stop_words_path", "")
            CONFIG["stop_words_path"] = temp_path

            comp = TextComparator()
            assert "custom1" in comp.weak_words
            assert "custom2" in comp.weak_words
            assert "a" in comp.weak_words
            assert "o" in comp.weak_words
        finally:
            CONFIG["stop_words_path"] = original
            Path(temp_path).unlink()

    def test_stop_words_affect_relevant_word_score(self):
        """Test that stop words are filtered in relevant_word_score."""
        comp = TextComparator()

        # "a" and "o" are stop words, should be ignored
        score = comp.relevant_word_score("a apresentador disse", "apresentador disse")
        assert score == 1.0

        # Without stop words filtering, score would be lower
        # because "a" and "o" don't match anything in script

    def test_stop_words_affect_has_relevant_word_match(self):
        """Test that stop words are filtered in has_relevant_word_match."""
        comp = TextComparator()

        # "a" is stop word, should not count as match
        assert comp.has_relevant_word_match("a apresentador", "o apresentador")
        assert not comp.has_relevant_word_match("a", "o apresentador")

    def test_stop_words_affect_is_noise(self):
        """Test that single stop word is considered noise."""
        comp = TextComparator()

        # Single stop word should be noise
        assert comp.is_noise("a", "apresentador disse")
        # Single non-stop word should not be noise
        assert not comp.is_noise("apresentador", "o apresentador disse")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])