import pytest
from app.services.state_machine import StateMachine, TeleprompterState
from app.services.aligner import ScriptAligner
from app.services.script_processor import ScriptProcessor


class TestStateMachine:
    def setup_method(self):
        self.state = StateMachine()

    def test_initial_state(self):
        assert self.state.state == TeleprompterState.WAITING
        assert self.state.running is False
        assert self.state.current_spoken_index == 0
        assert self.state.current_visual_index == 0

    def test_change_state(self):
        self.state.change_state(TeleprompterState.AUTOMATIC)
        assert self.state.state == TeleprompterState.AUTOMATIC

        # Changing to same state should be no-op
        self.state.change_state(TeleprompterState.AUTOMATIC)
        assert self.state.state == TeleprompterState.AUTOMATIC

    def test_is_automatic(self):
        assert not self.state.is_automatic()
        self.state.change_state(TeleprompterState.AUTOMATIC)
        assert self.state.is_automatic()

    def test_is_paused(self):
        assert not self.state.is_paused()
        self.state.change_state(TeleprompterState.PAUSED)
        assert self.state.is_paused()

    def test_is_finished(self):
        assert not self.state.is_finished()
        self.state.change_state(TeleprompterState.FINISHED)
        assert self.state.is_finished()

    def test_is_improv(self):
        assert not self.state.is_improv()
        self.state.change_state(TeleprompterState.IMPROV)
        assert self.state.is_improv()

    def test_is_vt_or_link(self):
        assert not self.state.is_vt_or_link()
        self.state.change_state(TeleprompterState.VT_OR_LINK)
        assert self.state.is_vt_or_link()

    def test_can_evaluate_audio(self):
        # Should be able to evaluate in these states
        for state in [TeleprompterState.AUTOMATIC, TeleprompterState.IMPROV, TeleprompterState.VT_OR_LINK]:
            self.state.change_state(state)
            assert self.state.can_evaluate_audio()

        # Should NOT be able to evaluate in these states
        for state in [TeleprompterState.WAITING, TeleprompterState.PAUSED, TeleprompterState.FINISHED, TeleprompterState.FAILED]:
            self.state.change_state(state)
            assert not self.state.can_evaluate_audio()

    def test_advance_to(self):
        self.state.spoken_lines = ["line1", "line2", "line3"]
        self.state.spoken_to_visual_map = [0, 1, 2]

        assert self.state.advance_to(1)
        assert self.state.current_spoken_index == 1
        assert self.state.current_visual_index == 1

        # Out of bounds
        assert not self.state.advance_to(10)
        assert not self.state.advance_to(-1)

    def test_go_back(self):
        self.state.spoken_lines = ["line1", "line2", "line3"]
        self.state.spoken_to_visual_map = [0, 1, 2]
        self.state.current_spoken_index = 2
        self.state.current_visual_index = 2

        assert self.state.go_back()
        assert self.state.current_spoken_index == 1
        assert self.state.current_visual_index == 1

        # At beginning
        self.state.current_spoken_index = 0
        assert not self.state.go_back()


class TestScriptAligner:
    def test_get_visual_index(self):
        spoken_to_visual = [0, 2, 4, 5]
        visual_lines = ["v0", "v1", "v2", "v3", "v4", "v5"]
        aligner = ScriptAligner(spoken_to_visual, visual_lines)

        assert aligner.get_visual_index(0) == 0
        assert aligner.get_visual_index(1) == 2
        assert aligner.get_visual_index(2) == 4
        assert aligner.get_visual_index(3) == 5

        # Out of bounds returns last visual index
        assert aligner.get_visual_index(10) == 5

    def test_get_first_visual_index(self):
        aligner = ScriptAligner([2, 4], ["v0", "v1", "v2", "v3"])
        assert aligner.get_first_visual_index() == 2

        # Empty map
        aligner_empty = ScriptAligner([], ["v0"])
        assert aligner_empty.get_first_visual_index() == 0


class TestScriptProcessor:
    def setup_method(self):
        self.processor = ScriptProcessor()

    def test_ensure_text(self):
        assert self.processor.ensure_text(None) == ""
        assert self.processor.ensure_text("hello") == "hello"
        assert self.processor.ensure_text(["a", "b"]) == "a\nb"
        assert self.processor.ensure_text(123) == "123"

    def test_to_seconds(self):
        assert self.processor.to_seconds(None) == 0.0
        assert self.processor.to_seconds("") == 0.0
        assert self.processor.to_seconds("10.5") == 10.5
        assert self.processor.to_seconds("invalid") == 0.0

    def test_clean_spaces(self):
        assert self.processor.clean_spaces("  hello   world  ") == "hello world"
        assert self.processor.clean_spaces("") == ""
        assert self.processor.clean_spaces(None) == ""

    def test_count_words(self):
        assert self.processor.count_words("hello world") == 2
        assert self.processor.count_words("") == 0
        assert self.processor.count_words("um-dois") == 2  # hyphen becomes space

    def test_is_separator(self):
        assert self.processor.is_separator("===")
        assert self.processor.is_separator("---")
        assert self.processor.is_separator("   ")
        assert not self.processor.is_separator("hello")
        assert not self.processor.is_separator("")

    def test_is_technical(self):
        assert self.processor.is_technical("{{COMANDO}}")
        assert self.processor.is_technical("{comando}")
        assert self.processor.is_technical("[comando]")
        assert self.processor.is_technical("(comando)")
        assert self.processor.is_technical("ABRE SOM VT")
        assert self.processor.is_technical("RODA VT")
        assert not self.processor.is_technical("O apresentador disse")

    def test_is_pause_command(self):
        assert self.processor.is_pause_command("ABRE SOM VT")
        assert self.processor.is_pause_command("RODA VT")
        assert self.processor.is_pause_command("LINK NO AR")
        assert self.processor.is_pause_command("VINHETA")
        assert not self.processor.is_pause_command("O apresentador disse")

    def test_classify_visual_line(self):
        assert self.processor.classify_visual_line("===") == "separador"
        assert self.processor.classify_visual_line("ABRE SOM VT") == "pausa_tecnica"
        assert self.processor.classify_visual_line("{{COMANDO}}") == "tecnico"
        assert self.processor.classify_visual_line("O apresentador disse") == "fala"

    def test_is_spoken_line(self):
        assert self.processor.is_spoken_line("O apresentador disse")
        assert not self.processor.is_spoken_line("")
        assert not self.processor.is_spoken_line("a")
        assert not self.processor.is_spoken_line("{{COMANDO}}")
        assert not self.processor.is_spoken_line("===")
        assert not self.processor.is_spoken_line("123")  # No letters

    def test_markup_keeps_spoken_to_visual_mapping(self):
        result = self.processor.process_text_block(
            "<p><pi>PRIMEIRA FALA</pi></p>\n"
            "<p><pi>{{RODA VT}}</pi></p>\n"
            "<p><pi>SEGUNDA FALA</pi></p>",
            visual_index_start=0,
        )

        assert result.spoken_lines == ["PRIMEIRA FALA", "SEGUNDA FALA"]
        assert result.spoken_to_visual_map == [0, 2]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
