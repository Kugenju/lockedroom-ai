"""A character agent: persona + scoped knowledge + leak-intercepted dialogue.

Pipeline per player message:
  1. record the player's message (event log)
  2. generate a draft reply via the LLM
  3. LeakDetector checks the draft (InfoGuard Layer 2)
     - hard leak  -> one rewrite attempt with an explicit warning
     - still hard -> discard the draft entirely, emit a safe fallback line
     - soft leak  -> recorded, reply passes
  4. record the approved reply; memory only ever sees approved text
"""

from dataclasses import dataclass, field

from app.core.agents.prompt_builder import build_system_prompt
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
    ):
        self.character = character
        self.script = script
        self.scope = scope
        self.llm = llm
        self.session = session
        self.detector = detector
        self._judge = judge
        self._guard = ContextGuard(script, scope)
        self.memory: list[ChatMessage] = []
        self._system_prompt = build_system_prompt(script, character, scope)

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
            *[self._guarded_memory(m) for m in self.memory],
            ChatMessage(role="user", content=guarded.text),
        ]
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
                    + "。请重新回答玩家上一个问题，彻底避开这些内容。）"
                ),
            )
            retry = await self.llm.chat([*messages, ChatMessage(role="assistant", content=draft.content), warn])
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

        self.session.record_message(
            self.character.id, "player", text, phase=phase,
            **({"rewritten": True} if rewritten else {}),
            **({"fell_back": True} if fell_back else {}),
        )
        # memory only ever contains approved text — leaked drafts never persist
        self.memory.append(ChatMessage(role="user", content=player_message))
        self.memory.append(ChatMessage(role="assistant", content=text))
        return AgentReply(text=text, leaks=leaks, rewritten=rewritten, fell_back=fell_back)
