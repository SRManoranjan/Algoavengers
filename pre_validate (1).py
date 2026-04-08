"""
pre_validate.py — Pre-submission validation for Clinical Decisions OpenEnv.

Checks:
  1. openenv.yaml is valid
  2. /health returns 200
  3. /reset works for all 3 tasks
  4. /step works for all action types
  5. /state works
  6. Reward is in [0.0, 1.0] for all tasks
  7. inference.py exists in root

Run:
    python pre_validate.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import subprocess
import threading
import httpx
import yaml

BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:8000")
TIMEOUT = 10.0
PASS = "✅"
FAIL = "❌"
results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    symbol = PASS if passed else FAIL
    print(f"  {symbol} {name}" + (f" — {detail}" if detail else ""))
    results.append((name, passed, detail))


def get(path: str) -> dict:
    r = httpx.get(f"{BASE_URL}{path}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def post(path: str, body: dict = None) -> dict:
    r = httpx.post(f"{BASE_URL}{path}", json=body or {}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


# ── 1. Check files exist ───────────────────────────────────────────────────────
print("\n[1] Checking required files...")
check("openenv.yaml exists", os.path.exists("openenv.yaml"))
check("inference.py exists", os.path.exists("inference.py"))
check("Dockerfile exists", os.path.exists("Dockerfile"))
check("requirements.txt exists", os.path.exists("requirements.txt"))

# ── 2. Validate openenv.yaml ──────────────────────────────────────────────────
print("\n[2] Validating openenv.yaml...")
try:
    with open("openenv.yaml") as f:
        config = yaml.safe_load(f)
    check("YAML parses successfully", True)
    check("Has 'name' field", "name" in config)
    check("Has 'tasks' field with 3+ tasks", isinstance(config.get("tasks"), list) and len(config["tasks"]) >= 3)
    check("Has 'api' field with reset/step/state", all(
        k in config.get("api", {}) for k in ("reset", "step", "state")
    ))
except Exception as e:
    check("YAML parses successfully", False, str(e))

# ── 3. Server health ──────────────────────────────────────────────────────────
print(f"\n[3] Checking server at {BASE_URL}...")
try:
    health = get("/health")
    check("/health returns 200", True, str(health))
except Exception as e:
    check("/health returns 200", False, str(e))
    print("  ⚠️  Server not running. Start with: uvicorn app.main:app --port 8000")
    print(f"\n{'─'*50}")
    print(f"RESULTS: {sum(1 for _, p, _ in results if p)}/{len(results)} checks passed")
    sys.exit(1)

# ── 4. Test /tasks ────────────────────────────────────────────────────────────
print("\n[4] Checking /tasks endpoint...")
try:
    tasks_resp = get("/tasks")
    tasks = tasks_resp.get("tasks", [])
    check("Has 3 tasks", len(tasks) >= 3)
    task_ids = [t["id"] for t in tasks]
    check("task_triage present", "task_triage" in task_ids)
    check("task_diagnosis present", "task_diagnosis" in task_ids)
    check("task_treatment present", "task_treatment" in task_ids)
    for t in tasks:
        rng = t.get("reward_range", [])
        check(
            f"reward_range valid for {t['id']}",
            len(rng) == 2 and rng[0] == 0.0 and rng[1] == 1.0,
            str(rng)
        )
except Exception as e:
    check("/tasks endpoint works", False, str(e))

# ── 5. Test /reset for all tasks ──────────────────────────────────────────────
print("\n[5] Testing /reset for all tasks...")
for task_id in ["task_triage", "task_diagnosis", "task_treatment"]:
    try:
        result = post("/reset", {"task_id": task_id})
        obs = result.get("observation", {})
        check(
            f"/reset task_id={task_id}",
            "patient_id" in obs and "chief_complaint" in obs,
            f"patient={obs.get('patient_id')}"
        )
    except Exception as e:
        check(f"/reset task_id={task_id}", False, str(e))

# ── 6. Test /step actions ─────────────────────────────────────────────────────
print("\n[6] Testing /step actions (using task_triage)...")
try:
    post("/reset", {"task_id": "task_triage"})

    # order_test
    r = post("/step", {"action": "order_test", "test": "ECG"})
    reward = r.get("reward", -1)
    check("/step order_test works", "observation" in r and "reward" in r, f"reward={reward}")
    check("reward in [0,1] after order_test", 0.0 <= reward <= 1.0, str(reward))

    # triage
    r = post("/step", {"action": "triage", "priority": "emergent"})
    reward = r.get("reward", -1)
    done = r.get("done", False)
    check("/step triage works + done=True", done, f"done={done}")
    check("reward in [0,1] after triage", 0.0 <= reward <= 1.0, str(reward))

except Exception as e:
    check("/step actions work", False, str(e))

# ── 7. Test /state ────────────────────────────────────────────────────────────
print("\n[7] Testing /state...")
try:
    post("/reset", {"task_id": "task_triage"})
    state = get("/state")
    check("/state returns session_id", "session_id" in state)
    check("/state returns task_id", "task_id" in state)
    check("/state returns observation", "observation" in state)
except Exception as e:
    check("/state works", False, str(e))

# ── 8. Full episode grader reward range ──────────────────────────────────────
print("\n[8] Testing full episodes + grader reward range...")
for task_id in ["task_triage", "task_diagnosis", "task_treatment"]:
    try:
        post("/reset", {"task_id": task_id})
        # Simulate a minimal passing episode
        if task_id == "task_triage":
            post("/step", {"action": "order_test", "test": "ECG"})
            r = post("/step", {"action": "triage", "priority": "emergent"})
        elif task_id == "task_diagnosis":
            post("/step", {"action": "order_test", "test": "BNP"})
            r = post("/step", {"action": "diagnose", "diagnosis": "heart failure"})
        elif task_id == "task_treatment":
            post("/step", {"action": "order_test", "test": "Chest X-Ray"})
            post("/step", {"action": "diagnose", "diagnosis": "pneumonia"})
            r = post("/step", {"action": "treat", "treatment": "azithromycin + levofloxacin IV"})

        reward = r.get("reward", -1)
        done = r.get("done", False)
        check(
            f"Full episode {task_id} — done=True, reward in [0,1]",
            done and 0.0 <= reward <= 1.0,
            f"done={done}, reward={reward:.4f}"
        )
    except Exception as e:
        check(f"Full episode {task_id}", False, str(e))

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'─'*50}")
passed = sum(1 for _, p, _ in results if p)
total = len(results)
print(f"RESULTS: {passed}/{total} checks passed")
if passed == total:
    print("🎉 All checks passed! Ready to submit.")
else:
    print("⚠️  Fix the failing checks before submitting.")
    failed = [(n, d) for n, p, d in results if not p]
    for name, detail in failed:
        print(f"  ❌ {name}: {detail}")
sys.exit(0 if passed == total else 1)
