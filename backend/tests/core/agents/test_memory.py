"""Tests for the tiered AgentMemory: working window, importance-gated episodic, leak-screened summary."""


from app.core.agents.memory import (
    EPISODIC_IMPORTANCE,
    AgentMemory,
    score_importance_async,
)
from app.core.infoguard.detector import LeakDetector
from app.core.infoguard.scope import compile_scopes
from app.core.llm.fake import FakeLLM
from app.core.scripts.loader import load_script

SCRIPT = load_script("snow-night-villa")
SCOPE = compile_scopes(SCRIPT)["lin_wanqiu"]
DETECTOR = LeakDetector(SCRIPT, SCOPE)


def _memory(scorer=None, summarizer=None) -> AgentMemory:
    return AgentMemory(
        scorer_llm=scorer or FakeLLM('{"importance": 3}'),
        summarizer_llm=summarizer or FakeLLM("早前对话概要。"),
        detector=DETECTOR,
        on_event=lambda **kw: None,
    )


def _fill(mem: AgentMemory, n: int, importance: int = 3):
    for i in range(n):
        mem.add_turn("user", f"玩家问题{i}？")
        mem.add_turn("assistant", f"回答{i}。", importance=importance)


def test_working_window_keeps_recent_verbatim():
    mem = _memory()
    _fill(mem, 15)
    ctx = mem.build_context()
    texts = "\n".join(m.content for m in ctx)
    # last turns verbatim
    assert "回答14。" in texts
    # old turns fell out of the verbatim working window
    assert "回答2。" not in texts


def test_high_importance_turns_survive_in_episodic():
    mem = _memory()
    mem.add_turn("user", "关键提问？")
    mem.add_turn("assistant", "我听见书房有争吵。", importance=9)
    _fill(mem, 14)  # push the key turn far beyond the window
    ctx = mem.build_context()
    texts = "\n".join(m.content for m in ctx)
    assert "我听见书房有争吵。" in texts  # kept verbatim via episodic tier


async def test_low_importance_backlog_goes_to_summary():
    summarizer = FakeLLM("玩家问过路线，角色否认涉案。")
    mem = _memory(summarizer=summarizer)
    _fill(mem, 15, importance=2)
    await mem.consolidate()
    ctx = mem.build_context()
    summary_line = next((m for m in ctx if "摘要" in m.content), None)
    assert summary_line is not None
    assert "玩家问过路线" in summary_line.content
    # verbatim backlog is gone once summarized
    texts = "\n".join(m.content for m in ctx)
    assert "回答3。" not in texts


async def test_consolidation_leak_is_blocked():
    # summary draft containing a forbidden fact must NOT enter memory
    bad_summarizer = FakeLLM("老爷死于过量胰岛素注射。")
    mem = _memory(summarizer=bad_summarizer)
    _fill(mem, 15, importance=2)
    await mem.consolidate()
    ctx = mem.build_context()
    texts = "\n".join(m.content for m in ctx)
    assert "胰岛素" not in texts  # blocked summary never surfaces


def test_leaky_stored_summary_is_skipped_at_build_time():
    mem = _memory()
    mem._summary = "摘要里混进了胰岛素细节。"  # simulate poisoned store
    ctx = mem.build_context()
    texts = "\n".join(m.content for m in ctx)
    assert "胰岛素" not in texts


async def test_budget_guard_bounds_total_memory_size():
    mem = _memory(summarizer=FakeLLM("长摘要" * 400))
    _fill(mem, 40, importance=9)  # everything high-importance
    await mem.consolidate()
    total = sum(len(m.content) for m in mem.build_context())
    assert total <= mem.budget_chars * 2  # hard ceiling even in pathological cases


async def test_importance_scoring_parses_json():
    score = await score_importance_async(
        FakeLLM('{"importance": 9}'), "林晚秋", "管家", "我什么都不知道。"
    )
    assert score == 9


async def test_importance_scoring_defaults_on_garbage():
    score = await score_importance_async(FakeLLM("不是JSON"), "林晚秋", "管家", "你好。")
    assert score == 5


async def test_importance_scoring_clamps_range():
    score = await score_importance_async(FakeLLM('{"importance": 99}'), "林晚秋", "管家", "x")
    assert score == 10


def test_episodic_threshold_constant():
    assert EPISODIC_IMPORTANCE >= 7
