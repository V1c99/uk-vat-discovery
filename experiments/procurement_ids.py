"""Which identifiers do UK procurement notices carry for suppliers. Find a Tender's OCDS feed,
one week of notices. Looking for any VAT scheme next to the company number.

    python experiments/procurement_ids.py 2026-11-03 2026-11-10 results/probes/procurement_ids.csv
"""

import collections
import csv
import json
import sys
import time
from pathlib import Path

import requests

API = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; uk-vat-research/0.1)"}
RAW = Path("data/probes/procurement")


def releases(start, end):
    url = f"{API}?updatedFrom={start}T00:00:00&updatedTo={end}T00:00:00&limit=100"
    page = 0
    while url:
        path = RAW / f"{start}_{end}_{page}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            time.sleep(1)
            r = requests.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()
            data = r.json()
            RAW.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data), encoding="utf-8")
        yield from data.get("releases", [])
        url = (data.get("links") or {}).get("next")
        page += 1


def main(start, end, out_csv):
    schemes = collections.Counter()
    supplier_schemes = collections.Counter()
    parties = suppliers = notices = 0
    for rel in releases(start, end):
        notices += 1
        for p in rel.get("parties", []):
            parties += 1
            ids = [p.get("identifier") or {}] + (p.get("additionalIdentifiers") or [])
            names = {i.get("scheme") for i in ids if i.get("scheme")}
            schemes.update(names)
            if "supplier" in (p.get("roles") or []) or "tenderer" in (p.get("roles") or []):
                suppliers += 1
                supplier_schemes.update(names)
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scheme", "parties", "supplier_parties"])
        for s, n in schemes.most_common():
            w.writerow([s, n, supplier_schemes.get(s, 0)])
    print(f"{notices} notices, {parties} parties, {suppliers} supplier parties")
    print(schemes.most_common(15))


if __name__ == "__main__":
    main(*sys.argv[1:4])
