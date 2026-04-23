-- V26.4: create l3_features table for 24/25 golden stitching

CREATE TABLE IF NOT EXISTS l3_features (
    match_id VARCHAR(50) PRIMARY KEY REFERENCES matches(match_id) ON DELETE CASCADE,
    external_id VARCHAR(50),
    golden_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    tactical_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    odds_movement_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    odds_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    elo_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    rolling_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    efficiency_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    draw_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    market_sentiment JSONB NOT NULL DEFAULT '{}'::jsonb,
    stitch_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    computed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_l3_features_external_id
ON l3_features(external_id);

CREATE INDEX IF NOT EXISTS idx_l3_features_computed_at
ON l3_features(computed_at DESC);

CREATE INDEX IF NOT EXISTS idx_l3_features_tactical_gin
ON l3_features USING GIN(tactical_features);
