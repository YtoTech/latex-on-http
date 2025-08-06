-- +goose Up
CREATE TABLE user_agents (
    id INT GENERATED ALWAYS AS IDENTITY,
    user_agent VARCHAR(255),
    PRIMARY KEY(id),
    UNIQUE(user_agent)
)
CREATE TABLE jobs (
    id UUID NOT NULL,
    -- received, fetching, compiling, completed, errored
    job_status VARCHAR(25) NOT NULL,
    error_code VARCHAR(100),
    compiler VARCHAR(20) NOT NULL,
    compilation_hash VARCHAR(64) NOT NULL,
    input_spec_mode VARCHAR(25) NOT NULL,
    http_payload_size SMALLINT NOT NULL,
    cleaned_payload jsonb NOT NULL,
    remote_ip VARCHAR(40) NOT NULL,
    forwarded_remote_ip VARCHAR(40),
    user_agent_id INT NOT NULL,
    fetched_resources_count SMALLINT,
    fetched_resources_size SMALLINT,
    fetched_resources_cache_hits SMALLINT,
    fetched_resources_cache_hits_size SMALLINT,
    output_type VARCHAR(10),
    output_size SMALLINT,
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
