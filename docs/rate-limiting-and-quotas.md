# Rate limiting and quotas

Public instances accept unauthenticated compilation requests, so `/builds/sync` is protected by a fair-use quota. Hot quota state lives in a Valkey store (an in-memory counters/ban layer), while PostgreSQL keeps the durable per-job record and the durable ban record for analytics and abuse post-mortems. The quota is deliberately simple and conservative in cost: one pipeline round-trip per request, and no database access on the hot path either — ban state changes are persisted best-effort (see [Durable ban record](#durable-ban-record)).

The quota is active only when `VALKEY_HOST` is configured. Without it (local development, unit tests) the API behaves exactly as before. When Valkey is unreachable the check fails **open** (the request is allowed and the failure is logged and reported to Sentry); a caching layer must not become a single point of failure for the compile service. Set `QUOTA_FAIL_MODE=closed` to invert this if a deployment prefers rejecting requests over serving without protection.

## What is counted

Every admitted `/builds/sync` request counts 1, at admission — before the payload is parsed. Rejected-by-quota requests do not consume quota, but they do count as violations (see escalation). Requests that fail payload validation (HTTP 400) are counted too: parsing is cheap, compilation is what must be protected. The `/fonts`, `/packages` and `/texlive` endpoints are cheap lookups and are not quotaed.

The client IP is read from `QUOTA_CLIENT_IP_HEADER` (default `X-Forwarded-For`, first value), falling back to `request.remote_addr`. This assumes the reverse proxy overwrites or appends the header; behind Cloudflare set `QUOTA_CLIENT_IP_HEADER=CF-Connecting-IP`. An optional `QUOTA_TRUSTED_IPS` allowlist (comma-separated) bypasses the quota entirely (monitoring probes, tests).

## Quota windows

Fixed, calendar-aligned windows in UTC: seconds/minutes/hours are floored, days start at midnight, weeks start on ISO Monday. All counters are self-expiring Valkey keys, so state vanishes without cleanup.

| Window | Default limit | Environment variable |
|---|---|---|
| 1 second | 2 | `QUOTA_LIMIT_SECOND` |
| 1 minute | 6 | `QUOTA_LIMIT_MINUTE` |
| 1 hour | 40 | `QUOTA_LIMIT_HOUR` |
| 1 day | 150 | `QUOTA_LIMIT_DAY` |
| 1 week | 400 | `QUOTA_LIMIT_WEEK` |

The defaults were calibrated against a real abuse episode (25 requests/min from one client saturating the CPU): the second and minute windows stop the flood, the minute window is the effective concurrency cap (with the 30s compilation timeout it bounds a client to ~3 concurrent compilations), and the hour/day/week windows bound sustained fair use.

The first (shortest) breached window determines the denial. The binding window — the one with the fewest remaining requests — is reported in the rate-limit headers of passing responses.

## Key layout

| Key | Value | TTL |
|---|---|---|
| `quota:c:{ip}:sec:{epoch_second}` | request counter | 3s |
| `quota:c:{ip}:min:{epoch_minute}` | request counter | 75s |
| `quota:c:{ip}:hour:{epoch_hour}` | request counter | 1h + 2min |
| `quota:c:{ip}:day:{YYYYMMDD}` | request counter | 25h |
| `quota:c:{ip}:week:{ISO week, e.g. 2026-W47}` | request counter | 8d + 1h |
| `quota:ban:{ip}` | ban level (`short` / `long`) | ban duration |
| `quota:viol:15m:{ip}` | violation counter | 15 min |
| `quota:viol:24h:{ip}` | violation counter | 24h |
| `quota:bans:24h:{ip}` | ban counter | 24h |

At most a handful of small keys per client IP, all with TTLs; run Valkey with bounded memory and an eviction policy (the Compose service uses `--save 60 1 --maxmemory 64mb --maxmemory-policy allkeys-lru`).

## Escalation for clients ignoring the quota

Clients that keep firing while over quota are kicked more severely. Every denial — and every request received while banned — increments the violation counters:

| Trigger | Effect |
|---|---|
| Window quota exceeded | HTTP 429 `QUOTA_EXCEEDED` |
| ≥ 3 violations within 15 min (`QUOTA_BAN_SHORT_VIOLATIONS`) | 1-hour ban (`QUOTA_BAN_SHORT_DURATION`) |
| Request received while banned | ban TTL re-extended, violations incremented |
| ≥ 10 violations within 24h (`QUOTA_BAN_LONG_VIOLATIONS`) or ≥ 3 bans within 24h (`QUOTA_BAN_COUNT_FOR_LONG`) | 24-hour ban (`QUOTA_BAN_LONG_DURATION`) |

A client hammering at 429s therefore escalates automatically: throttled → 1-hour ban → 24-hour ban. While a ban is active every attempt re-arms it, so the ban only starts counting down once the client stops.

## Durable ban record

Ban *state changes* — arming and escalation — are persisted in PostgreSQL (`quota_bans`, migration `tools/migrations/00004_quota_bans.sql`), on top of the Valkey hot state. Re-arms and denials are deliberately not recorded: a hammering client must never add write load to the database, and its denials are already visible in the logs. The persistence is best-effort: a database failure changes nothing for the client, the decision (already taken in Valkey) stands, and the failure is logged.

| Column | Meaning |
|---|---|
| `client_ip`, `level` | who, and which ban (`short` / `long`) |
| `source` | `violation_window` (armed from the escalation ladder) or `ban_escalation` (escalated while already banned) |
| `trigger_period` | the breached window when armed from a denial; `NULL` on escalation |
| `violations_short`, `violations_long`, `bans_24h` | the escalation counters snapshot at arming |
| `armed_at`, `expires_at` | when the ban started and its *initial* expiry — re-arms extend the real ban beyond `expires_at` |

Typical post-mortems:

```sql
-- Ban history of one client.
SELECT * FROM quota_bans
WHERE client_ip = '34.96.40.54'
ORDER BY armed_at DESC LIMIT 50;

-- Recent ban activity on the instance.
SELECT armed_at, client_ip, level, source, trigger_period,
       violations_short, violations_long, bans_24h
FROM quota_bans
WHERE armed_at >= NOW() - INTERVAL '24 hours'
ORDER BY armed_at DESC;
```

## Logging

Every quota event leaves a log line on the `latexonhttp.quota` logger, routed to the console by the application logging setup (visibility gated by `LOGGING_LEVEL`, `DEBUG` by default):

| Event | Level | Message |
|---|---|---|
| Window exceeded (HTTP 429) | INFO | `Quota denial for {ip}; {period} window exceeded ({count}/{limit})` |
| Request received while banned | INFO | `Quota denial (ban) for {ip}; level {level}, retry after {n} s` |
| Ban armed or escalated | WARNING | `Quota ban ({level}) applied to {ip} for {n} seconds` |
| Ban re-armed by a hammering client | INFO | `Quota ban ({level}) re-armed for {ip} ({n} seconds)` |
| Durable ban record persistence failed | ERROR | `Could not persist the quota ban of {ip}` — with traceback |
| Store unreachable | ERROR | `Quota store unreachable; failing {mode}` — with traceback, also reported to Sentry |

Only the rare state changes (a ban starting or escalating) log at `WARNING`; per-request denials and re-arms stay at `INFO` so an abusive client cannot flood the loud levels on purpose.

## HTTP contract

Quota denials return HTTP 429 before any payload parsing:

```json
{
  "error": "QUOTA_EXCEEDED",
  "message": "Fair-use quota exceeded. Slow down, or wait for the window to reset.",
  "documentation": "https://latex.ytotech.com/docs/api/rate-limiting/",
  "quota": {
    "period": "hour",
    "limit": 40,
    "retry_after": 812,
    "banned": false,
    "ban_expires_at": null
  }
}
```

The `documentation` field carries the absolute URL of the rate-limiting page
served by the instance itself (`/docs/api/rate-limiting/`), derived from the
incoming request (honouring the scheme announced by a TLS-terminating reverse
proxy).

`quota.period` is the breached window, or `null` with `banned: true` when a ban is active. Responses (denials and passing requests alike) carry:

* `Retry-After`: seconds until the breached window resets, or the remaining ban TTL;
* `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` (unix epoch of the binding window end).

Clients should honor `Retry-After`; continuing to poll only accelerates escalation to a ban. With `QUOTA_FAIL_MODE=closed`, an unreachable Valkey store yields HTTP 503 `QUOTA_STORE_UNAVAILABLE` instead of failing open.

## Deployment

The Compose base file ships a Valkey service and wires `VALKEY_HOST` into the application environment:

```yaml
valkey:
  image: docker.io/valkey/valkey:8-alpine
  command: ["valkey-server", "--save", "60", "1", "--maxmemory", "64mb", "--maxmemory-policy", "allkeys-lru"]
  volumes:
    - ./data/valkey:/data
```

Ban and quota state is snapshotted to `./data/valkey/dump.rdb` at most once a minute (and on clean shutdown), so a restart loses at most the last minute of counters; TTLs are preserved on reload and expired keys are dropped. A restored snapshot can slightly undercount a window, which is acceptable for a fair-use mechanism (the durable evidence lives in the `jobs` table). To disable the quota on an instance, unset `VALKEY_HOST` (or set `QUOTA_ENABLED=0`); to disable it per client, use `QUOTA_TRUSTED_IPS`.

## Database indexes

Migration `tools/migrations/00002_quota_ip_indexes.sql` adds indexes for IP/period lookups on the durable record (analytics, abuse post-mortems, limit tuning — not the request hot path):

```sql
CREATE INDEX jobs_remote_ip_received_at_idx ON jobs (remote_ip, received_at DESC);
CREATE INDEX jobs_forwarded_remote_ip_received_at_idx ON jobs (forwarded_remote_ip, received_at DESC);
CREATE INDEX jobs_received_at_idx ON jobs (received_at);
```

Typical lookups this enables:

```sql
-- Requests per client IP over the last hour.
SELECT forwarded_remote_ip, COUNT(*) FROM jobs
WHERE received_at >= NOW() - INTERVAL '1 hour'
GROUP BY forwarded_remote_ip ORDER BY COUNT(*) DESC;

-- Recent history for one client.
SELECT job_status, error_code, received_at FROM jobs
WHERE forwarded_remote_ip = '34.96.40.54'
ORDER BY received_at DESC LIMIT 50;
```

## Testing

* `make test-unit` runs the quota unit tier (`tests/test_quota.py`) against an in-memory fake store: window counting and calendar alignment, breach ordering, escalation ladder (ban arming, re-arming and upgrade), enforcement log lines, durable ban record capture, fail-open behavior, client IP extraction and allowlist. No Valkey, Docker or LaTeX needed.
* `make test-quota` runs the integration tier through a dedicated Compose override (`docker-compose.quota-test.yml`) that adds the Valkey service and low limits, and exercises 429 responses, rate-limit headers and ban escalation over HTTP with spoofed `X-Forwarded-For` values, including the durable ban record in PostgreSQL.

## Known limits and future work

* Fixed windows allow up to 2× the limit around a boundary; sliding windows or GCRA would be more precise at the cost of complexity.
* Per-IP quotas do not identify distributed abuse (rotating IPs); API keys for known integrators are the long-term answer.
* The quota counts requests, not what they consume: each request now also gets a usage score (incoming/fetch/processing/outgoing tokens, see [API usage scoring](usage-scoring.md)); switching the windows to token budgets calibrated on that data is the follow-up.
* The flood behind this feature was really a concurrency attack; a Valkey-based per-IP semaphore on in-flight compilations would cap it directly.
