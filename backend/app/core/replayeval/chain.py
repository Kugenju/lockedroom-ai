"""Reasoning-chain extraction — how did the player actually reason?

An LLM reads the player's questions, unlocked clues and final accusation, and
produces a structured replay of the deduction: who they suspected and when,
which insights carried them forward, which required facts they never touched.

Degrades gracefully: unparseable model output yields an empty chain with a
fallback summary — the report still renders, the event log remains the
authoritative record.
"""

import json
from dataclasses import dataclass, field

from app.core.engine.events import EventType, GameEvent
from app.core.llm.base import BaseChatModel, ChatMessage
from app.models.script import Script

_MAX_QUESTIONS = 30

_SYSTEM = """你是剧本杀复盘分析师。根据玩家的提问、搜证与最终指认，还原其推理过程。
严格只输出 JSON：
{"suspect_trajectory": ["阶段化的怀疑对象及原因", ...],
 "key_insights": ["推动推理的关键洞察", ...],
 "missed_clues": ["玩家未触及或未重视的关键事实", ...],
 "summary": "一段话总结其推理路径与得失"}"""

_FALLBACK_SUMMARY = "（推理链提取失败，可查看原始事件流了解对局过程。）"


@dataclass
class ReasoningChain:
    suspect_trajectory: list[str] = field(default_factory=list)
    key_insights: list[str] = field(default_factory=list)
    missed_clues: list[str] = field(default_factory=list)
    summary: str = ""

    @property
    def ok(self) -> bool:
        return self.summary != "" and self.summary != _FALLBACK_SUMMARY


async def extract_chain(
    script: Script, events: list[GameEvent], llm: BaseChatModel
) -> ReasoningChain:
    questions = [
        e.payload.get("content", "")
        for e in events
        if e.type is EventType.MESSAGE and e.payload.get("sender") == "player"
    ][: _MAX_QUESTIONS]
    unlocked = {
        e.payload.get("clue_id")
        for e in events
        if e.type is EventType.CLUE_UNLOCKED
    }
    clue_lines = [
        f"- {c.title}：{c.description}"
        for c in script.clues
        if c.id in unlocked
    ]
    accusation = next(
        (e for e in events if e.type is EventType.PLAYER_ACTION
         and e.payload.get("action") == "accuse"),
        None,
    )
    accusation_desc = "未进行指认"
    if accusation is not None:
        d = accusation.payload.get("detail", {})
        try:
            suspect = script.get_character(d.get("suspect_id", "")).name
            motive = script.get_fact(d.get("motive_fact_id", "")).content
            accusation_desc = f"指认凶手={suspect}，动机={motive}"
        except KeyError:
            accusation_desc = json.dumps(d, ensure_ascii=False)

    ev = script.evaluation
    truth = (
        f"真相：凶手={script.get_character(ev.killer_id).name}，"
        f"动机={script.get_fact(ev.motive_fact_id).content}"
    )
    required = "\n".join(f"- {script.get_fact(fid).content}" for fid in ev.required_fact_ids)

    user = (
        "玩家提问（按时间序，至多30条）：\n" + "\n".join(f"- {q}" for q in questions) + "\n\n"
        "已解锁线索：\n" + ("\n".join(clue_lines) or "（无）") + "\n\n"
        f"最终指认：{accusation_desc}\n\n"
        f"{truth}\n破案必需事实：\n{required}"
    )
    resp = await llm.chat(
        [ChatMessage(role="system", content=_SYSTEM), ChatMessage(role="user", content=user)],
        temperature=0.3,
    )
    return _parse(resp.content)


def _parse(content: str) -> ReasoningChain:
    try:
        start, end = content.index("{"), content.rindex("}")
        data = json.loads(content[start : end + 1])
        return ReasoningChain(
            suspect_trajectory=_str_list(data.get("suspect_trajectory")),
            key_insights=_str_list(data.get("key_insights")),
            missed_clues=_str_list(data.get("missed_clues")),
            summary=str(data.get("summary", "")) or _FALLBACK_SUMMARY,
        )
    except (ValueError, json.JSONDecodeError, AttributeError):
        return ReasoningChain(summary=_FALLBACK_SUMMARY)


def _str_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if v]
