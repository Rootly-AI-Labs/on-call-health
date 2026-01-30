-- Add unique constraint to prevent duplicate survey periods for same user/org/date range on same day
-- This enables true idempotency using INSERT ... ON CONFLICT

-- First, remove any duplicates that might exist (keep the earliest one)
WITH duplicates AS (
    SELECT id, organization_id, user_correlation_id, period_start_date, period_end_date,
           DATE(initial_sent_at) as sent_date,
           ROW_NUMBER() OVER (
               PARTITION BY organization_id, user_correlation_id, period_start_date, period_end_date, DATE(initial_sent_at)
               ORDER BY initial_sent_at ASC, id ASC
           ) as rn
    FROM survey_periods
)
DELETE FROM survey_periods WHERE id IN (SELECT id FROM duplicates WHERE rn > 1);

-- Add unique constraint on natural key + sent date
-- This prevents multiple periods for same user/org/date range created on the same day
CREATE UNIQUE INDEX IF NOT EXISTS uq_survey_periods_daily_idempotency
ON survey_periods(organization_id, user_correlation_id, period_start_date, period_end_date, DATE(initial_sent_at));
