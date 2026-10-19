from types import SimpleNamespace
from unittest.mock import Mock

from app.services.aligner import ScriptAligner
from app.services.script_processor import ScriptProcessor
from app.services.state_machine import StateMachine
from app.websocket.handlers import _load_processed_script


def test_loading_script_updates_visual_and_spoken_session_data():
    session = SimpleNamespace(
        state=StateMachine(),
        script_processor=ScriptProcessor(),
        aligner=ScriptAligner([], []),
        scroll_controller=SimpleNamespace(
            last_final_text="old phrase",
            last_partial_processed="old partial",
        ),
        speech_recognizer=Mock(),
    )

    line_count = _load_processed_script(
        session,
        {
            "slugs": [
                {
                    "body": "<p><pi>OLÁ, BOM DIA./</pi></p>\n"
                    "<p><pi>{{RODA VT}}</pi></p>\n"
                    "<p><pi>VAMOS ÀS NOTÍCIAS.</pi></p>"
                }
            ]
        },
    )

    assert line_count == 3
    assert session.state.visual_lines == ["OLÁ, BOM DIA./", "{{RODA VT}}", "VAMOS ÀS NOTÍCIAS."]
    assert session.state.spoken_lines == ["OLÁ, BOM DIA./", "VAMOS ÀS NOTÍCIAS."]
    assert session.state.spoken_to_visual_map == [0, 2]
    assert session.aligner.visual_lines == session.state.visual_lines
    assert session.scroll_controller.last_final_text == ""
    session.speech_recognizer.reset_vosk.assert_called_once_with()
