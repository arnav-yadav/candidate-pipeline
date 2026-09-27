# Candidate pipeline evidence - 2026-07

**Run status:** success

> All client data in this project is simulated (see `docs/simulation.md`).

## Headline

- **Duplicate-screening rate (KPI): 14.9%** of 389 applications (58 repeat screens, ~9.7 recruiter-hours); up to 16.7% if every unconfirmed phone match is the same person.
- Name matching - the method behind the old 22% baseline - reports **27.8%** for the same month: it over-counts, because different people with common names collide.
- **11.8%** of last month's applications were marked DUP by name although the person had never been screened.
- Of last month's applications, **28.5%** were not screened within 30 days; 12.8 percentage points of that never reached the tracker at all.
- **83.8%** heard nothing within 30 days.

## Metrics

| id | metric | value | unit | numerator | denominator | basis |
|---|---|---|---|---|---|---|
| M1 | Duplicate-screening rate (KPI) | 14.9 | % of applications | 58 | 389 | CV screens in 2026-07 of a person already screened in the previous 90 days (resolved identity) |
| M1-upper | Duplicate-screening rate, upper bound | 16.7 | % of applications | 65 | 389 | also counts nameless phone matches still awaiting recruiter confirmation |
| M1-name | Duplicate-screening rate, name matching (old baseline method) | 27.8 | % of applications | 108 | 389 | same definition, but 'same person' = same first + last name string |
| M2 | Applications unreviewed after 30 days | 28.5 | % of cohort | 109 | 382 | applications received in 2026-06 not screened within 30 days |
| M2a |   of which never reached the tracker | 12.8 | % of cohort | 49 | 382 | arrived in a channel but no tracker row links to it |
| M2b |   of which wrongly marked DUP by name | 11.8 | % of cohort | 45 | 382 | marked DUP, but this person had never been screened |
| M3 | Median days to first response (contacted applicants) | 14.0 | days | <NA> | 62 | applications received in 2026-06 that were contacted within 30 days |
| M3a | No response within 30 days | 83.8 | % of cohort | 320 | 382 | includes every silent rejection - the recruiter never tells rejected applicants |
| M4 | Recruiter hours spent re-screening | 9.7 | hours | 58 | <NA> | duplicate screens x 10 min (Assignment 1 costing assumption) |
| M5 | Incorrect merges on recruiter-labelled pairs (guardrail) | 0.0 | pairs | 0 | 180 | target 0; recall 80.7% on the same sample |
| M5a | Possible matches awaiting recruiter confirmation | 12.0 | applications | 12 | <NA> | nameless records whose phone matches a named candidate - not merged automatically |

## How sensitive is the KPI to the 'duplicate' window?

A re-screen only counts as waste if the same person was screened recently. The window is a policy choice.

| lookback_days | duplicate_screens | applications | rate_pct |
|---|---|---|---|
| 30 | 1 | 389 | 0.3 |
| 90 | 58 | 389 | 14.9 |
| 180 | 69 | 389 | 17.7 |
| ever | 69 | 389 | 17.7 |

## Matching rule evidence (recruiter-labelled pairs)

| rule | pairs_evaluated | true_matches_found | false_merges | missed_matches | correctly_kept_apart | precision_pct | recall_pct |
|---|---|---|---|---|---|---|---|
| name_only | 180 | 90 | 25 | 50 | 15 | 78.3 | 64.3 |
| email_only | 180 | 83 | 0 | 57 | 40 | 100.0 | 59.3 |
| phone_only | 180 | 92 | 1 | 48 | 39 | 98.9 | 65.7 |
| email_or_phone | 180 | 133 | 1 | 7 | 39 | 99.3 | 95.0 |
| chosen_plus_unverified | 180 | 133 | 0 | 7 | 40 | 100.0 | 95.0 |
| chosen | 180 | 113 | 0 | 27 | 40 | 100.0 | 80.7 |

## Sources used

| source | status | evidence |
|---|---|---|
| job_board_api | ok | {"pages": 10, "records_received": 969, "overlap_duplicates_removed": 1, "unique_records": 968, "api_total": 968} |
| careers_db | ok | {"query_count": 465, "rows_returned": 465, "db_sha256": "8c54e12fa91a7565", "cutoff_utc": "2026-07-31 18:29:59"} |
| referral_form | ok | {"file_rows": 350, "unparseable_timestamps": 0, "rows_as_of": 308, "sha256": "4863649b223be23b"} |
| whatsapp_export | ok | {"messages_parsed": 1062, "unparsed_lines": 0, "classified": {"application": 418, "follow_up_or_media": 404, "business_reply": 193, "not_hiring": 47}, "sha256": |
| ops_head_mailbox | ok | {"messages_in_file": 427, "parse_failures": 0, "classified": {"application": 251, "internal_or_robot": 100, "other": 26}, "sha256": "8654797c5b1456d5"} |
| recruiter_tracker | ok | {"rows": 2548, "sha256": "61feb63eea11f3a3", "export_is_snapshot": true} |
| audit_sample | ok | {"pairs": 237, "sha256": "43c285e7562076cd"} |

## Data quality (flag, don't fix)

| rule | level | rule_text | rows_flagged | share_pct |
|---|---|---|---|---|
| A03 | warning | at least one usable identifier (email or phone) - otherwise the person cannot be de-duplicated | 27 | 1.12 |
| A04 | warning | email, when given, is a real address (placeholders like 'na' count as missing) | 106 | 4.4 |
| A05 | warning | phone, when given, is a valid 10-digit Indian mobile number | 1 | 0.04 |
| A06 | warning | identifier is not a placeholder or a value shared by many different people | 5 | 0.21 |
| A07 | warning | referral: candidate phone is not the referrer's own phone | 22 | 0.91 |
| A08 | warning | a name is present (WhatsApp/email often have none; matching then relies on identifiers alone) | 222 | 9.21 |
| T03 | warning | Date Logged is not day/month ambiguous (read day-first, the sheet's convention) | 213 | 9.95 |
| T05 | warning | a row whose status says it was screened has a Screened On date | 78 | 3.64 |
| T06 | warning | Status is a known label with an agreed meaning | 250 | 11.68 |
| T07 | warning | Ref is not duplicated (the auto-import sometimes pastes a row twice) | 9 | 0.42 |
| T08 | warning | the row can be linked to an application in a source system | 46 | 2.15 |
