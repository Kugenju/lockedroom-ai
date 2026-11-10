"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.store import GameStore
from app.core.llm.base import BaseChatModel
from app.core.persistence.event_store import SqlAlchemyEventStore


def create_app(llm: BaseChatModel | None = None) -> FastAPI:
    llm_injected = llm is not None
    if llm is None:
        from app.core.llm.factory import create_chat_model

        llm = create_chat_model()

    app = FastAPI(title="LockedRoom AI", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tightened once the frontend origin is known
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.store = GameStore(
        llm,
        enable_judge=llm_injected is None,
        event_store=None if llm_injected else SqlAlchemyEventStore(),
    )

    from app.api.routes_game import router as game_router

    app.include_router(game_router)
    return app
