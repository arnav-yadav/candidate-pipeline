# Candidate pipeline evidence - 2026-03

**Run status:** degraded - history starts 2026-01-01: fewer than 90 days of look-back, so M1 is understated

> All client data in this project is simulated (see `docs/simulation.md`).

## Headline

- **Duplicate-screening rate (KPI): 12.6%** of 380 applications (48 repeat screens, ~8.0 recruiter-hours); up to 13.7% if every unconfirmed phone match is the same person.
- Name matching - the method behind the old 22% baseline - reports **26.3%** for the same month: it over-counts, because different people with common names collide.
- **5.8%** of last month's applications were marked DUP by name although the person had never been screened.
- Of last month's applications, **20.9%** were not screened within 30 days; 10.1 percentage points of that never reached the tracker at all.
- **74.4%** heard nothing within 30 days.

## Metrics

| id | metric | value | unit | numerator | denominator | basis |
|---|---|---|---|---|---|---|
| M1 | Duplicate-screening rate (KPI) | 12.6 | % of applications | 48 | 380 | CV screens in 2026-03 of a person already screened in the previous 90 days (resolved identity) |
| M1-upper | Duplicate-screening rate, upper bound | 13.7 | % of applications | 52 | 380 | also counts nameless phone matches still awaiting recruiter confirmation |
| M1-name | Duplicate-screening rate, name matching (old baseline method) | 26.3 | % of applications | 100 | 380 | same definition, but 'same person' = same first + last name string |
| M2 | Applications unreviewed after 30 days | 20.9 | % of cohort | 54 | 258 | applications received in 2026-02 not screened within 30 days |
| M2a |   of which never reached the tracker | 10.1 | % of cohort | 26 | 258 | arrived in a channel but no tracker row links to it |
| M2b |   of which wrongly marked DUP by name | 5.8 | % of cohort | 15 | 258 | marked DUP, but this person had never been screened |
| M3 | Median days to first response (contacted applicants) | 12.0 | days | <NA> | 66 | applications received in 2026-02 that were contacted within 30 days |
| M3a | No response within 30 days | 74.4 | % of cohort | 192 | 258 | includes every silent rejection - the recruiter never tells rejected applicants |
| M4 | Recruiter hours spent re-screening | 8.0 | hours | 48 | <NA> | duplicate screens x 10 min (Assignment 1 costing assumption) |
| M5 | Incorrect merges on recruiter-labelled pairs (guardrail) | 0.0 | pairs | 0 | 38 | target 0; recall 75.0% on the same sample |
| M5a | Possible matches awaiting recruiter confirmation | 5.0 | applications | 5 | <NA> | nameless records whose phone matches a named candidate - not merged automatically |

## How sensitive is the KPI to the 'duplicate' window?

A re-screen only counts as waste if the same person was screened recently. The window is a policy choice.

| lookback_days | duplicate_screens | applications | rate_pct |
|---|---|---|---|
| 30 | 5 | 380 | 1.3 |
| 90 | 48 | 380 | 12.6 |
| 180 | 48 | 380 | 12.6 |
| ever | 48 | 380 | 12.6 |

## Matching rule evidence (recruiter-labelled pairs)

| rule | pairs_evaluated | true_matches_found | false_merges | missed_matches | correctly_kept_apart | precision_pct | recall_pct |
|---|---|---|---|---|---|---|---|
| name_only | 38 | 13 | 7 | 15 | 3 | 65.0 | 46.4 |
| email_only | 38 | 16 | 0 | 12 | 10 | 100.0 | 57.1 |
| phone_only | 38 | 20 | 0 | 8 | 10 | 100.0 | 71.4 |
| email_or_phone | 38 | 27 | 0 | 1 | 10 | 100.0 | 96.4 |
| chosen_plus_unverified | 38 | 27 | 0 | 1 | 10 | 100.0 | 96.4 |
| chosen | 38 | 21 | 0 | 7 | 10 | 100.0 | 75.0 |

## Sources used

| source | status | evidence |
|---|---|---|
| job_board_api | ok | {"pages": 4, "records_received": 371, "overlap_duplicates_removed": 1, "unique_records": 370, "api_total": 370} |
| careers_db | ok | {"query_count": 154, "rows_returned": 154, "db_sha256": "8c54e12fa91a7565", "cutoff_utc": "2026-03-31 18:29:59"} |
| referral_form | ok | {"file_rows": 350, "unparseable_timestamps": 0, "rows_as_of": 120, "sha256": "4863649b223be23b"} |
| whatsapp_export | ok | {"messages_parsed": 406, "unparsed_lines": 0, "classified": {"application": 161, "follow_up_or_media": 151, "business_reply": 75, "not_hiring": 19}, "sha256": " |
| ops_head_mailbox | ok | {"messages_in_file": 427, "parse_failures": 0, "classified": {"application": 79, "internal_or_robot": 41, "other": 15}, "sha256": "8654797c5b1456d5"} |
| recruiter_tracker | ok | {"rows": 2548, "sha256": "61feb63eea11f3a3", "export_is_snapshot": true} |
| audit_sample | ok | {"pairs": 237, "sha256": "43c285e7562076cd"} |

## Data quality (flag, don't fix)

| rule | level | rule_text | rows_flagged | share_pct |
|---|---|---|---|---|
| A03 | warning | at least one usable identifier (email or phone) - otherwise the person cannot be de-duplicated | 11 | 1.24 |
| A04 | warning | email, when given, is a real address (placeholders like 'na' count as missing) | 47 | 5.32 |
| A06 | warning | identifier is not a placeholder or a value shared by many different people | 1 | 0.11 |
| A07 | warning | referral: candidate phone is not the referrer's own phone | 6 | 0.68 |
| A08 | warning | a name is present (WhatsApp/email often have none; matching then relies on identifiers alone) | 74 | 8.37 |
| T03 | warning | Date Logged is not day/month ambiguous (read day-first, the sheet's convention) | 77 | 9.9 |
| T05 | warning | a row whose status says it was screened has a Screened On date | 34 | 4.37 |
| T06 | warning | Status is a known label with an agreed meaning | 89 | 11.44 |
| T07 | warning | Ref is not duplicated (the auto-import sometimes pastes a row twice) | 2 | 0.26 |
| T08 | warning | the row can be linked to an application in a source system | 19 | 2.44 |
