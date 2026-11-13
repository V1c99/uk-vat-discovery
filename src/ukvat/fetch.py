"""Polite page fetching: robots.txt, one host at a time, a pause between requests, a disk cache."""

import gzip
import hashlib
import json
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

AGENT = "uk-vat-research/0.1"
HEADERS = {"User-Agent": f"Mozilla/5.0 (compatible; {AGENT})", "Accept-Language": "en-GB"}
CACHE = Path("data/pages")
PAUSE = 1.0

_dns = ThreadPoolExecutor(max_workers=32)
_robots = {}


def resolves(domain, timeout=4):
    try:
        _dns.submit(socket.getaddrinfo, domain, 443).result(timeout=timeout)
        return True
    except (OSError, FutureTimeout):
        return False


def _cache_path(url):
    return CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".json.gz")


def allowed(url):
    host = urlsplit(url).netloc
    if host not in _robots:
        rp = RobotFileParser()
        try:
            r = requests.get(f"https://{host}/robots.txt", headers=HEADERS, timeout=(5, 10))
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except requests.RequestException:
            rp.parse([])
        _robots[host] = rp
    return _robots[host].can_fetch(AGENT, url)


def get(url):
    """Returns {url, final_url, status, html} or None. Cached, so a rerun costs nothing."""
    path = _cache_path(url)
    if path.exists():
        return json.loads(gzip.decompress(path.read_bytes()))
    if not allowed(url):
        page = {"url": url, "final_url": url, "status": "robots", "html": ""}
    else:
        time.sleep(PAUSE)
        try:
            r = requests.get(url, headers=HEADERS, timeout=(5, 12), allow_redirects=True)
            ctype = r.headers.get("content-type", "")
            html = r.text[:2_000_000] if "html" in ctype else ""
            page = {"url": url, "final_url": r.url, "status": r.status_code, "html": html}
        except requests.RequestException as e:
            page = {"url": url, "final_url": url, "status": type(e).__name__, "html": ""}
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(page).encode()))
    return page
