"""The Peppol Directory, the e-invoicing network's public list of who can receive invoices.

In Peppol a UK business can be registered under scheme 9932, which is its VAT number. That makes
it a source of VAT numbers that does not come from websites, and a set where I know the right
answer before I look.

    python -m ukvat.peppol data/probes/peppol/participants.csv results/peppol
"""

import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import duckdb
import requests

from ukvat.names import looks_like_company
from ukvat.vat import check_digits_ok

SEARCH = "https://directory.peppol.eu/search/1.0/json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; uk-vat-research/0.1)"}
RAW = Path("data/probes/peppol/cards")


def uk_numbers(participants_csv):
    rows = duckdb.sql(f"""
        select split_part(split_part("Participant ID", '::', 2), ':', 2) as value
        from read_csv('{participants_csv}', header = true, all_varchar = true)
        where split_part(split_part("Participant ID", '::', 2), ':', 1) = '9932'
    """).fetchall()
    # most are written gb123456789, a few without gb. the raw value is kept for the lookup,
    # the first run sent the bare digits and 190 of 200 lookups came back empty
    raw = {}
    for (value,) in rows:
        vrn = value.upper().replace("GB", "").replace(" ", "")
        raw.setdefault(vrn, value)
    nine = [v for v in raw if len(v) == 9 and v.isdigit()]
    good = {v: raw[v] for v in nine if check_digits_ok(v)}
    total = duckdb.sql(f"select count(*) from read_csv('{participants_csv}', header = true)")
    counts = {
        "participants_all_countries": total.fetchall()[0][0],
        "scheme_9932_ids": len(rows),
        "with_gb_prefix": sum(1 for (v,) in rows if v.lower().startswith("gb")),
        "distinct_numbers": len(raw),
        "distinct_nine_digits": len(nine),
        "distinct_nine_digits_pass_check": len(good),
    }
    return good, counts


def card(value):
    """The business card behind one participant. Cached, the API allows 2 queries a second."""
    path = RAW / f"{value}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    time.sleep(0.6)
    r = requests.get(SEARCH, params={"participant": f"iso6523-actorid-upis::9932:{value}"},
                     headers=HEADERS, timeout=30)  # fmt: skip
    r.raise_for_status()
    RAW.mkdir(parents=True, exist_ok=True)
    path.write_text(r.text, encoding="utf-8")
    return r.json()


def pick(numbers, n=200, seed="2026-11-13"):
    return sorted(numbers, key=lambda v: hashlib.md5((seed + v).encode()).hexdigest())[:n]


def main(participants_csv, out_dir, n=200):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    numbers, counts = uk_numbers(participants_csv)
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["what", "count"])
        w.writerows(counts.items())
    rows = []
    # the order is md5 of the seed and the number, so a bigger n keeps the cards of a smaller one
    for vrn in pick(list(numbers), n):
        matches = card(numbers[vrn]).get("matches", [])
        entity = (matches[0]["entities"] or [{}])[0] if matches else {}
        names = entity.get("name") or [{}]
        ids = entity.get("identifiers", [])
        rows.append({
            "vrn": vrn,
            "name": names[0].get("name", ""),
            "country": entity.get("countryCode", ""),
            "reg_date": entity.get("regDate", ""),
            "other_ids": " ".join(f"{i['scheme']}:{i['value']}" for i in ids),
            "website": " ".join(entity.get("websites", [])),
        })  # fmt: skip
    # the full names stay in data/ for the linking. the committed copy drops names that look
    # like a person's, some cards are sole traders
    write(RAW.parent / ("cards_full.csv" if n == 200 else f"cards_full_{n}.csv"), rows)
    public = [
        {**r, "looks_like_company": looks_like_company(r["name"]),
         "name": r["name"] if looks_like_company(r["name"]) else ""}
        for r in rows
    ]  # fmt: skip
    write(out / "cards.csv", public)
    print(counts, f"{len(rows)} cards read")


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 200)
