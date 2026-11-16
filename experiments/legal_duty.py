"""How often a company that is VAT registered, and has a site provably its own, prints the number
there. Regulation 6(1)(g) of the E-Commerce Regulations 2002 asks for it. The companies are the
Peppol known set, so all of them are registered and their number is known.

For the sites that show the company number but no VAT number, the cached html is read again to see
whether the number was there and my reader missed it (in a script, an attribute, a pdf link).

    python experiments/legal_duty.py results/peppol_2000 results/probes/legal_duty.csv
"""

import csv
import gzip
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import duckdb


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (round(100 * (centre - half), 1), round(100 * (centre + half), 1))


def cached_html(url):
    path = Path("data/pages") / (hashlib.sha1(url.encode()).hexdigest() + ".json.gz")
    if not path.exists():
        return ""
    return json.loads(gzip.decompress(path.read_bytes()))["html"]


def missed(sites_rows, vrn):
    """Where the known number is in the raw html of an own site the reader said had none."""
    for s in sites_rows:
        html = cached_html(f"https://{s['domain']}/") or cached_html(f"http://{s['domain']}/")
        if re.search(r"\s?".join(vrn), html):
            return "in the html, not in the text I read"
        if re.search(r"href=\"[^\"]+\.pdf\"", html, re.I):
            return "no number in html, the site links a pdf"
    return "not in the html at all"


def main(folder, out_csv):
    folder = Path(folder)
    con = duckdb.connect()
    con.execute(f"""create view j as
        select c.*, k.peppol_vrn, left(n.sic_1, 2) as sic2
        from read_csv('{folder}/websites/companies.csv', header = true, all_varchar = true) c
        join read_csv('{folder}/known_set.csv', header = true, all_varchar = true) k
            using (company_number)
        left join 'data/ch_names.parquet' n using (company_number)""")
    rows = []
    total = con.execute("select count(*) from j").fetchall()[0][0]
    own = con.execute("select count(*) from j where own_site is not null").fetchall()[0][0]
    shows = con.execute("select count(*) from j where outcome = 'strict'").fetchall()[0][0]
    same = con.execute("select count(*) from j where outcome = 'strict' and vrn = peppol_vrn"
                       ).fetchall()[0][0]  # fmt: skip
    low, high = wilson(shows, own)
    rows += [("registered companies", total), ("with a site showing their company number", own),
             ("of those, printing one VAT number", shows),
             ("percent printing it, 95% interval",
              f"{round(100 * shows / own, 1)} ({low} to {high})"),
             ("printed number equal to Peppol's", same)]  # fmt: skip
    for stratum, n_own, n_shows in con.execute("""select stratum,
            count(*) filter (where own_site is not null), count(*) filter (where outcome = 'strict')
            from j group by all order by all""").fetchall():
        rows.append((f"{stratum}: own site, printing it", f"{n_own}, {n_shows}"))
    loose = con.execute("""select outcome, count(*) filter (where vrn = peppol_vrn),
                                  count(*) filter (where vrn <> peppol_vrn)
                           from j where outcome in ('strict', 'loose_only')
                           group by all""").fetchall()
    for outcome, right, wrong in loose:
        rows.append((f"{outcome}: same as Peppol, different", f"{right}, {wrong}"))
    sites = {}
    for r in csv.DictReader(open(folder / "websites/sites.csv", encoding="utf-8")):
        if r["own_number"] == "True":
            sites.setdefault(r["company_number"], []).append(r)
    silent = con.execute("select company_number, peppol_vrn from j where outcome = "
                         "'own_site_no_vat' order by company_number").fetchall()  # fmt: skip
    why = {}
    for number, vrn in silent:
        reason = missed(sites.get(number, []), vrn)
        why[reason] = why.get(reason, 0) + 1
    rows += [(f"own site, no number printed: {k}", v) for k, v in sorted(why.items())]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["what", "value"])
        w.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
