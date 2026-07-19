from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from time import perf_counter
from typing import Any, Dict, List

from cores.core.execution_plan import ExecutionPlan
from cores.interfaces.module import ModuleResult, ModuleStatus


@dataclass
class TraceEntry:
    module_name: str
    status: ModuleStatus
    execution_time_ms: float
    error_message: str | None = None
    cycle: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_name": self.module_name,
            "status": str(self.status),
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "cycle": self.cycle,
        }


class ExecutionLayer:
    def __init__(self, tracing_enabled: bool = True) -> None:
        self._tracing_enabled = tracing_enabled
        self._trace: List[TraceEntry] = []

    def execute(
        self,
        plan: ExecutionPlan,
        state: Any,
        context: Any,
    ) -> List[ModuleResult]:
        results = []
        for module in plan.modules:
            started_at = perf_counter()
            try:
                result = module.execute(state, context)
            except Exception as exc:
                elapsed = (perf_counter() - started_at) * 1000.0
                result = ModuleResult(
                    module_name=module.name,
                    status=ModuleStatus.FAILURE,
                    error_message=str(exc),
                    execution_time_ms=elapsed,
                )
            if self._tracing_enabled:
                self._trace.append(TraceEntry(
                    module_name=result.module_name,
                    status=result.status,
                    execution_time_ms=result.execution_time_ms,
                    error_message=result.error_message,
                    cycle=context.cycle_count if hasattr(context, "cycle_count") else 0,
                ))
            results.append(result)
        return results

    @property
    def execution_trace(self) -> List[TraceEntry]:
        return list(self._trace)

    def clear_trace(self) -> None:
        self._trace.clear()
