# Candidate pipeline evidence - 2026-06

**Run status:** success

> All client data in this project is simulated (see `docs/simulation.md`).

## Headline

- **Duplicate-screening rate (KPI): 14.4%** of 382 applications (55 repeat screens, ~9.2 recruiter-hours); up to 15.4% if every unconfirmed phone match is the same person.
- Name matching - the method behind the old 22% baseline - reports **31.7%** for the same month: it over-counts, because different people with common names collide.
- **9.3%** of last month's applications were marked DUP by name although the person had never been screened.
- Of last month's applications, **23.8%** were not screened within 30 days; 11.5 percentage points of that never reached the tracker at all.
- **78.9%** heard nothing within 30 days.

## Metrics

| id | metric | value | unit | numerator | denominator | basis |
|---|---|---|---|---|---|---|
| M1 | Duplicate-screening rate (KPI) | 14.4 | % of applications | 55 | 382 | CV screens in 2026-06 of a person already screened in the previous 90 days (resolved identity) |
| M1-upper | Duplicate-screening rate, upper bound | 15.4 | % of applications | 59 | 382 | also counts nameless phone matches still awaiting recruiter confirmation |
| M1-name | Duplicate-screening rate, name matching (old baseline method) | 31.7 | % of applications | 121 | 382 | same definition, but 'same person' = same first + last name string |
| M2 | Applications unreviewed after 30 days | 23.8 | % of cohort | 95 | 399 | applications received in 2026-05 not screened within 30 days |
| M2a |   of which never reached the tracker | 11.5 | % of cohort | 46 | 399 | arrived in a channel but no tracker row links to it |
| M2b |   of which wrongly marked DUP by name | 9.3 | % of cohort | 37 | 399 | marked DUP, but this person had never been screened |
| M3 | Median days to first response (contacted applicants) | 11.0 | days | <NA> | 84 | applications received in 2026-05 that were contacted within 30 days |
| M3a | No response within 30 days | 78.9 | % of cohort | 315 | 399 | includes every silent rejection - the recruiter never tells rejected applicants |
| M4 | Recruiter hours spent re-screening | 9.2 | hours | 55 | <NA> | duplicate screens x 10 min (Assignment 1 costing assumption) |
| M5 | Incorrect merges on recruiter-labelled pairs (guardrail) | 0.0 | pairs | 0 | 137 | target 0; recall 77.4% on the same sample |
| M5a | Applications awaiting recruiter confirmation | 8.0 | applications | 8 | <NA> | nameless records whose phone matches a named candidate - not merged automatically |

## How sensitive is the KPI to the 'duplicate' window?

A re-screen only counts as waste if the same person was screened recently. The window is a policy choice.

| lookback_days | duplicate_screens | applications | rate_pct |
|---|---|---|---|
| 30 | 1 | 382 | 0.3 |
| 90 | 55 | 382 | 14.4 |
| 180 | 62 | 382 | 16.2 |
| ever | 62 | 382 | 16.2 |

## Matching rule evidence (recruiter-labelled pairs)

| rule | pairs_evaluated | true_matches_found | false_merges | missed_matches | correctly_kept_apart | precision_pct | recall_pct |
|---|---|---|---|---|---|---|---|
| name_only | 137 | 66 | 20 | 40 | 11 | 76.7 | 62.3 |
| email_only | 137 | 59 | 0 | 47 | 31 | 100.0 | 55.7 |
| phone_only | 137 | 72 | 1 | 34 | 30 | 98.6 | 67.9 |
| email_or_phone | 137 | 100 | 1 | 6 | 30 | 99.0 | 94.3 |
| chosen_plus_unverified | 137 | 100 | 0 | 6 | 31 | 100.0 | 94.3 |
| chosen | 137 | 82 | 0 | 24 | 31 | 100.0 | 77.4 |

## Sources used

| source | status | evidence |
|---|---|---|
| job_board_api | ok | {"pages": 9, "records_received": 813, "overlap_duplicates_removed": 1, "unique_records": 812, "api_total": 812} |
| careers_db | ok | {"query_count": 390, "rows_returned": 390, "db_sha256": "8c54e12fa91a7565", "cutoff_utc": "2026-06-30 18:29:59"} |
| referral_form | ok | {"file_rows": 350, "unparseable_timestamps": 0, "rows_as_of": 257, "sha256": "4863649b223be23b"} |
| whatsapp_export | ok | {"messages_parsed": 897, "unparsed_lines": 0, "classified": {"application": 355, "follow_up_or_media": 344, "business_reply": 161, "not_hiring": 37}, "sha256":  |
| ops_head_mailbox | ok | {"messages_in_file": 427, "parse_failures": 0, "classified": {"application": 214, "internal_or_robot": 82, "other": 21}, "sha256": "8654797c5b1456d5"} |
| recruiter_tracker | ok | {"rows": 2548, "sha256": "61feb63eea11f3a3", "export_is_snapshot": true} |
| audit_sample | ok | {"pairs": 237, "sha256": "43c285e7562076cd"} |

## Data quality (flag, don't fix)

| rule | level | rule_text | rows_flagged | share_pct |
|---|---|---|---|---|
| A03 | warning | at least one usable identifier (email or phone) - otherwise the person cannot be de-duplicated | 24 | 1.18 |
| A04 | warning | email, when given, is a real address (placeholders like 'na' count as missing) | 89 | 4.39 |
| A05 | warning | phone, when given, is a valid 10-digit Indian mobile number | 1 | 0.05 |
| A06 | warning | identifier is not a placeholder or a value shared by many different people | 3 | 0.15 |
| A07 | warning | referral: candidate phone is not the referrer's own phone | 19 | 0.94 |
| A08 | warning | a name is present (WhatsApp/email often have none; matching then relies on identifiers alone) | 185 | 9.12 |
| T03 | warning | Date Logged is not day/month ambiguous (read day-first, the sheet's convention) | 182 | 10.13 |
| T05 | warning | a row whose status says it was screened has a Screened On date | 66 | 3.67 |
| T06 | warning | Status is a known label with an agreed meaning | 213 | 11.85 |
| T07 | warning | Ref is not duplicated (the auto-import sometimes pastes a row twice) | 8 | 0.45 |
| T08 | warning | the row can be linked to an application in a source system | 39 | 2.17 |
