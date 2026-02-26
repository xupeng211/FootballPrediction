-- V41.390: Add golden_features column to matches table
-- This column stores the extracted golden features (market value, injury, rating)

ALTER TABLE matches 
ADD COLUMN IF NOT EXISTS golden_features JSONB;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_matches_golden_features 
ON matches USING GIN (golden_features);

-- Add comment
COMMENT ON COLUMN matches.golden_features IS 'V41.390 Golden Features: market value, injury, rating data extracted from L2 lineup information';
