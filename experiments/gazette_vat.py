"""How many Gazette notices mention a VAT number, from the Gazette's own search.

python experiments/gazette_vat.py results/probes/gazette_vat.csv
"""

import csv
import sys
import time

import requests

URL = "https://www.thegazette.co.uk/all-notices/notice/data.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; uk-vat-research/0.1)",
           "Accept": "application/json"}  # fmt: skip
PHRASES = ['"VAT registration number"', '"VAT number"', '"VAT No"', '"VAT reg"',
           '"VAT registration no"', '"Company number"']  # fmt: skip


def total(text):
    r = requests.get(URL, params={"text": text, "results-page-size": 1}, headers=HEADERS,
                     timeout=60)  # fmt: skip
    r.raise_for_status()
    return int(r.json().get("f:total", 0))


def main(out_csv):
    rows = []
    for p in PHRASES:
        rows.append((p, total(p)))
        time.sleep(1)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["search", "notices"])
        w.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main(sys.argv[1])
