-- Warehouse schema: organised around the candidate workflow, not around the source systems.

CREATE TABLE candidate (
    candidate_id      TEXT PRIMARY KEY,        -- one resolved person
    first_applied_at  TEXT NOT NULL,
    applications      INTEGER NOT NULL,
    channels          TEXT NOT NULL,           -- e.g. "job_board,whatsapp"
    display_name      TEXT
);

CREATE TABLE application (
    application_id    TEXT PRIMARY KEY,        -- "<source>:<source record id>"
    candidate_id      TEXT NOT NULL REFERENCES candidate (candidate_id),
    candidate_id_upper TEXT NOT NULL,          -- same, but also accepting unconfirmed nameless phone matches (upper bound)
    source            TEXT NOT NULL,           -- job_board | careers | referral | whatsapp | email | walk_in | tracker_only
    source_record_id  TEXT NOT NULL,
    applied_at        TEXT NOT NULL,           -- IST
    applied_date      TEXT NOT NULL,
    name_raw          TEXT,
    first_name        TEXT,
    last_name         TEXT,
    email_norm        TEXT,
    phone_norm        TEXT,
    name_key          TEXT,                    -- "first last": what name-only matching would use
    match_reason      TEXT,                    -- strongest link that joined it to its candidate
    failure_reasons   TEXT,
    warning_reasons   TEXT
);

CREATE TABLE tracker_row (
    row               INTEGER PRIMARY KEY,     -- row number in the recruiter's sheet
    application_id    TEXT REFERENCES application (application_id),
    link_method       TEXT,                    -- ref | identity | name_in_window | tracker_only
    channel           TEXT,
    logged_on         TEXT,
    screened_on       TEXT,
    first_contact_on  TEXT,
    status_raw        TEXT,
    status            TEXT,                    -- canonical: new | rejected | shortlisted | ... | unclear
    counts_as_screen  INTEGER NOT NULL,        -- a CV screen we are willing to count (dated, in scope, not a double import)
    failure_reasons   TEXT,
    warning_reasons   TEXT,
    in_scope          INTEGER NOT NULL
);

CREATE TABLE recruiter_event (
    event_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id    TEXT NOT NULL REFERENCES application (application_id),
    row               INTEGER REFERENCES tracker_row (row),
    event_type        TEXT NOT NULL,           -- logged | screened | contacted
    event_date        TEXT NOT NULL
);

CREATE INDEX ix_application_candidate ON application (candidate_id);
CREATE INDEX ix_event_application ON recruiter_event (application_id, event_type);
