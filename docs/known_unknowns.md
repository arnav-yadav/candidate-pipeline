# Known / Unknown / Assumption / Limitation

> All client data is simulated ([simulation.md](simulation.md)). "Known" below means known **within this simulated
> client**, and demonstrated by the pipeline.

## Known

- **2,887 applications from 2,121 people** reached the brand between January and August 2026, about 360 a month.
- **The duplicate-screening rate is 10.4%–14.9% a month** (April–August, the months with a full 90-day look-back),
  not the 22% Assignment 1 measured by name.
- **Name matching over-counts duplicates** (24.3%–31.7% a month): different people share common names. On the 237
  recruiter-labelled pairs it makes 36 incorrect merges, while the chosen rule makes none.
- **9.3%–13.1% of each month's applicants are marked `DUP` by name although they had never been screened**, so
  they're never reviewed at all.
- **23.8%–28.5% of each month's applications aren't screened within 30 days**; 10–13% never reach the tracker.
- **About 80% of applicants hear nothing within 30 days.** Rejections are silent.
- **A sixth intake path exists:** 43 walk-ins typed straight into the tracker, with no source system behind them.

## Unknown

- **Whether H2 is true for the real client.** The simulator encodes "silence drives re-application", so the
  pipeline's H2 result (43% of unanswered applicants re-apply vs 6% who heard back) is circular. The *test* is
  ready to run on real data.
- **What `NS` and `On hold` mean** (287 and 1 rows): "not suitable", "no-show", or something else. Kept as
  `unclear` until the recruiter defines them.
- **The recruiter's decision history.** The sheet keeps only the current status, so how a row got there can't be
  reconstructed.
- **Why some hand-logged rows can't be linked** (49 rows): walk-ins, or applications that exist in a channel nobody
  exported.
- **Applications outside the exported systems** (for example, a recruiter's personal inbox) are invisible.

## Assumptions

- **A re-screen is a duplicate only if the same person was screened in the previous 90 days.** This is a policy
  choice, so every month also publishes the rate at 30, 180 days and "ever" (0.5% / 13.0% / 15.5% / 15.5% in August).
- **One CV screen takes 10 minutes** (Assignment 1: 88 re-screens ≈ 15 hours), for M4.
- **Slash dates in the tracker are day-first**, the Indian convention used in the sheet. The 9.9% that are
  ambiguous are flagged.
- **Every timestamp is compared in IST**; the careers database stores UTC and is converted.
- **The recruiter-labelled sample is correct.** The matching-rule evidence is only as good as those 237 labels.

## Limitations

- **The data is simulated.** The pipeline's behaviour is demonstrated; the exact rates are illustrative and must be
  re-measured on the client's real exports ([simulation.md](simulation.md#what-the-simulation-means-for-the-conclusions)).
- **Recall is 79.3%** on the labelled pairs: the chosen rule leaves nameless phone matches for the recruiter to
  confirm, rather than risk an incorrect merge. The M1 upper bound (up to about 2 points higher) shows how much this
  could matter.
- **The labelled sample is 237 pairs.** "Zero incorrect merges" means zero in that sample, not a guarantee.
- **February and March have less than 90 days of history**, so their M1 is understated; they're labelled degraded.
- **Batch, monthly, as-of month end.** This is not a live candidate view; it's the evidence for building one.
