# API usage scoring

Every compilation request gets a **usage score**: a single number — usage
tokens — measuring what the request actually consumed, over four
categories: incoming data, resource fetching (discounted by the input
cache), processing time and outgoing data. The score is computed per
request in a dedicated module (`latexonhttp/usage.hy`), persisted with the
job metadata in PostgreSQL, and will later calibrate limits: a token
budget per window for the public API (instead of today's request counts),
then quotas for authenticated users and subscription plans.

Scoring only **measures**. Limiting stays with the quota layer (see
[Rate limiting and quotas](rate-limiting-and-quotas.md)); switching its
windows from request counts to token budgets is a later, small step — the
score is a plain number, ready to be incremented into the existing Valkey
windows.

## The token

1 token = 1 KiB of data transferred, or 1 second of server occupancy —
before weighting.

| Category | Measured as | Weight (default) | Environment |
|---|---|---|---|
| incoming | HTTP payload size (buffered before parsing: exact bytes, multipart framing included) | 1.0 | `USAGE_WEIGHT_INCOMING` |
| fetch | resource bytes fetched, cache hits discounted | 1.0 | `USAGE_WEIGHT_FETCH` |
| — cache hits | bytes served from the input cache | 0 (free) | `USAGE_WEIGHT_CACHE` |
| processing | wall-clock seconds, received → replied | 1.0 | `USAGE_WEIGHT_PROCESSING` |
| outgoing | response body size (PDF, or the error JSON with its logs) | 1.0 | `USAGE_WEIGHT_OUTGOING` |

```
incoming    = payload_size / 1024 × USAGE_WEIGHT_INCOMING
fetch       = (network_fetched_bytes + USAGE_WEIGHT_CACHE × cache_hit_bytes)
              / 1024 × USAGE_WEIGHT_FETCH
processing  = (replied_at − received_at) × USAGE_WEIGHT_PROCESSING
outgoing    = response_body_size / 1024 × USAGE_WEIGHT_OUTGOING
total       = incoming + fetch + processing + outgoing
```

Design decisions:

- **Cache hits are free** (`USAGE_WEIGHT_CACHE=0`): only bytes the service
  had to fetch are charged. Raw cache-hit sizes remain recorded, so the
  policy can be revisited without touching history.
- **Processing = received → replied**: the full server occupancy of the
  request (parse, fetch, compile, response build). It is always
  computable — including for requests failing mid-flight — and the
  per-phase timestamps stay recorded for finer breakdowns.
- **Components are rounded** to 6 decimals, and the total is the sum of
  the rounded components: the stored line always adds up.
- **Raw measures are persisted** with the scores, so weights can be
  recalibrated from production history at any time; the stored score is
  the calibration snapshot of the day.

## Scope

- **Scored**: every request that reaches job tracking — i.e. passes
  payload validation. Successes, compilation errors, fetch failures and
  500s alike: each reply closes its record.
- **Not scored**: requests rejected before job creation (HTTP 400
  validation errors, 429 quota denials). They leave no job row; the
  quota violations already track the abusive ones.
- **Internal only**: the score is not exposed to the client for now —
  the meaning of the numbers will move during calibration. Exposure
  (response headers, usage pages) will come with the limits and users.

## Where it is measured

`latexonhttp/usage.hy` owns the model: the weights (read once at import,
like the other application modules), the usage record opened at
admission (`received_at` + payload size), and the pure scoring of the
closed record.

The API module (`latexonhttp/api/builds.py`) wires it at two points:

- at admission, right after the request body is buffered:
  `new_usage(received_at, http_payload_size)`;
- at reply time, in the after-request hook that already closes the job
  record: it measures the response body, computes the score and adds it
  to the same single job update. No extra database round trip; a
  scoring failure is logged and never replaces the compilation
  response.

## Persistence

Migration `tools/migrations/00003_usage_scores.sql` extends the durable
`jobs` row:

| Column | Content |
|---|---|
| `response_size` | outgoing bytes, any response type |
| `usage_score_incoming` | incoming tokens |
| `usage_score_fetch` | fetch tokens |
| `usage_score_processing` | processing tokens |
| `usage_score_outgoing` | outgoing tokens |
| `usage_score_total` | sum of the components |

`NUMERIC(20,6)`, nullable (rows interrupted by a crash simply stay
unscored). The rate-limiting migration already indexed
`(remote_ip, received_at)` and `(forwarded_remote_ip, received_at)`, so
per-client usage aggregation is ready:

```sql
-- Tokens consumed per client IP over the last day.
SELECT forwarded_remote_ip,
       SUM(usage_score_total) AS tokens,
       COUNT(*) AS requests
FROM jobs
WHERE received_at >= NOW() - INTERVAL '1 day'
GROUP BY forwarded_remote_ip
ORDER BY tokens DESC;

-- Which category weighs most over the last week (weight calibration).
SELECT SUM(usage_score_incoming) AS incoming,
       SUM(usage_score_fetch) AS fetch,
       SUM(usage_score_processing) AS processing,
       SUM(usage_score_outgoing) AS outgoing
FROM jobs
WHERE received_at >= NOW() - INTERVAL '7 days';
```

## Implementation plan

1. `latexonhttp/usage.hy`: weights, usage record, pure scoring.
2. Migration `00003_usage_scores.sql` + the `jobs` repository column
   whitelist.
3. Wiring of the API module (admission + reply hook).
4. Tests: unit tier on the scoring model, job-tracking assertions on
   the HTTP flow, PostgreSQL round-trip.
5. This document, cross-linked from the rate-limiting page, and the
   `USAGE_*` variables documented in `.env.example`.

## Testing

- `make test-unit` — `tests/test_usage.py` runs the model (weights, KiB
  normalization, cache discount, rounding, clock-skew clamp) without
  Docker, Valkey or LaTeX; `tests/test_job_tracking.py` asserts the
  scores along the HTTP flow (success, compile error, fetch failure,
  cache hits, malformed requests).
- `tests/test_jobs_postgres.py` (when `TEST_DATABASE_URL` is set): the
  new columns round-trip through the repository.

## Future work

- **Score-based limiting**: switch the quota windows from request counts
  to token budgets (Valkey `INCRBYFLOAT` per window, denial when over
  budget) — calibrated on the production data this feature starts
  collecting.
- **API keys** for known integrators, then users; budgets per
  key/user/plan.
- **Concurrency semaphore**: the flood behind the quota feature was
  really a concurrency attack; a Valkey semaphore on in-flight
  compilations per client would cap it directly, and request occupancy
  time is now measured.
- Scoring rejected requests too, if production data shows meaningful
  cost there.
