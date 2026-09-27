-- name: duplicate_screening
-- M1 (KPI) + M4. A screen is a duplicate when the same person (by :key) was already screened
-- within the previous :lookback days. key = candidate (resolved, conservative), upper (adds unconfirmed
-- nameless phone matches) or name (today's name-string matching).
WITH screens AS (
    SELECT e.event_date AS screened_on, e.row,
           CASE :key WHEN 'name' THEN a.name_key WHEN 'upper' THEN a.candidate_id_upper ELSE a.candidate_id END AS person
    FROM recruiter_event e JOIN application a USING (application_id)
    WHERE e.event_type = 'screened'
),
in_month AS (
    SELECT s.*, EXISTS (
        SELECT 1 FROM screens p
        WHERE p.person = s.person AND s.person IS NOT NULL
          AND (p.screened_on < s.screened_on OR (p.screened_on = s.screened_on AND p.row < s.row))
          AND p.screened_on >= date(s.screened_on, '-' || :lookback || ' days')
    ) AS is_duplicate
    FROM screens s
    WHERE s.screened_on BETWEEN :m_start AND :m_end
)
SELECT COUNT(*)                                   AS screens,
       COALESCE(SUM(is_duplicate), 0)             AS duplicate_screens,
       (SELECT COUNT(*) FROM application
        WHERE applied_date BETWEEN :m_start AND :m_end
          AND failure_reasons = '')               AS applications
FROM in_month;

-- name: cohort_follow_up
-- M2 + M3 for the cohort of applications received in the previous month (every one is >= 30 days old).
WITH cohort AS (
    SELECT a.application_id, a.candidate_id, a.applied_date, a.source
    FROM application a
    WHERE a.applied_date BETWEEN :c_start AND :c_end AND a.failure_reasons = ''
),
handling AS (
    SELECT c.application_id, c.candidate_id, c.applied_date,
           MIN(CASE WHEN e.event_type = 'logged'    THEN e.event_date END) AS logged_on,
           MIN(CASE WHEN e.event_type = 'screened'  THEN e.event_date END) AS screened_on,
           MIN(CASE WHEN e.event_type = 'contacted' THEN e.event_date END) AS contacted_on,
           MAX(CASE WHEN t.status = 'marked_duplicate' THEN 1 ELSE 0 END)  AS marked_duplicate
    FROM cohort c
    LEFT JOIN recruiter_event e USING (application_id)
    LEFT JOIN tracker_row t ON t.application_id = c.application_id AND t.in_scope = 1
    GROUP BY c.application_id
),
classified AS (
    SELECT h.*,
           -- a DUP mark only counts as "reviewed" if the same resolved person really was screened before
           EXISTS (SELECT 1 FROM recruiter_event e2 JOIN application a2 USING (application_id)
                   WHERE a2.candidate_id = h.candidate_id AND e2.event_type = 'screened'
                     AND e2.event_date <= h.applied_date) AS person_screened_before,
           julianday(h.screened_on)  - julianday(h.applied_date) AS days_to_screen,
           julianday(h.contacted_on) - julianday(h.applied_date) AS days_to_contact
    FROM handling h
)
SELECT application_id, applied_date, logged_on, screened_on, contacted_on, marked_duplicate,
       person_screened_before, days_to_screen, days_to_contact,
       CASE
         WHEN days_to_screen IS NOT NULL AND days_to_screen <= :unreviewed_days THEN 'screened_in_time'
         WHEN marked_duplicate = 1 AND person_screened_before = 1           THEN 'correctly_marked_duplicate'
         WHEN marked_duplicate = 1                                           THEN 'wrongly_marked_duplicate'
         WHEN logged_on IS NULL                                              THEN 'never_logged'
         ELSE 'logged_not_screened'
       END AS review_state
FROM classified
ORDER BY application_id;
