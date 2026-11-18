"""Which public sector spend files have a supplier VAT number column. Only the header line is read.

python experiments/spend_headers.py results/probes/spend_headers.csv
"""

import csv
import io
import re
import sys
import time

import requests

CKAN = "https://ckan.publishing.service.gov.uk/api/action/package_search"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; uk-vat-research/0.1)"}
VAT_ID = re.compile(r"vat\s*(reg|registration|number|no\b|id\b)", re.I)
COMPANY_NO = re.compile(r"compan(y|ies)\s*(house|reg|number|no)|\bcrn\b", re.I)


def packages(query, rows=1000):
    r = requests.get(CKAN, params={"q": query, "rows": rows}, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.json()["result"]["results"]


def header_line(url):
    try:
        with requests.get(url, headers=HEADERS, timeout=(10, 20), stream=True) as r:
            if r.status_code != 200:
                return None
            chunk = next(r.iter_content(16384), b"")
    except requests.RequestException:
        return None
    text = chunk.decode("utf-8-sig", "replace")
    first = next(csv.reader(io.StringIO(text.splitlines()[0] if text else "")), [])
    return [c.strip() for c in first]


def main(out_csv):
    by_publisher = {}
    for q in ('"spend over 500"', '"over 25000"', '"spend over 25k"'):
        for p in packages(q):
            org = (p.get("organization") or {}).get("title", "")
            csvs = [x for x in p.get("resources", []) if (x.get("format") or "").upper() == "CSV"]
            if org and csvs and org not in by_publisher:
                newest = max(csvs, key=lambda x: x.get("created") or "")
                by_publisher[org] = newest["url"]
    rows = []
    for org, url in sorted(by_publisher.items()):
        cols = header_line(url)
        time.sleep(0.5)
        if not cols:
            continue
        line = " | ".join(cols)
        rows.append([org, url, bool(VAT_ID.search(line)), bool(COMPANY_NO.search(line)), line])
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["publisher", "url", "has_vat_number_column", "has_company_number_column",
                    "header"])  # fmt: skip
        w.writerows(rows)
    print(f"{len(by_publisher)} publishers, {len(rows)} headers read, "
          f"{sum(r[2] for r in rows)} with a VAT number column, "
          f"{sum(r[3] for r in rows)} with a company number column")  # fmt: skip


if __name__ == "__main__":
    main(sys.argv[1])
