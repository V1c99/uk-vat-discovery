"""The customer's problem, in public. St Helens and Knowsley Teaching Hospitals NHS Trust's spend
file is the only one of the 112 that fills its VAT column: a buyer's own supplier list with the
VAT number next to each supplier. Three questions on it.

1. How many of its numbers are already in Peppol.
2. Does HMRC's EORI record agree with the name the hospital has.
3. Could the website route have found them without the hospital's file.

    python experiments/nhs_ledger.py results/probes/nhs_ledger.csv results/probes/nhs_ledger
"""

import csv
import hashlib
import io
import re
import sys
from pathlib import Path

import duckdb

from ukvat.eori import check
from ukvat.names import core_words, looks_like_company, same_name
from ukvat.vat import check_digits_ok


def ledger():
    files = csv.DictReader(open("results/probes/spend_headers.csv", encoding="utf-8"))
    head = next(r for r in files if r["publisher"].startswith("St Helens"))
    path = Path("data/probes/spend") / (hashlib.sha1(head["url"].encode()).hexdigest() + ".csv")
    rows = csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig", errors="replace")))
    suppliers = {}
    for r in rows:
        vrn = re.sub(r"\D", "", r["VAT Registration Number"])[-9:]
        if check_digits_ok(vrn):
            suppliers.setdefault(vrn, (r["Supplier"].strip(), r["Supplier Postcode"].strip()))
    return suppliers


def main(out_csv, out_dir):
    suppliers = ledger()
    peppol = {
        r[0]
        for r in duckdb.sql("""
        select upper(replace(split_part(split_part("Participant ID", '::', 2), ':', 2), 'gb', ''))
        from read_csv('data/probes/peppol/participants.csv', header = true, all_varchar = true)
        where split_part(split_part("Participant ID", '::', 2), ':', 1) = '9932'""").fetchall()
    }
    answers = {a["eori"][2:11]: a for a in check(sorted(suppliers))}
    con = duckdb.connect()
    rows, to_run = [], []
    for vrn, (name, pc) in sorted(suppliers.items()):
        a = answers[vrn]
        trader = (a.get("companyDetails") or {}).get("traderName", "")
        if not a["valid"]:
            eori = "no eori"
        elif not trader:
            eori = "eori, no name shared"
        else:
            eori = "same name" if same_name(name, trader) else "other name: " + trader
        found = con.execute("select company_number, company_name from 'data/ch_names.parquet' "
                            "where key = ?", [" ".join(core_words(name))]).fetchall()  # fmt: skip
        if len(found) == 1 and looks_like_company(name):
            number, ch_name = found[0]
            to_run.append({"stratum": "nhs", "company_number": number, "company_name": ch_name,
                           "postcode": pc, "ledger_vrn": vrn})  # fmt: skip
        rows.append(
            [vrn, name if looks_like_company(name) else "", vrn in peppol, eori, len(found)]
        )
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vrn", "supplier", "in_peppol", "eori", "companies_with_that_name"])
        w.writerows(rows)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    with open(Path(out_dir) / "linked.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(to_run[0]))
        w.writeheader()
        w.writerows(to_run)
    print(f"{len(rows)} numbers, {sum(r[2] for r in rows)} in peppol, "
          f"{sum(1 for r in rows if r[3] == 'same name')} with the same eori name, "
          f"{sum(1 for r in rows if r[3].startswith('other'))} with another eori name, "
          f"{len(to_run)} linked to one company")  # fmt: skip


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
