"""Puts my HMRC checks next to what was found, and says for each number whether HMRC agrees.

    python -m ukvat.score results/hmrc/to_check.csv results/hmrc/checks.csv \
        results/hmrc/scored.csv

verdict:
  right company       live, and HMRC's name is the company's name (same key words)
  same postcode only  live, another name at the company's postcode, and fewer than 100 companies
                      sit at that postcode. A VAT group looks like this, read one by one
  someone else        live, another name, and the postcode is different or is one of the
                      crowded ones (a third of live companies sit at a postcode with 100 or more,
                      sql/crowding.sql), so it proves nothing
  not registered      HMRC says the number is not a live registration
  not checked         no check yet

A different postcode is never held against a match: on the 29 page pairs where HMRC's name was
the company's own, the postcode differed in 8 (results/probes/commoncrawl_pairs.csv).
"""

import csv
import sys
from functools import cache

from ukvat.names import same_name

CROWDED = "results/probes/crowded_postcodes.csv"


def postcode(s):
    return (s or "").replace(" ", "").upper()


@cache
def crowded():
    return {r["postcode"] for r in csv.DictReader(open(CROWDED, encoding="utf-8"))}


def verdict(found, check):
    if check is None:
        return "not checked"
    if check["valid"] != "True":
        return "not registered"
    if same_name(found["company_name"] or "", check["hmrc_name"] or ""):
        return "right company"
    pc = postcode(found["postcode"])
    if pc and pc == postcode(check["hmrc_postcode"]) and pc not in crowded():
        return "same postcode only"
    return "someone else"


def main(todo_csv, checks_csv, out_csv):
    checks = {r["vrn"]: r for r in csv.DictReader(open(checks_csv, encoding="utf-8"))}
    rows = []
    for f in csv.DictReader(open(todo_csv, encoding="utf-8")):
        c = checks.get(f["vrn"])
        rows.append({**f, "hmrc_name": (c or {}).get("hmrc_name", ""),
                     "hmrc_postcode": (c or {}).get("hmrc_postcode", ""),
                     "verdict": verdict(f, c)})  # fmt: skip
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print({v: sum(1 for r in rows if r["verdict"] == v) for v in {r["verdict"] for r in rows}})


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
