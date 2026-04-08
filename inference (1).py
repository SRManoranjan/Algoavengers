"""
inference.py — Baseline inference script for Clinical Decisions OpenEnv.

Runs an LLM agent through all 3 tasks and emits structured stdout logs
in the required [START] / [STEP] / [END] format.

Usage:
    python inference.py

Environment variables (required):
    API_BASE_URL   — LLM API endpoint (OpenAI-compatible)
    MODEL_NAME     — Model identifier
    HF_TOKEN       — Hugging Face / API key
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Any, Optional

import httpx
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE_URL: str = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME: str = os.environ.get("MODEL_NAME", "gpt-4o-mini")
API_KEY: str = os.environ.get("HF_TOKEN", "")
ENV_BASE_URL: str = os.environ.get("ENV_BASE_URL", "http://localhost:8000")

MAX_TOKENS: int = 512
SUCCESS_SCORE_THRESHOLD: float = 0.5

TASKS = [
    {
        "task_id": "task_triage",
        "task_name": "Emergency Triage Classification",
        "max_steps": 5,
        "max_total_reward": 1.0,
    },
    {
        "task_id": "task_diagnosis",
        "task_name": "Differential Diagnosis",
        "max_steps": 8,
        "max_total_reward": 1.0,
    },
    {
        "task_id": "task_treatment",
        "task_name": "Treatment Planning",
        "max_steps": 10,
        "max_total_reward": 1.0,
    },
]

BENCHMARK = "clinical-decisions-openenv"


# ── Logging helpers ───────────────────────────────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(json.dumps({
        "type": "START",
        "task": task,
        "env": env,
        "model": model,
    }), flush=True)


def log_step(
    step: int,
    action: Any,
    reward: float,
    done: bool,
    error: Optional[str] = None,
) -> None:
    print(json.dumps({
        "type": "STEP",
        "step": step,
        "action": action,
        "reward": reward,
        "done": done,
        "error": error,
    }), flush=True)


def log_end(
    success: bool,
    steps: int,
    score: float,
    rewards: list[float],
) -> None:
    print(json.dumps({
        "type": "END",
        "success": success,
        "steps": steps,
        "score": score,
        "rewards": rewards,
    }), flush=True)


# ── Environment client ────────────────────────────────────────────────────────

class ClinicalEnvClient:
    """Thin async HTTP client wrapping the OpenEnv REST API."""

    def __init__(self, base_url: str = ENV_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def reset(self, task_id: str) -> dict[str, Any]:
        resp = await self._client.post(
            f"{self.base_url}/reset",
            json={"task_id": task_id},
        )
        resp.raise_for_status()
        return resp.json()

    async def step(self, action: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(
            f"{self.base_url}/step",
            json=action,
        )
        resp.raise_for_status()
        return resp.json()

    async def state(self) -> dict[str, Any]:
        resp = await self._client.get(f"{self.base_url}/state")
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()

    async def health(self) -> dict[str, Any]:
        resp = await self._client.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()


# ── LLM agent ────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an experienced emergency medicine physician.
You are assessing a patient. You must take clinical actions in JSON format.

Available actions:
  {"action": "order_test", "test": "<test name>"}
  {"action": "triage", "priority": "emergent|urgent|non-urgent"}
  {"action": "diagnose", "diagnosis": "<your diagnosis>"}
  {"action": "treat", "treatment": "<your treatment plan>"}

Rules:
- Always respond with a SINGLE valid JSON object and nothing else.
- Order tests to gather information before making decisions.
- Base triage on vital signs and chief complaint severity.
- For diagnosis tasks, state the condition clearly.
- For treatment tasks, prescribe specific drugs/interventions and check for allergies.
- If a patient has an allergy, NEVER prescribe that drug class.
"""


def build_user_prompt(
    observation: dict[str, Any],
    step: int,
    last_reward: float,
    history: list[str],
) -> str:
    obs = observation
    vitals = obs.get("vitals", {})
    test_results = obs.get("test_results", {})

    lines = [
        f"=== PATIENT: {obs.get('patient_id')} | Step {step}/{obs.get('max_steps')} ===",
        f"Chief Complaint: {obs.get('chief_complaint')}",
        "",
        "Vitals:",
        f"  HR: {vitals.get('heart_rate')} bpm | BP: {vitals.get('blood_pressure_systolic')}/{vitals.get('blood_pressure_diastolic')} mmHg",
        f"  Temp: {vitals.get('temperature')}°C | RR: {vitals.get('respiratory_rate')} /min | SpO2: {vitals.get('oxygen_saturation')}%",
        "",
        f"Medical History: {obs.get('history')}",
        "",
        f"Available Tests: {', '.join(obs.get('available_tests', []))}",
    ]

    if test_results:
        lines.append("\nTest Results Ordered So Far:")
        for test, result in test_results.items():
            lines.append(f"  [{test}]: {result}")

    hint = obs.get("hint")
    if hint:
        lines.append(f"\nSystem Note: {hint}")

    if history:
        lines.append(f"\nYour action history:")
        for h in history[-5:]:
            lines.append(f"  {h}")

    lines.append(f"\nLast step reward: {last_reward:+.4f}")
    lines.append(f"Task: {obs.get('task_id')}")
    lines.append("\nWhat is your next clinical action? Respond with JSON only.")

    return "\n".join(lines)


def get_agent_action(
    client: OpenAI,
    observation: dict[str, Any],
    step: int,
    last_reward: float,
    history: list[str],
) -> dict[str, Any]:
    """Call the LLM and parse its JSON action."""
    user_prompt = build_user_prompt(observation, step, last_reward, history)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        action = json.loads(text.strip())
        return action
    except json.JSONDecodeError:
        print(f"[DEBUG] Failed to parse LLM JSON, defaulting to triage urgent", flush=True)
        return {"action": "triage", "priority": "urgent"}
    except Exception as exc:
        print(f"[DEBUG] LLM call failed: {exc}", flush=True)
        return {"action": "triage", "priority": "urgent"}


# ── Main loop ─────────────────────────────────────────────────────────────────

async def run_task(
    env: ClinicalEnvClient,
    llm_client: OpenAI,
    task: dict[str, Any],
) -> tuple[float, bool, int, list[float]]:
    """Run one task episode. Returns (score, success, steps_taken, rewards)."""
    task_id = task["task_id"]
    task_name = task["task_name"]
    max_steps = task["max_steps"]
    max_total_reward = task["max_total_reward"]

    rewards: list[float] = []
    history: list[str] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        reset_result = await env.reset(task_id)
        observation = reset_result["observation"]
        last_reward = 0.0
        done = observation.get("done", False)

        for step in range(1, max_steps + 1):
            if done:
                break

            action = get_agent_action(llm_client, observation, step, last_reward, history)

            try:
                step_result = await env.step(action)
            except Exception as exc:
                print(f"[DEBUG] step() error: {exc}", flush=True)
                log_step(step=step, action=action, reward=0.0, done=False, error=str(exc))
                break

            observation = step_result["observation"]
            reward = step_result.get("reward") or 0.0
            done = step_result.get("done", False)
            error = None

            rewards.append(reward)
            steps_taken = step
            last_reward = reward

            log_step(step=step, action=action, reward=reward, done=done, error=error)

            history.append(
                f"Step {step}: action={action.get('action')} -> reward {reward:+.4f}"
            )

            if done:
                break

        # Final score = last reward if episode terminated (grader fires on done)
        # For tasks that give a single terminal reward:
        score = rewards[-1] if rewards else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as exc:
        print(f"[DEBUG] Task '{task_id}' failed: {exc}", flush=True)

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    return score, success, steps_taken, rewards


async def main() -> None:
    # Verify env is up
    env = ClinicalEnvClient(ENV_BASE_URL)
    llm_client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    print(f"[DEBUG] Connecting to env at {ENV_BASE_URL}", flush=True)
    try:
        health = await env.health()
        print(f"[DEBUG] Env health: {health}", flush=True)
    except Exception as exc:
        print(f"[DEBUG] Cannot reach env: {exc}", flush=True)
        sys.exit(1)

    all_scores: list[float] = []

    for task in TASKS:
        print(f"\n[DEBUG] === Running task: {task['task_id']} ===", flush=True)
        score, success, steps, rewards = await run_task(env, llm_client, task)
        all_scores.append(score)
        print(
            f"[DEBUG] Task '{task['task_id']}' complete | score={score:.4f} | success={success} | steps={steps}",
            flush=True,
        )
        # Small pause between tasks
        await asyncio.sleep(1)

    overall = sum(all_scores) / len(all_scores) if all_scores else 0.0
    print(f"\n[DEBUG] === OVERALL SCORE: {overall:.4f} across {len(TASKS)} tasks ===", flush=True)

    await env.close()


if __name__ == "__main__":
    asyncio.run(main())
