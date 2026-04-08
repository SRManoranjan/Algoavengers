"""
Environment session management for Clinical Decisions OpenEnv.
"""

from __future__ import annotations
import uuid
import copy
from typing import Any, Optional

from tasks.cases import CASES, TASK_DEFAULT_CASES
from tasks.graders import get_grader
from app.models import (
    ClinicalObservation, Vitals, StepResult, StepRequest,
    ResetResult, StateResult
)


class ClinicalSession:
    """Holds mutable state for a single episode."""

    def __init__(self, case_id: str):
        self.session_id = str(uuid.uuid4())
        self.case_id = case_id
        self.case = copy.deepcopy(CASES[case_id])
        self.task_id: str = self.case["task_id"]
        self.current_step: int = 0
        self.max_steps: int = self.case["max_steps"]
        self.done: bool = False
        self.reward_so_far: float = 0.0
        self.ordered_tests: list[str] = []
        self.test_results: dict[str, str] = {}
        self.triage_submitted: Optional[str] = None
        self.diagnosis_submitted: Optional[str] = None
        self.treatment_submitted: Optional[str] = None
        self.last_info: dict[str, Any] = {}

    # ── Observation builder ────────────────────────────────────────────────────

    def _build_observation(self, hint: Optional[str] = None) -> ClinicalObservation:
        return ClinicalObservation(
            patient_id=self.case["patient_id"],
            chief_complaint=self.case["chief_complaint"],
            vitals=Vitals(**self.case["vitals"]),
            history=self.case["history"],
            available_tests=self.case["available_tests"],
            test_results=self.test_results,
            current_step=self.current_step,
            max_steps=self.max_steps,
            done=self.done,
            reward_so_far=round(self.reward_so_far, 4),
            task_id=self.task_id,
            hint=hint,
        )

    # ── Step ──────────────────────────────────────────────────────────────────

    def step(self, request: StepRequest) -> StepResult:
        if self.done:
            return StepResult(
                observation=self._build_observation(),
                reward=0.0,
                done=True,
                info={"error": "Episode already done. Call /reset to start a new episode."},
            )

        self.current_step += 1
        step_reward = 0.0
        hint: Optional[str] = None

        action = request.action.lower()

        if action == "order_test":
            test = (request.test or "").strip()
            if test in self.case["available_tests"] and test not in self.ordered_tests:
                self.ordered_tests.append(test)
                result_text = self.case["hints"].get(test, "No result available for this test.")
                self.test_results[test] = result_text
                hint = result_text
                # Small partial reward for ordering a relevant test
                if test in self.case["relevant_tests"]:
                    step_reward = 0.05
            elif test in self.ordered_tests:
                hint = f"Test '{test}' already ordered. Results: {self.test_results.get(test, 'pending')}"
            else:
                hint = f"Test '{test}' is not available. Available: {self.case['available_tests']}"

        elif action == "triage":
            priority = (request.priority or "").strip().lower()
            if priority in ("emergent", "urgent", "non-urgent"):
                self.triage_submitted = priority
                correct = self.case.get("correct_triage", "")
                if priority == correct:
                    step_reward = 0.10  # partial signal
                hint = f"Triage priority recorded: {priority}"
            else:
                hint = "Invalid priority. Use: emergent | urgent | non-urgent"

        elif action == "diagnose":
            diagnosis = (request.diagnosis or "").strip()
            if diagnosis:
                self.diagnosis_submitted = diagnosis
                hint = f"Diagnosis recorded: {diagnosis}"
                step_reward = 0.05
            else:
                hint = "Diagnosis cannot be empty."

        elif action == "treat":
            treatment = (request.treatment or "").strip()
            if treatment:
                self.treatment_submitted = treatment
                hint = f"Treatment plan recorded: {treatment}"
                step_reward = 0.05
                # Trigger grading on treatment submission for task_treatment
                if self.task_id == "task_treatment":
                    self.done = True
            else:
                hint = "Treatment cannot be empty."

        else:
            hint = f"Unknown action '{action}'. Use: order_test | triage | diagnose | treat"

        # ── Check terminal conditions ──────────────────────────────────────────
        if self.current_step >= self.max_steps:
            self.done = True

        # For triage task, mark done when triage is submitted
        if self.task_id == "task_triage" and self.triage_submitted:
            self.done = True

        # For diagnosis task, mark done when diagnosis is submitted
        if self.task_id == "task_diagnosis" and self.diagnosis_submitted:
            self.done = True

        # ── Final grading on done ──────────────────────────────────────────────
        final_reward = step_reward
        if self.done:
            grader = get_grader(self.task_id)
            session_state = {
                "triage_submitted": self.triage_submitted,
                "diagnosis_submitted": self.diagnosis_submitted,
                "treatment_submitted": self.treatment_submitted,
                "ordered_tests": self.ordered_tests,
                "current_step": self.current_step,
            }
            final_score, explanation = grader.grade(session_state, self.case)
            final_reward = final_score
            self.last_info = {"grader_explanation": explanation, "final_score": final_score}
            hint = (hint or "") + f"\n\n[GRADER] {explanation}"

        self.reward_so_far = final_reward if self.done else self.reward_so_far + step_reward

        return StepResult(
            observation=self._build_observation(hint=hint),
            reward=round(final_reward if self.done else step_reward, 4),
            done=self.done,
            info=self.last_info,
        )

    # ── State ─────────────────────────────────────────────────────────────────

    def get_state(self) -> StateResult:
        return StateResult(
            session_id=self.session_id,
            task_id=self.task_id,
            case_id=self.case_id,
            current_step=self.current_step,
            max_steps=self.max_steps,
            done=self.done,
            reward_so_far=round(self.reward_so_far, 4),
            ordered_tests=self.ordered_tests,
            triage_submitted=self.triage_submitted,
            diagnosis_submitted=self.diagnosis_submitted,
            treatment_submitted=self.treatment_submitted,
            observation=self._build_observation(),
        )


# ──────────────────────────────────────────────────────────────────────────────
# Global session store (single active session per server instance)
# ──────────────────────────────────────────────────────────────────────────────

_active_session: Optional[ClinicalSession] = None


def get_session() -> ClinicalSession:
    if _active_session is None:
        raise RuntimeError("No active session. Call /reset first.")
    return _active_session


def create_session(task_id: str, case_id: Optional[str] = None) -> ClinicalSession:
    global _active_session
    if case_id is None:
        case_id = TASK_DEFAULT_CASES.get(task_id)
    if case_id is None or case_id not in CASES:
        raise ValueError(f"Invalid task_id '{task_id}' or case_id '{case_id}'")
    _active_session = ClinicalSession(case_id)
    return _active_session
