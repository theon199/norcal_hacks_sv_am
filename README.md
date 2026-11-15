# LabMirror

**Don't just trust the research. Test it.**

LabMirror takes a falsifiable machine-learning claim, such as *"Random Forest beats Logistic Regression by at least 5 percentage points of accuracy"*, and tests it against a CSV dataset. It reruns the comparison, then deliberately looks for conditions under which the claimed advantage weakens: other train/test splits, noisy inputs, signs of leakage. It ends with a verdict, the fixed rule that produced it, and a report anyone can rerun.

**Live app:** https://labmirror-jade.vercel.app (no sign-in). Built for [NorCal Hacks 27](https://norcal-hacks-27.devpost.com/), New Frontiers track.

> The backend runs on a free Render instance that sleeps when idle. The first request after a quiet period can take up to a minute while it wakes; the page says so while it waits.

## What it is, and what it is not

LabMirror **independently re-evaluates** a claim on the data and protocol shown on screen. It is **not a reproduction** of a published study unless that study's exact data, splits and code were used, and the interface never says otherwise. Accuracies you type in from a paper are shown as "reported by user, not verified"; everything else is "measured by LabMirror".

- **Verdicts are product labels, not statistical tests.** They come from a fixed, published rule (below). LabMirror reports no p-values and makes no significance claims.
- **There is no AI in the scoring path.** Every number comes from scikit-learn running on your data, and the verdict comes from the fixed rule. An optional Claude layer (off by default, see `LABMIRROR_LLM` below) can do two things only: a *Skeptical Auditor* that reorders the three stress tests (all of them always run), and an *Evidence Writer* that replaces the template summary when every number in its text is found in the report. It is sent the claim, column names and kinds, and aggregate results, never raw rows. Any failure falls back to the fixed order and the template.
- **Users cannot run arbitrary code.** Only an allowlisted set of seven stages exists, with fixed hyperparameters.

Scope: binary classification · tabular CSV · Random Forest vs Logistic Regression (plus a most-frequent-class sanity baseline) · accuracy as the claimed metric, with balanced accuracy and F1 reported alongside.

## Try it in one minute

1. Open the live app and click **Try this example** on *Factory machine breakdowns (synthetic)*. It has 400 machines with eight readings each (temperature, vibration, oil pressure, motor current, speed, oil quality, sound level, hours since service) and asks whether a machine will break down.
2. Click **Run stress test** and watch the stages run.
3. The default split shows Random Forest ahead by **+7.5 pp**, which clears the claimed +5 pp. Across five other splits, the claim's margin holds on **3 of 5**, each time exactly at +5.0 pp, and on one split the two models tie. Verdict: **Mixed: sensitive to conditions**.
4. Download the Markdown or JSON report and compare it with the screen.

That dataset was **selected** to show split sensitivity, and the app says so. [`scripts/make_demo_fixture.py`](scripts/make_demo_fixture.py) generated candidates with scikit-learn's `make_classification` and kept the first one where the production engine found the claim met on the default split but on only one to three other splits. The generated columns were given machine-reading names and units with one fixed scale per column, chosen before the search; the data does not describe real machines. The full search is recorded in [`sensor_fault_synthetic.provenance.json`](backend/labmirror/demo_data/sensor_fault_synthetic.provenance.json). No value was edited, and every number on screen is recomputed live.

The second example, **Breast Cancer Wisconsin** (exported unmodified from scikit-learn), is a contrasting case: the claim fails on all five splits, so the verdict is *Not reproduced in tested settings*.

## How an audit works

```text
Browser ── Next.js on Vercel
   │  upload CSV / pick demo → build claim → poll progress every second
   ▼
FastAPI on Render (one Docker container, one worker)
   ├─ jobs.py      bounded queue (1 running, 5 waiting); one child process per audit; hard 120 s limit
   │     └─ child ── engine.run_audit() ── writes job.json after every stage
   ├─ engine/      pure Python + pandas + scikit-learn; also runnable as a CLI
   └─ DATA_DIR/    uploaded datasets and run results, deleted after 24 hours
```

The seven stages, in order:

| Stage | What it does |
|---|---|
| Validate | Binary target, ≥ 20 rows per class, every selected feature usable |
| Default split | One stratified 80/20 split (seed 42); candidate, baseline and dummy share the same rows |
| Five other splits | Same pipelines refitted on seeds 11, 23, 37, 51, 79 |
| Feature noise | Default-split models scored on test rows with Gaussian noise at 10% of each numeric feature's training standard deviation, 20 seeded draws |
| Leakage diagnostics | Cross-split duplicate rows, conflicting-label duplicates, identifier-like or leakage-suggestive column names, class imbalance, tiny test classes |
| Verdict | The fixed rule below |
| Report | Hash, seeds, hyperparameters, library versions, narrative, limitations |

## Scientific protocol

- **Pipelines.** Numeric features: median imputation, then standard scaling. Categorical features: most-frequent imputation, then one-hot encoding. Preprocessing is fitted on training rows only, inside one scikit-learn `Pipeline` per model, and both models use identical preprocessing.
- **Models (untuned).** `LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)`, `RandomForestClassifier(n_estimators=100)`, `DummyClassifier("most_frequent")`. Model `random_state` is fixed at 0 on every split, so the five-split test measures split sensitivity, not model-initialization sensitivity.
- **Lift.** `(candidate accuracy − baseline accuracy) × 100`, in percentage points, computed unrounded. A split meets the claim when the lift is at least the claimed threshold.
- **F1.** The positive class is the minority class (ties broken by sorted label order), shown in the report.

### Verdict rule

Evaluated in order; the first match wins. *k* is the number of the five other splits that meet the claimed threshold.

1. **Inconclusive:** a required test failed, or a critical diagnostic is present.
2. **Not reproduced in tested settings:** *k* = 0.
3. **Mixed / sensitive to conditions:** *k* = 1, 2 or 3.
4. **Mixed / sensitive to conditions:** *k* ≥ 4, but under feature noise the mean lift falls below the threshold and drops by at least 2.0 pp.
5. **Consistent with claim in tested settings:** *k* ≥ 4 and rule 4 did not apply.

The rule was fixed before any demo dataset existed. It is shown next to every verdict and printed in every report.

## Data limits

Up to 20 MB, **100–5,000 rows**, 2–50 feature columns, and **rows × feature columns ≤ 100,000** (for example 5,000 × 20 or 2,000 × 50). These limits came from a timing test on the deployed free instance: a 20,000 × 50 audit hit the 120 s limit, while 2,000 × 50 finished in 57 s. They are single constants in [`backend/labmirror/config.py`](backend/labmirror/config.py) and can go back up on a larger instance.

Don't upload confidential or personal data. Uploads and results are deleted after 24 hours, and links to past runs stop working when the backend redeploys.

## Run it locally

Requires Python 3.13 and Node.js 20 or later.

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements-dev.txt
uvicorn labmirror.api:app --port 8000 --workers 1
```

Keep it to one worker: the job queue lives in process memory.

```bash
cd frontend
npm install
npm run dev                   # http://localhost:3000, talks to http://localhost:8000 by default
```

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | frontend | `http://localhost:8000` | Backend base URL |
| `ALLOWED_ORIGINS` | backend | `http://localhost:3000` | Comma-separated CORS origins |
| `DATA_DIR` | backend | `backend/data` | Where uploads and runs are stored |
| `MAX_UPLOAD_MB` | backend | `20` | Upload size limit |
| `JOB_TIMEOUT_S` | backend | `120` | Per-audit time limit |
| `LABMIRROR_LLM` | backend | unset | Set to `1` (with `ANTHROPIC_API_KEY`) to turn on the Skeptical Auditor and Evidence Writer |
| `ANTHROPIC_API_KEY` | backend | unset | Claude API key; stays server-side |
| `LLM_MODEL` | backend | `claude-opus-5-5` | Claude model for both roles |
| `LLM_TIMEOUT_S` | backend | `20` | Per-call timeout; no retries, so both calls fit inside the job limit |

### Command line, tests and checks

```bash
cd backend
python -m labmirror.cli audit labmirror/demo_data/sensor_fault_synthetic.csv --target machine_fault --threshold 5 --out report.json
python -m pytest -q                                          # engine, API, verdict, report and demo-fixture tests
python ../scripts/smoke_test.py https://labmirror-api.onrender.com   # end-to-end check against a deployed API
python ../scripts/make_demo_fixture.py labmirror/demo_data   # regenerates the synthetic demo byte-for-byte
```

The CLI runs exactly the same engine as the website. Among other things, the tests check that no preprocessing is fitted on test rows, that candidate and baseline see identical rows, that a rerun produces identical results, that every number in the Markdown report comes from the JSON report, and that each demo still produces the verdict its card describes.

## Limitations

- LabMirror independently re-evaluates a claim on the data and protocol shown. It is not a reproduction of any published study unless that study's exact data, splits and code were used.
- Only binary classification on tabular CSV data, with the two listed scikit-learn models, is supported. Hyperparameters are fixed and untuned; a tuned model could behave differently.
- "2 of 5 splits" describes the tested splits; it is not a probability. Passing every test does not mean a result generalizes.
- The noise test is one specific noise model, not a claim about real-world measurement error.
- Leakage checks are heuristics. They can flag likely problems, but they cannot prove leakage or its absence.
- The synthetic demo was selected to illustrate split sensitivity. It does not describe real machines.

## Repository map

```text
backend/labmirror/engine/   profiling, validation, pipelines, splits, noise, diagnostics, verdict, report
backend/labmirror/          FastAPI app, job runner, storage, schemas, CLI, demo data
backend/tests/              pytest suite
frontend/src/               Next.js app: setup screen, live progress, results dashboard, SVG charts
scripts/                    demo fixture generator, Breast Cancer export, smoke test
docs/IMPLEMENTATION_PLAN.md build plan, API contract, and every deviation from the spec with its reason
LabMirror_Product_Spec.md   product requirements
```

## Acknowledgments

- [scikit-learn](https://scikit-learn.org/), [pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/), [FastAPI](https://fastapi.tiangolo.com/), [Next.js](https://nextjs.org/) and [Tailwind CSS](https://tailwindcss.com/).
- **Breast Cancer Wisconsin (Diagnostic)** dataset: W. H. Wolberg, W. N. Street and O. L. Mangasarian, UCI Machine Learning Repository, via `sklearn.datasets.load_breast_cancer`. For teaching only; not for clinical use.
- Hosted on [Vercel](https://vercel.com/) and [Render](https://render.com/).
