# LabMirror — Product Specification and Implementation-Planning Brief

**Version:** 1.0  
**Date:** November 13, 2026  
**Target event:** [NorCal Hacks 27](https://norcal-hacks-27.devpost.com/) — New Frontiers track  
**Event deadline:** November 15, 2026, 8:00 AM Pacific  
**Document status:** Product requirements, **not** an implementation plan

> **Instructions for Claude Code:** Read this entire specification before proposing an architecture or writing code. Your immediate task is to convert it into a concrete, prioritized **implementation plan**, not to implement the application yet. Preserve the scientific-integrity constraints and P0 acceptance criteria. If the repository already contains code, inspect it and build around what exists without assuming it is correct. See §15 for the exact planning deliverables.

---

## 1. Executive summary

**Product name:** LabMirror  
**Tagline:** *Don't just trust the research. Test it.*  
**One-sentence pitch:** LabMirror is an AI-assisted scientific stress-testing platform that takes a falsifiable machine-learning claim, independently evaluates it against a supplied dataset, deliberately probes its weaknesses, and produces a transparent, reproducible audit report.

A claim such as “Random Forest outperforms Logistic Regression by at least 5 percentage points of accuracy” may be supported on one train/test split but fail across other random splits, under small perturbations, or after removal of data leakage. LabMirror turns these questions into executable tests rather than merely summarizing a paper or generating an opinion.

**Core promise:** A user can go from a structured ML claim and a CSV dataset to a trustworthy, inspectable record of *what was tested, how it was tested, what happened, and what remains uncertain*.

**Central differentiation:** An **adversarial scientific auditor** searches for conditions under which a claimed advantage weakens or disappears. A conventional ML dashboard shows scores; LabMirror evaluates the *stability of a scientific conclusion*.

### Important scientific distinction

The hackathon MVP **independently re-evaluates/reconstructs** an experiment using user-provided data and an explicitly declared protocol. It is **not** a literal reproduction of an arbitrary published study unless the original study's exact data, preprocessing, split, methods, and code are available. The interface, documentation, and generated reports must never conflate these. The longer-term vision includes genuine paper/code reproduction.

### Target users

1. Students and teachers checking claims in introductory ML experiments.
2. Researchers who want a quick first-pass robustness and validity audit.
3. Reviewers and technical teams comparing reported ML improvements with reproducible evidence.

### Primary hackathon objective

Show a compelling **end-to-end interactive demo** in which a real experiment claim is tested, a skeptical agent proposes meaningful stress tests, Python executes them, and a dashboard explains why the original conclusion is supported, fragile, or unsupported under the tested conditions.

---

## 2. Competition constraints and product priorities

The hackathon has four published judging criteria: **novelty, impact, presentation, and implementation**. Submissions require a working project URL (a hosted interactive app is strongly preferred), a project description, and a link to a **five-minute pitch video**. Teams can have up to four participants. Source: [official event page](https://norcal-hacks-27.devpost.com/).

The remaining implementation time is very short. Therefore:

- **P0 (must ship):** CSV input + structured claim; real controlled Python execution; original and baseline model comparison; multiple random-seed re-evaluations; at least one perturbation/stress test; deterministic audit verdict; readable evidence dashboard; working deployment; demo dataset; basic downloadable report.
- **P1 (ship only after P0 works):** LLM claim interpretation and skeptical-test proposals; additional stress test(s); report narrative grounded in numeric results; shareable run links; polished motion/visuals.
- **P2 (post-hackathon):** PDF paper ingestion; GitHub repository import; arbitrary model/code replication; scientific literature retrieval; multi-agent coding loops; broad scientific domains; persistent collaborative projects.

**Do not** trade away correctness or a complete demo to create a large agent framework, authentication system, vector database, or distributed compute platform.

### Hard requirements for judging/demo readiness

- At least **one public interactive URL** works without special credentials.
- A live run completes without relying on mocked result values.
- A five-minute demo can explain the original claim, tests, findings, limitations, and impact.
- The full reproducibility metadata and algorithm choices are visible to judges.
- Documentation clearly distinguishes original/hypothetical claims from empirical results.
- Everything advertised as implemented is actually implemented; no fabricated metrics or simulated “AI ran an experiment” animation.

---

## 3. Problem, hypothesis, and outcome

### Problem

Research papers and ML demos often report isolated performance improvements. Their conclusions may be sensitive to dataset splits, random seeds, choice of baselines, noisy inputs, training sample sizes, or accidental target leakage. Manual investigation is tedious, requiring ML literacy and reproducible engineering practices.

### Product hypothesis

An interface that translates a claim into a structured audit and automates a small, scientifically defensible collection of adversarial experiments can make reliability issues legible in minutes rather than requiring manual experimentation.

### Desired user outcome

After using LabMirror, the user should know:

1. The **precise claim** that was evaluated and any assumptions needed to operationalize it.
2. The **dataset and protocol** that were used.
3. Whether the claimed model advantage persists across multiple controlled conditions.
4. Which perturbations most strongly weaken the claim.
5. What leakage/validity warnings were detected (and what was *not* checked).
6. The uncertainty and limitations of the audit.
7. How to rerun or share the same experiments.

### Non-goals for MVP

- No general-purpose claim fact-checker.
- No arbitrary PDF-to-code replication pipeline.
- No arbitrary Python uploaded by users, shell access, or unconstrained agent-generated code execution.
- No scientific claim of universal validity or proof that a paper is fraudulent.
- No formal hypothesis-testing significance assertions unless the statistical design actually justifies them.
- No multi-tenant authentication, payment, or team workspace.

---

## 4. Core experience: required end-to-end journey

### Step A — Select a demo or upload a dataset

The landing page offers two clear paths:

- **Try an example:** A prepared dataset and claim that reliably demonstrate at least one meaningful, real failure mode (e.g., seed sensitivity or train/test duplicates). All values must be generated by the same execution engine used for uploads.
- **Audit your own claim:** Upload a tabular CSV and configure the comparison.

Show the supported scope near the upload: **binary classification, CSV tabular data, scikit-learn models**.

### Step B — State a falsifiable claim

The user selects:

- Target column.
- Candidate model: **Random Forest classifier** or **Logistic Regression**.
- Baseline model: the other supported model; optionally add **DummyClassifier** (most-frequent) as an additional sanity baseline.
- Primary metric: **accuracy** for P0; balanced accuracy and F1 are displayed as secondary metrics. Binary ROC-AUC is P1.
- Claimed improvement threshold, in **percentage points** (e.g. “at least +5.0 pp”).
- Optional originally reported accuracy values and source/citation/notes (context only, not verified by the system).

A visible confirmation reads, for example:

> “Audit whether Random Forest exceeds Logistic Regression by **at least 5.0 percentage points** of test-set accuracy on this dataset.”

No free-form model or target claims in P0. The LLM may help translate natural language into a structured claim in P1, but the user must review and confirm the parsed specification before running.

### Step C — Inspect an automatically generated audit plan

The plan shows:

1. Dataset validation and summary.
2. A fixed initial stratified holdout comparison.
3. Five repeat comparisons over different split seeds.
4. A noise robustness test (same holdout, only numeric test features perturbed).
5. A basic leakage/suspicious-feature diagnostic.
6. Optional sample-size stress test (P1).

Display **why** each test matters. A skeptical LLM agent may suggest from an *allowlisted* set of tests; it cannot invent unsupported executable tools or modify the evaluation code.

### Step D — Run and observe progress

Provide a run button and a real status timeline, for example:

`Validating data -> Creating splits -> Training baselines -> Repeating experiments -> Stress-testing -> Auditing evidence -> Generating report`

Each status is backed by actual backend state. Show useful errors; allow re-running on the same uploaded dataset/configuration without a second upload, where practical.

### Step E — See the finding with evidence

The final dashboard prominently answers:

- **Does the evidence support the thresholded claim under tested settings?**
- **How often did the candidate meet the claimed advantage?** (e.g. 2/5 split seeds).
- **What did the original/default split show?**
- **How does performance change under the adversarial tests?**
- **What caveats prevent stronger conclusions?**

The UI must expose numeric data, not merely an AI-written verdict.

### Step F — Export and reproduce

Download a Markdown (or JSON + Markdown) audit report with a full experiment configuration and numeric results. Re-running with the same dataset hash, split seeds, model settings, and library versions should reproduce the same outputs within deterministic/scientific limitations.

---

## 5. Input contract, validation, and supported scope

### Accepted dataset

- CSV only for P0; UTF-8 preferred.
- Maximum file size: **20 MB** (configurable).
- Suggested resource limits: **100–20,000 rows**, **2–50 feature columns**; the planning agent may tighten these limits to guarantee predictable runtime.
- Exactly **two non-null target classes** after validation; reject missing target labels in P0 (do not silently drop them).
- Numerical and low-cardinality categorical input features supported.
- Reject columns with unmanageable categories, enormous free-text fields, invalid CSV structure, or ambiguous target formats with precise error messages.
- At least **20 examples per target class**; warn about class imbalance and small samples.
- Let users explicitly exclude IDs, post-outcome fields, or suspicious features from model training.
- Treat missing *feature* values via a train-fitted imputer in a pipeline.

### Dataset inspection

Before the run, show:

- Row/column counts and target class proportions.
- Numeric/categorical feature detection.
- Missingness summary.
- Duplicate-row count.
- Suspected identifiers and potential target-leakage columns (heuristic warnings only).
- Dataset SHA-256 and displayed/selected feature list.

Never transmit raw uploaded rows to an external LLM provider by default. If an LLM is enabled, send only the confirmed claim, column names/types, safe summaries, and aggregated experiment results unless the user explicitly opts into sending samples.

### Error states

At minimum handle: no file, oversized file, malformed CSV, nonexistent target, continuous/multiclass target, too few minority-class observations, no usable features, invalid improvement threshold, unsupported categorical cardinality, timeout, backend exception, LLM failure, and canceled/interrupted runs.

---

## 6. Scientifically defensible experiment engine

**Principle:** The **LLM plans and explains; deterministic Python code evaluates**. Never ask the LLM to calculate reported metrics from memory or generate the experiment outcomes.

### 6.1 Evaluation setup

- Use **scikit-learn Pipelines** to prevent preprocessing leakage.
- Build numeric preprocessing from training data only: median imputation and scaling where appropriate.
- Build categorical preprocessing from training data only: most-frequent imputation + one-hot encoding with unknown-category support.
- Compare models on **identical train/test records** for each seed.
- Initial/default comparison: stratified **80/20** split, `random_state=42`.
- Seed sensitivity: stratified **80/20** splits with five fixed, distinct seeds (for example `[11, 23, 37, 51, 79]`).
- All randomness explicitly seeded; model hyperparameters fixed, documented, and identical between repeated trials.
- No hyperparameter tuning on the test set. Do not use the test set to select a winner and then present that same result as an unbiased confirmation.
- Treat repeated-split results as descriptive **robustness evidence**, not independent observations that justify naive p-values.

### 6.2 Required models and metrics

- `LogisticRegression` (suitable configured solver, appropriate `max_iter`, documented scaling).
- `RandomForestClassifier` (small bounded number of trees, fixed seed and single-job/limited parallelism as needed).
- Optional but valuable: `DummyClassifier(strategy="most_frequent")`.
- Primary metric: **accuracy**, represented consistently as fractions internally and percentages in UI.
- Secondary: balanced accuracy, F1 (state positive-class convention), train/test sample counts, per-class distribution; confusion matrix optional P1.
- All lifts in **percentage points**, never ambiguous “percent improvement.”

### 6.3 Required test 1 — Reconstructed default comparison

Train the candidate and baseline on the same 80/20 split (`seed=42`). Return their actual held-out metrics, the absolute difference (candidate minus baseline), and a clear comparison with any user-entered originally reported result.

If the experiment details are different from an external paper, explicitly say the results are **not a direct reproduction of the paper**.

### 6.4 Required test 2 — Random-seed sensitivity

Repeat the complete training and evaluation pipeline on the five fixed split seeds. For each run record candidate and baseline accuracies, difference in percentage points, and whether the claim's threshold was met.

Derive:

- Number of seeds where candidate beats baseline.
- Number of seeds where candidate meets the claimed minimum advantage.
- Median and min/max candidate-minus-baseline difference.
- Spread/range of candidate and baseline accuracies.

Display a paired comparison chart and explicit statement such as “The stated +5 pp threshold was met on 2 of 5 evaluated splits.” Do not conflate that count with a probability of truth.

### 6.5 Required test 3 — Robustness to test-feature noise

Using the **same default trained models** and the same default held-out test records, perturb **numeric feature values only** by seeded Gaussian noise with scale **10% of the training-set standard deviation per feature** (skip constant/invalid-variance features; document the rule). Run predictions on perturbed data and report accuracy changes for each model. Categorical features remain unchanged.

This tests sensitivity to a specific noise model; it is not automatically a realistic physical perturbation. Include the perturbation specification in the report.

### 6.6 Required test 4 — Leakage and validity diagnostics

Run transparent heuristic checks, including:

- Identical feature/record duplicates occurring across a specific train/test split.
- Candidate identifier-like columns (unique IDs, near-unique values, names containing terms such as `id`, `uuid`, `record_id`).
- Suspicious feature names suggesting direct labels or post-outcome variables.
- Class imbalance and tiny per-class test counts.

Each finding must include a severity/description and exact evidence (e.g., count of duplicates), with a statement that these checks **cannot prove the absence of leakage**. For duplicate detection, distinguish exact full-row duplicates from identical feature vectors with different labels.

**Stretch:** Let the user select a group/entity column and re-run group-aware splits; detect extreme target correlation cautiously. Do not assume high predictive power itself proves leakage.

### 6.7 P1 — Sample-size sensitivity

On a fixed holdout test set, subsample the **training** set at 50%, 75%, and 100% (stratified, deterministically seeded), refit the same pipelines, and compare the candidate/baseline gains. Never subsample the evaluation test set in this test; explain when small subsets become invalid.

### 6.8 P1 — Missingness stress test

Inject 5% missing values into numeric **test** features using a seeded random mask; evaluate through the train-fitted imputation pipelines. Report absolute performance and differences from the unperturbed holdout. Do not randomly drop test labels.

### 6.9 Consistency and validity safeguards

- Do not treat leakage heuristics or a single stress test as proof of fraud.
- Avoid confidence intervals or p-values in P0 unless a specifically defensible statistical method is implemented and documented.
- Never manufacture results to make the demo look more dramatic.
- Keep a truthful relationship between observed data and explanations.
- If an experiment fails, record `failed`/`inconclusive`; do not silently replace it with an invented result.
- Make it clear that good robustness on these tests does not guarantee external generalization.

---

## 7. Skeptic AI: behavior and boundaries

The AI component should make LabMirror more than a standard metrics dashboard, without compromising computational correctness.

### Agent roles (logical separation, not necessarily separate processes)

**Claim Interpreter (P1):** Converts a user's informal sentence into a proposed structured `ClaimSpec`, identifies unknowns, and requires explicit user confirmation. Supported scope remains a binary tabular classification comparison.

**Skeptical Auditor (P1, strongly preferred):** Inspects claim, dataset metadata, and initial aggregated results, then selects and **prioritizes** tests from this finite registry:

- `seed_sensitivity`
- `numeric_noise`
- `leakage_diagnostics`
- `sample_size_sensitivity` (if implemented)
- `numeric_missingness` (if implemented)

The auditor must provide a short, specific rationale: “The candidate beat baseline on the default split, but the dataset is small; test whether the gain persists across alternative splits.” It may not invent unimplemented experiments or arbitrary Python execution.

**Evidence Writer (P1):** Receives actual typed numeric results and produces a short, cautious report: what was tested, key observations, biggest weakness, limitations, and sensible next investigation. Every numerical claim must be verifiable against the structured results; favor a deterministic templating fallback if the LLM fails.

### Typed agent boundaries

- Strict JSON schemas validated via Pydantic or equivalent.
- User-controlled inputs are untrusted data, **not** instructions to agents or the backend.
- No file/network/shell permissions for the LLM.
- The execution registry decides what runs, with explicit resource limits.
- No model/metric recommendations outside the supported MVP scope.
- If the API key is unavailable, the product still generates the **same real experiments and a templated report**; AI commentary may be disabled gracefully.
- Agent messages and selections can be displayed in an inspectable **Audit Reasoning / Decisions** panel; avoid exposing or implying hidden chain-of-thought. Show concise justifications and structured decisions instead.

### Meaningful novelty without exaggeration

Show the adversarial selection loop explicitly: **claim -> observed result -> skeptic proposes stress test -> runner evaluates -> finding is updated**. Do not label a single prompt-response pair “autonomous scientists” unless multiple meaningful decisions and executable follow-through exist.

---

## 8. Audit verdict and explanation contract

Use deterministic decision rules derived from the actual experimental results, then optionally attach an AI explanation.

### Suggested verdicts

1. **Consistent with claim in tested settings:** At least **4/5** seeded comparisons meet or exceed the *claimed threshold*, with no critical data-validity blockers.
2. **Mixed / sensitive to conditions:** **1–3/5** meet the threshold, or the stress tests show a materially different result requiring qualification.
3. **Not reproduced in tested settings:** **0/5** meet the threshold, assuming the run is otherwise valid. This is not a universal refutation of the external paper.
4. **Inconclusive / audit blocked:** The data, validation, preprocessing, or diagnostic findings create an unresolved blocker or required tests fail.

These are **product labels**, not formal statistical significance results. Show the exact rule alongside the verdict. If noise sensitivity is observed but the five split tests pass, the report must mention the fragility and may select “Mixed” if a predeclared materiality threshold is met; define that threshold *before coding*, not retroactively to make demos persuasive. Critical leak warnings should trigger “Inconclusive” only when they truly prevent interpreting the evaluation, rather than treating all heuristic flags as proof of contamination.

### Minimum explanation elements

- Claim and minimum improvement threshold.
- Default-split candidate/baseline results.
- Seed-to-seed stability (threshold met on N/5).
- Most consequential stress-test effect.
- Diagnostic warnings with supporting counts.
- Explicit limitations and next experiment recommendation.
- Language such as **“under tested conditions”**, **“suggests”**, and **“does not establish”** where appropriate.

---

## 9. User interface and presentation requirements

Build a responsive, polished research-tool interface. A concise scientific aesthetic is preferable to gaming visuals. The product should feel credible and understandable to a judge who has never used ML.

### Screen 1 — Landing / setup

- Hero: **LabMirror — Don't just trust the research. Test it.**
- Short product description and a visible **Try Demo** action.
- Upload CSV area.
- Data preview and dataset health summary.
- Claim builder with candidate, baseline, target, threshold, and metric.
- Primary call to action: **Generate Audit / Run Stress Test**.

### Screen 2 — Audit plan / progress

- Human-readable list of scheduled tests and why each was chosen.
- Execution progress as the backend actually completes steps.
- Elapsed/runtime context, real errors, and no fake progress percentages.

### Screen 3 — Results dashboard (critical screen)

Above the fold:

- Large evidence headline and **cautious verdict**, with a short reason.
- A clear statement of the exact claim.
- Default split comparison (candidate vs baseline).
- Count **N/5 splits met the claim**.

Below the fold:

- **Seed sensitivity chart:** paired accuracy/lift per seed.
- **Adversarial stress chart:** original vs numeric-noise accuracy for each model.
- **Validity warnings:** duplicate contamination and suspicious features.
- **Audit trace:** what each agent/test decided and why, with evidence.
- **Reproducibility details:** splits, hyperparameters, preprocessing, versions, dataset hash.
- **Download report** and **Run new audit** actions.

### Data visualization rules

- Clearly label **accuracy (%)** and **lift (percentage points)**; they are different units.
- Never truncate the y-axis without signaling that it is truncated.
- Use legends, sensible precision (1–2 decimals), clear tooltip descriptions, and accessible colors.
- Make it obvious whether a number was supplied by the user or measured by LabMirror.
- Warn when model comparisons cannot support a confident conclusion.

### Suggested visual narrative

The most memorable moment should be a transition from an apparently convincing default-split performance comparison to a distribution of five re-evaluations revealing instability.

---

## 10. Demo scenarios and data integrity

### Demo A — Seed-sensitive result (preferred)

Use a **genuinely generated and tested** small synthetic binary-classification dataset or a properly licensed public dataset. Select a seed/configuration in which a default split appears promising while multiple repeat splits reveal material variability.

**Do not prescribe exact outcomes without running the code.** The demo seed and dataset should be verified through the real experiment engine, committed as a documented fixture, and stable between runs. If the chosen dataset does not naturally exhibit the planned effect, pick another legitimate fixture rather than hard-coding scores.

**Live demo sequence:**

1. Open the public site and select the prepared example.
2. Show the explicit claim “Model A is at least +X pp better than Model B.”
3. Show the dataset and configured audit tests.
4. Run the experiment and watch real execution states.
5. Show default split, five-seed chart, stress-test result, warnings, and verdict.
6. Export the report and reveal the complete seeded protocol.

### Demo B — Leakage warning (optional, compelling)

Create a synthetic dataset where duplicates or a clearly labeled post-outcome proxy causes a visible diagnostic warning. Do not claim that a heuristic warning has proven leakage; if implementing a corrective rerun, demonstrate it with an actual feature-exclusion or group-aware re-evaluation.

### Demo recording fallback

In case the hosted compute becomes temporarily unavailable during judging, keep a **recorded screen capture of an authentic completed run**, an exported real report, and a previously generated persisted run when feasible. Clearly identify saved reports as past experimental results, not live execution. The application itself should still be interactive when operational.

---

## 11. Architecture preferences (planning input, not an inflexible mandate)

Prefer a simple separation of responsibilities:

```text
User browser (Next.js / React)
    |
    | upload data, submit ClaimSpec, poll status, view result
    v
Python API (FastAPI + Pydantic)
    |
    +-- dataset validator / profiler
    +-- deterministic experiment runner (pandas, numpy, scikit-learn)
    +-- stress-test registry
    +-- deterministic verdict engine
    +-- optional LLM advisor / report writer
    +-- report exporter
    |
    v
JSON run artifacts / temporary file storage
```

### Practical stack

- **Frontend:** Next.js + TypeScript + Tailwind CSS; Recharts or equivalent for actual charts.
- **Backend:** FastAPI, Python 3.11+, Pydantic, pandas, NumPy, scikit-learn.
- **Optional LLM:** A currently accessible model API with JSON/structured-output support; environment-variable configuration. No LLM required for numeric correctness.
- **Persistence:** Temporary local files and JSON run results are sufficient for a single-instance MVP; Supabase is optional only if it materially improves shareable runs or deployment reliability.
- **Deployment:** Public frontend URL plus a reachable Python backend/worker. Do not rely on a frontend-hosting platform's short serverless timeouts for ML jobs.
- **Compute:** The DGX Spark is available as an optional resource, but the MVP's scikit-learn experiments should usually run on ordinary CPU infrastructure; avoid coupling the demo to complicated remote SSH/GPU provisioning.

### Suggested backend contracts

The plan should specify exact schemas for at least:

- `DatasetSummary`: ID/hash, size, column schema, target class counts, diagnostics.
- `ClaimSpec`: target, candidate, baseline, metric, minimum threshold (pp), optional original claim source.
- `AuditConfig`: split ratio, seed list, preprocessing settings, enabled test IDs, model settings.
- `AuditJob`: job ID, status, progress stages, timing, error details.
- `ExperimentResult`: test type, seed, model, score, observations, warnings.
- `DiagnosticFinding`: severity, check type, count/evidence, caveat.
- `AuditVerdict`: label, rule, threshold-met counts, explanatory evidence links.
- `AuditReport`: schema version, all settings, structured results, warnings, limitations, narrative.

Illustrative REST contract (can be refined by planner):

```text
POST /api/datasets                 Upload and profile CSV
POST /api/audits                   Validate claim and start run
GET  /api/audits/{id}              Status + partial/final results
GET  /api/audits/{id}/report.md    Download audit report
GET  /api/health                   Health check
```

Make the jobs genuinely asynchronous/non-blocking from the browser's perspective, using an uncomplicated worker/background task design that fits deployment. A single-worker bounded queue is acceptable for the hackathon. The API must enforce size/runtime limits.

### Reproducibility artifacts

For each completed run, store (or include in export):

- `dataset_sha256`
- input claim and original source metadata
- selected features/target and excluded columns
- split seed(s), ratios, sample counts
- preprocessing and model hyperparameters
- package versions
- detailed per-test numeric results
- audit verdict rule and triggered diagnostics
- run timestamp, schema/version, and non-reproduction caveats

---

## 12. Security, privacy, and responsible scientific communication

**Threat model:** Arbitrary user-uploaded CSVs and untrusted strings may be malformed, large, private, or deliberately crafted to manipulate LLM prompts or crash resource-intensive code.

Minimum controls:

- Maximum request size and bounded row/column counts.
- Never execute user-uploaded code or `eval` anything from a dataset.
- Restrict agent actions to predefined experiment functions; never execute generated shell or Python code.
- CSV/HTML content must be escaped when rendered. Mitigate spreadsheet formula injection if CSV export is added.
- Avoid raw CSV logging; report aggregated stats instead of row-level personally identifying examples.
- Document temporary-file retention and deletion; prefer short retention and clean up after completed jobs.
- Restrict CORS to intended origin(s), store API secrets server-side, and rate limit expensive endpoints as feasible.
- Impose per-run CPU/time/memory bounds and user-friendly timeout behavior.
- Treat prompt text, column names, and dataset values as untrusted inputs, not system instructions.
- Include a notice that users should not upload confidential or personal information.
- Avoid medical/clinical recommendations from model outputs and do not promise that audits certify scientific truth.

---

## 13. Quantitative acceptance criteria and test cases

These define **done** for P0. Performance targets are design goals to test, not claims already achieved.

### Functional tests

- [ ] A user can open the deployed site without signing in.
- [ ] A demo CSV and realistic structured claim are available in one click.
- [ ] The user can upload a compatible CSV and select the target and features.
- [ ] Invalid datasets/claims fail visibly with actionable messages.
- [ ] At least two real classifiers are fitted using identical splits and leak-safe pipelines.
- [ ] Initial split and five additional seeded comparisons produce **real, repeatable** values.
- [ ] Numeric-noise perturbation runs on the default test data and is documented.
- [ ] Basic leakage diagnostics return evidence-backed warnings or a precise “no issues found in performed checks” statement.
- [ ] Audit verdict follows deterministic documented rules and references actual measurements.
- [ ] Dashboard charts agree exactly with backend JSON and exported report.
- [ ] An experiment can be re-run with the same inputs and produce equivalent results within expected deterministic behavior.
- [ ] Markdown/JSON report is downloadable and includes scientific limitations.
- [ ] A public URL, README, demo data, and a tested pitch walkthrough exist.

### Correctness tests

- [ ] No preprocessing is fitted using test-set data.
- [ ] Candidate/baseline use the same rows in each paired comparison.
- [ ] No random-seed results are hard-coded in frontend, report, or API.
- [ ] Accuracy-to-percentage and fraction-to-percentage-point transformations are unit-tested.
- [ ] With a deliberately invalid threshold or empty target, backend rejects the request.
- [ ] With duplicate records across a train/test split, duplicate detector reports the actual count.
- [ ] Dataset hash, split seeds, and model parameters are present in exported evidence.
- [ ] Agent/API failure does not corrupt computed experiment scores.
- [ ] The audit never calls a 5-split outcome a formal statistical-significance finding.

### Nonfunctional goals

- [ ] Target **under 60 seconds** for a prepared small demo (~1–5k rows, modest feature count) on chosen deployment; if not attainable, set truthful expectations and retain a saved authentic run.
- [ ] A maximum per-job runtime (proposed **120 seconds**) returns a clear error rather than hanging indefinitely.
- [ ] Desktop and mobile layouts remain usable; no critical chart text is clipped.
- [ ] The five-minute demo is intelligible to non-specialists.
- [ ] An unauthenticated judge can complete the entire primary flow.

### Explicit “not done” examples

- A static UI showing fabricated audit statistics.
- An LLM that simply summarizes a CSV and asserts a verdict without Python evaluation.
- A reproducibility label with no actual split/configuration metadata.
- A claim of “replicating any paper” when the product only supports CSV classification experiments.
- A system where the main demo requires undocumented local credentials or manual backend intervention.

---

## 14. Beyond the hackathon: longer-term roadmap

The product vision extends to genuine scientific reproducibility, but this is **not** MVP scope.

### Phase 2 — Richer ML studies

- Multiclass/regression experiments; user-defined metrics.
- Cross-validation, leakage-aware grouped/temporal splitting, paired confidence intervals where statistically justified.
- Additional statistical stress tests and more sophisticated baseline selection.
- Explicit versioned experiment recipes and comparative project history.

### Phase 3 — Paper-to-experiment workflows

- Ingest a paper PDF, paper supplements, dataset links, and GitHub repo.
- Extract claims with evidence citations and confidence scores.
- Identify reproduction requirements and missing information before attempting code execution.
- Retrieve/dependency-pin original study code and approved public datasets.
- Run author-supplied code or agent-authored adaptations **only in isolated, resource-limited environments** with human approval and auditing.
- Distinguish **exact reproduction**, **independent replication**, and **robustness extension**.

### Phase 4 — Autonomous scientific review

- Multi-agent roles for literature analysis, reproduction planning, execution, adversarial stress tests, and critique.
- Counterexample search, disagreement analysis, uncertainty quantification, persistent run provenance.
- Benchmarks evaluating whether AI agents can reliably reproduce scientific results without overstating success.
- Integration points with related autonomous-research-reliability work (e.g., Veritas) while keeping their benchmarks and product claims separate.

---

## 15. EXACT TASK FOR CLAUDE CODE: Generate the implementation plan

**Do not immediately write application code.** First produce a realistic implementation plan that respects the above scope and the imminent event deadline.

### Required first actions

1. Inspect the current repository structure and existing dependencies, scripts, or application scaffolding (if any).
2. Identify what can be reused, what is missing, and which parts of this spec must be simplified to deliver a fully working P0.
3. Note any genuine feasibility concerns or scientific validity issues, and resolve them with concrete, justified assumptions. Do **not** block the plan on unnecessary clarification questions.
4. Check platform/dependency versions from existing project configuration or installed tools. Avoid relying on outdated APIs.

### Primary deliverable

Create **`docs/IMPLEMENTATION_PLAN.md`** (and optionally `docs/ARCHITECTURE.md` if useful). The plan must contain:

1. **Scope lock:** exact P0 features vs explicitly deferred P1/P2 features.
2. **Technical architecture:** frontend/backend/worker boundaries, data flow, request/response schemas, storage, progress tracking, error handling, deployment choice.
3. **Repository layout:** specific folders and files to create, with responsibilities (frontend, backend, experiments, agents, datasets, tests, docs).
4. **Scientific design:** exact supported dataset types, preprocessing pipelines, model hyperparameters, split logic, robustness tests, metric formulas, deterministic verdict thresholds, and disclosure text.
5. **Demo fixture design:** which synthetic/public dataset to use, how to create/verify it reproducibly, what failure mode the demo is intended to reveal, and a fallback if it does not produce that result.
6. **Task breakdown:** ordered, granular implementation tasks with dependencies, time estimates or relative effort, expected files, and a specific acceptance test per task.
7. **Parallel work options:** practical allocation for 2–4 developers or coding agents, with clearly defined integration boundaries and a single-owner merge/testing strategy.
8. **Testing matrix:** unit tests, integration tests, representative datasets, edge cases, performance checks, reproducibility verification, and live deployment smoke tests.
9. **Critical path:** the smallest end-to-end path that can work and be demonstrated first (backend science before elaborate agent/UI extras).
10. **Deployment plan:** working public URL and realistic handling of Python jobs, API keys, CORS, timeouts, and hosting limitations.
11. **Presentation deliverables:** five-minute pitch structure, demo script, README, diagrams, source acknowledgments, and Devpost submission checklist.
12. **Risk register:** biggest likely blockers and precise fallbacks (LLM unavailable, hosting issues, long job, dataset fails, unconvincing fixture).
13. **Definition of done:** a final release checklist mirroring §13, with clear evidence needed to mark each item complete.
14. **Build order:** numbered milestones that maximize the likelihood of a complete working submission before the deadline.

### Planning preferences

- Make choices rather than presenting long menus of equally weighted alternatives.
- State any deviations from this specification explicitly, with the reason.
- A **working, scientifically honest demo** outranks overengineered features.
- Prefer minimal dependencies and existing project tools.
- Protect the critical path: CSV -> claim -> real experiments -> verdict -> visualization -> export -> deployment.
- Include a working-without-LLM fallback in the plan.
- Treat any AI-written interpretation as subordinate to measured evidence.
- Do not claim statistical significance, reproduction fidelity, security, or novelty beyond what the implemented system actually demonstrates.
- After generating the implementation plan, summarize the architecture decision, the first milestone, any major risks, and what should be postponed. **Then stop and await explicit approval before implementing.**

---

## 16. Product pitch and final success criterion

### Short pitch

“LabMirror is a scientific stress-test engine. Instead of treating an impressive ML metric as proof, it independently reruns the comparison, challenges it with alternate splits and controlled perturbations, and tells you which conclusions still hold—with code-backed evidence and an exportable reproducibility record.”

### What success looks like at judging

A judge opens LabMirror, selects a dataset, sees an apparently persuasive experimental claim, runs an actual audit, watches that claim encounter adversarial tests, and leaves with a clear, evidence-backed answer: **the result is consistent, fragile, or not reproduced under precisely defined conditions**.

**Make that flow work first. Everything else is secondary.**
