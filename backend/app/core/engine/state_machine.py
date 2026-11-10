"""Game phase state machine.

intro → self_intro → evidence → investigation → accusation → reveal → ended
"""

from enum import Enum


class Phase(str, Enum):
    INTRO = "intro"  # 背景介绍
    SELF_INTRO = "self_intro"  # 角色自我介绍
    EVIDENCE = "evidence"  # 搜证
    INVESTIGATION = "investigation"  # 自由调查（对话）
    ACCUSATION = "accusation"  # 指认凶手与动机
    REVEAL = "reveal"  # 真相揭示
    ENDED = "ended"


_TRANSITIONS: dict[Phase, list[Phase]] = {
    Phase.INTRO: [Phase.SELF_INTRO],
    Phase.SELF_INTRO: [Phase.EVIDENCE],
    Phase.EVIDENCE: [Phase.INVESTIGATION],
    Phase.INVESTIGATION: [Phase.ACCUSATION],
    Phase.ACCUSATION: [Phase.REVEAL],
    Phase.REVEAL: [Phase.ENDED],
    Phase.ENDED: [],
}


class IllegalPhaseTransition(Exception):
    """Raised when a phase change is not in the transition table."""


class GameStateMachine:
    def __init__(self, phase: Phase = Phase.INTRO):
        self.phase = phase

    def advance(self, target: Phase) -> None:
        if target not in _TRANSITIONS[self.phase]:
            raise IllegalPhaseTransition(f"cannot advance {self.phase.value} -> {target.value}")
        self.phase = target
