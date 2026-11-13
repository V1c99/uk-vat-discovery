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
DNS_CACHE = Path("data/dns.json")
PAUSE = 1.0

_dns = ThreadPoolExecutor(max_workers=32)
_robots = {}
# two runs on the same sample differed by six companies because lookups timed out under load,
# so answers are kept and a rerun sees the same domains
_answers = json.loads(DNS_CACHE.read_text()) if DNS_CACHE.exists() else {}


def _lookup(domain, timeout):
    """True, False when the name does not exist, None when the resolver did not answer."""
    try:
        _dns.submit(socket.getaddrinfo, domain, 443).result(timeout=timeout)
        return True
    except socket.gaierror as e:
        # 11002 is Windows' "try again", it means busy, not missing
        return None if e.errno in (socket.EAI_AGAIN, 11002) else False
    except (OSError, FutureTimeout):
        return None


def resolves(domain):
    if domain not in _answers:
        ok = _lookup(domain, 8)
        if ok is None:
            ok = bool(_lookup(domain, 15))
        _answers[domain] = ok
    return _answers[domain]


def save_dns():
    DNS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    DNS_CACHE.write_text(json.dumps(_answers, indent=0, sort_keys=True))


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
