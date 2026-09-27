# Candidate pipeline evidence - 2026-02

**Run status:** degraded - history starts 2026-01-01: fewer than 90 days of look-back, so M1 is understated

> All client data in this project is simulated (see `docs/simulation.md`).

## Headline

- **Duplicate-screening rate (KPI): 4.7%** of 258 applications (12 repeat screens, ~2.0 recruiter-hours); up to 5.0% if every unconfirmed phone match is the same person.
- Name matching - the method behind the old 22% baseline - reports **14.7%** for the same month: it over-counts, because different people with common names collide.
- **4.2%** of last month's applications were marked DUP by name although the person had never been screened.
- Of last month's applications, **20.4%** were not screened within 30 days; 12.8 percentage points of that never reached the tracker at all.
- **79.6%** heard nothing within 30 days.

## Metrics

| id | metric | value | unit | numerator | denominator | basis |
|---|---|---|---|---|---|---|
| M1 | Duplicate-screening rate (KPI) | 4.7 | % of applications | 12 | 258 | CV screens in 2026-02 of a person already screened in the previous 90 days (resolved identity) |
| M1-upper | Duplicate-screening rate, upper bound | 5.0 | % of applications | 13 | 258 | also counts nameless phone matches still awaiting recruiter confirmation |
| M1-name | Duplicate-screening rate, name matching (old baseline method) | 14.7 | % of applications | 38 | 258 | same definition, but 'same person' = same first + last name string |
| M2 | Applications unreviewed after 30 days | 20.4 | % of cohort | 54 | 265 | applications received in 2026-01 not screened within 30 days |
| M2a |   of which never reached the tracker | 12.8 | % of cohort | 34 | 265 | arrived in a channel but no tracker row links to it |
| M2b |   of which wrongly marked DUP by name | 4.2 | % of cohort | 11 | 265 | marked DUP, but this person had never been screened |
| M3 | Median days to first response (contacted applicants) | 14.0 | days | <NA> | 54 | applications received in 2026-01 that were contacted within 30 days |
| M3a | No response within 30 days | 79.6 | % of cohort | 211 | 265 | includes every silent rejection - the recruiter never tells rejected applicants |
| M4 | Recruiter hours spent re-screening | 2.0 | hours | 12 | <NA> | duplicate screens x 10 min (Assignment 1 costing assumption) |
| M5 | Incorrect merges on recruiter-labelled pairs (guardrail) | 0.0 | pairs | 0 | 15 | target 0; recall 88.9% on the same sample |
| M5a | Possible matches awaiting recruiter confirmation | 0.0 | applications | 0 | <NA> | nameless records whose phone matches a named candidate - not merged automatically |

## How sensitive is the KPI to the 'duplicate' window?

A re-screen only counts as waste if the same person was screened recently. The window is a policy choice.

| lookback_days | duplicate_screens | applications | rate_pct |
|---|---|---|---|
| 30 | 2 | 258 | 0.8 |
| 90 | 12 | 258 | 4.7 |
| 180 | 12 | 258 | 4.7 |
| ever | 12 | 258 | 4.7 |

## Matching rule evidence (recruiter-labelled pairs)

| rule | pairs_evaluated | true_matches_found | false_merges | missed_matches | correctly_kept_apart | precision_pct | recall_pct |
|---|---|---|---|---|---|---|---|
| name_only | 15 | 5 | 5 | 4 | 1 | 50.0 | 55.6 |
| email_only | 15 | 6 | 0 | 3 | 6 | 100.0 | 66.7 |
| phone_only | 15 | 6 | 0 | 3 | 6 | 100.0 | 66.7 |
| email_or_phone | 15 | 9 | 0 | 0 | 6 | 100.0 | 100.0 |
| chosen_plus_unverified | 15 | 9 | 0 | 0 | 6 | 100.0 | 100.0 |
| chosen | 15 | 8 | 0 | 1 | 6 | 100.0 | 88.9 |

## Sources used

| source | status | evidence |
|---|---|---|
| job_board_api | ok | {"pages": 3, "records_received": 208, "overlap_duplicates_removed": 0, "unique_records": 208, "api_total": 208} |
| careers_db | ok | {"query_count": 91, "rows_returned": 91, "db_sha256": "8c54e12fa91a7565", "cutoff_utc": "2026-02-28 18:29:59"} |
| referral_form | ok | {"file_rows": 350, "unparseable_timestamps": 0, "rows_as_of": 72, "sha256": "4863649b223be23b"} |
| whatsapp_export | ok | {"messages_parsed": 252, "unparsed_lines": 0, "classified": {"application": 98, "follow_up_or_media": 89, "business_reply": 52, "not_hiring": 13}, "sha256": "1d |
| ops_head_mailbox | ok | {"messages_in_file": 427, "parse_failures": 0, "classified": {"application": 44, "internal_or_robot": 28, "other": 13}, "sha256": "8654797c5b1456d5"} |
| recruiter_tracker | ok | {"rows": 2548, "sha256": "61feb63eea11f3a3", "export_is_snapshot": true} |
| audit_sample | ok | {"pairs": 237, "sha256": "43c285e7562076cd"} |

## Data quality (flag, don't fix)

| rule | level | rule_text | rows_flagged | share_pct |
|---|---|---|---|---|
| A03 | warning | at least one usable identifier (email or phone) - otherwise the person cannot be de-duplicated | 7 | 1.36 |
| A04 | warning | email, when given, is a real address (placeholders like 'na' count as missing) | 29 | 5.65 |
| A06 | warning | identifier is not a placeholder or a value shared by many different people | 1 | 0.19 |
| A07 | warning | referral: candidate phone is not the referrer's own phone | 6 | 1.17 |
| A08 | warning | a name is present (WhatsApp/email often have none; matching then relies on identifiers alone) | 43 | 8.38 |
| T03 | warning | Date Logged is not day/month ambiguous (read day-first, the sheet's convention) | 52 | 11.63 |
| T05 | warning | a row whose status says it was screened has a Screened On date | 21 | 4.7 |
| T06 | warning | Status is a known label with an agreed meaning | 52 | 11.63 |
| T08 | warning | the row can be linked to an application in a source system | 10 | 2.24 |
