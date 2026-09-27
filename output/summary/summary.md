# Cross-month summary

> All client data in this project is simulated (see `docs/simulation.md`).

Produced from 7 monthly runs with config `c4997a4f760a4b51` and code `a05aded`; every month's manifest was checked to match.

## KPI and supporting metrics by month

| month | status | M1 KPI % | M1 upper % | M1 name-matching % | M2b wrongly DUP % | M2 unreviewed % | M2a never logged % | M3 median days | M3a no reply % | M4 hours | M5 false merges | review queue |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-02 | degraded | 4.7 | 5.0 | 14.7 | 4.2 | 20.4 | 12.8 | 14.0 | 79.6 | 2.0 | 0.0 | 0.0 |
| 2026-03 | degraded | 12.6 | 13.7 | 26.3 | 5.8 | 20.9 | 10.1 | 12.0 | 74.4 | 8.0 | 0.0 | 5.0 |
| 2026-04 | success | 10.4 | 12.0 | 24.3 | 9.7 | 27.4 | 13.4 | 12.0 | 78.2 | 6.7 | 0.0 | 9.0 |
| 2026-05 | success | 13.0 | 13.8 | 24.6 | 11.0 | 27.4 | 12.5 | 12.0 | 80.4 | 8.7 | 0.0 | 8.0 |
| 2026-06 | success | 14.4 | 15.4 | 31.7 | 9.3 | 23.8 | 11.5 | 11.0 | 78.9 | 9.2 | 0.0 | 8.0 |
| 2026-07 | success | 14.9 | 16.7 | 27.8 | 11.8 | 28.5 | 12.8 | 14.0 | 83.8 | 9.7 | 0.0 | 12.0 |
| 2026-08 | success | 13.0 | 14.6 | 27.6 | 13.1 | 28.3 | 12.1 | 12.0 | 83.0 | 9.3 | 0.0 | 16.0 |

## H1 vs H2: why do people re-apply? (Assignment 1, V1)

Re-application within 75 days, split by whether the applicant heard back within 30 days.

| heard_back_30d | applications | reapplied | reapply_rate_pct |
|---|---|---|---|
| no reply within 30 days | 1202 | 518 | 43.1 |
| heard back within 30 days | 333 | 20 | 6.0 |

## Matching rule comparison

| rule | pairs_evaluated | true_matches_found | false_merges | missed_matches | correctly_kept_apart | precision_pct | recall_pct |
|---|---|---|---|---|---|---|---|
| name_only | 237 | 117 | 36 | 62 | 22 | 76.5 | 65.4 |
| email_only | 237 | 107 | 0 | 72 | 58 | 100.0 | 59.8 |
| phone_only | 237 | 112 | 2 | 67 | 56 | 98.2 | 62.6 |
| email_or_phone | 237 | 168 | 2 | 11 | 56 | 98.8 | 93.9 |
| chosen_plus_unverified | 237 | 166 | 0 | 13 | 58 | 100.0 | 92.7 |
| chosen | 237 | 142 | 0 | 37 | 58 | 100.0 | 79.3 |
