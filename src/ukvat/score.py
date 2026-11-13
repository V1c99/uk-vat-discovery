"""Puts my HMRC checks next to what was found, and says for each number whether HMRC agrees.

    python -m ukvat.score results/hmrc/to_check.csv results/hmrc/checks.csv \
        results/hmrc/scored.csv

verdict:
  right company       live, and HMRC's name is the company's name (same key words)
  same postcode only  live, another name at the company's postcode. A VAT group looks like this,
                      so does a formation agent's address with thousands of companies on it,
                      these are read one by one
  someone else        live, another name at another postcode
  not registered      HMRC says the number is not a live registration
  not checked         no check yet
"""

import csv
import sys

from ukvat.names import same_name


def postcode(s):
    return (s or "").replace(" ", "").upper()


def verdict(found, check):
    if check is None:
        return "not checked"
    if check["valid"] != "True":
        return "not registered"
    if same_name(found["company_name"] or "", check["hmrc_name"] or ""):
        return "right company"
    pc = postcode(found["postcode"])
    if pc and pc == postcode(check["hmrc_postcode"]):
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
