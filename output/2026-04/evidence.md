# Candidate pipeline evidence - 2026-04

**Run status:** success

> All client data in this project is simulated (see `docs/simulation.md`).

## Headline

- **Duplicate-screening rate (KPI): 10.4%** of 383 applications (40 repeat screens, ~6.7 recruiter-hours); up to 12.0% if every unconfirmed phone match is the same person.
- Name matching - the method behind the old 22% baseline - reports **24.3%** for the same month: it over-counts, because different people with common names collide.
- **9.7%** of last month's applications were marked DUP by name although the person had never been screened.
- Of last month's applications, **27.4%** were not screened within 30 days; 13.4 percentage points of that never reached the tracker at all.
- **78.2%** heard nothing within 30 days.

## Metrics

| id | metric | value | unit | numerator | denominator | basis |
|---|---|---|---|---|---|---|
| M1 | Duplicate-screening rate (KPI) | 10.4 | % of applications | 40 | 383 | CV screens in 2026-04 of a person already screened in the previous 90 days (resolved identity) |
| M1-upper | Duplicate-screening rate, upper bound | 12.0 | % of applications | 46 | 383 | also counts nameless phone matches still awaiting recruiter confirmation |
| M1-name | Duplicate-screening rate, name matching (old baseline method) | 24.3 | % of applications | 93 | 383 | same definition, but 'same person' = same first + last name string |
| M2 | Applications unreviewed after 30 days | 27.4 | % of cohort | 104 | 380 | applications received in 2026-03 not screened within 30 days |
| M2a |   of which never reached the tracker | 13.4 | % of cohort | 51 | 380 | arrived in a channel but no tracker row links to it |
| M2b |   of which wrongly marked DUP by name | 9.7 | % of cohort | 37 | 380 | marked DUP, but this person had never been screened |
| M3 | Median days to first response (contacted applicants) | 12.0 | days | <NA> | 83 | applications received in 2026-03 that were contacted within 30 days |
| M3a | No response within 30 days | 78.2 | % of cohort | 297 | 380 | includes every silent rejection - the recruiter never tells rejected applicants |
| M4 | Recruiter hours spent re-screening | 6.7 | hours | 40 | <NA> | duplicate screens x 10 min (Assignment 1 costing assumption) |
| M5 | Incorrect merges on recruiter-labelled pairs (guardrail) | 0.0 | pairs | 0 | 70 | target 0; recall 70.9% on the same sample |
| M5a | Applications awaiting recruiter confirmation | 9.0 | applications | 9 | <NA> | nameless records whose phone matches a named candidate - not merged automatically |

## How sensitive is the KPI to the 'duplicate' window?

A re-screen only counts as waste if the same person was screened recently. The window is a policy choice.

| lookback_days | duplicate_screens | applications | rate_pct |
|---|---|---|---|
| 30 | 3 | 383 | 0.8 |
| 90 | 40 | 383 | 10.4 |
| 180 | 41 | 383 | 10.7 |
| ever | 41 | 383 | 10.7 |

## Matching rule evidence (recruiter-labelled pairs)

| rule | pairs_evaluated | true_matches_found | false_merges | missed_matches | correctly_kept_apart | precision_pct | recall_pct |
|---|---|---|---|---|---|---|---|
| name_only | 70 | 29 | 11 | 26 | 4 | 72.5 | 52.7 |
| email_only | 70 | 29 | 0 | 26 | 15 | 100.0 | 52.7 |
| phone_only | 70 | 38 | 0 | 17 | 15 | 100.0 | 69.1 |
| email_or_phone | 70 | 51 | 0 | 4 | 15 | 100.0 | 92.7 |
| chosen_plus_unverified | 70 | 51 | 0 | 4 | 15 | 100.0 | 92.7 |
| chosen | 70 | 39 | 0 | 16 | 15 | 100.0 | 70.9 |

## Sources used

| source | status | evidence |
|---|---|---|
| job_board_api | ok | {"pages": 6, "records_received": 508, "overlap_duplicates_removed": 1, "unique_records": 507, "api_total": 507} |
| careers_db | ok | {"query_count": 243, "rows_returned": 243, "db_sha256": "8c54e12fa91a7565", "cutoff_utc": "2026-04-30 18:29:59"} |
| referral_form | ok | {"file_rows": 350, "unparseable_timestamps": 0, "rows_as_of": 164, "sha256": "4863649b223be23b"} |
| whatsapp_export | ok | {"messages_parsed": 565, "unparsed_lines": 0, "classified": {"application": 224, "follow_up_or_media": 209, "business_reply": 102, "not_hiring": 30}, "sha256":  |
| ops_head_mailbox | ok | {"messages_in_file": 427, "parse_failures": 0, "classified": {"application": 124, "internal_or_robot": 54, "other": 16}, "sha256": "8654797c5b1456d5"} |
| recruiter_tracker | ok | {"rows": 2548, "sha256": "61feb63eea11f3a3", "export_is_snapshot": true} |
| audit_sample | ok | {"pairs": 237, "sha256": "43c285e7562076cd"} |

## Data quality (flag, don't fix)

| rule | level | rule_text | rows_flagged | share_pct |
|---|---|---|---|---|
| A03 | warning | at least one usable identifier (email or phone) - otherwise the person cannot be de-duplicated | 13 | 1.03 |
| A04 | warning | email, when given, is a real address (placeholders like 'na' count as missing) | 61 | 4.83 |
| A05 | warning | phone, when given, is a valid 10-digit Indian mobile number | 1 | 0.08 |
| A06 | warning | identifier is not a placeholder or a value shared by many different people | 1 | 0.08 |
| A07 | warning | referral: candidate phone is not the referrer's own phone | 9 | 0.71 |
| A08 | warning | a name is present (WhatsApp/email often have none; matching then relies on identifiers alone) | 108 | 8.56 |
| T03 | warning | Date Logged is not day/month ambiguous (read day-first, the sheet's convention) | 105 | 9.48 |
| T05 | warning | a row whose status says it was screened has a Screened On date | 49 | 4.42 |
| T06 | warning | Status is a known label with an agreed meaning | 125 | 11.28 |
| T07 | warning | Ref is not duplicated (the auto-import sometimes pastes a row twice) | 4 | 0.36 |
| T08 | warning | the row can be linked to an application in a source system | 24 | 2.17 |
