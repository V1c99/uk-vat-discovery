"""Numbers found for more than one company, and how much the sources overlap.

python experiments/cross_sources.py results/probes/cross_sources.csv
"""

import csv
import sys
from collections import defaultdict
from glob import glob

import duckdb
from group_links import Register


def found_pairs():
    out = []
    for f in glob("results/**/candidates.csv", recursive=True):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r["check_digits_ok"] == "True":
                out.append((r["vrn"], r["company_number"], f.split("\\")[1].split("/")[0]))
    for r in csv.DictReader(open("data/probes/commoncrawl/wet_pairs.csv", encoding="utf-8")):
        out.append((r["vrn"], r["company_number"], "crawl page"))
    return out


def main(out_csv):
    pairs = found_pairs()
    companies = defaultdict(set)
    for vrn, number, _ in pairs:
        companies[vrn].add(number)
    shared = {v: c for v, c in companies.items() if len(c) > 1}
    peppol = {
        r[0]
        for r in duckdb.sql("""
        select upper(replace(split_part(split_part("Participant ID", '::', 2), ':', 2), 'gb', ''))
        from read_csv('data/probes/peppol/participants.csv', header = true, all_varchar = true)
        where split_part(split_part("Participant ID", '::', 2), ':', 1) = '9932'""").fetchall()
    }
    crawl = {v for v, _, w in pairs if w == "crawl page"}
    websites = {v for v, _, w in pairs if w == "websites"}
    both = len(crawl & peppol)
    # Chapman's two list estimate. The lists are not independent and overlap by 3, a rough size
    chapman = round((len(peppol) + 1) * (len(crawl) + 1) / (both + 1) - 1)
    rows = [
        ("valid numbers found next to a company, all routes", len(companies)),
        ("numbers found for two or more different companies", len(shared)),
        ("crawl page numbers", len(crawl)),
        ("crawl page numbers also in peppol", both),
        ("register sample website numbers", len(websites)),
        ("register sample website numbers also in peppol", len(websites & peppol)),
        ("peppol numbers", len(peppol)),
        ("two list estimate from peppol and the crawl slice", chapman),
    ]
    reg = Register()
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["what", "value"])
        w.writerows(rows)
        for vrn, cs in sorted(shared.items()):
            owner_sets = [{c} | {n for n, _, _ in reg.owners(c, depth=3) if n} for c in cs]
            related = bool(set.intersection(*owner_sets)) if all(owner_sets) else False
            kind = "same owner, a group number" if related else "no common owner, a platform?"
            w.writerow([f"shared number {vrn}", " ".join(sorted(cs)) + " | " + kind])
            print("shared", vrn, sorted(cs), kind)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main(sys.argv[1])
