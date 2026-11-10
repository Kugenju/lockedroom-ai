"""ORM models for game persistence."""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class GameRow(Base):
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    script_id: Mapped[str] = mapped_column(String)
    phase: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)
    ended_at: Mapped[str | None] = mapped_column(String, nullable=True)


class EventRow(Base):
    __tablename__ = "events"

    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), primary_key=True)
    seq: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String)
    ts: Mapped[str] = mapped_column(String)
    payload: Mapped[str] = mapped_column(String)  # JSON-serialized GameEvent payload
