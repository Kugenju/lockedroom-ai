"""In-memory game registry (W1). Persistence arrives with the database milestone."""

import uuid

from app.core.agents.agent import CharacterAgent
from app.core.engine.session import GameSession
from app.core.infoguard.detector import LeakDetector
from app.core.infoguard.judge import LeakJudge
from app.core.infoguard.scope import compile_scopes
from app.core.llm.base import BaseChatModel
from app.core.scripts.loader import load_script


class UnknownGameError(KeyError):
    pass


class GameRecord:
    def __init__(self, session: GameSession, agents: dict[str, CharacterAgent]):
        self.session = session
        self.agents = agents


class GameStore:
    def __init__(
        self,
        llm: BaseChatModel,
        enable_judge: bool = True,
        event_store=None,
    ):
        self._llm = llm
        self._enable_judge = enable_judge
        self._event_store = event_store
        self._games: dict[str, GameRecord] = {}

    def create(self, script_id: str) -> GameRecord:
        from app.core.config import Settings
        from app.core.llm.factory import create_chat_model
        from app.core.llm.fake import FakeLLM

        script = load_script(script_id)  # FileNotFoundError → 404 at the route layer
        session = GameSession(
            session_id=uuid.uuid4().hex, script=script, llm=self._llm,
            event_store=self._event_store,
        )
        if self._event_store is not None:
            self._event_store.create_game(session.session_id, script_id, session.phase.value)
        scopes = compile_scopes(script)

        # The judge needs a real LLM; injected/FakeLLM backends (tests, offline dev)
        # run rule-only detection.
        settings = Settings()
        judge = None
        if (
            self._enable_judge
            and settings.judge_enabled
            and not isinstance(self._llm, FakeLLM)
        ):
            judge_llm = (
                create_chat_model(settings, model=settings.judge_model)
                if settings.judge_model
                else self._llm
            )
            judge = LeakJudge(judge_llm, script)

        agents = {
            c.id: CharacterAgent(
                character=c,
                script=script,
                scope=scopes[c.id],
                llm=self._llm,
                session=session,
                detector=LeakDetector(script, scopes[c.id]),
                judge=judge,
            )
            for c in script.talkable_characters
        }
        record = GameRecord(session=session, agents=agents)
        self._games[session.session_id] = record
        return record

    def get(self, game_id: str) -> GameRecord:
        try:
            return self._games[game_id]
        except KeyError:
            raise UnknownGameError(game_id) from None
