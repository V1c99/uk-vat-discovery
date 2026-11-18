"""What Amazon's and eBay's robots.txt allow on their UK seller pages.

python experiments/marketplace_robots.py results/probes/marketplace_robots.csv
"""

import csv
import sys
from datetime import date
from pathlib import Path
from urllib.robotparser import RobotFileParser

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; uk-vat-research/0.1)"}
RAW = Path("data/probes/marketplaces")
PAGES = {
    "amazon": ("https://www.amazon.co.uk/robots.txt",
               {"seller profile": "https://www.amazon.co.uk/sp?seller=A1B2C3D4E5F6G7"}),
    "ebay": ("https://www.ebay.co.uk/robots.txt",
             {"store": "https://www.ebay.co.uk/str/somestore",
              "user profile": "https://www.ebay.co.uk/usr/someuser",
              "listing": "https://www.ebay.co.uk/itm/123456789012"}),
}  # fmt: skip
AGENTS = ["CCBot", "*"]


def main(out_csv):
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for site, (robots_url, pages) in PAGES.items():
        text = requests.get(robots_url, headers=HEADERS, timeout=30).text
        (RAW / f"{site}_robots.txt").write_text(text, encoding="utf-8")
        rp = RobotFileParser()
        rp.parse(text.splitlines())
        for kind, url in pages.items():
            rows.append([site, kind, *(rp.can_fetch(a, url) for a in AGENTS), date.today()])
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["site", "page", "common_crawl_allowed", "any_crawler_allowed", "read_on"])
        w.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main(sys.argv[1])
