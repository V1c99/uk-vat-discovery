"""Which companies are controlled by another company. Companies House publishes "persons with
significant control" as 33 zip files of json lines. Only the lines where the controller is
itself a company are kept.

I need this for the cases where HMRC's name for a VAT number is not the company I found it for.
If that name is the company's owner, the number is a group's number and not a mistake.

    python experiments/psc_corporate.py 2026-11-13 33 data/psc_corporate.csv
"""

import csv
import json
import sys
import zipfile
from pathlib import Path

import requests

BASE = "https://download.companieshouse.gov.uk"
RAW = Path("data/psc")
# a housing association or a council is a "legal person", not a corporate entity. The first run
# kept only corporate entities and missed Torus, which owns one of the cases
KINDS = (b"corporate-entity-person-with-significant-control",
         b"legal-person-person-with-significant-control")  # fmt: skip


def part(day, i, n):
    path = RAW / f"psc-snapshot-{day}_{i}of{n}.zip"
    if not path.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        with requests.get(f"{BASE}/{path.name}", stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
    return path


def main(day, n, out_csv):
    n = int(n)
    kept = 0
    with open(out_csv, "w", newline="", encoding="utf-8") as out:
        w = csv.writer(out)
        w.writerow(["company_number", "owner_name", "owner_number", "ceased"])
        for i in range(1, n + 1):
            with zipfile.ZipFile(part(day, i, n)) as z:
                for name in z.namelist():
                    for line in z.open(name):
                        if not any(k in line for k in KINDS):
                            continue
                        d = json.loads(line)
                        data = d.get("data", {})
                        ident = data.get("identification") or {}
                        w.writerow([
                            d.get("company_number", ""),
                            data.get("name", ""),
                            ident.get("registration_number", ""),
                            "ceased_on" in data,
                        ])  # fmt: skip
                        kept += 1
            print(f"part {i} of {n}, {kept} corporate owners so far", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])
