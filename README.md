# 🏥 Clinical Decisions OpenEnv

A **real-world healthcare clinical decision-making environment** for AI agent training and evaluation, built to the [OpenEnv](https://openenv.dev) specification.

The agent plays the role of a **virtual physician** — assessing patient vitals, ordering diagnostic tests, interpreting results, and making triage, diagnosis, and treatment decisions. Reward is based on clinical accuracy, safety, and efficiency.

---

## 🗂️ Project Structure

```
clinical-openenv/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI server (OpenEnv API endpoints)
│   ├── env.py           # Session management + step/reset/state logic
│   └── models.py        # Typed Pydantic models
├── tasks/
│   ├── __init__.py
│   ├── cases.py         # Patient case definitions (6 cases, 3 tasks)
│   └── graders.py       # Agent graders (TriageGrader, DiagnosisGrader, TreatmentGrader)
├── inference.py         # Baseline LLM agent inference script
├── pre_validate.py      # Pre-submission validation script
├── openenv.yaml         # OpenEnv specification
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## 🎯 Tasks

| Task ID | Name | Difficulty | Max Steps | Scoring |
|---|---|---|---|---|
| `task_triage` | Emergency Triage Classification | Easy | 5 | Triage accuracy (60%) + relevant test (25%) + speed (15%) |
| `task_diagnosis` | Differential Diagnosis | Medium | 8 | Diagnosis accuracy (50%) + test efficiency (30%) + triage (20%) |
| `task_treatment` | Treatment Planning | Hard | 10 | Diagnosis (30%) + treatment (35%) + safety/no contraindications (25%) + tests (10%) |

All rewards are in **[0.0, 1.0]**. Partial credit is given for correct sub-steps.

---

## 👁️ Observation Space

```json
{
  "patient_id": "PT-001",
  "chief_complaint": "Severe chest pain radiating to left arm...",
  "vitals": {
    "heart_rate": 102,
    "blood_pressure_systolic": 88,
    "blood_pressure_diastolic": 60,
    "temperature": 36.8,
    "respiratory_rate": 22,
    "oxygen_saturation": 94.0
  },
  "history": "68-year-old male. Hypertension, T2DM...",
  "available_tests": ["ECG", "Troponin", "CBC", ...],
  "test_results": {"ECG": "ST elevation in II, III, aVF..."},
  "current_step": 2,
  "max_steps": 5,
  "done": false,
  "reward_so_far": 0.05,
  "task_id": "task_triage",
  "hint": "Test result or grader feedback"
}
```

---

## ⚡ Action Space

All actions are JSON objects sent to `POST /step`:

```json
// Order a diagnostic test
{"action": "order_test", "test": "ECG"}

// Set triage priority
{"action": "triage", "priority": "emergent"}

// Submit a diagnosis
{"action": "diagnose", "diagnosis": "Acute Myocardial Infarction (STEMI)"}

// Prescribe treatment
{"action": "treat", "treatment": "Aspirin 325mg, Heparin IV, PCI activation"}
```

---

## 🔌 API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/reset` | Start new episode |
| `POST` | `/step` | Take one action |
| `GET` | `/state` | Get current session state |
| `GET` | `/tasks` | List all tasks |
| `GET` | `/cases` | List all patient cases |
| `GET` | `/docs` | Interactive Swagger UI |

### Reset example

```bash
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task_triage"}'
```

### Step example

```bash
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"action": "order_test", "test": "ECG"}'
```

---

## 🚀 Setup & Running Locally

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Visit `http://localhost:8000/docs` for the interactive API explorer.

### 3. Run inference

Set environment variables then run:

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="your-api-key"
export ENV_BASE_URL="http://localhost:8000"

python inference.py
```

### 4. Pre-submission validation

```bash
# With server running:
python pre_validate.py
```

---

## 🐳 Docker

### Build

```bash
docker build -t clinical-openenv:latest .
```

### Run

```bash
docker run -p 7860:7860 \
  -e API_BASE_URL="https://api.openai.com/v1" \
  -e MODEL_NAME="gpt-4o-mini" \
  -e HF_TOKEN="your-key" \
  clinical-openenv:latest
```

---

## 🤗 Hugging Face Spaces Deployment

1. Create a new **Docker** Space on [huggingface.co/spaces](https://huggingface.co/spaces)
2. Push this repo:
   ```bash
   git remote add hf https://huggingface.co/spaces/<username>/<space-name>
   git push hf main
   ```
3. Set Space secrets (Settings → Repository secrets):
   - `API_BASE_URL`
   - `MODEL_NAME`
   - `HF_TOKEN`

The Space will auto-build from the Dockerfile and expose port 7860.

---

## 📊 Reward Function Design

### Task 1 — Triage (Easy)
Immediate life-threatening presentations (e.g., STEMI, SAH) must be classified as `emergent`. The reward is front-loaded toward correctness (0.60), with partial credit for gathering supporting evidence and acting quickly.

### Task 2 — Diagnosis (Medium)
A correct diagnosis requires understanding the clinical picture. The grader checks for key condition terms in the agent's diagnosis string, then evaluates test selection efficiency — penalising unnecessary tests via Jaccard overlap scoring.

### Task 3 — Treatment (Hard)
The hardest task: the agent must diagnose correctly **and** prescribe appropriate drugs **without** using contraindicated medications (e.g., penicillin in a penicillin-allergic patient). Patient safety violations yield 0 reward on the safety component, even if the treatment is otherwise reasonable.

### Partial Progress Signals
- Small +0.05 step rewards for ordering relevant tests and submitting actions
- Final terminal reward (from grader) on episode completion
- Intermediate feedback via `hint` field in observation

---

## 🏥 Clinical Cases

| Case ID | Task | Patient | Condition |
|---|---|---|---|
| `task_triage_001` | Triage | PT-001 | STEMI — Inferior MI |
| `task_triage_002` | Triage | PT-002 | Viral URI (non-urgent) |
| `task_diagnosis_001` | Diagnosis | PT-003 | Acute Decompensated Heart Failure |
| `task_diagnosis_002` | Diagnosis | PT-004 | Subarachnoid Hemorrhage |
| `task_treatment_001` | Treatment | PT-005 | Community-Acquired Pneumonia (penicillin allergy) |
| `task_treatment_002` | Treatment | PT-006 | Diabetic Ketoacidosis (new-onset T1DM) |

---

## 📋 Environment Variables

| Variable | Description | Required |
|---|---|---|
| `API_BASE_URL` | OpenAI-compatible LLM API endpoint | Yes (inference) |
| `MODEL_NAME` | Model identifier (e.g., `gpt-4o-mini`) | Yes (inference) |
| `HF_TOKEN` | Hugging Face / API key for LLM calls | Yes (inference) |
| `ENV_BASE_URL` | URL of the running OpenEnv server | Yes (inference) |
| `PORT` | Server port (default: 7860 for HF Spaces) | No |

---

## 📝 Inference Log Format

The inference script emits structured JSON logs to stdout:

```json
{"type": "START", "task": "Emergency Triage Classification", "env": "clinical-decisions-openenv", "model": "gpt-4o-mini"}
{"type": "STEP", "step": 1, "action": {"action": "order_test", "test": "ECG"}, "reward": 0.05, "done": false, "error": null}
{"type": "STEP", "step": 2, "action": {"action": "triage", "priority": "emergent"}, "reward": 1.0, "done": true, "error": null}
{"type": "END", "success": true, "steps": 2, "score": 1.0, "rewards": [0.05, 1.0]}
```

---

## License

MIT
