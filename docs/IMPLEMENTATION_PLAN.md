# LabMirror — Implementation Plan

**Source spec:** [LabMirror_Product_Spec.md](../LabMirror_Product_Spec.md) (v1.0)
**Written:** Friday, November 13, 2026
**Hard deadline:** Sunday, November 15, 2026, 8:00 AM Pacific
**Team:** two developers working in parallel — **Dev A (science + API)** and **Dev B (frontend + deploy + presentation)**

**Repository state at planning time:** the repo contains only the product spec. There is no code, no dependency manifest, and nothing to reuse. Local tools: Python 3.13.6, Node 24.18, npm 11.16. No Python packages for this project are installed yet.

---

## 0. How to read this plan

The work is cut into six phases. Inside each phase, Dev A and Dev B have separate task lists that touch **separate directories**, so neither waits on the other. The only shared artifact is the API contract in §3, which is frozen in Phase 0 and changed only by mutual agreement.

Each phase ends with a **gate**: a concrete check both developers run together. Do not start the next phase's work until the gate passes, except where a task is marked "can start early".

| Phase | Name | Budget (each dev) | Wall-clock gate (Pacific) |
|---|---|---|---|
| 0 | Contract freeze and scaffolding (together) | 1 h | Fri evening |
| 1 | Engine core ‖ UI shell, both deployed as skeletons | 4 h | Fri night |
| 2 | API and all P0 tests ‖ progress and results screens | 5 h | Sat ~1 PM |
| 3 | Report, demo fixture, hardening ‖ polish, errors, mobile | 3 h | **Sat 6 PM — P0 feature freeze** |
| 4 | P1 extras (only if the Phase 3 gate passed) | 3 h | Sat 10 PM — code freeze |
| 5 | Presentation and submission (together) | 3 h | Target submit **Sun 2 AM**; 6 h buffer |

If a gate slips by more than 90 minutes, drop Phase 4 entirely and go straight to Phase 5.

---

## 1. Scope lock

### P0 — ships

- CSV upload (≤ 20 MB) and one-click demo dataset, both through the same engine.
- Dataset profiling: counts, class proportions, feature types, missingness, duplicates, SHA-256, identifier and leakage-name heuristics.
- Structured claim builder: target, candidate (Random Forest or Logistic Regression), baseline (the other one), threshold in percentage points, optional reported values and source note, column exclusion.
- Four tests, all real: default 80/20 comparison, five-seed sensitivity, numeric-noise robustness, leakage and validity diagnostics.
- `DummyClassifier(most_frequent)` always run as a sanity row (it costs milliseconds).
- Deterministic verdict with the rule shown next to it.
- Async job with real stage-by-stage status, 120-second kill, bounded queue.
- Results dashboard with two charts, warnings, audit trace, reproducibility panel.
- Markdown and JSON report download, with a deterministic templated narrative.
- Public deployment, README, demo fixture with provenance.

### P1 — only after the Phase 3 gate

In priority order: (1) Skeptical Auditor LLM that orders and justifies the allowlisted tests, (2) Evidence Writer LLM narrative with numeric verification, (3) shareable run link `/audit/{id}`, (4) sample-size sensitivity test, (5) Demo B leakage fixture, (6) natural-language Claim Interpreter, (7) numeric missingness test, (8) ROC-AUC and confusion matrix.

### P2 — not built

PDF ingestion, GitHub import, arbitrary code replication, literature retrieval, multi-agent loops, auth, multiclass or regression, databases, the DGX Spark.

### Deviations from the spec (stated, with reasons)

1. **Noise test uses 20 seeded draws, not one.** A single draw of Gaussian noise is itself a noisy measurement; predicting 20 times is nearly free and lets the verdict use the mean. Min and max are reported alongside.
2. **Model `random_state` is held at 0 across all split seeds.** Variation in the seed test is then attributable to the split alone. This is disclosed in the report as "split-seed sensitivity, not model-initialization sensitivity".
3. **Positive class for F1 is the minority class** (tie broken by sorted label order), shown in the UI. The spec only requires that the convention be stated.
4. **Stage names** differ slightly from the spec's sample timeline so that each one maps to exactly one backend function.
5. **No per-IP rate limiting in P0.** The bounded job queue (1 running, 5 waiting, then HTTP 429) is the abuse control. Add `slowapi` in Phase 4 if there is time.
6. **Temporary storage is ephemeral.** Run links die on redeploy. Acceptable for a hackathon; stated in the README.

### Changes made during the build

- **Demo data lives in `backend/labmirror/demo_data/`,** not a top-level `datasets/` folder, because the Docker build context is `backend/` and the image must contain the demo files.
- **Integer columns are flagged identifier-like only when they are a contiguous run of unique values** (a row counter), not whenever they are > 95% unique. The original rule would have pre-excluded ordinary continuous integer features such as income.
- **The upload and demo endpoints (task A2.1) were built in Phase 1,** so the setup screen runs against the live API and task B1.4 needed no hand-typed fixture.
- **The cross-split duplicate check is informational when the feature space is coarse.** If fewer than 50% of rows have a distinct feature vector (for example, two small categorical columns), repeated vectors are expected and are reported as `info`, not `warning` or `critical`. A unit test found that the original rule marked every all-categorical dataset as critical and therefore inconclusive. This was changed before any demo fixture was generated.
- **Charts are hand-written SVG, not Recharts.** This removes a dependency and gives exact control over axis labelling.
- **`AuditRequest` rejects an unusable feature column rather than dropping it,** so every excluded column is explicit in the report. The UI and the CLI pre-exclude unusable and identifier-like columns.

---

## 2. Architecture

```text
Browser ── Next.js (Vercel, static + client components)
   │  fetch: multipart upload, JSON POST, 1 s polling
   ▼
FastAPI (one Docker container, one uvicorn worker)
   ├─ routes/        thin HTTP layer, Pydantic validation, error envelope
   ├─ jobs.py        queue + watchdog; spawns one child process per audit
   │      └─ child process ── engine.run_audit() ── writes job.json atomically
   ├─ engine/        pure Python, no web imports; also runnable as a CLI
   └─ DATA_DIR/      datasets/{id}/data.csv, summary.json
                     runs/{id}/job.json, report.json, report.md
```

**Decisions**

- **Engine is a pure library.** `backend/labmirror/engine` imports only pandas, NumPy, scikit-learn and the schemas. It is callable from a CLI (`python -m labmirror.cli`) so Dev A can produce real output in Phase 1 before any HTTP code exists, and so the demo fixture script uses exactly the production code path.
- **One child process per audit**, started with the `spawn` context. A parent watchdog thread calls `terminate()` at 120 s and marks the job `timeout`. Threads cannot be killed, so a thread pool would not give a real timeout.
- **Progress is a file.** The child rewrites `job.json` (write to temp, then `os.replace`) after each stage. `GET /api/audits/{id}` just reads it. No Redis, no database, no websockets.
- **Polling at 1 s** from the browser. Jobs take seconds; streaming adds risk for no visible benefit.
- **Single uvicorn worker.** The in-memory queue is only valid with one worker; this is written into the Dockerfile and README.
- **Hosting:** frontend on Vercel; backend as a Docker web service on Render. If Render's cold start or build fails, the same Dockerfile goes to a Hugging Face Docker Space. The frontend pings `/api/health` on page load to wake the backend and shows "waking the compute server" while it waits. Verify current free-tier limits on both hosts during task B1.3 before relying on them.
- **Python 3.13 in Docker**, matching local, with versions pinned by `pip freeze` after the first clean install. Package versions are read at runtime with `importlib.metadata` and written into every report.
- **Config by environment variable:** `DATA_DIR`, `ALLOWED_ORIGINS`, `MAX_UPLOAD_MB=20`, `JOB_TIMEOUT_S=120`, `ANTHROPIC_API_KEY` (optional), `LABMIRROR_LLM_MODEL` (optional); frontend `NEXT_PUBLIC_API_URL`.
- **Retention:** a startup sweep plus a sweep on each upload deletes uploaded datasets and runs older than 24 hours. Bundled demo datasets are never deleted. Raw rows are never logged.

---

## 3. The contract (frozen in Phase 0)

This section is the integration boundary. Dev A implements it in `backend/labmirror/schemas.py`; Dev B mirrors it by hand in `frontend/src/lib/types.ts`. Any change needs both developers to agree and both files to change in the same commit.

### 3.1 Endpoints

| Method | Path | Request | Success |
|---|---|---|---|
| GET | `/api/health` | — | `200 {status, version, llm_enabled}` |
| GET | `/api/demos` | — | `200 DemoDescriptor[]` |
| POST | `/api/datasets` | multipart `file` | `201 DatasetSummary` |
| POST | `/api/datasets/demo/{demo_id}` | — | `201 DatasetSummary` |
| POST | `/api/audits` | `AuditRequest` | `202 AuditJob` |
| GET | `/api/audits/{id}` | — | `200 AuditJob` |
| GET | `/api/audits/{id}/report.md` | — | `200 text/markdown` attachment |
| GET | `/api/audits/{id}/report.json` | — | `200 AuditReport` |

Every error is `{"error": {"code", "message", "field"?}}` with a 4xx or 5xx status. Codes: `no_file`, `file_too_large`, `malformed_csv`, `too_few_rows`, `too_many_rows`, `too_many_columns`, `unknown_dataset`, `unknown_target`, `target_not_binary`, `target_has_missing`, `class_too_small`, `no_usable_features`, `high_cardinality_feature`, `invalid_threshold`, `same_model`, `queue_full`, `unknown_audit`, `timeout`, `internal_error`.

### 3.2 Schemas

All accuracies are **fractions in [0, 1]**. All lifts are **percentage points** and carry the suffix `_pp`. The frontend multiplies fractions by 100 for display and never computes a lift itself.

```text
DemoDescriptor   { id, title, description, suggested_claim: ClaimSpec, provenance_note }

ColumnInfo       { name, kind: "numeric"|"categorical"|"unusable", n_unique, missing_fraction,
                   flags: ("identifier_like"|"leakage_name"|"high_cardinality"|"constant"|"free_text")[] }

DatasetSummary   { dataset_id, sha256, filename, is_demo, n_rows, n_columns,
                   columns: ColumnInfo[], duplicate_row_count,
                   binary_target_candidates: string[],
                   preview: { columns: string[], rows: string[][] }   // first 8 rows, strings, escaped on render
                 }

ClaimSpec        { target, candidate: "random_forest"|"logistic_regression", baseline: same enum,
                   metric: "accuracy", threshold_pp: number (0 < x <= 100),
                   reported_candidate_accuracy?, reported_baseline_accuracy?, source_note? }

AuditRequest     { dataset_id, claim: ClaimSpec, excluded_columns: string[] }

Stage            { id: "validate"|"default_split"|"seed_sensitivity"|"noise_robustness"
                       |"leakage_diagnostics"|"verdict"|"report",
                   label, why, status: "pending"|"running"|"done"|"failed"|"skipped",
                   started_at?, finished_at?, message? }

AuditJob         { audit_id, status: "queued"|"running"|"succeeded"|"failed"|"timeout",
                   created_at, started_at?, finished_at?, stages: Stage[],
                   error?: {code, message}, report?: AuditReport }   // report present, possibly partial, while running

ModelScore       { model: "candidate"|"baseline"|"dummy", estimator, accuracy, balanced_accuracy, f1 }

SplitResult      { seed, n_train, n_test, test_class_counts: {label: n},
                   scores: ModelScore[], lift_pp, candidate_wins: bool, meets_threshold: bool }

SeedSummary      { n_seeds, n_candidate_wins, n_meets_threshold, median_lift_pp, min_lift_pp, max_lift_pp,
                   candidate_accuracy_range: [min, max], baseline_accuracy_range: [min, max] }

NoiseResult      { noise_scale: 0.10, n_draws: 20, rng_seed, perturbed_features: string[], skipped_features: string[],
                   per_model: { model, clean_accuracy, noisy_mean_accuracy, noisy_min, noisy_max, delta_pp }[],
                   clean_lift_pp, noisy_mean_lift_pp }

DiagnosticFinding{ check: "cross_split_duplicates"|"conflicting_label_duplicates"|"identifier_like"
                          |"leakage_name"|"class_imbalance"|"small_test_class",
                   severity: "info"|"warning"|"critical", description, evidence: {…counts, column names}, caveat }

AuditVerdict     { label: "consistent"|"mixed"|"not_reproduced"|"inconclusive",
                   headline, rule_text, triggered_rules: string[], reasons: string[] }

TraceEntry       { step, actor: "engine"|"skeptic"|"writer", decision, rationale, evidence_ref? }

AuditReport      { schema_version: "1.0", audit_id, created_at,
                   dataset: { sha256, filename, n_rows, features_used, excluded_columns,
                              numeric_features, categorical_features, class_counts, positive_class },
                   claim: ClaimSpec, claim_sentence,
                   config: { test_size: 0.2, default_seed: 42, seeds: [11,23,37,51,79],
                             preprocessing: {…}, models: {…hyperparameters}, noise: {…} },
                   environment: { python, numpy, pandas, scikit_learn, labmirror },
                   default_split?: SplitResult, seed_runs?: SplitResult[], seed_summary?: SeedSummary,
                   noise?: NoiseResult, diagnostics?: DiagnosticFinding[], no_issue_statement?,
                   verdict?: AuditVerdict, trace: TraceEntry[],
                   narrative?: { source: "template"|"llm", text },
                   limitations: string[], runtime_seconds? }
```

### 3.3 The handoff artifact

At the end of Phase 1, Dev A commits `contracts/sample_report.json`, **produced by the real engine CLI on a real dataset**. Dev B builds the results screen against this file in a development-only route (`/dev/results`). It is never imported by a production page, and that route is deleted in Phase 3. This keeps Dev B unblocked without putting a fabricated number anywhere in the product.

---

## 4. Repository layout

```text
backend/                          ← Dev A owns everything here
  pyproject.toml, requirements.txt (pinned), Dockerfile
  labmirror/
    schemas.py                    Pydantic models from §3.2
    config.py                     env settings, constants (seeds, limits, thresholds)
    engine/
      profiling.py                load CSV, hash, column typing, flags, DatasetSummary
      validation.py               claim + dataset checks → error codes
      pipelines.py                ColumnTransformer + estimator factories
      splits.py                   stratified split, fit/score one paired comparison
      tests_default.py            default 80/20 comparison
      tests_seeds.py              five-seed sensitivity + summary
      tests_noise.py              Gaussian test-feature noise
      diagnostics.py              duplicates, identifiers, names, imbalance
      verdict.py                  deterministic rules
      narrative.py                templated narrative + limitations text
      report_md.py                AuditReport → Markdown
      registry.py                 allowlisted test IDs → callables, labels, "why" text
      run.py                      run_audit(request, on_stage) orchestrator
      units.py                    fraction ↔ percent ↔ pp helpers
    agents/                       (P1) skeptic.py, writer.py, client.py
    jobs.py                       queue, child process, watchdog, job.json I/O
    api.py                        FastAPI app, routes, error handlers, CORS
    cli.py                        python -m labmirror.cli audit data.csv --target … --threshold …
  tests/                          pytest; see §8
datasets/
  demo_seed_sensitive.csv         committed fixture
  demo_seed_sensitive.provenance.json
  demos.json                      DemoDescriptor list
scripts/
  make_demo_fixture.py            generates + verifies the fixture through the engine
  smoke_test.py                   hits a deployed URL end to end
contracts/
  sample_report.json              real engine output; dev handoff only
frontend/                         ← Dev B owns everything here
  src/app/page.tsx                setup screen (hero, demo, upload, claim builder)
  src/app/audit/[id]/page.tsx     progress → results (same URL, so run links work)
  src/lib/types.ts                mirror of §3.2
  src/lib/api.ts                  typed fetch wrappers, error envelope handling, polling hook
  src/lib/format.ts               pct(), pp() display helpers
  src/components/                 UploadDropzone, DatasetHealth, DataPreview, ClaimBuilder,
                                  AuditPlan, StageTimeline, VerdictHeader, DefaultSplitCard,
                                  SeedChart, NoiseChart, DiagnosticsList, AuditTrace,
                                  ReproPanel, ErrorBanner, ServerWakeNotice
docs/
  IMPLEMENTATION_PLAN.md          this file
  DEMO_SCRIPT.md, PITCH.md        Phase 5
README.md                         Phase 5 (stub in Phase 0)
```

---

## 5. Scientific design

### 5.1 Supported data

- CSV, UTF-8 (fallback latin-1), 100–20,000 rows, 2–50 feature columns after exclusions, ≤ 20 MB.
- Target: exactly two distinct non-null values and **no missing target values**; otherwise reject. At least 20 rows per class.
- Column typing: numeric dtype → `numeric`. Anything else with ≤ 20 unique values → `categorical`. Anything else → `unusable` with flag `high_cardinality` or `free_text` (mean string length > 50). Constant columns → `unusable`.
- Unusable and `identifier_like` columns are pre-ticked for exclusion in the UI. If the user un-excludes an unusable column, `POST /api/audits` rejects with `high_cardinality_feature`.

### 5.2 Pipelines and models

```text
numeric      SimpleImputer(strategy="median") → StandardScaler()
categorical  SimpleImputer(strategy="most_frequent") → OneHotEncoder(handle_unknown="ignore")
ColumnTransformer([numeric, categorical]) → estimator       # one Pipeline per model, fitted on train only

LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000, random_state=0)
RandomForestClassifier(n_estimators=100, max_depth=None, random_state=0, n_jobs=1)
DummyClassifier(strategy="most_frequent")
```

The same preprocessing is used for both models so the comparison differs only in the estimator. No tuning anywhere.

### 5.3 Splits and metrics

- `train_test_split(test_size=0.2, stratify=y, random_state=seed)`. Default seed 42. Sensitivity seeds `[11, 23, 37, 51, 79]`.
- One index split per seed, shared by every model in that comparison.
- `accuracy`, `balanced_accuracy`, `f1` (positive = minority class).
- `lift_pp = (acc_candidate − acc_baseline) × 100`, computed unrounded.
- `meets_threshold = lift_pp ≥ threshold_pp − 1e-9`. `candidate_wins = lift_pp > 0`.

### 5.4 Noise test

Using the default-split fitted pipelines and default test rows: for each numeric feature *j*, `σ_j` is the training-set standard deviation of the raw column (NaN ignored). Skip the feature if `σ_j` is zero or non-finite, and list it under `skipped_features`. For draw *d* in 0…19, `rng = default_rng(1000 + d)`, add `N(0, (0.10·σ_j)²)` to the raw test values (NaN stays NaN), predict with both models. Report clean accuracy, mean, min and max noisy accuracy, and `delta_pp`. Categorical features are untouched. If there are no numeric features the stage is `skipped` with a message, and the verdict ignores it.

### 5.5 Diagnostics

| Check | Evidence | Severity |
|---|---|---|
| Identical feature vectors in both train and test (default split) | count and share of test rows | `critical` if ≥ 10% of test rows, `warning` if any, else none |
| Identical feature vectors with different labels (whole dataset) | count of conflicting groups | `warning` |
| Identifier-like column still in features | names; rule: > 95% unique non-numeric or integer, or name matches `id`, `uuid`, `record_id`, `index`, `key` | `warning` |
| Leakage-suggestive name still in features | names; rule: name contains the target name, or `label`, `outcome`, `target`, `result`, `diagnosis`, `status`, `post_` | `warning` |
| Class imbalance | minority share | `warning` if < 20%, `info` if < 35% |
| Small test class | minority count in default test split | `warning` if < 10 |

Every finding carries the caveat that heuristics cannot prove leakage or its absence. If nothing fires, `no_issue_statement` reads: "No issues were found in the checks performed. These checks cannot establish the absence of leakage."

### 5.6 Verdict rules (declared now, before any code or fixture exists)

Evaluated in order; the first match wins. Let *k* be the number of the five seeds where `meets_threshold` is true.

1. **Inconclusive** — any of the default, seed or diagnostics stages failed, or a `critical` diagnostic is present.
2. **Not reproduced in tested settings** — *k* = 0.
3. **Mixed / sensitive to conditions** — *k* is 1, 2 or 3.
4. **Mixed / sensitive to conditions** — *k* ≥ 4, and the noise test ran, and `noisy_mean_lift_pp < threshold_pp`, and `clean_lift_pp − noisy_mean_lift_pp ≥ 2.0`. (This is the noise materiality rule.)
5. **Consistent with claim in tested settings** — *k* ≥ 4 otherwise.

`rule_text` prints these five rules verbatim; `triggered_rules` names the one that fired. Constants live in `config.py` and are covered by a unit test so they cannot drift quietly.

### 5.7 Fixed disclosure text

Placed in the report, the results footer and the README:

> LabMirror independently re-evaluates a claim on the data and protocol shown here. It is not a reproduction of any published study unless that study's exact data, splits and code were used. Verdict labels are product labels derived from the stated rule; they are not statistical significance results. Counts such as "2 of 5 splits" describe the tested splits and are not probabilities. Passing these tests does not guarantee that a result generalizes.

---

## 6. Demo fixture

**Intended failure mode:** a default split that meets the claimed threshold while several alternate splits do not.

**Method (`scripts/make_demo_fixture.py`):**

1. Generate candidates with `sklearn.datasets.make_classification` — roughly 400 rows, 8 numeric features, 4 informative, 2 clusters per class, `flip_y≈0.05` — for generator seeds 0…199. Name the columns plausibly (`sensor_1` …) and add nothing that is not generated.
2. Run each candidate through `engine.run_audit` with the claim "Random Forest beats Logistic Regression by ≥ 5.0 pp".
3. Keep the first generator seed where the default split meets the threshold and *k* is between 1 and 3.
4. Write the CSV and a provenance file recording generator parameters, the generator seed, how many candidates were examined, the selection criterion, and the SHA-256.

**Honesty requirement:** this dataset is *selected* to illustrate seed sensitivity. The provenance note says so, the demo card in the UI says so ("chosen because it shows split sensitivity"), and the pitch says so. Every number on screen still comes from a live run.

**Fallbacks, in order:** widen the search (row count 200–800, threshold 3–8 pp); then use scikit-learn's bundled Breast Cancer Wisconsin dataset with whatever verdict it truly produces and tell that story instead. Never edit a score.

**Second example (P1, cheap):** Breast Cancer Wisconsin as a contrasting case, labelled with its real verdict after it is run.

---

## 7. Task breakdown by phase

Effort is in hours. "AT" is the acceptance test that marks the task done.

### Phase 0 — Contract freeze and scaffolding (together, 1 h)

| ID | Task | AT |
|---|---|---|
| 0.1 | Read §3 together; amend and freeze it | Both say "frozen" |
| 0.2 | Create the folder layout, `.gitignore`, README stub, branch rules (§9) | `git pull` works for both |
| 0.3 | Dev A: `backend` venv, install FastAPI, uvicorn, pandas, NumPy, scikit-learn, pytest, python-multipart; `pip freeze` | `pytest` runs zero tests cleanly |
| 0.4 | Dev B: `create-next-app` with TypeScript and Tailwind; add Recharts | `npm run dev` serves a page |
| 0.5 | Dev A writes `schemas.py`; Dev B writes `types.ts`, both from §3.2 | Side-by-side read-through matches |

**Gate 0:** contract frozen, both toolchains run.

### Phase 1 — Engine core ‖ UI shell (4 h each)

**Dev A**

| ID | Task | h | Files | AT |
|---|---|---|---|---|
| A1.1 | Profiling: load, hash, type columns, flags, preview | 1.0 | `profiling.py` | Unit tests on three small CSVs give expected kinds and flags |
| A1.2 | Pipelines and paired split scoring | 1.0 | `pipelines.py`, `splits.py`, `units.py` | Test proves the imputer and scaler statistics equal train-only statistics; both models see identical indices |
| A1.3 | Default test and seed test with summary | 0.75 | `tests_default.py`, `tests_seeds.py` | Two runs give byte-identical JSON |
| A1.4 | Orchestrator with stage callback, and CLI | 0.75 | `run.py`, `registry.py`, `cli.py` | CLI prints a partial `AuditReport` for a CSV |
| A1.5 | Commit `contracts/sample_report.json` from the CLI | 0.25 | `contracts/` | File validates against `AuditReport` |
| A1.6 | Minimal FastAPI app with `/api/health` and a Dockerfile | 0.25 | `api.py`, `Dockerfile` | `docker build` and `curl /api/health` succeed locally |

**Dev B**

| ID | Task | h | Files | AT |
|---|---|---|---|---|
| B1.1 | Layout, hero, design tokens, `format.ts` | 0.75 | `page.tsx`, `format.ts` | Page renders on desktop and at 375 px |
| B1.2 | `api.ts`: typed wrappers, error-envelope parsing, polling hook | 0.75 | `api.ts` | Unit check against a hand-made error response |
| B1.3 | **Deploy skeletons now:** frontend to Vercel, Dev A's health-only backend to Render; set CORS and `NEXT_PUBLIC_API_URL` | 1.0 | — | Public page shows "backend: ok" fetched from the public backend |
| B1.4 | Upload dropzone, dataset health card, data preview table | 1.0 | components | Renders from a hand-typed `DatasetSummary` in a dev route |
| B1.5 | Claim builder with live claim sentence and client-side validation | 0.5 | `ClaimBuilder.tsx` | Sentence updates; invalid threshold disables Run |

**Gate 1:** `sample_report.json` is committed and real; a public frontend talks to a public backend health endpoint. Deployment risk is now retired.

### Phase 2 — API and remaining tests ‖ progress and results (5 h each)

**Dev A**

| ID | Task | h | Files | AT |
|---|---|---|---|---|
| A2.1 | `POST /api/datasets`, demo loader, `GET /api/demos`, size limits, error envelope | 1.0 | `api.py`, `validation.py` | Each dataset error code is produced by a test |
| A2.2 | Job runner: queue, spawned child, atomic `job.json`, watchdog timeout | 1.25 | `jobs.py` | A test job that sleeps is killed and reports `timeout`; sixth queued job gets 429 |
| A2.3 | `POST /api/audits`, `GET /api/audits/{id}` with partial reports | 0.5 | `api.py` | Polling shows stages moving `pending → running → done` |
| A2.4 | Noise test | 0.75 | `tests_noise.py` | Deterministic; constant feature is skipped; no-numeric dataset skips the stage |
| A2.5 | Diagnostics | 0.75 | `diagnostics.py` | Planted cross-split duplicates are counted exactly |
| A2.6 | Verdict engine | 0.5 | `verdict.py` | Table-driven test covers all five rules |
| A2.7 | Redeploy backend | 0.25 | — | `scripts/smoke_test.py` passes against the public URL |

**Dev B** (builds against `sample_report.json` until A2.3 lands, then switches to the live API)

| ID | Task | h | Files | AT |
|---|---|---|---|---|
| B2.1 | Wire setup screen to the live upload and demo endpoints | 0.75 | `page.tsx` | Demo click and a real upload both show a health summary |
| B2.2 | Audit plan and stage timeline with elapsed time and real errors | 1.0 | `AuditPlan`, `StageTimeline` | Timeline reflects polled stage statuses; no percentages |
| B2.3 | Verdict header, claim statement, default-split card, N/5 count | 1.0 | components | Matches the JSON values exactly |
| B2.4 | Seed chart: paired accuracy per seed, lift per seed, threshold line | 1.0 | `SeedChart.tsx` | Axes labelled "accuracy (%)" and "lift (pp)"; y-axis from 0 or visibly marked as truncated |
| B2.5 | Noise chart: clean vs noisy per model, with min–max whiskers | 0.5 | `NoiseChart.tsx` | Tooltip shows the noise specification |
| B2.6 | Diagnostics list, audit trace, reproducibility panel | 0.75 | components | Hash, seeds, hyperparameters and versions all visible |

**Gate 2 (integration checkpoint):** on the deployed site, click the demo, run, and reach a results dashboard populated only from the live API. Both developers click through it together and file every mismatch as a task for Phase 3.

### Phase 3 — Report, fixture, hardening ‖ polish (3 h each)

**Dev A**

| ID | Task | h | AT |
|---|---|---|---|
| A3.1 | Templated narrative, limitations, Markdown report, download endpoints | 1.0 | Report contains hash, seeds, hyperparameters, versions, rule text, disclosure; a test checks every number in the Markdown appears in the JSON |
| A3.2 | Demo fixture script; commit CSV, provenance, `demos.json` | 1.0 | Re-running the script reproduces the same file hash |
| A3.3 | Remaining error paths, retention sweep, no raw-row logging | 0.5 | All §3.1 codes covered by tests |
| A3.4 | Performance check at 20,000 × 50 on the deployed host | 0.5 | Finishes under 120 s, or lower the row cap and update the UI copy |

**Dev B**

| ID | Task | h | AT |
|---|---|---|---|
| B3.1 | Download buttons, "Run new audit", re-run without re-upload | 0.5 | Downloaded Markdown opens and matches the screen |
| B3.2 | Every error code mapped to an actionable message; server-wake notice | 0.75 | Manually trigger six different errors |
| B3.3 | Mobile pass, chart clipping, accessible palette, "reported by user" vs "measured by LabMirror" badges | 1.0 | 375 px and 1440 px screenshots reviewed |
| B3.4 | The reveal: default-split card first, then the five-seed chart animates in | 0.5 | Reads clearly in a 10-second clip |
| B3.5 | Delete `/dev/*` routes; scope notice and privacy notice near upload | 0.25 | `grep` finds no import of `sample_report.json` |

**Gate 3 — P0 feature freeze (Sat 6 PM):** the full §13 checklist in §12 of this plan passes on the public URL, from a browser that has never visited the site. Tag `v0-p0`. Record a backup screen capture of a real run immediately.

### Phase 4 — P1 extras (3 h each, optional)

Rule: each item goes on its own branch and merges only if it is finished and Gate 3 still passes afterward. Anything unfinished at Sat 10 PM is abandoned.

| Dev A | Dev B |
|---|---|
| A4.1 Skeptical Auditor: after the default split, send claim, column names and types, and aggregate results to the Claude API; receive an ordered subset of the registry IDs with a one-sentence rationale each; validate with Pydantic; unknown IDs are dropped; required P0 tests always run regardless. Falls back to the fixed order on any failure. (1.5 h) | B4.1 Audit trace panel shows skeptic decisions as claim → result → proposed test → finding, labelled as AI-suggested (1 h) |
| A4.2 Evidence Writer: LLM narrative from the typed results; a verifier extracts every number from the text and rejects the narrative if any is absent from the report, falling back to the template (1 h) | B4.2 Shareable `/audit/{id}` link with copy button and a "saved past run" label (0.5 h) |
| A4.3 Sample-size sensitivity test (0.5 h) | B4.3 Chart for A4.3; second demo card (1 h) |

LLM boundaries: no raw rows are ever sent; column names and user notes are passed as delimited data, not instructions; the model has no tools; the key stays server-side; `llm_enabled=false` hides the AI panels and changes nothing else.

### Phase 5 — Presentation and submission (together, 3 h)

| ID | Owner | Task |
|---|---|---|
| 5.1 | A | README: what it is, what it is not, architecture diagram, scientific protocol, local run, limitations, acknowledgments (scikit-learn, dataset sources) |
| 5.2 | B | `docs/DEMO_SCRIPT.md` and a rehearsed click path |
| 5.3 | Both | Record the five-minute video (structure in §11) |
| 5.4 | B | Devpost entry: description, URL, video link, screenshots, track |
| 5.5 | A | Final smoke test from a clean browser and from a phone; export one real report into `docs/` as a labelled past result |

---

## 8. Testing matrix

| Layer | What | Owner |
|---|---|---|
| Unit | Unit conversions; column typing; pipeline fitted on train only; identical rows per paired comparison; noise determinism and skip rule; duplicate counts on planted data; all five verdict rules; threshold boundary at exactly the threshold | A |
| Reproducibility | Same request twice → identical `report.json` apart from timestamps, ID and runtime | A |
| API integration | FastAPI `TestClient`: upload → audit → poll → report; every error code; timeout; queue full | A |
| Datasets | Demo fixture; Breast Cancer; numeric-only; categorical-only; mixed with missing values; 3-class target; continuous target; missing target labels; 19-row minority; a column with 500 categories; a 21 MB file; empty file; a CSV with `=CMD()` cells and `<script>` strings | A builds, B checks rendering |
| Frontend | `format.ts` helpers; manual check that every displayed number equals the JSON; error rendering; 375 px layout | B |
| Performance | 5,000 × 20 under 60 s and 20,000 × 50 under 120 s on the deployed host | A |
| Live smoke | `scripts/smoke_test.py <url>` runs the demo end to end and asserts a verdict and a non-empty report | Both, before every gate |

Explicit grep check before Gate 3: no numeric literal resembling a score exists in `frontend/src` or in `report_md.py`.

---

## 9. Parallel-work rules

- **Ownership by directory.** Dev A: `backend/`, `scripts/`, `datasets/`, `contracts/`. Dev B: `frontend/`, `docs/DEMO_SCRIPT.md`, `docs/PITCH.md`, hosting dashboards. Neither edits the other's directory; ask instead.
- **Contract changes** touch `schemas.py` and `types.ts` in one commit, announced before pushing.
- **Branches:** short-lived `a/<task>` and `b/<task>`, rebased and merged to `main` at least every two hours. `main` must always deploy.
- **Single integration owner: Dev B.** Dev B owns the two hosting dashboards, runs the smoke test after every merge that changes the API, and is the only one who tags gates. Dev A owns scientific correctness and has the final say on any wording about results.
- **If one developer is blocked,** the other does not wait: Dev B continues against `sample_report.json`; Dev A continues with CLI and tests.
- **With a third or fourth person:** one takes Phase 4's LLM work from the start (it only needs the contract and `sample_report.json`); one takes the fixture, README, pitch and video.

---

## 10. Critical path and build order

The smallest thing that proves the product: **CLI audit → API job → results screen → deployed → report**.

1. Contract frozen (Phase 0).
2. Engine CLI produces a real default and seed comparison (A1.1–A1.5).
3. Skeleton frontend and backend are public (B1.3).
4. Upload and audit endpoints with the job runner (A2.1–A2.3).
5. Results screen reads the live API (B2.1–B2.4).
6. Noise, diagnostics, verdict (A2.4–A2.6) and their panels (B2.5–B2.6).
7. Report export and demo fixture (A3.1–A3.2).
8. Hardening and polish to Gate 3.
9. Backup recording.
10. P1 extras, strictly optional.
11. README, video, Devpost.

Science comes before agents; deployment comes before polish.

---

## 11. Presentation deliverables

**Five-minute pitch**

| Time | Content |
|---|---|
| 0:00–0:30 | The problem: one impressive split is not evidence |
| 0:30–1:00 | What LabMirror does and, in one sentence, what it does not do |
| 1:00–3:15 | Live demo: pick example → read the claim → run → default split looks convincing → five-seed chart → noise → warnings → verdict with its rule |
| 3:15–3:45 | Export the report; show hash, seeds, versions |
| 3:45–4:20 | How it works: the model plans and explains, Python measures; the allowlisted registry |
| 4:20–4:45 | Limitations stated plainly, including that the demo dataset was selected to show the effect |
| 4:45–5:00 | Roadmap and close |

**Devpost checklist:** public URL works logged out; video link is public; description distinguishes re-evaluation from reproduction; repo link; screenshots of the setup, progress and results screens; track set to New Frontiers; team members added; acknowledgments listed.

---

## 12. Risk register

| Risk | Likelihood | Fallback |
|---|---|---|
| Backend host cold start or sleep during judging | High on free tiers | Health ping on page load with a visible wake notice; hit the URL shortly before judging; move the same Dockerfile to the second host; backup recording |
| No fixture shows the intended effect | Medium | Widen the search; then use a public dataset and present its real verdict |
| Job exceeds time on host CPU | Low–medium | Lower the row cap to 10,000 and say so in the UI; forest size is the last resort and must be changed before the fixture is generated |
| Contract drift between the two developers | Medium | One-commit rule; `sample_report.json` validated in CI-style test; smoke test at each gate |
| Spawned child process misbehaves on the host | Low | Switch to a single worker thread with a cooperative deadline checked between stages |
| LLM unavailable, slow or wrong | Medium | Template narrative and fixed test order are the default path; LLM is additive only |
| Phase 2 overruns | Medium | Drop Phase 4; cut B3.4 and the mobile pass before cutting any test or disclosure |
| Verdict rules tempt retuning after seeing the fixture | Medium | Rules are fixed in §5.6 and in a unit test before the fixture script exists; changing them requires both developers and a note in the README |
| Vercel build or env misconfiguration late | Low | Deployed in Phase 1; every merge redeploys |

---

## 13. Definition of done

Each item needs the stated evidence before Gate 3 is tagged.

**Functional**

- [ ] Site opens without sign-in — incognito screenshot.
- [ ] One-click demo with a structured claim — screen recording.
- [ ] Upload a compatible CSV, choose target and features — recording with a non-demo file.
- [ ] Invalid inputs fail with actionable messages — six error screenshots.
- [ ] Two real classifiers on identical splits in leak-safe pipelines — passing unit tests.
- [ ] Default and five seeded comparisons are real and repeatable — reproducibility test.
- [ ] Noise test runs on default test data and is documented — report excerpt.
- [ ] Diagnostics return evidence or the exact no-issue statement — tests and screenshot.
- [ ] Verdict follows the documented rule — table-driven test; rule visible in UI.
- [ ] Charts, JSON and Markdown agree — manual three-way comparison on the demo run.
- [ ] Re-run gives equivalent results — two downloaded reports diffed.
- [ ] Markdown and JSON reports download and include limitations.
- [ ] Public URL, README, demo data and a rehearsed walkthrough exist.

**Correctness**

- [ ] No preprocessing fitted on test data — unit test.
- [ ] Same rows for candidate and baseline — unit test.
- [ ] No hard-coded results — grep check.
- [ ] Unit conversions tested.
- [ ] Invalid threshold and empty target rejected by the backend — API tests.
- [ ] Duplicate detector reports the true count — unit test.
- [ ] Hash, seeds and model parameters in the export — report test.
- [ ] LLM failure leaves scores untouched — test with the key unset and with a forced exception (if Phase 4 ships).
- [ ] The words "significant" and "p-value" do not appear in generated output except in the disclosure — grep check.

**Nonfunctional**

- [ ] Demo run under 60 s on the deployed host — timed.
- [ ] 120 s limit returns a clear error — test.
- [ ] Usable on desktop and mobile — screenshots.
- [ ] Walkthrough understood by someone outside the team — one dry run with a friend.
- [ ] Unauthenticated judge can finish the primary flow — incognito run from a different network.
