"""Does a VAT number date itself. Pairs from Peppol, the crawl pages and the strict finds, and each
band is dated by the 90th percentile of its companies' incorporation dates.

    python experiments/vat_number_age.py results/probes
"""

import csv
import sys
from pathlib import Path

import duckdb

from ukvat.eori import check
from ukvat.names import same_name
from ukvat.vat import WEIGHTS


def scheme(vrn):
    total = sum(int(d) * w for d, w in zip(vrn[:7], WEIGHTS, strict=True)) + int(vrn[7:])
    return "plain" if total % 97 == 0 else "plus55"


def pairs(linked):
    out = {}
    for f in (linked, "results/peppol/linked.csv"):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r["matches"] == "1" and r["looks_like_company"] == "True":
                out.setdefault(r["vrn"], (r["company_number"], "peppol"))
    for r in csv.DictReader(open("data/probes/commoncrawl/wet_pairs.csv", encoding="utf-8")):
        out.setdefault(r["vrn"], (r["company_number"], "crawl page"))
    for f in ("results/websites/companies.csv", "results/peppol/websites/companies.csv"):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r["outcome"] == "strict":
                out.setdefault(r["vrn"], (r["company_number"], "website"))
    return [(v, c, s, scheme(v)) for v, (c, s) in out.items()]


def main(out_dir, linked="results/peppol_2000/linked.csv"):
    out = Path(out_dir)
    con = duckdb.connect()
    con.execute("create table p (vrn varchar, company_number varchar, source varchar, "
                "scheme varchar)")  # fmt: skip
    con.executemany("insert into p values (?, ?, ?, ?)", pairs(linked))
    con.execute("""create table j as
        select p.*, c.incorporated, left(p.vrn, 2) as band
        from p join 'data/ch_names.parquet' c using (company_number)
        where c.incorporated is not null""")
    # companies register after incorporation, so the newest ones date the band
    con.execute("""create table bands as
        select scheme, band, count(*) as pairs,
               median(year(incorporated))::int as median_year,
               quantile_disc(incorporated, 0.9) as issued_about
        from j group by all""")
    con.execute(f"copy (select * from bands order by scheme, band) "
                f"to '{out / 'vat_number_age_bands.csv'}' (header)")  # fmt: skip
    con.execute("""create table flagged as
        select j.*, b.issued_about from j join bands b using (scheme, band)
        where (j.scheme = 'plus55' and b.pairs >= 5
               and j.incorporated > b.issued_about + interval 2 year)
           or (j.scheme = 'plain' and j.incorporated >= date '2012-01-01')""")
    con.execute(f"copy (select vrn, company_number, source, scheme, incorporated, issued_about "
                f"from flagged order by vrn) to '{out / 'vat_number_older_than_company.csv'}' "
                f"(header)")  # fmt: skip
    rho = {s: con.execute("""select corr(a, b) from (
                select rank() over (order by vrn::bigint) a, rank() over (order by incorporated) b
                from j where scheme = ? and incorporated >= ?)""",
                [s, "2010-01-01" if s == "plus55" else "1900-01-01"]).fetchall()[0][0]
           for s in ("plus55", "plain")}  # fmt: skip
    summary = con.execute("""select scheme, count(*), median(year(incorporated))::int,
                             quantile_cont(year(incorporated), 0.1)::int,
                             quantile_cont(year(incorporated), 0.9)::int from j group by all
                             order by 1""").fetchall()  # fmt: skip
    total = con.execute("select count(*) from j").fetchall()[0][0]
    flagged = con.execute("select scheme, count(*) from flagged group by all").fetchall()
    rows = [("pairs with an incorporation date", total)]
    for s, n, med, p10, p90 in summary:
        rows.append((f"{s}: pairs", n))
        rows.append(
            (f"{s}: incorporation year, 10th, median, 90th percentile", f"{p10} {med} {p90}")
        )
    rows += [(f"{s}: rank correlation of number and incorporation date", round(r, 3))
             for s, r in rho.items()]  # fmt: skip
    rows += [(f"{s}: number looks older than the company", n) for s, n in flagged]
    # serials issued per year
    speed = con.execute("""select (max(band::int) - min(band::int)) * 100000.0
                           / (date_diff('day', min(issued_about), max(issued_about)) / 365.25)
                           from bands where scheme = 'plus55' and band::int in (20, 50)
                           """).fetchall()[0][0]  # fmt: skip
    rows.append(("plus55: serials issued per year, band 20 to band 50", round(speed)))
    rows += second_look(con, out)
    with open(out / "vat_number_age.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["what", "value"])
        w.writerows(rows)
    for r in rows:
        print(r)
    chart(con, out)


def second_look(con, out):
    rows = con.execute("""select f.vrn, f.company_number, c.company_name from flagged f
                          join 'data/ch_names.parquet' c using (company_number)""").fetchall()
    answers = {a["eori"][2:11]: a for a in check([r[0] for r in rows])}
    counts = {}
    with open(out / "vat_number_older_second_look.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vrn", "company_number", "company_name", "eori"])
        for vrn, number, name in rows:
            a = answers[vrn]
            trader = (a.get("companyDetails") or {}).get("traderName", "")
            if not a["valid"]:
                seen = "no eori"
            elif not trader:
                seen = "no name shared"
            else:
                seen = "same name" if same_name(name, trader) else "another name"
            counts[seen] = counts.get(seen, 0) + 1
            w.writerow([vrn, number, name, seen])
    return [(f"older than the company, eori says: {k}", v) for k, v in sorted(counts.items())]


def chart(con, out):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    for s, label in (("plain", "mod 97"), ("plus55", "mod 97 after adding 55")):
        xs, ys = zip(*con.execute("select incorporated, vrn::bigint / 100 from j where scheme = ?",
                                  [s]).fetchall(), strict=True)  # fmt: skip
        ax.scatter(xs, ys, s=6, alpha=0.5, label=label)
    ax.set_xlabel("company incorporated")
    ax.set_ylabel("first seven digits of its VAT number")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "vat_number_age.png", dpi=120)


if __name__ == "__main__":
    main(*sys.argv[1:3])
