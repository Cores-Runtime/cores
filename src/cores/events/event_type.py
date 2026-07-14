from enum import StrEnum


class EventType(StrEnum):
    """
    Standard event types supported by the CORES Runtime.
    """
    MODULE_STARTED = "module_started"
    MODULE_COMPLETED = "module_completed"
    MODULE_FAILED = "module_failed"
    SYSTEM_EMERGENCY = "system_emergency"
    STATE_UPDATED = "state_updated"
    DIAGNOSTIC = "diagnostic"
