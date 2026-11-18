"""When HMRC's name for a number is another company, is it the owner, a former owner or a sister.
Owners from experiments/psc_corporate.py, two levels up, previous names included.

    python experiments/group_links.py results/probes/group_links.csv
"""

import csv
import sys

import duckdb

from ukvat.names import core_words, same_name

CH = "data/ch/BasicCompanyDataAsOneFile-*.csv"
PREVIOUS = [f"previousname_{i}companyname" for i in range(1, 11)]


def key(name):
    return " ".join(core_words(name or ""))


def cases():
    out = []
    for r in csv.DictReader(open("results/eori/websites.csv", encoding="utf-8")):
        if r["eori_trader_name"] and not same_name(r["company_name"], r["eori_trader_name"]):
            out.append((r["vrn"], r["company_number"], r["company_name"], r["eori_trader_name"]))
    for r in csv.DictReader(open("results/probes/commoncrawl_pairs.csv", encoding="utf-8")):
        if r["verdict"] in ("other name, same postcode", "other company"):
            out.append((r["vrn"], r["company_number"], r["ch_name"], r["eori_name"]))
    return out


class Register:
    def __init__(self):
        self.con = duckdb.connect()
        self.con.execute(
            "create view psc as select * from "
            "read_csv('data/psc_corporate.csv', header = true, all_varchar = true)"
        )
        self.con.execute("create view names as select company_number, key "
                         "from 'data/ch_names.parquet'")  # fmt: skip

    def companies_called(self, name):
        k = key(name)
        now = {r[0] for r in self.con.execute("select company_number from names where key = ?",
                                              [k]).fetchall()}  # fmt: skip
        # previous names, narrowed with like first and checked with the real key after
        like = "%" + "%".join(k.upper().split()) + "%"
        cols = ", ".join(PREVIOUS)
        where = " or ".join(f"upper({c}) like ?" for c in PREVIOUS)
        rows = self.con.execute(
            f"select companynumber, {cols} from read_csv('{CH}', header = true, "
            f"normalize_names = true, all_varchar = true) where {where}",
            [like] * len(PREVIOUS),
        ).fetchall()
        before = {r[0] for r in rows if any(key(n) == k for n in r[1:] if n)}
        return now, before

    def owners(self, number, depth=2):
        found, todo = set(), {number}
        for _ in range(depth):
            if not todo:
                break
            marks = ",".join("?" * len(todo))
            rows = self.con.execute(
                f"select owner_number, owner_name, ceased from psc "
                f"where company_number in ({marks})",
                list(todo),
            ).fetchall()
            new = {(n or "", key(name), ceased == "True") for n, name, ceased in rows}
            todo = {n for n, _, _ in new if n} - {f[0] for f in found}
            found |= new
        return found


def relation(reg, number, hmrc_name):
    now, before = reg.companies_called(hmrc_name)
    theirs = now | before
    mine = reg.owners(number)
    k = key(hmrc_name)
    for n, okey, ceased in mine:
        if n in theirs or okey == k:
            return ("hmrc name is a former owner" if ceased else "hmrc name is an owner"), theirs
    for _n, okey, _ in mine:
        # Independent Vetcare Finance Limited owned Inspiring Vet Care, HMRC: Independent Vetcare
        if okey.startswith(k) or k.startswith(okey):
            return "an owner has nearly that name", theirs
    mine_n = {n for n, _, _ in mine if n}
    mine_k = {okey for _, okey, _ in mine}
    for t in theirs:
        t_owners = reg.owners(t)
        if mine_n & {n for n, _, _ in t_owners if n} or mine_k & {okey for _, okey, _ in t_owners}:
            return "same owner", theirs
    return "no link found", theirs


def main(out_csv):
    reg = Register()
    rows = []
    for vrn, number, name, hmrc_name in cases():
        rel, theirs = relation(reg, number, hmrc_name)
        rows.append([vrn, number, name or "", hmrc_name, " ".join(sorted(theirs)), rel])
        print(name, "|", hmrc_name, "|", rel)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vrn", "company_number", "company_name", "hmrc_name",
                    "companies_with_hmrc_name", "relation"])  # fmt: skip
        w.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1])
