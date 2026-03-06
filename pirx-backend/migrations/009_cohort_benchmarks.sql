CREATE TABLE IF NOT EXISTS cohort_benchmarks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event TEXT NOT NULL,
  percentile_10 FLOAT,
  percentile_25 FLOAT,
  percentile_50 FLOAT,
  percentile_75 FLOAT,
  percentile_90 FLOAT,
  sample_size INT DEFAULT 0,
  computed_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cohort_benchmarks_event ON cohort_benchmarks(event, computed_at DESC);
