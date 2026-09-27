# Profiling and validation

> All client data is simulated ([simulation.md](simulation.md)).

## Principle: flag, don't fix

Nothing is deleted or silently corrected. Every application and every tracker row gets:

- `failure_reasons`: the **critical** rules it fails. The row can't be used for metrics.
- `warning_reasons`: the **warning** rules it trips. The row is used, with a known limitation.

Each month writes `output/<month>/quality_report.csv` with the count for every rule, including rules that flagged
nothing. If more than **5%** of a source's rows fail a critical rule, the month halts: at that point something
upstream is broken and the metrics would mislead.

Values are **normalised into new columns** (`email_norm`, `phone_norm`, `status`); the raw values stay next to them
(`name_raw`, `status_raw`) so every decision can be audited.

## What profiling found first

The rules were written after profiling the sources in
[`notebooks/01_profiling.ipynb`](../notebooks/01_profiling.ipynb). The main findings:

- **No identifier is present in every channel.** WhatsApp has a phone but rarely an email; the job boards have an
  email but a phone only two-thirds of the time.
- **The same identifier is written many ways**: `+91 98765 43210`, `098765…`, `987 654 3210`; `Sharma, Rahul` and
  `RAHUL SHARMA`. That's representation, and it's safe to normalise.
- **Common names are shared by different people.** A name is not an identifier.
- **Some values look like identifiers but aren't**: placeholder emails (`na`, `-`), dummy phones (`9999999999`), and
  referrers' own phone numbers typed in as the candidate's.
- **The tracker is hand-typed**: dates in several formats, some day/month-ambiguous; statuses such as `NS` and
  `On hold` with no agreed meaning.
- **Not every application reaches the tracker.** The auto-imported channels always do; the hand-logged ones often
  don't.

## Rules

Counts are from the run as of **31 August 2026** (2,838 source applications, 2,520 tracker rows).

| ID | Level | Business rule | Why it matters | Flagged |
|---|---|---|---|---:|
| A01 | critical | Source record ID is unique within its source (later copies flagged) | A duplicated record would count one application twice | 0 |
| A02 | critical | Application time exists and lies between the posting opening and the run cut-off | A future-dated or undated application can't be placed in a month | 0 |
| A03 | warning | At least one usable identifier (email or phone) | Otherwise the person can't be de-duplicated at all | 28 (1.0%) |
| A04 | warning | An email, when given, is a real address (placeholders count as missing) | `na` must never link two strangers | 118 (4.2%) |
| A05 | warning | A phone, when given, is a valid 10-digit Indian mobile number | An invalid number is missing, not guessed | 2 (0.1%) |
| A06 | warning | The identifier isn't a placeholder or a value shared by many different people | A shared value would merge strangers | 7 (0.2%) |
| A07 | warning | Referral: the candidate's phone isn't the referrer's own | The referrer's number would link every person they referred | 23 (0.8%) |
| A08 | warning | A name is present | Without a name, phone matches go to the review queue instead of merging | 273 (9.6%) |
| T02 | critical | `Date Logged` can be read as a date | An undated screen can't be placed in a month | 0 |
| T03 | warning | `Date Logged` is not day/month ambiguous (read day-first, the sheet's convention) | `03/04/2026` is either 3 April or 4 March | 249 (9.9%) |
| T04 | warning | `Screened On` is not earlier than `Date Logged` | A screen before logging means one of the dates is wrong | 0 |
| T05 | warning | A row whose status says it was screened has a `Screened On` date | Without a date it can't be counted as a screen in any month | 84 (3.3%) |
| T06 | warning | `Status` is a known label with an agreed meaning | `NS` could mean "not suitable" or "no-show": kept as `unclear` | 288 (11.4%) |
| T07 | warning | `Ref` is not duplicated | The auto-import sometimes pastes a row twice; the copy isn't a second screen | 12 (0.5%) |
| T08 | warning | The row can be linked to an application in a source system | Unlinkable rows (mostly walk-ins) become applications of their own | 49 (1.9%) |

### How statuses are mapped

The recruiter's free-text statuses are mapped to a small canonical set, and anything without an agreed meaning is
kept as `unclear`, not guessed. For example, `Rejected`, `rejected`, `Rejected ` and `Not suitable` → `rejected`;
`DUP`, `dup` and `Duplicate` → `marked_duplicate`; `CV OK`, `Screened - OK` and `Phone screen done` → `shortlisted`;
`NS` and `On hold` → `unclear`. A row counts as a CV screen only if it has a `Screened On` date, is in scope, and is
not a double import.

## Rules as they apply to each month

Every monthly run is **point-in-time**: a run "as of" 31 March only sees records that existed by then, including
tracker dates. So a backfill reproduces what the client could have known each month, not what is known today.
