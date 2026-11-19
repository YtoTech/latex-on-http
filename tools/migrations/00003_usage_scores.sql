-- +goose Up
-- Per-request API usage scoring (see docs/usage-scoring.md).
ALTER TABLE jobs
    ADD COLUMN response_size BIGINT,
    ADD COLUMN usage_score_incoming NUMERIC(20,6),
    ADD COLUMN usage_score_fetch NUMERIC(20,6),
    ADD COLUMN usage_score_processing NUMERIC(20,6),
    ADD COLUMN usage_score_outgoing NUMERIC(20,6),
    ADD COLUMN usage_score_total NUMERIC(20,6);

-- +goose Down
ALTER TABLE jobs
    DROP COLUMN response_size,
    DROP COLUMN usage_score_incoming,
    DROP COLUMN usage_score_fetch,
    DROP COLUMN usage_score_processing,
    DROP COLUMN usage_score_outgoing,
    DROP COLUMN usage_score_total;
