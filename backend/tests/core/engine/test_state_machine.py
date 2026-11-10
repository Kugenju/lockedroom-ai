"""Tests for the game phase state machine."""

import pytest
from app.core.engine.state_machine import GameStateMachine, IllegalPhaseTransition, Phase


def test_initial_phase_is_intro():
    sm = GameStateMachine()
    assert sm.phase is Phase.INTRO


def test_legal_advance_follows_the_happy_path():
    sm = GameStateMachine()
    for target in [
        Phase.SELF_INTRO, Phase.EVIDENCE, Phase.INVESTIGATION,
        Phase.ACCUSATION, Phase.REVEAL, Phase.ENDED,
    ]:
        sm.advance(target)
        assert sm.phase is target


def test_illegal_advance_raises():
    sm = GameStateMachine()
    with pytest.raises(IllegalPhaseTransition):
        sm.advance(Phase.INVESTIGATION)  # skipping self_intro + evidence
    with pytest.raises(IllegalPhaseTransition):
        sm.advance(Phase.ENDED)
    assert sm.phase is Phase.INTRO  # state unchanged after rejection


def test_ended_is_terminal():
    sm = GameStateMachine(Phase.ENDED)
    with pytest.raises(IllegalPhaseTransition):
        sm.advance(Phase.REVEAL)
