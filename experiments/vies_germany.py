"""What VIES says about a German VAT ID. The two numbers are the ones the website route met on a
German group's Impressum page (results/websites/candidates.csv, E.R.K SYSTEMS LIMITED).

    python experiments/vies_germany.py results/probes/vies_germany.csv 250965905 136632461
"""

import csv
import json
import sys
import time
from pathlib import Path

import requests

URL = "https://ec.europa.eu/taxation_customs/vies/rest-api/ms/DE/vat/{}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; uk-vat-research/0.1)"}
RAW = Path("data/probes/vies")


def main(out_csv, numbers):
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for n in numbers:
        for _ in range(3):
            r = requests.get(URL.format(n), headers=HEADERS, timeout=60)
            if r.ok and r.text.strip():
                break
            time.sleep(5)
        d = r.json()
        (RAW / f"DE{n}.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
        rows.append([f"DE{n}", d.get("isValid"), d.get("name") not in (None, "", "---"),
                     d.get("address") not in (None, "", "---"), d.get("requestDate")])  # fmt: skip
        time.sleep(2)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vat_id", "valid", "name_shown", "address_shown", "checked_at"])
        w.writerows(rows)
    for row in rows:
        print(row)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
