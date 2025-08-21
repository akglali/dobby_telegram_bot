# db.py
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from sqlalchemy import (
    BigInteger, Text, String, ForeignKey, func, select, delete
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship
)
from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession
)

# Load env
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# We accept a sync-style DATABASE_URL and convert to async
RAW_DB_URL = os.getenv("DATABASE_URL")
if not RAW_DB_URL:
    raise RuntimeError("DATABASE_URL missing in .env")

ASYNC_DB_URL = (
    RAW_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
    if RAW_DB_URL.startswith("postgresql://")
    else RAW_DB_URL
)

# --- SQLAlchemy setup ---
engine = create_async_engine(ASYNC_DB_URL, echo=False, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Conversation(Base):
    __tablename__ = "conversations"
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[Optional[str]] = mapped_column(server_default=func.now(), onupdate=func.now())

    messages: Mapped[List["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan"
    )

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("conversations.chat_id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[Optional[str]] = mapped_column(server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

# --- API ---
DEFAULT_SYSTEM_PROMPT = "You are Dobby, a helpful but concise assistant for Telegram."

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_persona(session: AsyncSession, chat_id: int) -> str:
    res = await session.get(Conversation, chat_id)
    return res.system_prompt if (res and res.system_prompt) else DEFAULT_SYSTEM_PROMPT

async def set_persona(session: AsyncSession, chat_id: int, prompt: str) -> None:
    conv = await session.get(Conversation, chat_id)
    if not conv:
        conv = Conversation(chat_id=chat_id, system_prompt=prompt)
        session.add(conv)
    else:
        conv.system_prompt = prompt
    await session.commit()

async def reset_chat(session: AsyncSession, chat_id: int) -> None:
    # delete the conversation row -> cascades messages
    await session.execute(delete(Conversation).where(Conversation.chat_id == chat_id))
    await session.commit()

async def fetch_history(session: AsyncSession, chat_id: int, limit_pairs: int = 6) -> List[dict]:
    """
    Return last N pairs (~2*limit) in chronological order.
    """
    stmt = (
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit_pairs * 2)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    rows.reverse()  # chronological
    return [{"role": m.role, "content": m.content} for m in rows]

async def ensure_conversation_exists(session: AsyncSession, chat_id: int) -> None:
    if await session.get(Conversation, chat_id) is None:
        session.add(Conversation(chat_id=chat_id))
        await session.commit()

async def append_message(session: AsyncSession, chat_id: int, role: str, content: str) -> None:
    await ensure_conversation_exists(session, chat_id)
    session.add(Message(chat_id=chat_id, role=role, content=content))
    await session.commit()

async def append_pair(session: AsyncSession, chat_id: int, user_text: str, assistant_text: str) -> None:
    await ensure_conversation_exists(session, chat_id)
    session.add_all([
        Message(chat_id=chat_id, role="user", content=user_text),
        Message(chat_id=chat_id, role="assistant", content=assistant_text),
    ])
    await session.commit()
