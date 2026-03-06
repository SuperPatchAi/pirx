from pydantic import BaseModel
from typing import Optional


class TerraUser(BaseModel):
    user_id: str
    provider: str
    reference_id: Optional[str] = None


class TerraWebhookPayload(BaseModel):
    type: str  # "auth", "activity", "sleep", "body", "daily"
    user: Optional[TerraUser] = None
    data: Optional[list[dict]] = None
    status: Optional[str] = None


class TerraWidgetRequest(BaseModel):
    redirect_url: str
    failure_redirect_url: Optional[str] = None


class TerraWidgetResponse(BaseModel):
    url: str
    session_id: str
