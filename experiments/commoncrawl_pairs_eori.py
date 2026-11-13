"""How often a VAT number and a company number on the same page belong together. For the pairs
from the Common Crawl slice, HMRC's open EORI API gives a name for the traders who agreed to share
it, and that name is compared with the Companies House name of the company number on the page.

    python experiments/commoncrawl_pairs_eori.py data/probes/commoncrawl/wet_pairs.csv \
        results/probes/commoncrawl_pairs.csv
"""

import csv
import sys

import duckdb

from ukvat.eori import check
from ukvat.names import same_name


def main(pairs_csv, out_csv):
    rows = duckdb.sql(f"""
        select p.vrn, p.company_number, p.host, c.company_name, c.postcode
        from (select distinct on (vrn) * from read_csv('{pairs_csv}', header = true,
              all_varchar = true) order by vrn) p
        left join 'data/ch_names.parquet' c using (company_number)
        order by p.vrn
    """).fetchall()
    answers = {a["eori"][2:11]: a for a in check([r[0] for r in rows])}
    out = []
    for vrn, number, host, name, postcode in rows:
        a = answers[vrn]
        d = a.get("companyDetails") or {}
        trader = d.get("traderName", "")
        trader_pc = (d.get("address") or {}).get("postcode", "")
        if not a["valid"]:
            verdict = "no eori"
        elif not trader:
            verdict = "eori, no name shared"
        elif same_name(name or "", trader):
            verdict = "same company"
        elif (postcode or "").replace(" ", "") == trader_pc.replace(" ", ""):
            verdict = "other name, same postcode"
        else:
            verdict = "other company"
        out.append([vrn, number, host, name, a["valid"], trader, verdict])
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vrn", "company_number", "host", "ch_name", "eori_valid", "eori_name",
                    "verdict"])  # fmt: skip
        w.writerows(out)
    counts = {}
    for r in out:
        counts[r[-1]] = counts.get(r[-1], 0) + 1
    print(len(out), counts)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
