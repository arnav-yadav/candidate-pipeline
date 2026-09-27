# Candidate pipeline evidence - 2026-05

**Run status:** success

> All client data in this project is simulated (see `docs/simulation.md`).

## Headline

- **Duplicate-screening rate (KPI): 13.0%** of 399 applications (52 repeat screens, ~8.7 recruiter-hours); up to 13.8% if every unconfirmed phone match is the same person.
- Name matching - the method behind the old 22% baseline - reports **24.6%** for the same month: it over-counts, because different people with common names collide.
- **11.0%** of last month's applications were marked DUP by name although the person had never been screened.
- Of last month's applications, **27.4%** were not screened within 30 days; 12.5 percentage points of that never reached the tracker at all.
- **80.4%** heard nothing within 30 days.

## Metrics

| id | metric | value | unit | numerator | denominator | basis |
|---|---|---|---|---|---|---|
| M1 | Duplicate-screening rate (KPI) | 13.0 | % of applications | 52 | 399 | CV screens in 2026-05 of a person already screened in the previous 90 days (resolved identity) |
| M1-upper | Duplicate-screening rate, upper bound | 13.8 | % of applications | 55 | 399 | also counts nameless phone matches still awaiting recruiter confirmation |
| M1-name | Duplicate-screening rate, name matching (old baseline method) | 24.6 | % of applications | 98 | 399 | same definition, but 'same person' = same first + last name string |
| M2 | Applications unreviewed after 30 days | 27.4 | % of cohort | 105 | 383 | applications received in 2026-04 not screened within 30 days |
| M2a |   of which never reached the tracker | 12.5 | % of cohort | 48 | 383 | arrived in a channel but no tracker row links to it |
| M2b |   of which wrongly marked DUP by name | 11.0 | % of cohort | 42 | 383 | marked DUP, but this person had never been screened |
| M3 | Median days to first response (contacted applicants) | 12.0 | days | <NA> | 75 | applications received in 2026-04 that were contacted within 30 days |
| M3a | No response within 30 days | 80.4 | % of cohort | 308 | 383 | includes every silent rejection - the recruiter never tells rejected applicants |
| M4 | Recruiter hours spent re-screening | 8.7 | hours | 52 | <NA> | duplicate screens x 10 min (Assignment 1 costing assumption) |
| M5 | Incorrect merges on recruiter-labelled pairs (guardrail) | 0.0 | pairs | 0 | 95 | target 0; recall 74.7% on the same sample |
| M5a | Applications awaiting recruiter confirmation | 8.0 | applications | 8 | <NA> | nameless records whose phone matches a named candidate - not merged automatically |

## How sensitive is the KPI to the 'duplicate' window?

A re-screen only counts as waste if the same person was screened recently. The window is a policy choice.

| lookback_days | duplicate_screens | applications | rate_pct |
|---|---|---|---|
| 30 | 4 | 399 | 1.0 |
| 90 | 52 | 399 | 13.0 |
| 180 | 56 | 399 | 14.0 |
| ever | 56 | 399 | 14.0 |

## Matching rule evidence (recruiter-labelled pairs)

| rule | pairs_evaluated | true_matches_found | false_merges | missed_matches | correctly_kept_apart | precision_pct | recall_pct |
|---|---|---|---|---|---|---|---|
| name_only | 95 | 45 | 15 | 30 | 5 | 75.0 | 60.0 |
| email_only | 95 | 40 | 0 | 35 | 20 | 100.0 | 53.3 |
| phone_only | 95 | 50 | 1 | 25 | 19 | 98.0 | 66.7 |
| email_or_phone | 95 | 70 | 1 | 5 | 19 | 98.6 | 93.3 |
| chosen_plus_unverified | 95 | 70 | 0 | 5 | 20 | 100.0 | 93.3 |
| chosen | 95 | 56 | 0 | 19 | 20 | 100.0 | 74.7 |

## Sources used

| source | status | evidence |
|---|---|---|
| job_board_api | ok | {"pages": 7, "records_received": 664, "overlap_duplicates_removed": 1, "unique_records": 663, "api_total": 663} |
| careers_db | ok | {"query_count": 321, "rows_returned": 321, "db_sha256": "8c54e12fa91a7565", "cutoff_utc": "2026-05-31 18:29:59"} |
| referral_form | ok | {"file_rows": 350, "unparseable_timestamps": 0, "rows_as_of": 209, "sha256": "4863649b223be23b"} |
| whatsapp_export | ok | {"messages_parsed": 737, "unparsed_lines": 0, "classified": {"application": 294, "follow_up_or_media": 278, "business_reply": 130, "not_hiring": 35}, "sha256":  |
| ops_head_mailbox | ok | {"messages_in_file": 427, "parse_failures": 0, "classified": {"application": 166, "internal_or_robot": 69, "other": 20}, "sha256": "8654797c5b1456d5"} |
| recruiter_tracker | ok | {"rows": 2548, "sha256": "61feb63eea11f3a3", "export_is_snapshot": true} |
| audit_sample | ok | {"pairs": 237, "sha256": "43c285e7562076cd"} |

## Data quality (flag, don't fix)

| rule | level | rule_text | rows_flagged | share_pct |
|---|---|---|---|---|
| A03 | warning | at least one usable identifier (email or phone) - otherwise the person cannot be de-duplicated | 18 | 1.09 |
| A04 | warning | email, when given, is a real address (placeholders like 'na' count as missing) | 70 | 4.23 |
| A05 | warning | phone, when given, is a valid 10-digit Indian mobile number | 1 | 0.06 |
| A06 | warning | identifier is not a placeholder or a value shared by many different people | 2 | 0.12 |
| A07 | warning | referral: candidate phone is not the referrer's own phone | 14 | 0.85 |
| A08 | warning | a name is present (WhatsApp/email often have none; matching then relies on identifiers alone) | 148 | 8.95 |
| T03 | warning | Date Logged is not day/month ambiguous (read day-first, the sheet's convention) | 146 | 10.02 |
| T05 | warning | a row whose status says it was screened has a Screened On date | 57 | 3.91 |
| T06 | warning | Status is a known label with an agreed meaning | 169 | 11.6 |
| T07 | warning | Ref is not duplicated (the auto-import sometimes pastes a row twice) | 5 | 0.34 |
| T08 | warning | the row can be linked to an application in a source system | 32 | 2.2 |
