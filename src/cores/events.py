from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class Event(BaseModel):
    """
    An Event is a structured message describing something that occurred during runtime.
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=0)
