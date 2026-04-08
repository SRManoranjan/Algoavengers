"""
Graders for each task. Each grader takes the session state and
returns a reward in [0.0, 1.0] with a human-readable explanation.
"""

from __future__ import annotations
import re
from typing import Any


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _contains_any(text: str, keywords: list[str]) -> bool:
    text = text.lower()
    return any(kw.lower() in text for kw in keywords)


def _jaccard_overlap(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    inter = set_a & set_b
    return len(inter) / len(union)


# ──────────────────────────────────────────────────────────────────────────────
# Task 1 — Triage Grader (Easy)
# ──────────────────────────────────────────────────────────────────────────────

class TriageGrader:
    """
    Scoring breakdown (total 1.0):
      0.60  — Correct triage priority submitted
      0.25  — Ordered at least one relevant test before deciding
      0.15  — Decided quickly (within first 3 steps for emergent, 4 for others)
    """

    def grade(self, state: dict[str, Any], case: dict[str, Any]) -> tuple[float, str]:
        triage_submitted: str | None = state.get("triage_submitted")
        ordered_tests: set[str] = set(state.get("ordered_tests", []))
        steps_used: int = state.get("current_step", 0)
        correct: str = case["correct_triage"]
        relevant: set[str] = case["relevant_tests"]

        reward = 0.0
        parts = []

        # 1. Correct triage priority
        if triage_submitted and triage_submitted.lower() == correct.lower():
            reward += 0.60
            parts.append(f"+0.60 correct triage priority ({correct})")
        elif triage_submitted:
            # partial — adjacent priority
            adjacency = {"emergent": ["urgent"], "urgent": ["emergent", "non-urgent"], "non-urgent": ["urgent"]}
            if triage_submitted.lower() in adjacency.get(correct.lower(), []):
                reward += 0.20
                parts.append(f"+0.20 triage priority off by one level")
            else:
                parts.append(f"+0.00 wrong triage priority (submitted '{triage_submitted}', expected '{correct}')")
        else:
            parts.append("+0.00 no triage submitted")

        # 2. Relevant test ordered
        overlap = ordered_tests & relevant
        if overlap:
            reward += 0.25
            parts.append(f"+0.25 ordered relevant test(s): {overlap}")
        else:
            parts.append("+0.00 no relevant tests ordered")

        # 3. Speed bonus
        speed_threshold = 3 if correct == "emergent" else 4
        if triage_submitted and steps_used <= speed_threshold:
            reward += 0.15
            parts.append(f"+0.15 fast decision (step {steps_used})")
        else:
            parts.append(f"+0.00 decision too slow or not submitted")

        explanation = " | ".join(parts)
        return round(min(max(reward, 0.0), 1.0), 4), explanation


# ──────────────────────────────────────────────────────────────────────────────
# Task 2 — Diagnosis Grader (Medium)
# ──────────────────────────────────────────────────────────────────────────────

DIAGNOSIS_KEYWORDS: dict[str, list[str]] = {
    "task_diagnosis_001": [
        "heart failure", "chf", "hfref", "decompensated", "congestive"
    ],
    "task_diagnosis_002": [
        "subarachnoid", "hemorrhage", "sah", "bleed", "aneurysm"
    ],
}

class DiagnosisGrader:
    """
    Scoring breakdown (total 1.0):
      0.50  — Diagnosis contains correct keywords
      0.30  — Test selection efficiency (ordered relevant tests, avoided wasteful ones)
      0.20  — Triage priority also correct (bonus for correct urgency assessment)
    """

    def grade(self, state: dict[str, Any], case: dict[str, Any]) -> tuple[float, str]:
        diagnosis_submitted: str | None = state.get("diagnosis_submitted")
        ordered_tests: set[str] = set(state.get("ordered_tests", []))
        triage_submitted: str | None = state.get("triage_submitted")
        case_id: str = case["patient_id"]
        relevant: set[str] = case["relevant_tests"]
        available: set[str] = set(case["available_tests"])

        # Look up keywords by patient_id → case key mapping
        case_key = next(
            (k for k, v in {
                "PT-003": "task_diagnosis_001",
                "PT-004": "task_diagnosis_002",
            }.items() if k == case_id),
            None
        )
        keywords = DIAGNOSIS_KEYWORDS.get(
            {
                "PT-003": "task_diagnosis_001",
                "PT-004": "task_diagnosis_002",
            }.get(case_id, ""), []
        )

        reward = 0.0
        parts = []

        # 1. Correct diagnosis
        if diagnosis_submitted and keywords and _contains_any(diagnosis_submitted, keywords):
            reward += 0.50
            parts.append("+0.50 correct diagnosis identified")
        elif diagnosis_submitted:
            parts.append(f"+0.00 diagnosis incorrect (got: '{diagnosis_submitted[:60]}')")
        else:
            parts.append("+0.00 no diagnosis submitted")

        # 2. Test efficiency
        ordered_relevant = ordered_tests & relevant
        ordered_total = len(ordered_tests)
        if ordered_relevant:
            efficiency = len(ordered_relevant) / max(ordered_total, 1)
            test_score = round(0.30 * efficiency, 4)
            reward += test_score
            parts.append(
                f"+{test_score:.2f} test efficiency "
                f"({len(ordered_relevant)}/{ordered_total} tests were relevant)"
            )
        else:
            parts.append("+0.00 no relevant tests ordered")

        # 3. Triage bonus
        correct_triage = case.get("correct_triage", "urgent")
        if triage_submitted and triage_submitted.lower() == correct_triage.lower():
            reward += 0.20
            parts.append(f"+0.20 correct triage priority ({correct_triage})")
        else:
            parts.append("+0.00 triage priority missing or wrong")

        explanation = " | ".join(parts)
        return round(min(max(reward, 0.0), 1.0), 4), explanation


# ──────────────────────────────────────────────────────────────────────────────
# Task 3 — Treatment Grader (Hard)
# ──────────────────────────────────────────────────────────────────────────────

TREATMENT_KEYWORDS: dict[str, list[str]] = {
    "PT-005": ["azithromycin", "levofloxacin", "fluoroquinolone", "macrolide", "doxycycline"],
    "PT-006": ["insulin", "normal saline", "fluid", "iv fluid", "saline"],
}

DIAGNOSIS_KEYWORDS_TREATMENT: dict[str, list[str]] = {
    "PT-005": ["pneumonia", "cap", "streptococcus", "pneumococcal"],
    "PT-006": ["dka", "diabetic ketoacidosis", "ketoacidosis", "type 1 diabetes"],
}

class TreatmentGrader:
    """
    Scoring breakdown (total 1.0):
      0.30  — Correct diagnosis submitted
      0.35  — Treatment contains correct drug/intervention keywords
      0.25  — No contraindicated drugs prescribed
      0.10  — Relevant confirmatory tests were ordered
    """

    def grade(self, state: dict[str, Any], case: dict[str, Any]) -> tuple[float, str]:
        diagnosis_submitted: str | None = state.get("diagnosis_submitted")
        treatment_submitted: str | None = state.get("treatment_submitted")
        ordered_tests: set[str] = set(state.get("ordered_tests", []))
        patient_id: str = case["patient_id"]
        relevant_tests: set[str] = case["relevant_tests"]
        contraindicated: list[str] = case.get("contraindicated_drugs", [])

        dx_keywords = DIAGNOSIS_KEYWORDS_TREATMENT.get(patient_id, [])
        tx_keywords = TREATMENT_KEYWORDS.get(patient_id, [])

        reward = 0.0
        parts = []

        # 1. Diagnosis
        if diagnosis_submitted and dx_keywords and _contains_any(diagnosis_submitted, dx_keywords):
            reward += 0.30
            parts.append("+0.30 correct diagnosis")
        else:
            parts.append(f"+0.00 diagnosis missing/incorrect")

        # 3. Safety check FIRST — contraindicated drugs zero out treatment score
        used_contraindicated: list[str] = []
        if treatment_submitted:
            used_contraindicated = [d for d in contraindicated if d.lower() in treatment_submitted.lower()]

        # 2. Treatment keywords (only score if no safety violation)
        if treatment_submitted and tx_keywords and _contains_any(treatment_submitted, tx_keywords):
            if not used_contraindicated:
                reward += 0.35
                parts.append("+0.35 appropriate treatment prescribed")
            else:
                parts.append(
                    "+0.00 treatment keywords present but SAFETY VIOLATION overrides treatment score"
                )
        else:
            parts.append("+0.00 treatment missing or inappropriate")

        # 3. Safety reward
        if treatment_submitted:
            if not used_contraindicated:
                reward += 0.25
                parts.append("+0.25 no contraindicated drugs used — patient safety maintained")
            else:
                parts.append(
                    f"+0.00 PATIENT SAFETY VIOLATION: contraindicated drug(s) used: {used_contraindicated}"
                )
        elif not treatment_submitted:
            parts.append("+0.00 no treatment submitted")

        # 4. Relevant tests ordered
        overlap = ordered_tests & relevant_tests
        if overlap:
            reward += 0.10
            parts.append(f"+0.10 ordered relevant confirmatory tests: {overlap}")
        else:
            parts.append("+0.00 no relevant tests ordered")

        explanation = " | ".join(parts)
        return round(min(max(reward, 0.0), 1.0), 4), explanation


# ──────────────────────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────────────────────

def get_grader(task_id: str):
    if task_id == "task_triage":
        return TriageGrader()
    elif task_id == "task_diagnosis":
        return DiagnosisGrader()
    elif task_id == "task_treatment":
        return TreatmentGrader()
    else:
        raise ValueError(f"Unknown task_id: {task_id}")
