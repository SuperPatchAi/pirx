from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WearableConnection(BaseModel):
    provider: str
    connected_at: datetime
    last_sync_at: Optional[datetime] = None
    status: str


class StravaTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: int
    athlete: dict


class StravaWebhookEvent(BaseModel):
    object_type: str
    object_id: int
    aspect_type: str
    owner_id: int
    subscription_id: int
    event_time: int


class ConnectRequest(BaseModel):
    code: str
    redirect_uri: str


class ConnectResponse(BaseModel):
    provider: str
    status: str
    athlete_name: Optional[str] = None
