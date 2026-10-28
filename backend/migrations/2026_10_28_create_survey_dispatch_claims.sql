-- One row per scheduled survey job occurrence, so an external trigger that
-- polls every minute runs each initial send, reminder and follow-up once.
CREATE TABLE IF NOT EXISTS survey_dispatch_claims (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    job_kind VARCHAR(20) NOT NULL,
    fire_time TIMESTAMPTZ NOT NULL,
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_survey_dispatch_claim
    ON survey_dispatch_claims(organization_id, job_kind, fire_time);

CREATE INDEX IF NOT EXISTS idx_survey_dispatch_claims_claimed_at
    ON survey_dispatch_claims(claimed_at);
