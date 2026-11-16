"""Tiered memory for character agents.

Three tiers, smallest-first:
- working window: the newest WORKING_TURNS half-turns, verbatim, always in context
- episodic: assistant turns rated importance >= EPISODIC_IMPORTANCE survive
  verbatim beyond the window (capped at EPISODIC_MAX_ITEMS)
- semantic: everything else older than the window is compressed into a rolling
  summary by an LLM. The draft summary MUST pass the leak detector before it
  enters memory — InfoGuard guards writes, not just speech.

Consolidation is lazy: it only runs when the un-summarized backlog reaches
CONSOLIDATE_BACKLOG half-turns, amortizing the extra LLM call over many turns.
"""

import json
from dataclasses import dataclass

from app.core.infoguard.detector import LeakDetector
from app.core.llm.base import BaseChatModel, ChatMessage

WORKING_TURNS = 10
EPISODIC_IMPORTANCE = 7
EPISODIC_MAX_ITEMS = 6
SUMMARY_MAX_CHARS = 1200
CONSOLIDATE_BACKLOG = 8
DEFAULT_IMPORTANCE = 5

_SCORER_SYSTEM = """你是剧本杀信息评估员。给角色这句话的信息重要性评分 1-10：
新线索、可疑陈述、关键自白、前后矛盾 = 高分；客套话、重复信息、纯情绪表达 = 低分。
只输出 JSON：{"importance": 整数}"""


@dataclass
class MemoryItem:
    role: str  # "user" (player) | "assistant" (the character)
    content: str
    importance: int
    seq: int


async def score_importance_async(
    llm: BaseChatModel, char_name: str, char_role: str, content: str
) -> int:
    resp = await llm.chat(
        [
            ChatMessage(role="system", content=_SCORER_SYSTEM),
            ChatMessage(role="user", content=f"角色：{char_name}（{char_role}）\n这句话：{content}"),
        ],
        temperature=0,
    )
    return _parse_importance(resp.content)


def _parse_importance(content: str) -> int:
    try:
        start, end = content.index("{"), content.rindex("}")
        value = json.loads(content[start : end + 1]).get("importance", DEFAULT_IMPORTANCE)
        return max(1, min(10, int(value)))
    except (ValueError, json.JSONDecodeError, AttributeError, TypeError):
        return DEFAULT_IMPORTANCE


class AgentMemory:
    def __init__(
        self,
        scorer_llm: BaseChatModel,
        summarizer_llm: BaseChatModel,
        detector: LeakDetector,
        on_event=None,
        budget_chars: int = 3000,
    ):
        self._scorer = scorer_llm
        self._summarizer = summarizer_llm
        self._detector = detector
        self._on_event = on_event  # callable(**payload) -> None, for observability
        self.budget_chars = budget_chars
        self._items: list[MemoryItem] = []
        self._summary = ""
        self._consolidated_upto = 0  # items with seq < this are folded into the summary

    # --- writing ---

    def add_turn(self, role: str, content: str, importance: int = DEFAULT_IMPORTANCE) -> MemoryItem:
        item = MemoryItem(role=role, content=content, importance=importance, seq=len(self._items))
        self._items.append(item)
        return item

    async def score_turn(self, role: str, content: str, char_name: str, char_role: str) -> int:
        """v1 scores assistant turns only; player turns keep the default."""
        if role != "assistant":
            return DEFAULT_IMPORTANCE
        return await score_importance_async(self._scorer, char_name, char_role, content)

    def consolidation_due(self) -> bool:
        return len(self._backlog_candidates()) >= CONSOLIDATE_BACKLOG

    async def consolidate(self) -> bool:
        """Fold the low-importance backlog into the rolling summary.
        Returns True when a (leak-safe) consolidation happened."""
        backlog = self._backlog_candidates()
        if len(backlog) < CONSOLIDATE_BACKLOG:
            return False
        turns = "\n".join(f"{'玩家' if it.role == 'user' else '角色'}：{it.content}" for it in backlog)
        prompt = (
            f"现有摘要：{self._summary or '（无）'}\n"
            f"新增对话：\n{turns}\n"
            f"请合并为一段不超过{SUMMARY_MAX_CHARS}字的连续摘要，保留与案件相关的事实，"
            "舍去寒暄。只输出摘要正文。"
        )
        resp = await self._summarizer.chat(
            [ChatMessage(role="user", content=prompt)], temperature=0.2
        )
        draft = resp.content.strip()[: SUMMARY_MAX_CHARS * 2]
        leaks = self._detector.check(draft)
        if leaks:
            if self._on_event:
                self._on_event(
                    op="blocked", backlog=len(backlog), leaked_facts=[l.fact_id for l in leaks]
                )
            return False  # keep the old summary; backlog retries next time
        self._summary = draft[:SUMMARY_MAX_CHARS]
        self._consolidated_upto = max(it.seq for it in backlog) + 1
        if self._on_event:
            self._on_event(op="consolidated", backlog=len(backlog), chars=len(self._summary))
        return True

    # --- reading ---

    def build_context(self) -> list[ChatMessage]:
        """Memory as prompt messages: summary note + episodic + working window."""
        msgs: list[ChatMessage] = []
        summary = self._safe_summary()
        if summary:
            msgs.append(ChatMessage(role="system", content=f"（早前对话摘要）{summary}"))
        for it in self._episodic_items():
            msgs.append(ChatMessage(role=it.role, content=it.content))
        for it in self._items[-WORKING_TURNS:]:
            msgs.append(ChatMessage(role=it.role, content=it.content))
        # hard budget: drop oldest episodic, then shrink the summary
        while sum(len(m.content) for m in msgs) > self.budget_chars and msgs:
            if len(msgs) > 2 and msgs[1].role in ("user", "assistant"):
                msgs.pop(1)  # oldest episodic first
            elif msgs and msgs[0].role == "system":
                msgs[0] = ChatMessage(role="system", content=msgs[0].content[: self.budget_chars // 2])
            else:
                msgs.pop(0)
        return msgs

    # --- internals ---

    def _backlog_candidates(self) -> list[MemoryItem]:
        """Beyond the working window, not yet consolidated, below episodic threshold."""
        cutoff = max(0, len(self._items) - WORKING_TURNS)
        return [
            it
            for it in self._items[:cutoff]
            if it.seq >= self._consolidated_upto and it.importance < EPISODIC_IMPORTANCE
        ]

    def _episodic_items(self) -> list[MemoryItem]:
        high = [it for it in self._items if it.importance >= EPISODIC_IMPORTANCE]
        high.sort(key=lambda it: (-it.importance, -it.seq))
        keep = {it.seq for it in high[:EPISODIC_MAX_ITEMS]}
        return sorted((it for it in high if it.seq in keep), key=lambda it: it.seq)

    def _safe_summary(self) -> str:
        if not self._summary:
            return ""
        return "" if self._detector.check(self._summary) else self._summary
