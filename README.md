# Single-view candidate pipeline: a D2C brand hiring non-stop

One recruiter, five intake channels, one hand-kept spreadsheet. The same people keep coming back, some are screened
twice, and some are never seen at all.

This project turns the brand's scattered intake systems into one de-duplicated view of every applicant, and a
monthly evidence pack that measures the problem honestly, through a repeatable pipeline:
**extract → validate → resolve → model → metrics**.

Track C (own problem) · FDE Data Foundations, Classes 4–8 · continues the Assignment 1 problem statement.

> **All client data is simulated.** The client is the constructed case from Assignment 1; no real person's data is
> used. How the data was generated, and what that means for each conclusion:
> [docs/simulation.md](docs/simulation.md).

## The problem

A ~150-person D2C brand hires customer-support agents continuously. Applications arrive through five channels: job
boards, the careers page, employee referrals, a WhatsApp number and emails to the Head of Ops. One recruiter merges
them by hand into a Google Sheet and spots duplicates by name.

Assignment 1 scoped it as **"No single view of the candidate pipeline"**: duplicates are re-screened, some
applications are never reviewed, and applicants wait a long time for a response. Its first validation step was to
**re-measure the duplicate baseline**, because 22% had been measured by name matching only. This project is that
measurement, built so it can run every month.

## Who it's for

| Stakeholder | Role | What they get |
|---|---|---|
| Head of Customer Support Ops | Outcome owner; asked for "an AI tool to sort through CVs" | A measured baseline and a monthly trend, instead of a guess |
| Recruiter | User and operator; owns the tracker | A de-duplicated candidate list, a worklist of unreviewed applicants, a short review queue |
| Support team leads | Receive shortlisted candidates | Fewer candidates lost before they reach interview |
| Web/IT team, job-board vendor | Data and system owners | A clear list of what each source is missing |
| Applicants | Affected | Fewer people silently dropped |

## KPI

**Duplicate-screening rate (M1)**: CV screens of a person already screened in the previous 90 days, as a share of
the month's applications. It's the primary KPI from Assignment 1 (target: under 5%, against a re-measured baseline).

| | Metric | What it answers |
|---|---|---|
| **M1** | Duplicate-screening rate *(KPI)* | How much screening is repeat work? |
| M2 | Unreviewed after 30 days | Who never gets looked at? |
| M3 | Time to first response | How long do applicants wait, and how many hear nothing? |
| M4 | Recruiter hours on re-screening | What does the waste cost? |
| M5 | Incorrect merges *(guardrail)* | Does de-duplication wrongly collapse two people into one? Target: 0 |

Definitions, numerators and denominators: [docs/data_model.md](docs/data_model.md#the-metrics).

## What the data shows

Months with a full 90-day look-back (April–August 2026). All months: [output/summary/summary.md](output/summary/summary.md).

| | Apr | May | Jun | Jul | Aug |
|---|---:|---:|---:|---:|---:|
| **M1 duplicate-screening rate (KPI)** | **10.4%** | **13.0%** | **14.4%** | **14.9%** | **13.0%** |
| M1 by name matching (the old method) | 24.3% | 24.6% | 31.7% | 27.8% | 27.6% |
| Marked `DUP` by name, but never screened | 9.7% | 11.0% | 9.3% | 11.8% | 13.1% |
| M2 unreviewed after 30 days | 27.4% | 27.4% | 23.8% | 28.5% | 28.3% |
| M3 median days to first response | 12 | 12 | 11 | 14 | 12 |
| M3a heard nothing within 30 days | 78.2% | 80.4% | 78.9% | 83.8% | 83.0% |
| M4 recruiter hours on re-screening | 6.7 | 8.7 | 9.2 | 9.7 | 9.3 |
| M5 incorrect merges (guardrail) | 0 | 0 | 0 | 0 | 0 |

- **The real duplicate rate is about 10–15%, not 22%.** Assignment 1 thought 22% was a *lower bound*; it is
  1.5–2 times the measured rate.
- **Name matching fails in both directions.** It merges different people who share a common name, and it misses
  the same person written differently. Its biggest cost isn't wasted screens: **9–13% of applicants are dismissed as
  duplicates without ever being screened.**
- **A quarter of applications aren't screened within 30 days**, and about 80% of applicants never hear back.

## The decision it supports

1. **Stop marking duplicates by name**; use the resolved candidate list.
2. **Work the backlog**: `unreviewed_worklist.csv` lists last month's applicants who were never screened, and why.
3. **Confirm the review queue**: `identity_review_queue.csv` lists the few possible matches that need one call.
4. **Don't build AI shortlisting yet.** The pipeline shows the problem is visibility, not judgement: people are
   lost before anyone reads their CV. The next step is running this on the client's real exports.

## Sources

| Source | Owner | Retrieval | One row = |
|---|---|---|---|
| Job boards (Indeed / Naukri) | Job-board vendor | **REST API**, paginated, with retries | one application |
| Careers page | Web/IT team | **SQL** (SQLite) | one form submission |
| Employee referral form | Recruiter | **CSV** export | one referral |
| WhatsApp "Hiring - Ops" number | Head of Ops | **WhatsApp `.txt`** export | one message |
| Head of Ops mailbox | Head of Ops | **`.mbox`** export | one email |
| Recruiter's hiring tracker | Recruiter | **CSV** export of the Google Sheet | one logged row |
| Recruiter-labelled pairs | Recruiter | **CSV** | one pair, same / different person |

Ownership, identifiers per channel, join decisions and gaps: [docs/source_map.md](docs/source_map.md).

## How it works

| Stage | What happens | Details |
|---|---|---|
| **Extract** | Pulls all seven sources, saves them untouched, and proves each pull is complete (API `total`, SQL `COUNT(*)`, file checksums) | [docs/pipeline.md](docs/pipeline.md) |
| **Validate** | 15 business rules flag problems without deleting or fixing anything; writes a quality report | [docs/validation_rules.md](docs/validation_rules.md) |
| **Resolve** | Groups applications into people on email, or phone plus a compatible name; links tracker rows to applications | [docs/data_model.md](docs/data_model.md#identity-resolution) |
| **Model** | Loads a workflow-shaped SQLite warehouse in one transaction, with integrity checks before commit | [docs/data_model.md](docs/data_model.md) |
| **Metrics** | Computes M1–M5 with numerators and denominators, the worklists and an evidence page | [docs/data_model.md](docs/data_model.md#the-metrics) |

**Dependability:**
- It halts when a critical source fails, and degrades (with a label) when a supplementary one does.
- A rerun gives byte-identical outputs, and publishing is atomic.
- A failed run never overwrites good outputs, and a `--chaos` test run never touches real outputs.
- Every run writes a manifest recording the git commit, config hash, source evidence and rule counts.

## Setup and run

Needs Python 3.10+. The pipeline itself needs no internet access or API keys: the job-board API is a local mock that
the pipeline starts itself.

```bash
python -m venv .venv
.venv\Scripts\activate                         # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

python run_pipeline.py --range 2026-02 2026-08  # full backfill, plus the cross-month summary
python run_pipeline.py --month 2026-08          # one month
python run_pipeline.py --month 2026-08 --chaos job_board_down   # controlled failure (also: tracker_schema,
                                                                #  whatsapp_missing, mailbox_missing, referrals_missing)
pytest                                          # 52 tests

python simulator/generate_client_systems.py     # optional: regenerate the simulated client systems
```

## Where to find the evidence

| What | Where |
|---|---|
| Cross-month summary, H1-vs-H2 test, matching-rule comparison | [output/summary/](output/summary/) |
| One month's evidence page | e.g. [output/2026-08/evidence.md](output/2026-08/evidence.md) |
| Every metric with numerator and denominator | `output/<month>/metrics.csv` |
| Data quality per rule | `output/<month>/quality_report.csv` |
| Worklist and review queue | `output/<month>/unreviewed_worklist.csv`, `identity_review_queue.csv` |
| What each run did, including failed and chaos runs | `output/<month>/run_manifest.json`, `logs/manifests/` |
| Profiling that shaped the rules | [notebooks/01_profiling.ipynb](notebooks/01_profiling.ipynb) |

## Known / Unknown / Assumption / Limitation

The most important points; the full list is in [docs/known_unknowns.md](docs/known_unknowns.md).

- **Known:** the duplicate rate is 10–15% a month; name matching over-counts it and wrongly dismisses 9–13% of
  applicants; about 80% of applicants hear nothing within 30 days.
- **Unknown:** whether silence drives re-application (H2) for the real client. The simulator assumes it, so the
  pipeline's H2 result is circular; the test itself is ready for real data.
- **Assumption:** a re-screen is a duplicate only within 90 days (sensitivity at 30 / 180 days / ever is published);
  one screen takes 10 minutes; slash dates are day-first.
- **Limitation:** the data is simulated, so the rates are illustrative. The chosen matching rule finds 79.3% of true
  duplicates on the labelled pairs, leaving nameless phone matches for the recruiter to confirm rather than guess.

## The judgement call

The obvious matching rule, "same email **or** same phone", found the most duplicates on the recruiter-labelled pairs
(93.9% recall). **I didn't use it.** It made 2 incorrect merges out of 237 pairs, and both were siblings sharing one
phone number: Aarti and Sneha Sharma, and Sandeep and Rahul Sharma, each pair merged into one "candidate".

Assignment 1 set a guardrail of **zero incorrect merges**, because an incorrect merge is the worst failure this fix
can introduce: it silently removes a real applicant, the exact problem the project exists to solve. So the chosen rule
only merges on phone when the names are compatible.

That leaves the hard case: a WhatsApp message with a phone number but **no name**. Auto-merging those made no
incorrect merges in this sample (92.7% recall), but on a phone that two siblings share, a nameless message can't be
attributed to either, and one wrong guess breaks the guardrail. Zero in 237 pairs isn't zero risk. So the chosen rule
sends them to a **review queue** (8–12 applications a month, one phone call each) instead of guessing. Recall on the labelled pairs
drops to 79.3%, but those matches aren't lost, they're waiting for confirmation, and the KPI's upper bound shows what
they would add: at most about 2 points.

The same evidence overturned an Assignment 1 assumption. Assignment 1 treated 22% (by name) as a *lower bound* on
duplicates. Name matching turned out to **over-count**, because common names collide, and its worse effect is hiding
people: applicants wrongly marked `DUP` are never screened.

## Repo layout

| Path | Purpose |
|---|---|
| `run_pipeline.py` | Single entrypoint (`--month`, `--range`, `--chaos`) |
| `config.yaml` | Source locations, critical sources, thresholds, matching settings |
| `pipeline/` | Extract, normalise, validate, resolve, model, metrics, publish |
| `sql/` | Warehouse schema and metric queries |
| `client_systems/` | The simulated client systems: mock job-board API, careers DB, exports |
| `simulator/` | The generator for `client_systems/` (the pipeline never reads `_ground_truth/`) |
| `output/` | Published results (committed); `data/` is rebuilt by the pipeline and not committed |
| `logs/` | Run manifests, including failed and chaos runs |
| `docs/` | Simulation, source map, validation rules, data model and metrics, pipeline, known unknowns |
| `notebooks/` | Profiling |
| `tests/` | 52 tests |
