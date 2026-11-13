"""Are the sites where I found a company's own number also in Common Crawl, and is the page with
the VAT number there. If they are, a bulk corpus could replace crawling site by site.

The index server timed out on most lookups, so this reads the index files through ccindex.py.

    python experiments/commoncrawl_coverage.py results/probes/commoncrawl_coverage.csv
"""

import csv
import sys
from urllib.parse import urlsplit

import ccindex

SITES = ["results/websites/sites.csv", "results/peppol/websites/sites.csv"]
CANDIDATES = ["results/websites/candidates.csv", "results/peppol/websites/candidates.csv"]


def host(url):
    h = urlsplit(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def key(url):
    # pages compared without scheme, www and a trailing slash, so the home page is just the host
    return host(url) + urlsplit(url).path.rstrip("/")


def main(out_csv):
    own = set()
    for f in SITES:
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r["own_number"] == "True":
                own.add(host(r["final_url"]))
    vat_pages = {}
    for f in CANDIDATES:
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r["check_digits_ok"] == "True" and r["own_number_on_page"] == "True":
                vat_pages.setdefault(host(r["page"]), set()).add(key(r["page"]))
    rows = []
    for h in sorted(own):
        ok = [c for c in ccindex.captures(h) if c.get("status") == "200"]
        keys = {key(c["url"]) for c in ok}
        pages = vat_pages.get(h, set())
        rows.append([h, len(ok), h in keys, len(pages), sum(p in keys for p in pages)])
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["host", "pages_in_crawl", "home_page_in_crawl", "vat_pages_found_live",
                    "vat_pages_in_crawl"])  # fmt: skip
        w.writerows(rows)
    with_vat = [r for r in rows if r[3]]
    print(f"{len(rows)} own-site hosts, {sum(1 for r in rows if r[1])} in the crawl, "
          f"{sum(1 for r in rows if r[2])} with their home page. "
          f"Hosts with a vat page found live: {len(with_vat)}, "
          f"with that page in the crawl: {sum(1 for r in with_vat if r[4])}")  # fmt: skip


if __name__ == "__main__":
    main(sys.argv[1])
