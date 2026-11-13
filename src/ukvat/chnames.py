"""Every Companies House name reduced to its key words, so another source's names can be looked
up without fuzzy matching. Writes data/ch_names.parquet (under a minute for 5.7 million names).

    python -m ukvat.chnames
    python -m ukvat.chnames link data/probes/peppol/cards_full.csv results/peppol/linked.csv
"""

import csv
import sys
from collections import defaultdict

import duckdb

from ukvat.names import core_words, looks_like_company, words

CH = "data/ch/BasicCompanyDataAsOneFile-*.csv"
OUT = "data/ch_names.parquet"
ENDINGS = {"limited", "ltd", "plc", "llp"}


def build():
    con = duckdb.connect()
    rows = con.sql(f"""
        select companynumber, companyname, companystatus, regaddresspostcode,
               accountsaccountcategory, incorporationdate, siccodesictext_1
        from read_csv('{CH}', header = true, normalize_names = true, all_varchar = true)
    """).fetchall()
    # executemany into duckdb took over ten minutes, a csv in between takes seconds
    tmp = "data/ch_names.csv"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["company_number", "company_name", "status", "postcode", "accounts",
                    "incorporated", "sic_1", "key", "key_ending_only"])  # fmt: skip
        for r in rows:
            name = r[1] or ""
            # key drops the filler words too, key_ending_only only the legal ending
            only = " ".join(x for x in words(name) if x not in ENDINGS)
            w.writerow([*r, " ".join(core_words(name)), only])
    con.execute(f"""copy (select * replace (strptime(incorporated, '%d/%m/%Y')::date
                                            as incorporated)
                          from read_csv('{tmp}', header = true, all_varchar = true))
                    to '{OUT}' (format parquet)""")  # fmt: skip
    print(f"{len(rows)} names keyed")


def link(cards_csv, out_csv):
    """Exact match on the key. Reports how many companies share it, that is the whole problem."""
    cards = list(csv.DictReader(open(cards_csv, encoding="utf-8")))
    by_key = defaultdict(list)
    keys = {" ".join(core_words(c["name"])) for c in cards}
    con = duckdb.connect()
    con.execute("create temp table k (key varchar)")
    con.executemany("insert into k values (?)", [(k,) for k in keys])
    found_rows = con.sql(f"""select key, company_number, company_name, status, postcode, accounts
                             from '{OUT}' join k using (key)""").fetchall()  # fmt: skip
    for row in found_rows:
        by_key[row[0]].append(row[1:])
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vrn", "peppol_name", "looks_like_company", "matches", "company_number",
                    "company_name", "status", "postcode", "accounts"])  # fmt: skip
        for c in cards:
            # the snapshot only holds live companies, so every match is a live one
            found = by_key.get(" ".join(core_words(c["name"])), [])
            one = found[0] if len(found) == 1 else (None,) * 5
            company = looks_like_company(c["name"])
            name = c["name"] if company else ""
            w.writerow([c["vrn"], name, company, len(found), *one])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "link":
        link(sys.argv[2], sys.argv[3])
    else:
        build()
