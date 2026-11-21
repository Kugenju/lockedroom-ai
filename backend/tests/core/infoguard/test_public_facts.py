"""Public-knowledge layer: unlocked clues become visible to every agent and
stop triggering InfoGuard — facts revealed by public clues are exempted from
both the output detector and the input context guard."""


from app.core.agents.agent import CharacterAgent
from app.core.agents.memory import AgentMemory
from app.core.engine.session import GameSession
from app.core.infoguard.context_guard import ContextGuard
from app.core.infoguard.detector import LeakDetector
from app.core.infoguard.scope import compile_scopes
from app.core.llm.fake import FakeLLM
from app.core.scripts.loader import load_script

SCRIPT = load_script("snow-night-villa")
SCOPES = compile_scopes(SCRIPT)


def test_detector_exempt_fact_stops_flagging():
    d = LeakDetector(SCRIPT, SCOPES["lin_wanqiu"])
    assert d.check("老爷是死于过量胰岛素注射的。")  # hard hit before
    d.exempt_fact("t_method")
    assert d.check("老爷是死于过量胰岛素注射的。") == []


def test_context_guard_exempt_fact_stops_wrapping():
    g = ContextGuard(SCRIPT, SCOPES["lin_wanqiu"])
    assert g.guard("是不是胰岛素注射？").findings  # wrapped before
    g.exempt_fact("t_method")
    result = g.guard("检验报告说死于胰岛素注射，你看到了吗？")
    assert result.findings == []
    assert result.text == "检验报告说死于胰岛素注射，你看到了吗？"


def _agent(session: GameSession, char_id: str) -> CharacterAgent:
    scope = SCOPES[char_id]
    detector = LeakDetector(SCRIPT, scope)
    return CharacterAgent(
        character=SCRIPT.get_character(char_id),
        script=SCRIPT,
        scope=scope,
        llm=session.llm,
        session=session,
        detector=detector,
        memory=AgentMemory(
            scorer_llm=FakeLLM('{"importance": 4}'),
            summarizer_llm=FakeLLM("早前对话摘要。"),
            detector=detector,
        ),
    )


async def test_note_public_clue_enters_memory_and_exempts():
    session = GameSession("s1", SCRIPT, FakeLLM())
    agent = _agent(session, "lin_wanqiu")
    agent.note_public_clue("初步检验结果", "针孔被领带遮住，死状近似急性心衰。", ["t_method", "t_time"])

    remembered = "\n".join(m.content for m in agent.memory.build_context())
    assert "[公开线索] 初步检验结果" in remembered
    # the revealed facts no longer count as leaks for this agent
    assert agent.detector.check("死于过量胰岛素注射") == []


async def test_public_clue_turn_does_not_auto_note():
    session = GameSession("s1", SCRIPT, FakeLLM())
    agent = _agent(session, "lin_wanqiu")
    agent.note_public_clue("初步检验结果", "描述", ["t_method", "t_time"])
    assert session.notes() == []  # importance 6 < 7


def test_note_public_clue_exempts_input_guard():
    session = GameSession("s1", SCRIPT, FakeLLM())
    agent = _agent(session, "lin_wanqiu")
    agent.note_public_clue("初步检验结果", "描述", ["t_method"])
    result = agent._guard.guard("检验报告提到胰岛素注射，你怎么看？")
    assert result.findings == []
