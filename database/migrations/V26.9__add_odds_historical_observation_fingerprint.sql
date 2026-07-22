-- lifecycle: permanent
-- M3-D4C additive contract repair. V26.8 is immutable after merge.
-- Existing deployments may contain rows, so null remains a fail-closed legacy state;
-- the D4C adapter requires a SHA-256 fingerprint for every new observation.

ALTER TABLE odds_historical_staging_observations
    ADD COLUMN IF NOT EXISTS business_fingerprint CHAR(64);

ALTER TABLE odds_historical_staging_observations
    ADD CONSTRAINT odds_historical_observation_fingerprint_format
    CHECK (business_fingerprint IS NULL OR business_fingerprint ~ '^[0-9a-f]{64}$');

COMMENT ON COLUMN odds_historical_staging_observations.business_fingerprint IS
'SHA-256 of the canonical observation; required by the D4C write adapter for identical-duplicate comparison.';
