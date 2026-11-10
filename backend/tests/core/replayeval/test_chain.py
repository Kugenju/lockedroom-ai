"""Tests for the reasoning-chain extractor (LLM-powered replay analysis)."""

import json

from app.core.engine.events import EventType, GameEvent, utc_now_iso
from app.core.llm.fake import FakeLLM
from app.core.replayeval.chain import ReasoningChain, extract_chain
from app.core.scripts.loader import load_script

SCRIPT = load_script("snow-night-villa")

GOOD_JSON = json.dumps(
    {
        "suspect_trajectory": ["方鹤鸣（赌债动机明显）", "周慕辰（胰岛素与窗户证据）"],
        "key_insights": ["针孔被领带遮住说明是专业手法", "窗台融雪证明窗户动过"],
        "missed_clues": ["没注意到采购单夹层的黑账"],
        "summary": "玩家从动机切入，靠两条物理证据锁定真凶，遗漏了直接指向动机的黑账线索。",
    },
    ensure_ascii=False,
)


def _events():
    return [
        GameEvent(0, EventType.MESSAGE, utc_now_iso(),
                  {"sender": "player", "recipient": "fang_heming", "content": "你的赌债怎么回事？"}),
        GameEvent(1, EventType.CLUE_UNLOCKED, utc_now_iso(), {"clue_id": "c_report"}),
        GameEvent(2, EventType.CLUE_UNLOCKED, utc_now_iso(), {"clue_id": "c_window"}),
        GameEvent(3, EventType.PLAYER_ACTION, utc_now_iso(), {
            "action": "accuse",
            "detail": {"suspect_id": "zhou_muchen", "motive_fact_id": "t_window",
                       "killer_correct": True, "motive_correct": False},
        }),
    ]


async def test_valid_json_populates_chain():
    chain = await extract_chain(SCRIPT, _events(), FakeLLM(GOOD_JSON))
    assert isinstance(chain, ReasoningChain)
    assert len(chain.suspect_trajectory) == 2
    assert "胰岛素" in chain.suspect_trajectory[1] or "窗户" in chain.suspect_trajectory[1]
    assert len(chain.key_insights) == 2
    assert len(chain.missed_clues) == 1
    assert "真凶" in chain.summary


async def test_prose_wrapped_json_is_extracted():
    chain = await extract_chain(SCRIPT, _events(), FakeLLM(f"分析如下：{GOOD_JSON}。完毕。"))
    assert len(chain.suspect_trajectory) == 2


async def test_malformed_output_degrades_gracefully():
    chain = await extract_chain(SCRIPT, _events(), FakeLLM("我分析不出来。"))
    assert chain.suspect_trajectory == []
    assert chain.key_insights == []
    assert chain.missed_clues == []
    assert "提取失败" in chain.summary


async def test_prompt_contains_player_actions_and_truth():
    seen = []

    def factory(messages):
        seen.append(messages[-1].content)
        return GOOD_JSON

    await extract_chain(SCRIPT, _events(), FakeLLM(factory))
    user = seen[0]
    assert "赌债" in user                 # player questions included
    assert "c_report" in user or "初步检验结果" in user  # unlocked clues included
    assert "周慕辰" in user          # accusation included (as character name)
    assert "处方药" in user          # ground truth (motive) included for gap analysis


async def test_empty_events_degrade():
    chain = await extract_chain(SCRIPT, [], FakeLLM("bad"))
    assert "提取失败" in chain.summary
