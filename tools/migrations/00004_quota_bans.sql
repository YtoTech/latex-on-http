-- +goose Up
-- Durable record of quota ban decisions (abuse post-mortems, limit tuning).
-- Ban state changes only: arming and escalation. Denied requests and
-- re-arms stay out of the database on purpose (denials must stay cheap).
CREATE TABLE quota_bans (
    id UUID NOT NULL,
    client_ip TEXT NOT NULL,
    -- short / long
    level VARCHAR(5) NOT NULL,
    -- violation_window (armed from the escalation ladder) /
    -- ban_escalation (escalated while a ban was already active)
    source VARCHAR(25) NOT NULL,
    -- The breached window when armed from a denial; NULL on escalation.
    trigger_period VARCHAR(10),
    -- The escalation counters snapshot at arming.
    violations_short INTEGER,
    violations_long INTEGER,
    bans_24h INTEGER,
    armed_at TIMESTAMPTZ NOT NULL,
    -- The initial expiry; re-arms extend the real ban beyond this value.
    expires_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY(id)
);
CREATE INDEX IF NOT EXISTS quota_bans_client_ip_armed_at_idx
    ON quota_bans (client_ip, armed_at DESC);
CREATE INDEX IF NOT EXISTS quota_bans_armed_at_idx
    ON quota_bans (armed_at);

-- +goose Down
DROP TABLE quota_bans;
