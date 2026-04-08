"""
Clinical Decisions OpenEnv — FastAPI server.
Implements the OpenEnv standard API: /reset, /step, /state, /tasks, /health
"""

from __future__ import annotations
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.models import (
    ResetRequest, ResetResult,
    StepRequest, StepResult,
    StateResult, TaskListResult, TaskInfo,
)
from app.env import create_session, get_session
from tasks.cases import CASES

# ── Task metadata ──────────────────────────────────────────────────────────────
TASK_METADATA = [
    TaskInfo(
        id="task_triage",
        name="Emergency Triage Classification",
        difficulty="easy",
        description=(
            "Given a patient's presenting symptoms and vitals, correctly classify "
            "the triage priority (emergent, urgent, non-urgent). Partial credit "
            "is given for ordering relevant tests before deciding."
        ),
        max_steps=5,
        reward_range=[0.0, 1.0],
    ),
    TaskInfo(
        id="task_diagnosis",
        name="Differential Diagnosis",
        difficulty="medium",
        description=(
            "Work through a patient case by ordering appropriate diagnostic tests "
            "and arriving at a correct diagnosis. Scored on test selection efficiency "
            "and diagnostic accuracy."
        ),
        max_steps=8,
        reward_range=[0.0, 1.0],
    ),
    TaskInfo(
        id="task_treatment",
        name="Treatment Planning",
        difficulty="hard",
        description=(
            "Given a patient presentation, order confirmatory tests, diagnose the "
            "condition, assess contraindications from patient history, and prescribe "
            "a safe and effective treatment plan. Full marks require correct diagnosis "
            "+ safe treatment + no contraindicated medications."
        ),
        max_steps=10,
        reward_range=[0.0, 1.0],
    ),
]

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Clinical Decisions OpenEnv",
    description=(
        "A healthcare clinical decision-making environment for AI agent training. "
        "The agent acts as a virtual physician: assessing patients, ordering tests, "
        "and making diagnostic and treatment decisions."
    ),
    version="1.0.0",
    docs_url="/docs",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check — returns 200 OK."""
    return {"status": "ok", "env": "clinical-decisions-openenv", "version": "1.0.0"}


@app.post("/reset", response_model=ResetResult)
async def reset(body: ResetRequest = None) -> ResetResult:
    """
    Reset the environment and start a new episode.
    Optionally specify task_id and case_id.
    """
    if body is None:
        body = ResetRequest()
    task_id = body.task_id or "task_triage"
    case_id = body.case_id

    valid_tasks = [t.id for t in TASK_METADATA]
    if task_id not in valid_tasks:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid task_id '{task_id}'. Valid: {valid_tasks}",
        )

    try:
        session = create_session(task_id, case_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    obs = session._build_observation(
        hint=(
            f"New episode started. Task: {task_id}. "
            f"You are the attending physician. Assess the patient and take clinical actions. "
            f"Available actions: order_test, triage, diagnose, treat."
        )
    )
    return ResetResult(
        observation=obs,
        task_id=task_id,
        case_id=session.case_id,
        message=f"Episode started for task '{task_id}'. Patient: {obs.patient_id}.",
    )


@app.post("/step", response_model=StepResult)
async def step(body: StepRequest) -> StepResult:
    """
    Take one action step in the current episode.
    """
    try:
        session = get_session()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return session.step(body)


@app.get("/state", response_model=StateResult)
async def state() -> StateResult:
    """
    Return full current state of the active session.
    """
    try:
        session = get_session()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return session.get_state()


@app.get("/tasks", response_model=TaskListResult)
async def list_tasks() -> TaskListResult:
    """
    List all available tasks with metadata.
    """
    return TaskListResult(tasks=TASK_METADATA)


@app.get("/cases")
async def list_cases() -> dict[str, Any]:
    """
    List all available case IDs (without ground truth).
    """
    result = {}
    for case_id, case in CASES.items():
        result[case_id] = {
            "task_id": case["task_id"],
            "patient_id": case["patient_id"],
            "chief_complaint": case["chief_complaint"],
            "max_steps": case["max_steps"],
        }
    return result
