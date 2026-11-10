from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, Field


class LinkCreate(BaseModel):
    url: AnyHttpUrl
    alias: str | None = Field(default=None, description="Custom short code")
    expires_at: datetime | None = None


class LinkOut(BaseModel):
    code: str
    short_url: str
    target_url: str
    created_at: datetime
    expires_at: datetime | None
