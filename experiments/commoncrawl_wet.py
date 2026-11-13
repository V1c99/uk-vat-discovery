"""A slice of Common Crawl's text files (October 2026): how many pages carry a UK VAT number, and
how many carry one next to a company number. Multiplied up, that is what a full harvest of one
crawl could give, for Part 3.

    python experiments/commoncrawl_wet.py CC-MAIN-2026-43 4 results/probes/commoncrawl_wet.csv
"""

import csv
import gzip
import hashlib
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import duckdb
import requests
from warcio.archiveiterator import ArchiveIterator

from ukvat.page import company_numbers
from ukvat.vat import find_candidates

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; uk-vat-research/0.1)"}
RAW = Path("data/probes/commoncrawl/wet")


def pick(crawl, k, seed="2026-11-13"):
    paths = gzip.open("data/probes/commoncrawl/wet.paths.gz", "rt").read().split()
    return sorted(paths, key=lambda p: hashlib.md5((seed + p).encode()).hexdigest())[:k]


def download(path):
    local = RAW / Path(path).name
    if not local.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        with requests.get(f"https://data.commoncrawl.org/{path}", headers=HEADERS, stream=True,
                          timeout=120) as r:  # fmt: skip
            r.raise_for_status()
            with open(local, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
    return local


def scan(local, pairs):
    n = uk = with_vat = with_both = 0
    with open(local, "rb") as f:
        for rec in ArchiveIterator(f):
            if rec.rec_type != "conversion":
                continue
            n += 1
            url = rec.rec_headers.get_header("WARC-Target-URI") or ""
            host = urlsplit(url).netloc.lower()
            uk += host.endswith(".uk")
            text = rec.content_stream().read().decode("utf-8", "replace")
            if "VAT" not in text and "GB" not in text:
                continue
            vrns = {v for v, _, ok in find_candidates(text) if ok}
            if not vrns:
                continue
            with_vat += 1
            nums = company_numbers(text)
            if nums:
                with_both += 1
                # a clean pair: one number of each on the page
                if len(vrns) == 1 and len(nums) == 1:
                    pairs.append((next(iter(vrns)), next(iter(nums)), host))
    return n, uk, with_vat, with_both


def main(crawl, k, out_csv):
    started = time.time()
    totals = [0, 0, 0, 0]
    pairs, size = [], 0
    for path in pick(crawl, int(k)):
        local = download(path)
        size += local.stat().st_size
        for i, v in enumerate(scan(local, pairs)):
            totals[i] += v
    con = duckdb.connect()
    con.execute("create table p (vrn varchar, company_number varchar, host varchar)")
    con.executemany("insert into p values (?, ?, ?)", pairs)
    con.execute("copy p to 'data/probes/commoncrawl/wet_pairs.csv' (header)")
    linked = con.sql("""select count(distinct p.vrn) from p
                        join 'data/ch_names.parquet' c using (company_number)""").fetchall()[0][0]
    distinct_vrn = len({p[0] for p in pairs})
    share = 100_000 / int(k)
    rows = [
        ("wet files read", k), ("of all wet files in the crawl", 100_000),
        ("gzip megabytes read", round(size / 1e6)), ("pages", totals[0]),
        ("pages on .uk hosts", totals[1]), ("pages with a valid uk vat number", totals[2]),
        ("pages with a vat number and a company number", totals[3]),
        ("clean pairs (one of each on the page)", len(pairs)),
        ("distinct vat numbers in clean pairs", distinct_vrn),
        ("distinct vat numbers whose company number is a live company", linked),
        ("distinct hosts in clean pairs", len({p[2] for p in pairs})),
        # pages scale with the crawl, distinct numbers do not, a footer is on every page of a
        # site, so only the page count is multiplied up
        ("pages with both, times the share of the crawl not read", round(totals[3] * share)),
        ("seconds", round(time.time() - started)),
    ]  # fmt: skip
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["what", "value"])
        w.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main(*sys.argv[1:4])
