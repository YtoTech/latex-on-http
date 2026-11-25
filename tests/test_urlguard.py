"""
tests.test_urlguard
~~~~~~~~~~~~~~~~~~~~~
Unit tests for the SSRF URL guard (no network, no Docker).

:copyright: (c) 2026 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import socket
from unittest import mock

import pytest

from latexonhttp.resources import urlguard
from latexonhttp.resources.urlguard import (
    InvalidURLError,
    SSRFBlockedError,
    _disallowed_ip_reason,
    safe_get,
    validate_url,
)

# --- _disallowed_ip_reason -------------------------------------------------


@pytest.mark.parametrize(
    "ip, expected",
    [
        ("127.0.0.1", "loopback"),
        ("::1", "loopback"),
        ("10.0.0.1", "private_ip"),
        ("172.16.0.1", "private_ip"),
        ("192.168.1.1", "private_ip"),
        ("100.64.0.1", "not_global"),  # CGNAT, not globally routable
        ("169.254.169.254", "link_local"),  # cloud metadata
        ("169.254.1.1", "link_local"),
        ("fc00::1", "private_ip"),  # IPv6 ULA
        ("fd12:3456::1", "private_ip"),  # IPv6 ULA
        ("::ffff:127.0.0.1", "loopback"),  # IPv4-mapped loopback
        ("::ffff:10.0.0.1", "private_ip"),  # IPv4-mapped private
        ("0.0.0.0", "unspecified"),
        ("224.0.0.1", "multicast"),
        ("255.255.255.255", "reserved"),
        # Public / routable -> not blocked.
        ("8.8.8.8", None),
        ("1.1.1.1", None),
        ("93.184.216.34", None),
        ("2001:4860:4860::8888", None),
    ],
)
def test_disallowed_ip_reason(ip, expected):
    assert _disallowed_ip_reason(ip) == expected


def test_disallowed_ip_reason_invalid():
    assert _disallowed_ip_reason("not-an-ip") == "invalid_ip"


# --- validate_url: IP literals (no DNS) -----------------------------------


def test_validate_url_blocks_loopback_literal():
    with pytest.raises(SSRFBlockedError) as exc:
        validate_url("http://127.0.0.1/secret")
    assert exc.value.reason == "loopback"


def test_validate_url_blocks_link_local_metadata():
    with pytest.raises(SSRFBlockedError) as exc:
        validate_url("http://169.254.169.254/latest/meta-data/")
    assert exc.value.reason == "link_local"


def test_validate_url_blocks_private_literal():
    with pytest.raises(SSRFBlockedError) as exc:
        validate_url("http://10.0.0.5:8080/")
    assert exc.value.reason == "private_ip"


def test_validate_url_allows_public_literal():
    parsed, ips = validate_url("http://8.8.8.8/x")
    assert ips == ["8.8.8.8"]
    assert parsed.hostname == "8.8.8.8"


# --- validate_url: scheme / host (unfetchable -> InvalidURLError) -----------


def test_validate_url_rejects_unsupported_scheme():
    with pytest.raises(InvalidURLError) as exc:
        validate_url("file:///etc/passwd")
    assert exc.value.reason == "unsupported_scheme"
    assert list(exc.value.allowed_schemes) == ["http", "https"]


def test_validate_url_rejects_missing_scheme():
    with pytest.raises(InvalidURLError) as exc:
        validate_url("example.com/path")
    assert exc.value.reason == "no_scheme"
    assert list(exc.value.allowed_schemes) == ["http", "https"]


def test_validate_url_rejects_missing_host():
    with pytest.raises(InvalidURLError) as exc:
        validate_url("http://")
    assert exc.value.reason == "missing_host"
    assert exc.value.allowed_schemes is None


def test_validate_url_rejects_out_of_range_port():
    # An out-of-range port makes parsed.port raise ValueError; that must be a
    # client-error invalid_url, never an unhandled 500.
    with pytest.raises(InvalidURLError) as exc:
        validate_url("http://example.com:99999/")
    assert exc.value.reason == "invalid_port"


# --- validate_url: name resolution (mocked getaddrinfo) --------------------


def _addrinfo(ip):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 80))]


def test_validate_url_blocks_name_resolving_to_private():
    with (
        mock.patch.object(
            urlguard.socket, "getaddrinfo", return_value=_addrinfo("10.1.2.3")
        ),
        pytest.raises(SSRFBlockedError) as exc,
    ):
        validate_url("http://internal.example/")
    assert exc.value.reason == "private_ip"
    assert "internal.example" in exc.value.detail


def test_validate_url_allows_name_resolving_to_public():
    with mock.patch.object(
        urlguard.socket, "getaddrinfo", return_value=_addrinfo("93.184.216.34")
    ):
        parsed, ips = validate_url("http://public.example/")
    assert ips == ["93.184.216.34"]


def test_validate_url_name_resolution_failure_propagates():
    with (
        mock.patch.object(
            urlguard.socket, "getaddrinfo", side_effect=socket.gaierror("no such host")
        ),
        pytest.raises(socket.gaierror),
    ):
        validate_url("http://doesnotexist-cucumber-impossible.org/")


def test_validate_url_blocks_if_any_address_is_private():
    # A name with both a public and a private address must be rejected.
    infos = _addrinfo("93.184.216.34") + _addrinfo("192.168.0.1")
    with (
        mock.patch.object(urlguard.socket, "getaddrinfo", return_value=infos),
        pytest.raises(SSRFBlockedError) as exc,
    ):
        validate_url("http://mixed.example/")
    assert exc.value.reason == "private_ip"


# --- safe_get: redirect re-validation (mocked transport) -------------------


class _FakeResponse:
    def __init__(self, status_code, location=None, content=b""):
        self.status_code = status_code
        self.headers = {"Location": location} if location else {}
        self._content = content
        self.is_redirect = "Location" in self.headers and status_code in (
            301,
            302,
            303,
            307,
            308,
        )

    @property
    def content(self):
        return self._content

    def close(self):
        pass


def test_safe_get_follows_and_revalidates_redirect_to_blocked():
    # First hop is public; it redirects to loopback, which must be blocked.
    with (
        mock.patch.object(
            urlguard.socket, "getaddrinfo", return_value=_addrinfo("93.184.216.34")
        ),
        mock.patch.object(urlguard.requests, "Session") as session_cls,
    ):
        session = session_cls.return_value
        session.get.side_effect = [
            _FakeResponse(302, location="http://127.0.0.1/admin"),
        ]
        with pytest.raises(SSRFBlockedError) as exc:
            safe_get("http://public.example/redirect", timeout=(5, 5))
    assert exc.value.reason == "loopback"


def test_safe_get_returns_content_on_success():
    with (
        mock.patch.object(
            urlguard.socket, "getaddrinfo", return_value=_addrinfo("93.184.216.34")
        ),
        mock.patch.object(urlguard.requests, "Session") as session_cls,
    ):
        session = session_cls.return_value
        session.get.return_value = _FakeResponse(200, content=b"hello")
        response = safe_get("http://public.example/file", timeout=(5, 5))
    assert response.content == b"hello"


def test_safe_get_blocks_too_many_redirects():
    with (
        mock.patch.object(
            urlguard.socket, "getaddrinfo", return_value=_addrinfo("93.184.216.34")
        ),
        mock.patch.object(urlguard.requests, "Session") as session_cls,
    ):
        session = session_cls.return_value
        # Every hop redirects to the next public URL -> exceeds MAX_REDIRECTS.
        session.get.return_value = _FakeResponse(
            302, location="http://public.example/next"
        )
        with pytest.raises(SSRFBlockedError) as exc:
            safe_get("http://public.example/a", timeout=(5, 5))
    assert exc.value.reason == "too_many_redirects"


# --- safe_get: capped body read (max_bytes) ---------------------------------


class _FakeStreamResponse:
    """A streamed response fake: the body is only visible through iter_content.

    ``iter_content`` yields the stored body in fixed-size chunks, like a
    requests streamed response; ``chunks_yielded`` counts how far the read
    went, to prove an oversized body is not consumed in full.
    """

    def __init__(self, body, chunk_size=65536):
        self.headers = {}
        self.is_redirect = False
        self._body = body
        self._chunk_size = chunk_size
        self._content = b""
        self._content_consumed = False
        self.chunks_yielded = 0

    def iter_content(self, chunk_size):
        for offset in range(0, len(self._body), self._chunk_size):
            self.chunks_yielded += 1
            yield self._body[offset : offset + self._chunk_size]

    def close(self):
        pass

    @property
    def content(self):
        return self._content


def test_safe_get_max_bytes_truncates_oversized_body_to_cap_plus_one():
    with (
        mock.patch.object(
            urlguard.socket, "getaddrinfo", return_value=_addrinfo("93.184.216.34")
        ),
        mock.patch.object(urlguard.requests, "Session") as session_cls,
    ):
        session = session_cls.return_value
        fake = _FakeStreamResponse(b"x" * 200_000)
        session.get.return_value = fake
        response = safe_get("http://public.example/big", timeout=(5, 5), max_bytes=1000)
    # The stored body is capped at exactly max_bytes + 1, not the full body.
    assert response.content == b"x" * 1001
    # The read is truncated mid-chunk at the cap: the stream stops after the
    # very first chunk, while the full 200000-byte body would need 4.
    assert fake.chunks_yielded == 1


def test_safe_get_max_bytes_keeps_a_body_that_fits():
    body = b"hello world"
    with (
        mock.patch.object(
            urlguard.socket, "getaddrinfo", return_value=_addrinfo("93.184.216.34")
        ),
        mock.patch.object(urlguard.requests, "Session") as session_cls,
    ):
        session = session_cls.return_value
        fake = _FakeStreamResponse(body)
        session.get.return_value = fake
        response = safe_get(
            "http://public.example/small", timeout=(5, 5), max_bytes=1000
        )
    assert response.content == body
    assert response._content_consumed is True


def test_safe_get_max_bytes_requests_a_streamed_response():
    with (
        mock.patch.object(
            urlguard.socket, "getaddrinfo", return_value=_addrinfo("93.184.216.34")
        ),
        mock.patch.object(urlguard.requests, "Session") as session_cls,
    ):
        session = session_cls.return_value
        session.get.return_value = _FakeStreamResponse(b"hello")
        safe_get("http://public.example/file", timeout=(5, 5), max_bytes=10)
    # A cap implies stream=True so the body can be aborted mid-download.
    assert session.get.call_args.kwargs["stream"] is True


def test_safe_get_without_max_bytes_keeps_the_historical_read():
    with (
        mock.patch.object(
            urlguard.socket, "getaddrinfo", return_value=_addrinfo("93.184.216.34")
        ),
        mock.patch.object(urlguard.requests, "Session") as session_cls,
    ):
        session = session_cls.return_value
        session.get.return_value = _FakeResponse(200, content=b"hello")
        response = safe_get("http://public.example/file", timeout=(5, 5))
    # No cap: no stream parameter, no capped read, body untouched.
    assert "stream" not in session.get.call_args.kwargs
    assert response.content == b"hello"
