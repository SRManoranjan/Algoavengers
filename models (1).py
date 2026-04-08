"""
Typed Pydantic models for the Clinical Decisions OpenEnv API.
"""

from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# ─── Observation ──────────────────────────────────────────────────────────────

class Vitals(BaseModel):
    heart_rate: int = Field(..., description="Heart rate in bpm")
    blood_pressure_systolic: int = Field(..., description="Systolic BP in mmHg")
    blood_pressure_diastolic: int = Field(..., description="Diastolic BP in mmHg")
    temperature: float = Field(..., description="Temperature in Celsius")
    respiratory_rate: int = Field(..., description="Respiratory rate breaths/min")
    oxygen_saturation: float = Field(..., description="SpO2 in %")


class ClinicalObservation(BaseModel):
    patient_id: str
    chief_complaint: str
    vitals: Vitals
    history: str
    available_tests: list[str]
    test_results: dict[str, str] = Field(default_factory=dict)
    current_step: int
    max_steps: int
    done: bool
    reward_so_far: float
    task_id: str
    hint: Optional[str] = None


# ─── Actions ──────────────────────────────────────────────────────────────────

class OrderTestAction(BaseModel):
    action: Literal["order_test"]
    test: str = Field(..., description="Name of the test to order")


class DiagnoseAction(BaseModel):
    action: Literal["diagnose"]
    diagnosis: str = Field(..., description="Free-text or ICD diagnosis")


class TreatAction(BaseModel):
    action: Literal["treat"]
    treatment: str = Field(..., description="Free-text treatment plan")


class TriageAction(BaseModel):
    action: Literal["triage"]
    priority: Literal["emergent", "urgent", "non-urgent"]


# Union for the step endpoint body
class StepRequest(BaseModel):
    action: str = Field(..., description="Action type: order_test | diagnose | treat | triage")
    test: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    priority: Optional[str] = None


# ─── API Responses ────────────────────────────────────────────────────────────

class StepResult(BaseModel):
    observation: ClinicalObservation
    reward: float
    done: bool
    info: dict[str, Any] = Field(default_factory=dict)


class ResetRequest(BaseModel):
    task_id: Optional[str] = Field(
        default="task_triage",
        description="One of: task_triage | task_diagnosis | task_treatment"
    )
    case_id: Optional[str] = Field(
        default=None,
        description="Specific case ID (optional). Defaults to first case of task."
    )


class ResetResult(BaseModel):
    observation: ClinicalObservation
    task_id: str
    case_id: str
    message: str


class StateResult(BaseModel):
    session_id: str
    task_id: str
    case_id: str
    current_step: int
    max_steps: int
    done: bool
    reward_so_far: float
    ordered_tests: list[str]
    triage_submitted: Optional[str]
    diagnosis_submitted: Optional[str]
    treatment_submitted: Optional[str]
    observation: ClinicalObservation


class TaskInfo(BaseModel):
    id: str
    name: str
    difficulty: str
    description: str
    max_steps: int
    reward_range: list[float]


class TaskListResult(BaseModel):
    tasks: list[TaskInfo]
