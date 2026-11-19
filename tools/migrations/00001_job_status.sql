-- +goose Up
CREATE TABLE user_agents (
    id INT GENERATED ALWAYS AS IDENTITY,
    user_agent TEXT NOT NULL,
    PRIMARY KEY(id),
    UNIQUE(user_agent)
);
CREATE TABLE jobs (
    id UUID NOT NULL,
    -- received, fetching, compiling, completed, errored
    job_status VARCHAR(25) NOT NULL,
    error_code VARCHAR(100),
    compiler VARCHAR(20) NOT NULL,
    compilation_hash VARCHAR(64),
    input_spec_mode VARCHAR(25) NOT NULL,
    http_payload_size BIGINT NOT NULL,
    cleaned_payload jsonb NOT NULL,
    remote_ip VARCHAR(40),
    forwarded_remote_ip TEXT,
    user_agent_id INT,
    fetched_resources_count INTEGER,
    fetched_resources_size BIGINT,
    fetched_resources_cache_hits INTEGER,
    fetched_resources_cache_hits_size BIGINT,
    output_type VARCHAR(10),
    output_size BIGINT,
    received_at TIMESTAMPTZ NOT NULL,
    started_fetch_at TIMESTAMPTZ,
    ended_fetch_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ,
    started_compiling_at TIMESTAMPTZ,
    ended_compiling_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    PRIMARY KEY(id),
    CONSTRAINT fk_user_agent
      FOREIGN KEY(user_agent_id)
        REFERENCES user_agents(id)
);

-- +goose Down
DROP TABLE jobs;
DROP TABLE user_agents;
