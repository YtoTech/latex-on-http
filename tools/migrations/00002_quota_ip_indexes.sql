-- +goose Up
-- Indexes for client-IP / period lookups on the durable jobs record
-- (quota analytics, abuse post-mortems, limit tuning).
CREATE INDEX IF NOT EXISTS jobs_remote_ip_received_at_idx
    ON jobs (remote_ip, received_at DESC);
CREATE INDEX IF NOT EXISTS jobs_forwarded_remote_ip_received_at_idx
    ON jobs (forwarded_remote_ip, received_at DESC);
CREATE INDEX IF NOT EXISTS jobs_received_at_idx
    ON jobs (received_at);

-- +goose Down
DROP INDEX IF EXISTS jobs_received_at_idx;
DROP INDEX IF EXISTS jobs_forwarded_remote_ip_received_at_idx;
DROP INDEX IF EXISTS jobs_remote_ip_received_at_idx;
