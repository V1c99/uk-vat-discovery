"""What the website route cost on this laptop, per company, for Part 3. Read from the files the
runs left behind, nothing is fetched again.

    python experiments/unit_costs.py results/probes/unit_costs.csv
"""

import csv
import gzip
import json
import sys
from pathlib import Path

RUNS = {
    "register sample": ("results/websites", 400, 295),
    "peppol known set": ("results/peppol/websites", 133, 174),
}  # companies and the seconds the first full run took, from its log line


def main(out_csv):
    pages = [json.loads(gzip.decompress(p.read_bytes())) for p in Path("data/pages").glob("*.gz")]
    html = [p for p in pages if p["html"]]
    dns = json.loads(Path("data/dns.json").read_text())
    rows = [
        ("page requests made, both runs", len(pages)),
        ("pages that came back as html", len(html)),
        ("html megabytes", round(sum(len(p["html"]) for p in html) / 1e6, 1)),
        ("domains looked up", len(dns)),
        ("domains that resolve", sum(dns.values())),
    ]
    for name, (folder, n, seconds) in RUNS.items():
        companies = list(csv.DictReader(open(f"{folder}/companies.csv", encoding="utf-8")))
        found = sum(1 for c in companies if c["outcome"] == "strict")
        rows += [
            (f"{name}: companies", n),
            (f"{name}: wall seconds, 12 threads", seconds),
            (f"{name}: strict finds", found),
            (f"{name}: wall seconds per strict find", round(seconds / max(found, 1), 1)),
        ]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["what", "value"])
        w.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main(sys.argv[1])
