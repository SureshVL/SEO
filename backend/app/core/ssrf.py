"""SSRF protection for outbound fetches of user-supplied URLs.

The crawler, edge site verifier, and feed importer all fetch URLs the user
controls. Without guarding, an attacker could point them at cloud metadata
(169.254.169.254), localhost, or private-network hosts and read the response
back through the free-audit report. This validates a URL/host resolves only to
public IP addresses, and provides a redirect-safe httpx transport.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx

BLOCKED_PORTS = {22, 23, 25, 3306, 5432, 6379, 9200, 11211, 27017}


class SSRFError(ValueError):
    """Raised when a URL resolves to a disallowed (private/internal) address."""


def _ip_is_public(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local     # 169.254.0.0/16 - cloud metadata
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def validate_public_url(url: str) -> str:
    """Return the URL if it is http(s) and its host resolves only to public
    IPs. Raises SSRFError otherwise."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFError(f"Only http/https URLs are allowed (got {parsed.scheme!r})")
    host = parsed.hostname
    if not host:
        raise SSRFError("URL has no host")
    if parsed.port in BLOCKED_PORTS:
        raise SSRFError(f"Port {parsed.port} is not allowed")

    # a literal IP host
    try:
        ipaddress.ip_address(host)
        if not _ip_is_public(host):
            raise SSRFError(f"Host {host} is a private/internal address")
        return url
    except ValueError:
        pass  # it's a hostname, resolve it

    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise SSRFError(f"Could not resolve host {host}: {exc}")

    resolved = {info[4][0] for info in infos}
    if not resolved:
        raise SSRFError(f"Host {host} did not resolve")
    for ip in resolved:
        if not _ip_is_public(ip):
            raise SSRFError(f"Host {host} resolves to a private/internal address ({ip})")
    return url


class _GuardedTransport(httpx.HTTPTransport):
    """Sync transport that re-validates every hop (defeats redirect-to-internal)."""

    def handle_request(self, request):
        validate_public_url(str(request.url))
        return super().handle_request(request)


class _GuardedAsyncTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request):
        validate_public_url(str(request.url))
        return await super().handle_async_request(request)


def guarded_client(**kwargs) -> httpx.Client:
    kwargs.setdefault("timeout", 15)
    return httpx.Client(transport=_GuardedTransport(), **kwargs)


def guarded_async_client(**kwargs) -> httpx.AsyncClient:
    kwargs.setdefault("timeout", 15)
    return httpx.AsyncClient(transport=_GuardedAsyncTransport(), **kwargs)


MAX_FETCH_BYTES = 8 * 1024 * 1024  # 8 MB cap on any user-triggered download


async def read_capped(response, max_bytes: int = MAX_FETCH_BYTES) -> bytes:
    """Read an httpx streaming response, aborting past a byte budget (anti-DoS)."""
    chunks: list[bytes] = []
    total = 0
    async for chunk in response.aiter_bytes():
        total += len(chunk)
        if total > max_bytes:
            raise SSRFError("Response exceeds size cap")
        chunks.append(chunk)
    return b"".join(chunks)


def safe_parse_xml(content: bytes):
    """Parse XML with entity-expansion / XXE protection (stdlib only).

    Python's xml.etree resolves internal entities (billion-laughs) - we reject
    any document declaring a DTD or entities before parsing. Also size-capped.
    """
    from xml.etree import ElementTree

    if len(content) > MAX_FETCH_BYTES:
        raise SSRFError("XML exceeds size cap")
    head = content[:4096].lstrip().lower()
    if b"<!doctype" in head or b"<!entity" in content[:65536].lower():
        raise SSRFError("XML with DTD/entities is not allowed")
    return ElementTree.fromstring(content)
