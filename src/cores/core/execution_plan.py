from typing import List
from pydantic import BaseModel, Field
from cores.interfaces.module import Module


class ExecutionPlan(BaseModel):
    """
    ExecutionPlan wraps the ordered list of modules to be executed during a runtime cycle.
    """
    model_config = {"arbitrary_types_allowed": True}

    modules: List[Module] = Field(default_factory=list)
