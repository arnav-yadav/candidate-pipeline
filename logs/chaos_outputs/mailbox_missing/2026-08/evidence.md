# Candidate pipeline evidence - 2026-08

**Run status:** degraded - ops_head_mailbox unavailable: its channel is missing from every metric

> All client data in this project is simulated (see `docs/simulation.md`).

## Headline

- **Duplicate-screening rate (KPI): 13.1%** of 421 applications (55 repeat screens, ~9.2 recruiter-hours); up to 14.7% if every unconfirmed phone match is the same person.
- Name matching - the method behind the old 22% baseline - reports **29.0%** for the same month: it over-counts, because different people with common names collide.
- **13.6%** of last month's applications were marked DUP by name although the person had never been screened.
- Of last month's applications, **26.1%** were not screened within 30 days; 9.3 percentage points of that never reached the tracker at all.
- **82.1%** heard nothing within 30 days.

## Metrics

| id | metric | value | unit | numerator | denominator | basis |
|---|---|---|---|---|---|---|
| M1 | Duplicate-screening rate (KPI) | 13.1 | % of applications | 55 | 421 | CV screens in 2026-08 of a person already screened in the previous 90 days (resolved identity) |
| M1-upper | Duplicate-screening rate, upper bound | 14.7 | % of applications | 62 | 421 | also counts nameless phone matches still awaiting recruiter confirmation |
| M1-name | Duplicate-screening rate, name matching (old baseline method) | 29.0 | % of applications | 122 | 421 | same definition, but 'same person' = same first + last name string |
| M2 | Applications unreviewed after 30 days | 26.1 | % of cohort | 98 | 375 | applications received in 2026-07 not screened within 30 days |
| M2a |   of which never reached the tracker | 9.3 | % of cohort | 35 | 375 | arrived in a channel but no tracker row links to it |
| M2b |   of which wrongly marked DUP by name | 13.6 | % of cohort | 51 | 375 | marked DUP, but this person had never been screened |
| M3 | Median days to first response (contacted applicants) | 12.0 | days | <NA> | 67 | applications received in 2026-07 that were contacted within 30 days |
| M3a | No response within 30 days | 82.1 | % of cohort | 308 | 375 | includes every silent rejection - the recruiter never tells rejected applicants |
| M4 | Recruiter hours spent re-screening | 9.2 | hours | 55 | <NA> | duplicate screens x 10 min (Assignment 1 costing assumption) |
| M5 | Incorrect merges on recruiter-labelled pairs (guardrail) | 0.0 | pairs | 0 | 200 | target 0; recall 77.6% on the same sample |
| M5a | Possible matches awaiting recruiter confirmation | 15.0 | applications | 15 | <NA> | nameless records whose phone matches a named candidate - not merged automatically |

## How sensitive is the KPI to the 'duplicate' window?

A re-screen only counts as waste if the same person was screened recently. The window is a policy choice.

| lookback_days | duplicate_screens | applications | rate_pct |
|---|---|---|---|
| 30 | 2 | 421 | 0.5 |
| 90 | 55 | 421 | 13.1 |
| 180 | 66 | 421 | 15.7 |
| ever | 66 | 421 | 15.7 |

## Matching rule evidence (recruiter-labelled pairs)

| rule | pairs_evaluated | true_matches_found | false_merges | missed_matches | correctly_kept_apart | precision_pct | recall_pct |
|---|---|---|---|---|---|---|---|
| name_only | 200 | 108 | 33 | 44 | 15 | 76.6 | 71.1 |
| email_only | 200 | 86 | 0 | 66 | 48 | 100.0 | 56.6 |
| phone_only | 200 | 105 | 2 | 47 | 46 | 98.1 | 69.1 |
| email_or_phone | 200 | 144 | 2 | 8 | 46 | 98.6 | 94.7 |
| chosen_plus_unverified | 200 | 143 | 0 | 9 | 48 | 100.0 | 94.1 |
| chosen | 200 | 118 | 0 | 34 | 48 | 100.0 | 77.6 |

## Sources used

| source | status | evidence |
|---|---|---|
| job_board_api | ok | {"pages": 12, "records_received": 1134, "overlap_duplicates_removed": 1, "unique_records": 1133, "api_total": 1133} |
| careers_db | ok | {"query_count": 562, "rows_returned": 562, "db_sha256": "8c54e12fa91a7565", "cutoff_utc": "2026-08-31 18:29:59"} |
| referral_form | ok | {"file_rows": 350, "unparseable_timestamps": 0, "rows_as_of": 350, "sha256": "4863649b223be23b"} |
| whatsapp_export | ok | {"messages_parsed": 1295, "unparsed_lines": 0, "classified": {"application": 506, "follow_up_or_media": 492, "business_reply": 237, "not_hiring": 60}, "sha256": |
| ops_head_mailbox | unavailable | {"reason": "mailbox export not found"} |
| recruiter_tracker | ok | {"rows": 2548, "sha256": "61feb63eea11f3a3", "export_is_snapshot": true} |
| audit_sample | ok | {"pairs": 237, "sha256": "43c285e7562076cd"} |

## Data quality (flag, don't fix)

| rule | level | rule_text | rows_flagged | share_pct |
|---|---|---|---|---|
| A03 | warning | at least one usable identifier (email or phone) - otherwise the person cannot be de-duplicated | 28 | 1.1 |
| A04 | warning | email, when given, is a real address (placeholders like 'na' count as missing) | 118 | 4.63 |
| A05 | warning | phone, when given, is a valid 10-digit Indian mobile number | 2 | 0.08 |
| A06 | warning | identifier is not a placeholder or a value shared by many different people | 7 | 0.27 |
| A07 | warning | referral: candidate phone is not the referrer's own phone | 23 | 0.9 |
| A08 | warning | a name is present (WhatsApp/email often have none; matching then relies on identifiers alone) | 200 | 7.84 |
| T03 | warning | Date Logged is not day/month ambiguous (read day-first, the sheet's convention) | 249 | 9.88 |
| T05 | warning | a row whose status says it was screened has a Screened On date | 84 | 3.33 |
| T06 | warning | Status is a known label with an agreed meaning | 288 | 11.43 |
| T07 | warning | Ref is not duplicated (the auto-import sometimes pastes a row twice) | 12 | 0.48 |
| T08 | warning | the row can be linked to an application in a source system | 237 | 9.4 |
