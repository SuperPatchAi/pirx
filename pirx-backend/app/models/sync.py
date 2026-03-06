from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WearableConnection(BaseModel):
    provider: str
    connected_at: datetime
    last_sync_at: Optional[datetime] = None
    status: str
