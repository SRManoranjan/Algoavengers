"""
Patient case definitions for the Clinical Decisions OpenEnv.
Each case includes the ground truth for grading.
"""

from typing import Any

CASES: dict[str, dict[str, Any]] = {

    # ─── TASK 1: TRIAGE (EASY) ────────────────────────────────────────────────
    "task_triage_001": {
        "task_id": "task_triage",
        "patient_id": "PT-001",
        "chief_complaint": "Severe chest pain radiating to left arm, onset 20 minutes ago. Diaphoretic.",
        "vitals": {
            "heart_rate": 102,
            "blood_pressure_systolic": 88,
            "blood_pressure_diastolic": 60,
            "temperature": 36.8,
            "respiratory_rate": 22,
            "oxygen_saturation": 94.0,
        },
        "history": (
            "68-year-old male. History of hypertension and type 2 diabetes. "
            "Takes metformin and lisinopril. Smoker for 40 years. "
            "No known drug allergies."
        ),
        "available_tests": [
            "ECG", "Troponin", "CBC", "BMP", "Chest X-Ray",
            "D-Dimer", "BNP", "Echocardiogram"
        ],
        "correct_triage": "emergent",
        "relevant_tests": {"ECG", "Troponin"},
        "hints": {
            "ECG": "Sinus tachycardia with ST elevation in leads II, III, aVF. Findings consistent with inferior STEMI.",
            "Troponin": "Troponin I: 2.8 ng/mL (ELEVATED — normal < 0.04 ng/mL). Consistent with myocardial injury.",
            "CBC": "WBC 11.2, Hgb 13.8, Plt 210 — within normal limits.",
            "BMP": "Na 138, K 4.1, Cr 1.1, Glucose 182 (elevated, consistent with known diabetes).",
            "Chest X-Ray": "No pneumothorax. Mild cardiomegaly. No acute pulmonary edema.",
            "D-Dimer": "D-Dimer 0.4 µg/mL — negative for pulmonary embolism.",
            "BNP": "BNP 180 pg/mL — mildly elevated, possible early heart failure.",
            "Echocardiogram": "Reduced EF ~40%. Inferior wall hypokinesis. Consistent with acute MI.",
        },
        "ground_truth_diagnosis": "Acute Myocardial Infarction (STEMI)",
        "ground_truth_treatment": "Aspirin 325mg, Heparin IV, PCI activation, Oxygen if SpO2 < 94%",
        "max_steps": 5,
    },

    "task_triage_002": {
        "task_id": "task_triage",
        "patient_id": "PT-002",
        "chief_complaint": "Mild sore throat and runny nose for 2 days. Low-grade fever.",
        "vitals": {
            "heart_rate": 78,
            "blood_pressure_systolic": 118,
            "blood_pressure_diastolic": 76,
            "temperature": 37.6,
            "respiratory_rate": 16,
            "oxygen_saturation": 99.0,
        },
        "history": (
            "24-year-old female. No significant past medical history. "
            "No medications. No known drug allergies."
        ),
        "available_tests": [
            "Rapid Strep Test", "CBC", "Mono Spot Test", "Throat Culture",
            "Chest X-Ray", "ECG"
        ],
        "correct_triage": "non-urgent",
        "relevant_tests": {"Rapid Strep Test"},
        "hints": {
            "Rapid Strep Test": "Negative for Group A Streptococcus.",
            "CBC": "WBC 9.8, Hgb 13.2, Plt 265 — normal.",
            "Mono Spot Test": "Negative for EBV heterophile antibodies.",
            "Throat Culture": "Pending. Likely viral etiology.",
            "Chest X-Ray": "Clear lung fields. Normal cardiomediastinal silhouette.",
            "ECG": "Normal sinus rhythm. No abnormalities.",
        },
        "ground_truth_diagnosis": "Viral Upper Respiratory Infection",
        "ground_truth_treatment": "Supportive care: rest, fluids, OTC analgesics. Return precautions given.",
        "max_steps": 5,
    },

    # ─── TASK 2: DIAGNOSIS (MEDIUM) ───────────────────────────────────────────
    "task_diagnosis_001": {
        "task_id": "task_diagnosis",
        "patient_id": "PT-003",
        "chief_complaint": "Progressive shortness of breath, bilateral leg swelling, orthopnea for 1 week.",
        "vitals": {
            "heart_rate": 96,
            "blood_pressure_systolic": 145,
            "blood_pressure_diastolic": 92,
            "temperature": 37.1,
            "respiratory_rate": 20,
            "oxygen_saturation": 91.0,
        },
        "history": (
            "72-year-old female. Known history of hypertension and atrial fibrillation. "
            "Currently on warfarin, amlodipine. Has not been adherent to low-sodium diet. "
            "No known drug allergies."
        ),
        "available_tests": [
            "BNP", "Echocardiogram", "Chest X-Ray", "CBC", "BMP",
            "D-Dimer", "Troponin", "ECG", "Urinalysis", "LFTs"
        ],
        "correct_triage": "urgent",
        "relevant_tests": {"BNP", "Chest X-Ray", "Echocardiogram"},
        "hints": {
            "BNP": "BNP 980 pg/mL (MARKEDLY ELEVATED — normal < 100 pg/mL). Strongly suggests heart failure.",
            "Echocardiogram": "EF 30% (severely reduced). Dilated left ventricle. Moderate mitral regurgitation.",
            "Chest X-Ray": "Cardiomegaly. Bilateral pleural effusions. Pulmonary vascular congestion — consistent with pulmonary edema.",
            "CBC": "WBC 8.5, Hgb 11.4 (mild anemia), Plt 188.",
            "BMP": "Na 132 (low), K 3.8, Cr 1.4 (mildly elevated), BUN 28.",
            "D-Dimer": "D-Dimer 1.1 µg/mL — mildly elevated but nonspecific in this context.",
            "Troponin": "Troponin I: 0.06 ng/mL — mildly elevated, possible demand ischemia vs chronic HF.",
            "ECG": "Irregular rhythm consistent with known atrial fibrillation. Left ventricular hypertrophy pattern.",
            "Urinalysis": "Mild proteinuria. No infection.",
            "LFTs": "Mildly elevated AST/ALT — possible congestive hepatopathy.",
        },
        "ground_truth_diagnosis": "Acute Decompensated Heart Failure (HFrEF)",
        "ground_truth_treatment": "IV furosemide 80mg, fluid restriction, low-sodium diet, continue warfarin, cardiology consult",
        "max_steps": 8,
    },

    "task_diagnosis_002": {
        "task_id": "task_diagnosis",
        "patient_id": "PT-004",
        "chief_complaint": "Sudden severe headache ('worst headache of my life'), neck stiffness, photophobia.",
        "vitals": {
            "heart_rate": 88,
            "blood_pressure_systolic": 165,
            "blood_pressure_diastolic": 95,
            "temperature": 38.2,
            "respiratory_rate": 18,
            "oxygen_saturation": 97.0,
        },
        "history": (
            "41-year-old male. No significant past medical history. "
            "Non-smoker. Occasional alcohol use. No medications. No known drug allergies."
        ),
        "available_tests": [
            "CT Head (non-contrast)", "Lumbar Puncture", "CBC", "BMP",
            "Blood Cultures", "Coagulation Panel", "MRI Brain", "ECG"
        ],
        "correct_triage": "emergent",
        "relevant_tests": {"CT Head (non-contrast)", "Lumbar Puncture"},
        "hints": {
            "CT Head (non-contrast)": "Hyperdense blood in subarachnoid space (basal cisterns). Findings consistent with subarachnoid hemorrhage.",
            "Lumbar Puncture": "Xanthochromia present. RBC count >100,000/µL in all tubes. Elevated opening pressure 28 cmH2O.",
            "CBC": "WBC 13.2 (mildly elevated), Hgb 14.1, Plt 290.",
            "BMP": "Na 138, K 4.0, Cr 0.9 — within normal limits.",
            "Blood Cultures": "Pending. Drawn prior to any antibiotics.",
            "Coagulation Panel": "PT/INR normal. PTT normal. No coagulopathy.",
            "MRI Brain": "Confirms blood in subarachnoid space. No parenchymal lesion. Aneurysm suspected at MCA bifurcation.",
            "ECG": "Normal sinus rhythm. No acute changes.",
        },
        "ground_truth_diagnosis": "Subarachnoid Hemorrhage (SAH)",
        "ground_truth_treatment": "Neurosurgery urgent consult, nimodipine 60mg q4h, BP control, ICU admission, CTA brain",
        "max_steps": 8,
    },

    # ─── TASK 3: TREATMENT (HARD) ─────────────────────────────────────────────
    "task_treatment_001": {
        "task_id": "task_treatment",
        "patient_id": "PT-005",
        "chief_complaint": "Productive cough, fever, right-sided pleuritic chest pain for 3 days.",
        "vitals": {
            "heart_rate": 108,
            "blood_pressure_systolic": 112,
            "blood_pressure_diastolic": 74,
            "temperature": 38.9,
            "respiratory_rate": 24,
            "oxygen_saturation": 92.0,
        },
        "history": (
            "58-year-old male. COPD (on tiotropium, albuterol). "
            "Penicillin allergy (anaphylaxis). Alcohol use disorder. "
            "No anticoagulants. Smokes 1 PPD for 30 years."
        ),
        "available_tests": [
            "Chest X-Ray", "CBC", "BMP", "Blood Cultures", "Sputum Culture",
            "Procalcitonin", "Lactate", "ABG", "Urinary Legionella Antigen",
            "Urinary Pneumococcal Antigen"
        ],
        "correct_triage": "urgent",
        "relevant_tests": {
            "Chest X-Ray", "CBC", "Blood Cultures",
            "Urinary Pneumococcal Antigen", "Procalcitonin"
        },
        "hints": {
            "Chest X-Ray": "Right lower lobe consolidation. Air bronchograms present. Consistent with lobar pneumonia.",
            "CBC": "WBC 18.4 (elevated), Hgb 12.1, Plt 310. Neutrophilia with left shift.",
            "BMP": "Na 131 (low), K 3.9, Cr 1.2, BUN 22, Glucose 110.",
            "Blood Cultures": "Pending x2. Drawn prior to antibiotics.",
            "Sputum Culture": "Gram-positive diplococci on Gram stain. Culture pending.",
            "Procalcitonin": "Procalcitonin 4.2 ng/mL (ELEVATED). Supports bacterial etiology.",
            "Lactate": "Lactate 1.8 mmol/L — not in septic shock range.",
            "ABG": "pH 7.38, PaO2 62, PaCO2 44, HCO3 22. Type 1 respiratory failure. Low PaO2 confirms need for supplemental O2.",
            "Urinary Legionella Antigen": "Negative.",
            "Urinary Pneumococcal Antigen": "Positive — Streptococcus pneumoniae confirmed.",
        },
        "ground_truth_diagnosis": "Community-Acquired Pneumonia (CAP) — Streptococcus pneumoniae",
        # CRITICAL: Patient has penicillin allergy — amoxicillin/ampicillin are CONTRAINDICATED
        "ground_truth_treatment": (
            "Azithromycin 500mg IV + Levofloxacin 750mg IV (penicillin-sparing regimen). "
            "Supplemental O2 to maintain SpO2 >94%. IV fluids. Admit to hospital. "
            "Avoid beta-lactams due to penicillin anaphylaxis allergy."
        ),
        "contraindicated_drugs": [
            "penicillin", "amoxicillin", "ampicillin", "piperacillin",
            "ceftriaxone", "cefazolin", "beta-lactam"
        ],
        "max_steps": 10,
    },

    "task_treatment_002": {
        "task_id": "task_treatment",
        "patient_id": "PT-006",
        "chief_complaint": "Polyuria, polydipsia, weight loss over 3 weeks. Now confused and breathing fast.",
        "vitals": {
            "heart_rate": 118,
            "blood_pressure_systolic": 98,
            "blood_pressure_diastolic": 62,
            "temperature": 37.2,
            "respiratory_rate": 26,
            "oxygen_saturation": 97.0,
        },
        "history": (
            "19-year-old female. No known past medical history. "
            "No medications. No drug allergies. Family history of type 1 diabetes (mother)."
        ),
        "available_tests": [
            "BMP", "CBC", "Blood Gas (Venous)", "Urinalysis", "Urine Ketones",
            "HbA1c", "C-Peptide", "Blood Cultures", "ECG", "Chest X-Ray"
        ],
        "correct_triage": "emergent",
        "relevant_tests": {"BMP", "Blood Gas (Venous)", "Urine Ketones", "HbA1c"},
        "hints": {
            "BMP": "Na 128, K 5.8 (high), Cr 1.6 (elevated), Glucose 612 (CRITICALLY HIGH), HCO3 8 (low — metabolic acidosis), AG = 24 (elevated anion gap).",
            "CBC": "WBC 14.2, Hgb 14.8, Plt 305 — mild leukocytosis, no obvious infection source.",
            "Blood Gas (Venous)": "pH 7.18, PaCO2 22, HCO3 8. Severe metabolic acidosis with respiratory compensation (Kussmaul breathing).",
            "Urinalysis": "Glucose 4+ (glycosuria). Ketones 4+ (ketonuria). No infection.",
            "Urine Ketones": "Large ketones — consistent with diabetic ketoacidosis.",
            "HbA1c": "HbA1c 13.2% — severely elevated, consistent with uncontrolled/new-onset diabetes.",
            "C-Peptide": "Low C-peptide — consistent with Type 1 Diabetes (no endogenous insulin).",
            "Blood Cultures": "No growth — no sepsis.",
            "ECG": "Sinus tachycardia. Peaked T-waves consistent with hyperkalemia.",
            "Chest X-Ray": "Clear. No infection.",
        },
        "ground_truth_diagnosis": "Diabetic Ketoacidosis (DKA) — new-onset Type 1 Diabetes",
        "ground_truth_treatment": (
            "IV normal saline fluid resuscitation (1L bolus then 250-500mL/hr). "
            "Regular insulin infusion 0.1 units/kg/hr. Potassium replacement when K < 5.5. "
            "Cardiac monitoring for hyperkalemia. Endocrine consult. ICU admission. "
            "Transition to subcutaneous insulin when anion gap closes and patient tolerating PO."
        ),
        "contraindicated_drugs": ["metformin", "sglt2", "sulfonylurea"],
        "max_steps": 10,
    },
}

# Map task IDs to their default cases
TASK_DEFAULT_CASES = {
    "task_triage": "task_triage_001",
    "task_diagnosis": "task_diagnosis_001",
    "task_treatment": "task_treatment_001",
}
