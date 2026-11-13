"""How many distinct hosts in the whole October crawl show a VAT number next to a company number.
The slice read 4 of 100,000 text files. A host with p pages in the crawl lands in the slice with a
chance of about 1 - (1 - 4/100000)^p, so each host seen counts as 1 over that chance
(Horvitz-Thompson). It assumes the pair is on every page of the host, a footer usually is, which
makes p too big for some hosts and the total too small, so it is a floor.

    python experiments/commoncrawl_estimate.py 4 results/probes/commoncrawl_estimate.csv
"""

import csv
import math
import sys

import ccindex


def main(files_read, out_csv):
    f = int(files_read) / 100_000
    hosts = sorted({r["host"] for r in csv.DictReader(open("data/probes/commoncrawl/wet_pairs.csv",
                                                             encoding="utf-8"))})  # fmt: skip
    rows = []
    for h in hosts:
        p = sum(1 for c in ccindex.captures(h) if c.get("status") == "200")
        chance = 1 - (1 - f) ** max(p, 1)
        rows.append([h, p, round(chance, 6), round(1 / chance)])
    total = sum(r[3] for r in rows)
    # each host is in or out on its own, so the variance is the sum of w * (w - 1)
    se = round(math.sqrt(sum(r[3] * (r[3] - 1) for r in rows)))
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["host", "pages_in_crawl", "chance_in_slice", "weight"])
        w.writerows(rows)
        w.writerow(["all hosts, estimate", sum(r[1] for r in rows), "", total])
        w.writerow(["all hosts, standard error", "", "", se])
    small = sorted(r[1] for r in rows)
    print(f"{len(rows)} hosts, median pages {small[len(small) // 2]}, "
          f"estimate {total:,} hosts, standard error {se:,}")  # fmt: skip


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
