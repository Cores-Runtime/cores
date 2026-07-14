import uuid
from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from cores.events.event_type import EventType


class Event(BaseModel):
    """
    An Event is an immutable structured message describing something that occurred during runtime.
    """
    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str
    event_type: EventType
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=0)
