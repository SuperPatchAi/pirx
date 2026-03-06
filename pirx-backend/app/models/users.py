from typing import Optional

from pydantic import BaseModel


class UserProfile(BaseModel):
    user_id: str
    email: str
    primary_event: Optional[str] = "3000"
    baseline_event_id: Optional[str] = None
