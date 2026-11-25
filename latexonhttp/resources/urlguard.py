"""
latexonhttp.resources.urlguard
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SSRF protection for user-supplied resource URLs.

The application fetches caller-controlled URLs on their behalf. Without a guard
that is a Server-Side Request Forgery: an unauthenticated client can make the
server read internal services, loopback, or cloud instance metadata
(169.254.169.254). The compilation sandbox does not help here because the fetch
runs in the application process, which has network access.

This module validates a URL *before* fetching and pins the resolved address for
the connection, so the request cannot be steered to a blocked address after
validation -- neither by an HTTP redirect nor by DNS rebinding (a name that
resolves to a public address at check time and an internal one at connect time).

:copyright: (c) 2026 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import ipaddress
import os
import socket
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from requests.adapters import HTTPAdapter

# Schemes a resource URL may use. Restrict via env (e.g. "https") if the
# deployment only wants encrypted fetches.
ALLOWED_SCHEMES = tuple(
    s.strip().lower()
    for s in os.getenv("FETCHER_ALLOWED_SCHEMES", "http,https").split(",")
    if s.strip()
)
# How many HTTP redirects to follow; every hop is re-validated and re-pinned.
MAX_REDIRECTS = int(os.getenv("FETCHER_MAX_REDIRECTS", "3"))


class UrlRejectedError(Exception):
    """A user-supplied URL was rejected before any request was attempted.

    ``reason`` is a stable, machine-readable code; ``detail`` is a
    human-readable explanation that may include the offending host/scheme.
    Subclasses separate an unfetchable URL (:class:`InvalidURLError`, a client
    error) from one that would have reached a blocked address
    (:class:`SSRFBlockedError`, a security block).
    """

    def __init__(self, reason, detail=""):
        super().__init__(reason if not detail else "%s: %s" % (reason, detail))
        self.reason = reason
        self.detail = detail


class InvalidURLError(UrlRejectedError):
    """The URL cannot be fetched at all (malformed, or an unsupported scheme).

    It never reaches the network, so it is a client error, not a security
    block. ``allowed_schemes`` carries the accepted schemes when the reason is
    scheme-related (``no_scheme`` / ``unsupported_scheme``), else ``None``.
    """

    def __init__(self, reason, detail="", allowed_schemes=None):
        super().__init__(reason, detail)
        self.allowed_schemes = allowed_schemes


class SSRFBlockedError(UrlRejectedError):
    """The URL would reach a blocked address.

    ``reason`` is a stable, machine-readable code (``loopback``, ``private_ip``,
    ``link_local``, ``reserved``, ``multicast``, ``not_global``,
    ``too_many_redirects``, ...); ``detail`` may name the offending
    host/address.
    """


def _disallowed_ip_reason(ip_str):
    """Return a reason code if the address is not publicly routable, else None.

    Covers loopback, private (RFC1918 + IPv6 ULA), link-local (incl. the cloud
    metadata range 169.254.0.0/16), reserved, multicast and unspecified
    addresses, and unwraps IPv4-mapped IPv6 addresses.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return "invalid_ip"
    # Most-specific reason codes first (several of these also report
    # is_private=True on modern CPython, so order matters for the label).
    if ip.is_unspecified:
        return "unspecified"
    if ip.is_loopback:
        return "loopback"
    if ip.is_link_local:
        return "link_local"
    if ip.is_multicast:
        return "multicast"
    if ip.is_reserved:
        return "reserved"
    if ip.is_private:
        return "private_ip"
    # IPv6 unique-local (fc00::/7); is_private covers it on modern CPython, but
    # be explicit so the guard does not depend on that.
    if ip.version == 6 and ip.packed[:1] in (b"\xfc", b"\xfd"):
        return "private_ip"
    # IPv4-mapped/compatible IPv6 (::ffff:a.b.c.d) -- judge the embedded v4 addr.
    if ip.version == 6 and ip.ipv4_mapped is not None:
        return _disallowed_ip_reason(str(ip.ipv4_mapped))
    # Catch-all: anything not globally routable (e.g. CGNAT 100.64.0.0/10, which
    # is_private does not flag on all CPython versions) is not a valid target.
    if not ip.is_global:
        return "not_global"
    return None


def _resolve_public_addresses(hostname, port):
    """Resolve ``hostname`` and return its validated public addresses.

    Raises :class:`SSRFBlockedError` if any resolved address is in a blocked
    range. A name that does not resolve at all raises :class:`socket.gaierror`
    (a plain fetch failure, not a security block).
    """
    # IP literal: validate directly, no DNS involved.
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        reason = _disallowed_ip_reason(hostname)
        if reason:
            raise SSRFBlockedError(reason, hostname)
        return [hostname]

    try:
        infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise
    addresses, seen = [], set()
    for info in infos:
        addr = info[4][0]
        if addr in seen:
            continue
        seen.add(addr)
        reason = _disallowed_ip_reason(addr)
        if reason:
            raise SSRFBlockedError(reason, "%s -> %s" % (hostname, addr))
        addresses.append(addr)
    if not addresses:
        raise SSRFBlockedError("no_addresses", hostname)
    return addresses


def validate_url(url):
    """Validate a user-supplied URL before fetching.

    Returns ``(parsed, [public_ips])``.

    Raises :class:`InvalidURLError` when the URL cannot be fetched at all
    (``no_scheme``, ``unsupported_scheme``, ``missing_host``, ``malformed_url``,
    ``invalid_port``) and :class:`SSRFBlockedError` when the target address is
    blocked. Propagates :class:`socket.gaierror` when a hostname does not
    resolve.
    """
    try:
        parsed = urlparse(url)
    except Exception as exc:  # urlparse is lenient; guard against the unexpected
        raise InvalidURLError("malformed_url", str(exc)) from exc
    scheme = (parsed.scheme or "").lower()
    if not scheme:
        raise InvalidURLError("no_scheme", url, allowed_schemes=ALLOWED_SCHEMES)
    if scheme not in ALLOWED_SCHEMES:
        raise InvalidURLError(
            "unsupported_scheme", scheme, allowed_schemes=ALLOWED_SCHEMES
        )
    try:
        port = parsed.port
    except ValueError as exc:  # e.g. an out-of-range port; would otherwise 500
        raise InvalidURLError("invalid_port", url) from exc
    hostname = parsed.hostname
    if not hostname:
        raise InvalidURLError("missing_host", url)
    port = port or (443 if scheme == "https" else 80)
    addresses = _resolve_public_addresses(hostname, port)
    return parsed, addresses


class _PinnedIPAdapter(HTTPAdapter):
    """Connect to a validated IP while presenting the original hostname.

    The TCP connection goes to the pinned address (so a DNS rebinding that
    returns a different address on the second lookup cannot reach an internal
    host), while the ``Host`` header and the TLS SNI/certificate check use the
    original hostname.
    """

    def __init__(self, hostname, ip, **kwargs):
        self._hostname = hostname
        self._ip = ip
        super().__init__(**kwargs)

    def send(self, request, **kwargs):
        parsed = urlparse(request.url)
        ip_host = "[%s]" % self._ip if ":" in self._ip else self._ip
        netloc = ip_host + (":%d" % parsed.port if parsed.port else "")
        request.url = urlunparse(parsed._replace(netloc=netloc))
        request.headers["Host"] = self._hostname + (
            ":%d" % parsed.port if parsed.port else ""
        )
        return super().send(request, **kwargs)

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        host_params, pool_kwargs = self.build_connection_pool_key_attributes(
            request, verify, cert
        )
        if request.url.lower().startswith("https"):
            pool_kwargs["server_hostname"] = self._hostname
        return self.poolmanager.connection_from_host(
            **host_params, pool_kwargs=pool_kwargs
        )


def _session_for(scheme, hostname, ip):
    session = requests.Session()
    session.mount(scheme + "://", _PinnedIPAdapter(hostname, ip))
    return session


def safe_get(url, timeout):
    """Fetch a user-supplied URL with SSRF protection.

    Returns the final :class:`requests.Response` (body already read into memory).
    Raises :class:`SSRFBlockedError` if any hop -- including a redirect target --
    is blocked, and lets :mod:`requests` transport exceptions (timeout,
    connection error) propagate for the caller to handle.
    """
    current_url = url
    for hop in range(MAX_REDIRECTS + 1):
        parsed, addresses = validate_url(current_url)
        scheme = parsed.scheme
        hostname = parsed.hostname
        session = _session_for(scheme, hostname, addresses[0])
        try:
            response = session.get(current_url, timeout=timeout, allow_redirects=False)
        except Exception:
            session.close()
            raise
        if response.is_redirect:
            location = response.headers.get("Location")
            response.close()
            session.close()
            if not location:
                raise SSRFBlockedError("redirect_without_location", current_url)
            if hop == MAX_REDIRECTS:
                raise SSRFBlockedError("too_many_redirects", url)
            current_url = urljoin(current_url, location)
            continue
        session.close()
        return response
    raise SSRFBlockedError("too_many_redirects", url)
