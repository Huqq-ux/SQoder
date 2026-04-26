import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


class SOPState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    STEP_COMPLETED = "step_completed"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_CONFIRMATION = "waiting_confirmation"
    PAUSED = "paused"


@dataclass
class StepResult:
    step_index: int
    step_name: str
    status: str
    result: str = ""
    error: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SOPExecution:
    execution_id: str
    sop_name: str
    state: SOPState = SOPState.PENDING
    current_step: int = 0
    total_steps: int = 0
    step_results: list[StepResult] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: str = ""


_VALID_TRANSITIONS = {
    SOPState.PENDING: [SOPState.RUNNING],
    SOPState.RUNNING: [
        SOPState.STEP_COMPLETED,
        SOPState.COMPLETED,
        SOPState.FAILED,
        SOPState.WAITING_CONFIRMATION,
        SOPState.PAUSED,
    ],
    SOPState.STEP_COMPLETED: [SOPState.RUNNING, SOPState.COMPLETED],
    SOPState.WAITING_CONFIRMATION: [SOPState.RUNNING, SOPState.FAILED, SOPState.PAUSED],
    SOPState.PAUSED: [SOPState.RUNNING, SOPState.FAILED],
    SOPState.FAILED: [SOPState.RUNNING],
    SOPState.COMPLETED: [],
}


class StateMachine:
    def __init__(self):
        self._executions: dict[str, SOPExecution] = {}

    def create_execution(self, sop_name: str, total_steps: int) -> SOPExecution:
        execution_id = f"{sop_name}_{uuid.uuid4().hex[:8]}"
        execution = SOPExecution(
            execution_id=execution_id,
            sop_name=sop_name,
            total_steps=total_steps,
            started_at=datetime.now().isoformat(),
        )
        self._executions[execution_id] = execution

        if sop_name not in self._executions:
            self._executions[sop_name] = execution

        return execution

    def transition(self, sop_name: str, new_state: SOPState) -> bool:
        execution = self._executions.get(sop_name)
        if not execution:
            return False

        if new_state not in _VALID_TRANSITIONS.get(execution.state, []):
            return False

        execution.state = new_state

        if new_state == SOPState.COMPLETED:
            execution.completed_at = datetime.now().isoformat()

        return True

    def advance_step(self, sop_name: str, step_result: StepResult) -> bool:
        execution = self._executions.get(sop_name)
        if not execution:
            return False

        if execution.state not in (SOPState.RUNNING, SOPState.STEP_COMPLETED):
            return False

        execution.step_results.append(step_result)
        execution.current_step = step_result.step_index + 1

        if execution.current_step >= execution.total_steps:
            return self.transition(sop_name, SOPState.COMPLETED)

        execution.state = SOPState.STEP_COMPLETED
        execution.state = SOPState.RUNNING
        return True

    def get_execution(self, sop_name: str) -> Optional[SOPExecution]:
        return self._executions.get(sop_name)

    def get_progress(self, sop_name: str) -> float:
        execution = self._executions.get(sop_name)
        if not execution or execution.total_steps == 0:
            return 0.0
        return execution.current_step / execution.total_steps

    def set_error(self, sop_name: str, error: str):
        execution = self._executions.get(sop_name)
        if not execution:
            return
        execution.error = error
        self.transition(sop_name, SOPState.FAILED)

    def list_executions(self) -> list[SOPExecution]:
        return list(self._executions.values())

    def remove_execution(self, sop_name: str) -> bool:
        if sop_name in self._executions:
            del self._executions[sop_name]
            return True
        return False

    def cleanup_completed(self, max_age_hours: int = 24) -> int:
        now = datetime.now()
        to_remove = []

        for key, execution in self._executions.items():
            if execution.state in (SOPState.COMPLETED, SOPState.FAILED):
                if execution.completed_at:
                    completed = datetime.fromisoformat(execution.completed_at)
                    age_hours = (now - completed).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        to_remove.append(key)

        for key in to_remove:
            del self._executions[key]

        return len(to_remove)
