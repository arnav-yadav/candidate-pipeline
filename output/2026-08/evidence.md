# Candidate pipeline evidence - 2026-08

**Run status:** success

> All client data in this project is simulated (see `docs/simulation.md`).

## Headline

- **Duplicate-screening rate (KPI): 13.0%** of 431 applications (56 repeat screens, ~9.3 recruiter-hours); up to 14.6% if every unconfirmed phone match is the same person.
- Name matching - the method behind the old 22% baseline - reports **27.6%** for the same month: it over-counts, because different people with common names collide.
- **13.1%** of last month's applications were marked DUP by name although the person had never been screened.
- Of last month's applications, **28.3%** were not screened within 30 days; 12.1 percentage points of that never reached the tracker at all.
- **83.0%** heard nothing within 30 days.

## Metrics

| id | metric | value | unit | numerator | denominator | basis |
|---|---|---|---|---|---|---|
| M1 | Duplicate-screening rate (KPI) | 13.0 | % of applications | 56 | 431 | CV screens in 2026-08 of a person already screened in the previous 90 days (resolved identity) |
| M1-upper | Duplicate-screening rate, upper bound | 14.6 | % of applications | 63 | 431 | also counts nameless phone matches still awaiting recruiter confirmation |
| M1-name | Duplicate-screening rate, name matching (old baseline method) | 27.6 | % of applications | 119 | 431 | same definition, but 'same person' = same first + last name string |
| M2 | Applications unreviewed after 30 days | 28.3 | % of cohort | 110 | 389 | applications received in 2026-07 not screened within 30 days |
| M2a |   of which never reached the tracker | 12.1 | % of cohort | 47 | 389 | arrived in a channel but no tracker row links to it |
| M2b |   of which wrongly marked DUP by name | 13.1 | % of cohort | 51 | 389 | marked DUP, but this person had never been screened |
| M3 | Median days to first response (contacted applicants) | 12.0 | days | <NA> | 66 | applications received in 2026-07 that were contacted within 30 days |
| M3a | No response within 30 days | 83.0 | % of cohort | 323 | 389 | includes every silent rejection - the recruiter never tells rejected applicants |
| M4 | Recruiter hours spent re-screening | 9.3 | hours | 56 | <NA> | duplicate screens x 10 min (Assignment 1 costing assumption) |
| M5 | Incorrect merges on recruiter-labelled pairs (guardrail) | 0.0 | pairs | 0 | 237 | target 0; recall 79.3% on the same sample |
| M5a | Possible matches awaiting recruiter confirmation | 16.0 | applications | 16 | <NA> | nameless records whose phone matches a named candidate - not merged automatically |

## How sensitive is the KPI to the 'duplicate' window?

A re-screen only counts as waste if the same person was screened recently. The window is a policy choice.

| lookback_days | duplicate_screens | applications | rate_pct |
|---|---|---|---|
| 30 | 2 | 431 | 0.5 |
| 90 | 56 | 431 | 13.0 |
| 180 | 67 | 431 | 15.5 |
| ever | 67 | 431 | 15.5 |

## Matching rule evidence (recruiter-labelled pairs)

| rule | pairs_evaluated | true_matches_found | false_merges | missed_matches | correctly_kept_apart | precision_pct | recall_pct |
|---|---|---|---|---|---|---|---|
| name_only | 237 | 117 | 36 | 62 | 22 | 76.5 | 65.4 |
| email_only | 237 | 107 | 0 | 72 | 58 | 100.0 | 59.8 |
| phone_only | 237 | 112 | 2 | 67 | 56 | 98.2 | 62.6 |
| email_or_phone | 237 | 168 | 2 | 11 | 56 | 98.8 | 93.9 |
| chosen_plus_unverified | 237 | 166 | 0 | 13 | 58 | 100.0 | 92.7 |
| chosen | 237 | 142 | 0 | 37 | 58 | 100.0 | 79.3 |

## Sources used

| source | status | evidence |
|---|---|---|
| job_board_api | ok | {"pages": 12, "records_received": 1134, "overlap_duplicates_removed": 1, "unique_records": 1133, "api_total": 1133} |
| careers_db | ok | {"query_count": 562, "rows_returned": 562, "db_sha256": "8c54e12fa91a7565", "cutoff_utc": "2026-08-31 18:29:59"} |
| referral_form | ok | {"file_rows": 350, "unparseable_timestamps": 0, "rows_as_of": 350, "sha256": "4863649b223be23b"} |
| whatsapp_export | ok | {"messages_parsed": 1295, "unparsed_lines": 0, "classified": {"application": 506, "follow_up_or_media": 492, "business_reply": 237, "not_hiring": 60}, "sha256": |
| ops_head_mailbox | ok | {"messages_in_file": 427, "parse_failures": 0, "classified": {"application": 287, "internal_or_robot": 108, "other": 32}, "sha256": "8654797c5b1456d5"} |
| recruiter_tracker | ok | {"rows": 2548, "sha256": "61feb63eea11f3a3", "export_is_snapshot": true} |
| audit_sample | ok | {"pairs": 237, "sha256": "43c285e7562076cd"} |

## Data quality (flag, don't fix)

| rule | level | rule_text | rows_flagged | share_pct |
|---|---|---|---|---|
| A03 | warning | at least one usable identifier (email or phone) - otherwise the person cannot be de-duplicated | 28 | 0.99 |
| A04 | warning | email, when given, is a real address (placeholders like 'na' count as missing) | 118 | 4.16 |
| A05 | warning | phone, when given, is a valid 10-digit Indian mobile number | 2 | 0.07 |
| A06 | warning | identifier is not a placeholder or a value shared by many different people | 7 | 0.25 |
| A07 | warning | referral: candidate phone is not the referrer's own phone | 23 | 0.81 |
| A08 | warning | a name is present (WhatsApp/email often have none; matching then relies on identifiers alone) | 273 | 9.62 |
| T03 | warning | Date Logged is not day/month ambiguous (read day-first, the sheet's convention) | 249 | 9.88 |
| T05 | warning | a row whose status says it was screened has a Screened On date | 84 | 3.33 |
| T06 | warning | Status is a known label with an agreed meaning | 288 | 11.43 |
| T07 | warning | Ref is not duplicated (the auto-import sometimes pastes a row twice) | 12 | 0.48 |
| T08 | warning | the row can be linked to an application in a source system | 49 | 1.94 |
