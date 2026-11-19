---
title: Rate limiting & quotas
layout: base.njk
active: "/api/rate-limiting/"
---

{% import "macros.njk" as macros %}

<div class="prose">

Public instances protect their compilation capacity with a fair-use quota on
`/builds/sync`: each client IP may run a bounded number of compilations over
five overlapping windows. When the quota is exceeded, the endpoint answers
`429` **before reading the request payload**, so rejected requests are cheap
to retry — but retrying in a loop only makes things worse (see
[escalation](#escalation)).

The `/fonts`, `/packages` and `/texlive` endpoints are cheap lookups and are
not quotaed.

## Quota windows

Requests are counted per client IP in calendar-aligned windows (UTC):

| Window | Default limit | Resets |
|---|---|---|
| 1 second | 2 | every second |
| 1 minute | 6 | every minute |
| 1 hour | 40 | every hour |
| 1 day | 150 | at midnight UTC |
| 1 week | 400 | on Mondays, 00:00 UTC |

The first window you exceed determines the denial. The limits are
instance-configured: a self-hosted deployment may raise, lower or disable
them (see the <a href="https://github.com/YtoTech/latex-on-http/blob/master/docs/rate-limiting-and-quotas.md">operator documentation</a>).

## Rate-limit response headers

Every `/builds/sync` response carries:

* `Retry-After`: seconds to wait before sending the next request — the time
  to the end of the breached window on a `429`, or the remaining ban time.
* `X-RateLimit-Limit`: the limit of the window you are closest to exhausting
  (the *binding* window).
* `X-RateLimit-Remaining`: how many requests remain in that window.
* `X-RateLimit-Reset`: unix timestamp at which that window resets.

## The 429 response

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

The `documentation` field points to the rate-limiting page served by the
instance itself.

`quota.period` names the breached window and `quota.limit` its limit. When a
ban is active instead, `period` and `limit` are `null` and:

```json
{
    "error": "QUOTA_EXCEEDED",
    "documentation": "https://latex.ytotech.com/docs/api/rate-limiting/",
    "quota": {
        "period": null,
        "limit": null,
        "retry_after": 3462,
        "banned": true,
        "ban_expires_at": 1763566854
    }
}
```

On instances configured to reject requests when the quota store is
unavailable (`QUOTA_FAIL_MODE=closed`), a store outage yields `503`
`QUOTA_STORE_UNAVAILABLE`; most instances fail open instead and keep serving.

## Escalation

A client that keeps sending requests while over quota is kicked more
severely. Every denial — and every request received while banned — counts as
a violation:

* 3 violations within 15 minutes → the client IP is **banned for 1 hour**;
* 10 violations within 24 hours, or 3 bans within 24 hours → **banned for
  24 hours**.

While a ban is active, every further attempt re-arms it: the ban only starts
counting down once the client stops hammering. Honoring `Retry-After` and
backing off is therefore not just polite — it is the difference between
waiting a few seconds and being locked out for a day.

## Handling it in a client

Wait for `Retry-After`, and stop retrying after a couple of denials — the
service is telling you something (a bug producing a tight retry loop, or a
workload that needs a self-hosted instance):

```python
import time

for attempt in range(3):
    response = requests.post(API_URL, json=payload, timeout=120)
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 5))
        time.sleep(retry_after)
        continue
    break

if response.status_code == 429:
    # Repeated denials escalate into a temporary ban: investigate instead
    # of retrying harder.
    quota = response.json()["quota"]
    print(f"Still quota-limited after retries: {quota}")
```

{{ macros.callout("note", "<p>A <code>429</code> never means your document was malformed — the request
was rejected before the payload was even parsed. Wait, then resend it
unchanged.</p>") }}

</div>
