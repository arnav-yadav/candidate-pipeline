# Candidate pipeline evidence - 2026-08

**Run status:** degraded - referral_form unavailable: its channel is missing from every metric

> All client data in this project is simulated (see `docs/simulation.md`).

## Headline

- **Duplicate-screening rate (KPI): 13.6%** of 419 applications (57 repeat screens, ~9.5 recruiter-hours); up to 15.3% if every unconfirmed phone match is the same person.
- Name matching - the method behind the old 22% baseline - reports **28.9%** for the same month: it over-counts, because different people with common names collide.
- **13.2%** of last month's applications were marked DUP by name although the person had never been screened.
- Of last month's applications, **24.3%** were not screened within 30 days; 8.1 percentage points of that never reached the tracker at all.
- **82.2%** heard nothing within 30 days.

## Metrics

| id | metric | value | unit | numerator | denominator | basis |
|---|---|---|---|---|---|---|
| M1 | Duplicate-screening rate (KPI) | 13.6 | % of applications | 57 | 419 | CV screens in 2026-08 of a person already screened in the previous 90 days (resolved identity) |
| M1-upper | Duplicate-screening rate, upper bound | 15.3 | % of applications | 64 | 419 | also counts nameless phone matches still awaiting recruiter confirmation |
| M1-name | Duplicate-screening rate, name matching (old baseline method) | 28.9 | % of applications | 121 | 419 | same definition, but 'same person' = same first + last name string |
| M2 | Applications unreviewed after 30 days | 24.3 | % of cohort | 90 | 370 | applications received in 2026-07 not screened within 30 days |
| M2a |   of which never reached the tracker | 8.1 | % of cohort | 30 | 370 | arrived in a channel but no tracker row links to it |
| M2b |   of which wrongly marked DUP by name | 13.2 | % of cohort | 49 | 370 | marked DUP, but this person had never been screened |
| M3 | Median days to first response (contacted applicants) | 12.0 | days | <NA> | 66 | applications received in 2026-07 that were contacted within 30 days |
| M3a | No response within 30 days | 82.2 | % of cohort | 304 | 370 | includes every silent rejection - the recruiter never tells rejected applicants |
| M4 | Recruiter hours spent re-screening | 9.5 | hours | 57 | <NA> | duplicate screens x 10 min (Assignment 1 costing assumption) |
| M5 | Incorrect merges on recruiter-labelled pairs (guardrail) | 0.0 | pairs | 0 | 193 | target 0; recall 81.9% on the same sample |
| M5a | Possible matches awaiting recruiter confirmation | 16.0 | applications | 16 | <NA> | nameless records whose phone matches a named candidate - not merged automatically |

## How sensitive is the KPI to the 'duplicate' window?

A re-screen only counts as waste if the same person was screened recently. The window is a policy choice.

| lookback_days | duplicate_screens | applications | rate_pct |
|---|---|---|---|
| 30 | 2 | 419 | 0.5 |
| 90 | 57 | 419 | 13.6 |
| 180 | 67 | 419 | 16.0 |
| ever | 67 | 419 | 16.0 |

## Matching rule evidence (recruiter-labelled pairs)

| rule | pairs_evaluated | true_matches_found | false_merges | missed_matches | correctly_kept_apart | precision_pct | recall_pct |
|---|---|---|---|---|---|---|---|
| name_only | 193 | 108 | 29 | 41 | 15 | 78.8 | 72.5 |
| email_only | 193 | 99 | 0 | 50 | 44 | 100.0 | 66.4 |
| phone_only | 193 | 93 | 2 | 56 | 42 | 97.9 | 62.4 |
| email_or_phone | 193 | 145 | 2 | 4 | 42 | 98.6 | 97.3 |
| chosen_plus_unverified | 193 | 143 | 0 | 6 | 44 | 100.0 | 96.0 |
| chosen | 193 | 122 | 0 | 27 | 44 | 100.0 | 81.9 |

## Sources used

| source | status | evidence |
|---|---|---|
| job_board_api | ok | {"pages": 12, "records_received": 1134, "overlap_duplicates_removed": 1, "unique_records": 1133, "api_total": 1133} |
| careers_db | ok | {"query_count": 562, "rows_returned": 562, "db_sha256": "8c54e12fa91a7565", "cutoff_utc": "2026-08-31 18:29:59"} |
| referral_form | unavailable | {"reason": "file not found"} |
| whatsapp_export | ok | {"messages_parsed": 1295, "unparsed_lines": 0, "classified": {"application": 506, "follow_up_or_media": 492, "business_reply": 237, "not_hiring": 60}, "sha256": |
| ops_head_mailbox | ok | {"messages_in_file": 427, "parse_failures": 0, "classified": {"application": 287, "internal_or_robot": 108, "other": 32}, "sha256": "8654797c5b1456d5"} |
| recruiter_tracker | ok | {"rows": 2548, "sha256": "61feb63eea11f3a3", "export_is_snapshot": true} |
| audit_sample | ok | {"pairs": 237, "sha256": "43c285e7562076cd"} |

## Data quality (flag, don't fix)

| rule | level | rule_text | rows_flagged | share_pct |
|---|---|---|---|---|
| A05 | warning | phone, when given, is a valid 10-digit Indian mobile number | 2 | 0.08 |
| A06 | warning | identifier is not a placeholder or a value shared by many different people | 7 | 0.28 |
| A08 | warning | a name is present (WhatsApp/email often have none; matching then relies on identifiers alone) | 273 | 10.97 |
| T03 | warning | Date Logged is not day/month ambiguous (read day-first, the sheet's convention) | 249 | 9.88 |
| T05 | warning | a row whose status says it was screened has a Screened On date | 84 | 3.33 |
| T06 | warning | Status is a known label with an agreed meaning | 288 | 11.43 |
| T07 | warning | Ref is not duplicated (the auto-import sometimes pastes a row twice) | 12 | 0.48 |
| T08 | warning | the row can be linked to an application in a source system | 290 | 11.51 |
