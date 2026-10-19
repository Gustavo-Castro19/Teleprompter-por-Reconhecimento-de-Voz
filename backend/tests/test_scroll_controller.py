from unittest.mock import Mock

import pytest

from app.services.scroll_controller import ScrollController
from app.services.state_machine import StateMachine, TeleprompterState


@pytest.mark.parametrize(
    "state",
    [TeleprompterState.WAITING, TeleprompterState.PAUSED, TeleprompterState.FINISHED],
)
def test_partial_speech_is_ignored_when_motor_cannot_evaluate_audio(state):
    controller = object.__new__(ScrollController)
    controller.state = StateMachine(state=state)
    controller.comparator = Mock()

    assert controller.evaluate_partial("fala reconhecida") is False
    controller.comparator.normalizer.normalize.assert_not_called()


def test_previous_line_match_has_a_threshold_so_voice_can_go_back():
    controller = object.__new__(ScrollController)

    assert controller.min_score_for_distance(-1) == 0.82
