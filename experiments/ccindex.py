"""Looking hosts up in Common Crawl's index without the index server, which kept timing out.

cluster.idx has the first key of every block of 3,000 index lines and where the block sits in
which cdx file. A host's lines are found by bisecting the keys and fetching only those blocks with
a range request. Blocks are cached in data/.
"""

import bisect
import gzip
import json
from pathlib import Path

import requests

CRAWL = "CC-MAIN-2026-43"
BASE = f"https://data.commoncrawl.org/cc-index/collections/{CRAWL}/indexes"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; uk-vat-research/0.1)"}
CACHE = Path("data/probes/commoncrawl/blocks")

_keys, _blocks = [], []


def load(path="data/probes/commoncrawl/cluster.idx"):
    for line in open(path, encoding="utf-8"):
        key, file, offset, length, _ = line.rstrip("\n").split("\t")
        _keys.append(key.split(" ")[0])
        _blocks.append((file, int(offset), int(length)))


def surt(host):
    host = host.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return ",".join(reversed(host.split(".")))


def block(i):
    file, offset, length = _blocks[i]
    path = CACHE / f"{file}_{offset}.gz"
    if not path.exists():
        span = {"Range": f"bytes={offset}-{offset + length - 1}"}
        r = requests.get(f"{BASE}/{file}", headers={**HEADERS, **span}, timeout=120)
        r.raise_for_status()
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    return gzip.decompress(path.read_bytes()).decode("utf-8", "replace").splitlines()


def captures(host):
    """Every index line for the host and its subdomains, as dicts."""
    if not _keys:
        load()
    out = []
    base = surt(host)
    for prefix in (base + ")", base + ","):
        i = max(bisect.bisect_right(_keys, prefix) - 1, 0)
        while i < len(_keys):
            lines = [x for x in block(i) if x.startswith(prefix)]
            for x in lines:
                out.append(json.loads(x.split(" ", 2)[2]))
            # stop once the next block already starts past the prefix
            if i + 1 >= len(_keys) or _keys[i + 1] > prefix + "\x7f":
                break
            i += 1
    return out
