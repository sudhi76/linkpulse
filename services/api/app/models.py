from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Link(Base):
    __tablename__ = "links"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    target_url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def is_expired(self, now: datetime) -> bool:
        if self.expires_at is None:
            return False
        expires = self.expires_at
        # SQLite drops timezone info; treat stored values as UTC.
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return expires <= now
