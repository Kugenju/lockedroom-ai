"""A character agent: persona + scoped knowledge + leak-intercepted dialogue.

Two public interaction channels:
- respond(): private interrogation — player talks one-on-one with this character
- discuss(): public discussion round — the character speaks in front of everyone

Both share the same screened-generation pipeline (generate → Layer-2 detect →
judge → rewrite/fallback); memory only ever sees approved text.
"""

from dataclasses import dataclass, field

from app.core.agents.memory import EPISODIC_IMPORTANCE, AgentMemory
from app.core.agents.prompt_builder import build_system_prompt
from app.core.engine.events import EventType
from app.core.engine.session import GameSession
from app.core.infoguard.context_guard import ContextGuard
from app.core.infoguard.detector import LeakDetector, LeakFinding
from app.core.infoguard.judge import AdjudicatedLeak, LeakJudge
from app.core.infoguard.scope import InformationScope
from app.core.llm.base import BaseChatModel, ChatMessage
from app.models.script import Script, ScriptCharacter

FALLBACK_LINE = "（沉默片刻，移开视线）……这件事，我不太清楚。"


@dataclass
class AgentReply:
    text: str
    leaks: list[LeakFinding] = field(default_factory=list)
    rewritten: bool = False
    fell_back: bool = False


class CharacterAgent:
    def __init__(
        self,
        character: ScriptCharacter,
        script: Script,
        scope: InformationScope,
        llm: BaseChatModel,
        session: GameSession,
        detector: LeakDetector,
        judge: LeakJudge | None = None,
        memory: AgentMemory | None = None,
    ):
        self.character = character
        self.script = script
        self.scope = scope
        self.llm = llm
        self.session = session
        self.detector = detector
        self._judge = judge
        self._guard = ContextGuard(script, scope)
        self.memory = memory or AgentMemory(
            scorer_llm=llm, summarizer_llm=llm, detector=detector,
            on_event=self._record_memory_event,
        )
        self._system_prompt = build_system_prompt(script, character, scope)

    def _record_memory_event(self, **payload) -> None:
        self.session.record_event(
            EventType.SYSTEM,
            {"kind": "memory_consolidation", "character_id": self.character.id, **payload},
        )

    def _emit_leaks(
        self,
        leaks: list[LeakFinding],
        action: str,
        verdicts: dict[str, AdjudicatedLeak] | None = None,
    ) -> None:
        for leak in leaks:
            detail = f"{leak.method} hit: {leak.matched_text}"
            if verdicts and (a := verdicts.get(leak.fact_id)):
                detail += f" | judge {a.verdict}: {a.reason}"
            self.session.record_leak(
                character_id=self.character.id,
                fact_id=leak.fact_id,
                severity=leak.severity,
                action=action,
                detail=detail,
            )

    def _guarded_memory(self, message: ChatMessage) -> ChatMessage:
        """Layer 3: re-guard user-side memory entries at prompt-build time."""
        if message.role != "user":
            return message
        return ChatMessage(role="user", content=self._guard.guard(message.content).text)

    def note_public_clue(self, title: str, description: str, fact_ids: list[str]) -> None:
        """A public clue was unlocked: it enters every agent's memory and its
        revealed facts stop counting as leaks (they are now public knowledge)."""
        self.memory.add_turn(
            "user", f"[公开线索] {title}：{description}", importance=6
        )
        for fid in fact_ids:
            self.detector.exempt_fact(fid)
            self._guard.exempt_fact(fid)

    # --- shared generation pipeline ---

    async def _screened_generate(
        self, messages: list[ChatMessage]
    ) -> tuple[str, list[LeakFinding], bool, bool]:
        """Generate a reply and screen it through InfoGuard Layer 2 (+judge).

        Returns (approved_text, surviving_leaks, rewritten, fell_back).
        """
        draft = await self.llm.chat(messages)
        leaks = self.detector.check(draft.content)
        verdicts: dict[str, AdjudicatedLeak] = {}
        if self._judge is not None and leaks:
            adjudicated = await self._judge.adjudicate(self.character.id, draft.content, leaks)
            leaks = [
                LeakFinding(
                    fact_id=a.finding.fact_id,
                    severity=a.effective_severity,
                    matched_text=a.finding.matched_text,
                    method=a.finding.method,
                )
                for a in adjudicated
            ]
            verdicts = {a.finding.fact_id: a for a in adjudicated}

        rewritten = False
        fell_back = False
        text = draft.content

        hard_leaks = [l for l in leaks if l.severity == "hard"]
        if hard_leaks:
            self._emit_leaks(hard_leaks, action="rewritten", verdicts=verdicts)
            warn = ChatMessage(
                role="user",
                content=(
                    "（导演提示：你刚才的回答泄露了你不可能知道的信息："
                    + "；".join(self.script.get_fact(l.fact_id).content[:40] for l in hard_leaks)
                    + "。请重新回答，彻底避开这些内容。）"
                ),
            )
            retry = await self.llm.chat(
                [*messages, ChatMessage(role="assistant", content=draft.content), warn]
            )
            retry_hard = [l for l in self.detector.check(retry.content) if l.severity == "hard"]
            if retry_hard:
                self._emit_leaks(retry_hard, action="fallback")
                fell_back = True
                text = FALLBACK_LINE
                leaks = retry_hard
            else:
                rewritten = True
                text = retry.content
                leaks = self.detector.check(text)
                self._emit_leaks([l for l in leaks if l.severity == "soft"], action="passed")
        else:
            self._emit_leaks(leaks, action="passed")
        return text, leaks, rewritten, fell_back

    async def _commit_reply(self, text: str, fell_back: bool) -> None:
        """Record the approved reply: event log + tiered memory + auto-note."""
        importance = 1 if fell_back else await self.memory.score_turn(
            "assistant", text, self.character.name, self.character.role
        )
        self.memory.add_turn("assistant", text, importance=importance)
        if importance >= EPISODIC_IMPORTANCE:
            self.session.record_note(
                source="auto",
                content=text[:200],
                char_id=self.character.id,
                importance=importance,
            )
        if self.memory.consolidation_due():
            await self.memory.consolidate()

    # --- channels ---

    async def respond(self, player_message: str) -> AgentReply:
        phase = self.session.phase.value

        # Layer 3: annotate and guard the incoming player message
        guarded = self._guard.guard(player_message)
        meta = {}
        if guarded.findings:
            meta = {
                "guarded": True,
                "guarded_fact_ids": [f.fact_id for f in guarded.findings],
            }
        self.session.record_message(
            "player", self.character.id, player_message, phase=phase, **meta
        )

        messages = [
            ChatMessage(role="system", content=self._system_prompt),
            *[self._guarded_memory(m) for m in self.memory.build_context()],
            ChatMessage(role="user", content=guarded.text),
        ]
        self.memory.add_turn("user", player_message)

        text, leaks, rewritten, fell_back = await self._screened_generate(messages)
        self.session.record_message(
            self.character.id, "player", text, phase=phase,
            **({"rewritten": True} if rewritten else {}),
            **({"fell_back": True} if fell_back else {}),
        )
        # memory only ever contains approved text — leaked drafts never persist
        await self._commit_reply(text, fell_back)
        return AgentReply(text=text, leaks=leaks, rewritten=rewritten, fell_back=fell_back)

    async def discuss(self, transcript: list[tuple[str, str]]) -> AgentReply:
        """One public discussion speech in front of everyone.

        transcript: raw (sender_id | "player", content) pairs of the public thread.
        Every entry is re-guarded against THIS agent's scope: a fact that is
        public for the speaker may still be unknown to the listener.
        """
        phase = self.session.phase.value
        public_lines = []
        for sender, content in transcript:
            name = "玩家" if sender == "player" else self.script.get_character(sender).name
            line = f"{name}：{content}"
            public_lines.append(
                ChatMessage(role="user", content=self._guard.guard(line).text)
            )
        discuss_prompt = (
            self._system_prompt
            + "\n\n【自由讨论环节】所有人围坐公开讨论案件，轮到你发言。根据讨论进展和你的立场"
            "说一段话——可以质疑、辩解、转移视线或补充信息，不超过三句话。"
            "仍然遵守铁律：不得透露你的秘密清单之外、你不应该知道的事。"
        )
        messages = [
            ChatMessage(role="system", content=discuss_prompt),
            *[
                self._guarded_memory(m) if m.role == "user" else m
                for m in self.memory.build_context()
            ],
            *public_lines,
        ]
        text, leaks, rewritten, fell_back = await self._screened_generate(messages)
        self.session.record_message(
            self.character.id, "all", text, phase=phase,
            **({"rewritten": True} if rewritten else {}),
            **({"fell_back": True} if fell_back else {}),
        )
        await self._commit_reply(text, fell_back)
        return AgentReply(text=text, leaks=leaks, rewritten=rewritten, fell_back=fell_back)
