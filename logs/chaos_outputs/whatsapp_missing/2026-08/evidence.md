# Candidate pipeline evidence - 2026-08

**Run status:** degraded - whatsapp_export unavailable: its channel is missing from every metric

> All client data in this project is simulated (see `docs/simulation.md`).

## Headline

- **Duplicate-screening rate (KPI): 15.7%** of 401 applications (63 repeat screens, ~10.5 recruiter-hours); up to 15.7% if every unconfirmed phone match is the same person.
- Name matching - the method behind the old 22% baseline - reports **32.7%** for the same month: it over-counts, because different people with common names collide.
- **13.7%** of last month's applications were marked DUP by name although the person had never been screened.
- Of last month's applications, **24.7%** were not screened within 30 days; 7.8 percentage points of that never reached the tracker at all.
- **82.0%** heard nothing within 30 days.

## Metrics

| id | metric | value | unit | numerator | denominator | basis |
|---|---|---|---|---|---|---|
| M1 | Duplicate-screening rate (KPI) | 15.7 | % of applications | 63 | 401 | CV screens in 2026-08 of a person already screened in the previous 90 days (resolved identity) |
| M1-upper | Duplicate-screening rate, upper bound | 15.7 | % of applications | 63 | 401 | also counts nameless phone matches still awaiting recruiter confirmation |
| M1-name | Duplicate-screening rate, name matching (old baseline method) | 32.7 | % of applications | 131 | 401 | same definition, but 'same person' = same first + last name string |
| M2 | Applications unreviewed after 30 days | 24.7 | % of cohort | 92 | 373 | applications received in 2026-07 not screened within 30 days |
| M2a |   of which never reached the tracker | 7.8 | % of cohort | 29 | 373 | arrived in a channel but no tracker row links to it |
| M2b |   of which wrongly marked DUP by name | 13.7 | % of cohort | 51 | 373 | marked DUP, but this person had never been screened |
| M3 | Median days to first response (contacted applicants) | 12.0 | days | <NA> | 67 | applications received in 2026-07 that were contacted within 30 days |
| M3a | No response within 30 days | 82.0 | % of cohort | 306 | 373 | includes every silent rejection - the recruiter never tells rejected applicants |
| M4 | Recruiter hours spent re-screening | 10.5 | hours | 63 | <NA> | duplicate screens x 10 min (Assignment 1 costing assumption) |
| M5 | Incorrect merges on recruiter-labelled pairs (guardrail) | 0.0 | pairs | 0 | 162 | target 0; recall 94.3% on the same sample |
| M5a | Applications awaiting recruiter confirmation | 0.0 | applications | 0 | <NA> | nameless records whose phone matches a named candidate - not merged automatically |

## How sensitive is the KPI to the 'duplicate' window?

A re-screen only counts as waste if the same person was screened recently. The window is a policy choice.

| lookback_days | duplicate_screens | applications | rate_pct |
|---|---|---|---|
| 30 | 3 | 401 | 0.7 |
| 90 | 63 | 401 | 15.7 |
| 180 | 73 | 401 | 18.2 |
| ever | 73 | 401 | 18.2 |

## Matching rule evidence (recruiter-labelled pairs)

| rule | pairs_evaluated | true_matches_found | false_merges | missed_matches | correctly_kept_apart | precision_pct | recall_pct |
|---|---|---|---|---|---|---|---|
| name_only | 162 | 89 | 27 | 33 | 13 | 76.7 | 73.0 |
| email_only | 162 | 103 | 0 | 19 | 40 | 100.0 | 84.4 |
| phone_only | 162 | 62 | 2 | 60 | 38 | 96.9 | 50.8 |
| email_or_phone | 162 | 115 | 2 | 7 | 38 | 98.3 | 94.3 |
| chosen_plus_unverified | 162 | 115 | 0 | 7 | 40 | 100.0 | 94.3 |
| chosen | 162 | 115 | 0 | 7 | 40 | 100.0 | 94.3 |

## Sources used

| source | status | evidence |
|---|---|---|
| job_board_api | ok | {"pages": 12, "records_received": 1134, "overlap_duplicates_removed": 1, "unique_records": 1133, "api_total": 1133} |
| careers_db | ok | {"query_count": 562, "rows_returned": 562, "db_sha256": "8c54e12fa91a7565", "cutoff_utc": "2026-08-31 18:29:59"} |
| referral_form | ok | {"file_rows": 350, "unparseable_timestamps": 0, "rows_as_of": 350, "sha256": "4863649b223be23b"} |
| whatsapp_export | unavailable | {"reason": "export file not found"} |
| ops_head_mailbox | ok | {"messages_in_file": 427, "parse_failures": 0, "classified": {"application": 287, "internal_or_robot": 108, "other": 32}, "sha256": "8654797c5b1456d5"} |
| recruiter_tracker | ok | {"rows": 2548, "sha256": "61feb63eea11f3a3", "export_is_snapshot": true} |
| audit_sample | ok | {"pairs": 237, "sha256": "43c285e7562076cd"} |

## Data quality (flag, don't fix)

| rule | level | rule_text | rows_flagged | share_pct |
|---|---|---|---|---|
| A03 | warning | at least one usable identifier (email or phone) - otherwise the person cannot be de-duplicated | 28 | 1.2 |
| A04 | warning | email, when given, is a real address (placeholders like 'na' count as missing) | 118 | 5.06 |
| A05 | warning | phone, when given, is a valid 10-digit Indian mobile number | 2 | 0.09 |
| A06 | warning | identifier is not a placeholder or a value shared by many different people | 7 | 0.3 |
| A07 | warning | referral: candidate phone is not the referrer's own phone | 23 | 0.99 |
| A08 | warning | a name is present (WhatsApp/email often have none; matching then relies on identifiers alone) | 73 | 3.13 |
| T03 | warning | Date Logged is not day/month ambiguous (read day-first, the sheet's convention) | 249 | 9.88 |
| T05 | warning | a row whose status says it was screened has a Screened On date | 84 | 3.33 |
| T06 | warning | Status is a known label with an agreed meaning | 288 | 11.43 |
| T07 | warning | Ref is not duplicated (the auto-import sometimes pastes a row twice) | 12 | 0.48 |
| T08 | warning | the row can be linked to an application in a source system | 389 | 15.44 |
