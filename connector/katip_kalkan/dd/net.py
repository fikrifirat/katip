"""One polite HTTP client for every source (pattern borrowed from rewyse-opinions' ReviewAPIClient).

- Honest user agent that names the project.
- robots.txt checked once per host and obeyed.
- At least ``min_interval`` seconds between requests to the same host.
- Retries only on timeouts and 5xx. A 403 or a captcha is reported, never worked around.
- Some .gov.tr servers send an incomplete certificate chain. We add the two public
  intermediate CA certificates in ``certs/`` to the normal trust store, so verification
  stays on. We never disable TLS verification.
"""
from __future__ import annotations

import json
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from pathlib import Path

USER_AGENT = "KatipDD/0.1 (+https://github.com/fikrifirat/katip; due-diligence screening of public lists)"
_CERTS = Path(__file__).with_name("certs") / "gov_tr_intermediates.pem"


class Blocked(Exception):
    """The site refused us (robots.txt, 401/403, captcha, dropped connection)."""


def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    try:  # python.org builds on macOS ship without a CA store
        import certifi  # type: ignore

        ctx.load_verify_locations(certifi.where())
    except Exception:
        pass
    if _CERTS.exists():
        ctx.load_verify_locations(str(_CERTS))
    return ctx


@dataclass
class Response:
    url: str
    status: int
    headers: dict
    body: bytes

    def json(self):
        return json.loads(self.body.decode("utf-8"))

    def text(self, encoding: str = "utf-8") -> str:
        return self.body.decode(encoding, errors="replace")


@dataclass
class PoliteClient:
    min_interval: float = 2.0
    timeout: float = 60.0
    retries: int = 2
    user_agent: str = USER_AGENT
    log: list = field(default_factory=list)
    _last: dict = field(default_factory=dict)
    _robots: dict = field(default_factory=dict)

    def __post_init__(self):
        self._ctx = _ssl_context()
        self._opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=self._ctx))

    # -- robots -----------------------------------------------------------------------------
    def allowed(self, url: str) -> bool:
        p = urllib.parse.urlsplit(url)
        host = f"{p.scheme}://{p.netloc}"
        rp = self._robots.get(host)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self._raw("GET", host + "/robots.txt", None, {}, check_robots=False)
                rp.parse(r.text().splitlines() if r.status == 200 else [])
            except Exception:
                rp.parse([])  # unreachable robots.txt: the request itself will tell us more
            self._robots[host] = rp
        return rp.can_fetch(self.user_agent, url)

    # -- requests ---------------------------------------------------------------------------
    def get(self, url: str, **kw) -> Response:
        return self._raw("GET", url, None, kw.get("headers", {}))

    def post_json(self, url: str, payload: dict, headers: dict | None = None) -> Response:
        h = {"Content-Type": "application/json"}
        h.update(headers or {})
        return self._raw("POST", url, json.dumps(payload).encode("utf-8"), h)

    def _wait(self, host: str):
        last = self._last.get(host)
        if last is not None:
            gap = time.monotonic() - last
            if gap < self.min_interval:
                time.sleep(self.min_interval - gap)
        self._last[host] = time.monotonic()

    def _raw(self, method, url, data, headers, check_robots=True) -> Response:
        if check_robots and not self.allowed(url):
            raise Blocked(f"robots.txt disallows {url}")
        host = urllib.parse.urlsplit(url).netloc
        h = {"User-Agent": self.user_agent, "Accept": "*/*"}
        h.update(headers)
        err = None
        for attempt in range(self.retries + 1):
            self._wait(host)
            t0 = time.monotonic()
            req = urllib.request.Request(url, data=data, headers=h, method=method)
            try:
                with self._opener.open(req, timeout=self.timeout) as r:
                    body = r.read()
                    resp = Response(url, r.status, dict(r.headers), body)
                    self.log.append({"url": url, "status": r.status, "bytes": len(body), "s": round(time.monotonic() - t0, 2)})
                    return resp
            except urllib.error.HTTPError as e:
                self.log.append({"url": url, "status": e.code, "s": round(time.monotonic() - t0, 2)})
                if e.code in (401, 403, 451):
                    raise Blocked(f"HTTP {e.code} from {host}") from e
                if e.code == 404:
                    return Response(url, 404, dict(e.headers or {}), b"")
                if e.code == 429 or e.code >= 500:
                    err = e
                    time.sleep(min(30, 5 * (attempt + 1)))
                    continue
                raise
            except (urllib.error.URLError, socket.timeout, ConnectionError, ssl.SSLError) as e:
                self.log.append({"url": url, "error": str(e)[:200], "s": round(time.monotonic() - t0, 2)})
                err = e
                time.sleep(min(30, 5 * (attempt + 1)))
        raise Blocked(f"{host} unreachable after {self.retries + 1} tries: {err}")
