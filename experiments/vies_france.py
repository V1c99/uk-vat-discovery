"""France, where a company's VAT number is worked out from its SIREN: FR, a two digit key, then
the SIREN. Two live SARL or SAS from each of ten departements, read from the state's open company
search, the key computed here, then each number in VIES. Where the search shows a different
number, that one goes to VIES too.

    python experiments/vies_france.py results/probes/vies_france.csv

Answers already saved in data/probes/vies are reused, so a second run only asks VIES again for
the numbers that got no answer.
"""

import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import requests

SEARCH = "https://recherche-entreprises.api.gouv.fr/search"
VIES = "https://ec.europa.eu/taxation_customs/vies/rest-api/ms/FR/vat/{}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; uk-vat-research/0.1)"}
RAW = Path("data/probes/vies")
DEPARTEMENTS = ("01", "13", "22", "31", "44", "59", "63", "67", "69", "75")
# France's side answers these when it is busy, they are not an answer about the number
BUSY = ("MS_MAX_CONCURRENT_REQ", "MS_UNAVAILABLE", "TIMEOUT", "SERVICE_UNAVAILABLE")


def fr_vat(siren):
    key = (12 + 3 * (int(siren) % 97)) % 97
    return f"FR{key:02d}{siren}"


def two_from(dep):
    # a page picked by md5, so it is not always the first companies the search returns
    page = int(hashlib.md5(f"2026-11-18{dep}".encode()).hexdigest(), 16) % 40 + 1
    params = {"departement": dep, "etat_administratif": "A", "categorie_entreprise": "PME",
              "nature_juridique": "5499,5710", "per_page": 25, "page": page}  # fmt: skip
    r = requests.get(SEARCH, params=params, headers=HEADERS, timeout=60)
    r.raise_for_status()
    # the filter also matches branches, only companies with their head office there are kept
    return [c for c in r.json()["results"] if c["siege"].get("departement") == dep][:2]


def vies(vat):
    saved = RAW / f"{vat}.json"
    if saved.exists():
        d = json.loads(saved.read_text(encoding="utf-8"))
        if d.get("userError") not in BUSY:
            return d
    for _ in range(8):
        d = requests.get(VIES.format(vat[2:]), headers=HEADERS, timeout=60).json()
        if d.get("userError") not in BUSY:
            break
        time.sleep(15)
    saved.write_text(json.dumps(d, indent=1), encoding="utf-8")
    time.sleep(3)
    return d


def main(out_csv):
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for dep in DEPARTEMENTS:
        for c in two_from(dep):
            vat = fr_vat(c["siren"])
            search_vat = (c.get("tva") or [""])[0]
            d = vies(vat)
            other = vies(search_vat) if search_vat and search_vat != vat else {}
            name_shown = any(x.get("name") not in (None, "", "---") for x in (d, other))
            rows.append([dep, c["siren"], c["date_creation"], vat, search_vat,
                         d.get("userError"), other.get("userError", ""), name_shown])  # fmt: skip
        time.sleep(1)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["departement", "siren", "created", "computed_vat", "search_vat",
                    "vies_on_computed", "vies_on_search_vat", "name_shown"])  # fmt: skip
        w.writerows(rows)
    for row in rows:
        print(row)


if __name__ == "__main__":
    main(sys.argv[1])
