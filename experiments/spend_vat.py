"""The spend files that do have a VAT number column: how full it is and whether the numbers pass
the check digits. Downloads each file whole into data/probes/spend/.

    python experiments/spend_vat.py results/probes/spend_headers.csv results/probes/spend_vat.csv
"""

import csv
import hashlib
import io
import re
import sys
from pathlib import Path

import requests

from ukvat.names import core_words, looks_like_company
from ukvat.vat import check_digits_ok

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; uk-vat-research/0.1)"}
RAW = Path("data/probes/spend")


def download(url):
    path = RAW / (hashlib.sha1(url.encode()).hexdigest() + ".csv")
    if not path.exists():
        r = requests.get(url, headers=HEADERS, timeout=120)
        r.raise_for_status()
        RAW.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    return path.read_bytes().decode("utf-8-sig", "replace")


def main(headers_csv, out_csv):
    files = [r for r in csv.DictReader(open(headers_csv, encoding="utf-8"))
             if r["has_vat_number_column"] == "True"]  # fmt: skip
    out = []
    pairs = {}
    for f in files:
        rows = list(csv.reader(io.StringIO(download(f["url"]))))
        head = [c.strip().lower() for c in rows[0]]
        vat_col = next(i for i, c in enumerate(head) if re.search(r"vat\s*reg", c))
        sup_col = next(i for i, c in enumerate(head) if "supplier" in c or "vendor" in c)
        body = [r for r in rows[1:] if len(r) > max(vat_col, sup_col)]
        filled = [r for r in body if re.sub(r"\D", "", r[vat_col])]
        vrns = {re.sub(r"\D", "", r[vat_col])[-9:] for r in filled}
        for r in filled:
            v = re.sub(r"\D", "", r[vat_col])[-9:]
            if check_digits_ok(v) and looks_like_company(r[sup_col]):
                pairs[v] = " ".join(core_words(r[sup_col]))
        out.append([f["publisher"], len(body), len(filled), len({r[sup_col] for r in body}),
                    len(vrns), sum(check_digits_ok(v) for v in vrns)])  # fmt: skip
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["publisher", "rows", "rows_with_vat", "suppliers", "distinct_vat_numbers",
                    "pass_check_digits"])  # fmt: skip
        w.writerows(out)
    for row in out:
        print(row)
    print(f"{len(pairs)} distinct valid numbers next to a company name, across the files")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
