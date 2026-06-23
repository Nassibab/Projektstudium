import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

StepStatus = Literal["running", "success", "skipped", "failed"]
RunStatus = Literal["running", "success", "failed"]


@dataclass
class PipelineStep:
    name: str
    status: StepStatus = "running"
    message: str = ""
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "duration_ms": self.duration_ms,
        }


@dataclass
class PipelineRun:
    thread_id: str
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    current_step: str | None = None
    status: RunStatus = "running"
    steps: list[PipelineStep] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return self.status == "failed"

    def add_step(self, step: PipelineStep) -> PipelineStep:
        self.steps.append(step)
        self.current_step = step.name
        if step.status == "failed":
            self.status = "failed"
        return step

    def finish(self) -> "PipelineRun":
        if self.status != "failed":
            self.status = "success"
        self.current_step = None
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "current_step": self.current_step,
            "status": self.status,
            "steps": [step.to_dict() for step in self.steps],
        }
