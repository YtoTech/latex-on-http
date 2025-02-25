-- +goose Up
-- TODO
CREATE TABLE jobs (
    id int NOT NULL,
    title text,
    body text,
    PRIMARY KEY(id)
);

-- +goose Down
DROP TABLE jobs;
