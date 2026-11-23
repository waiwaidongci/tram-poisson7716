from datetime import datetime
from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
from src.utils.time import now

class User(Base):
    __tablename__ = 'users'

    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(250))
    role: Mapped[str] = mapped_column(String(20))

class Audit(Base):
    __tablename__ = 'audit_events'

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(64))
    event: Mapped[str] = mapped_column(String(70))
    target: Mapped[str] = mapped_column(String(100))
    info: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=now)
