"""Every UK card under scheme 9932 from Peppol's full export, 12.6 GB unpacked, read as a stream.

python experiments/peppol_export.py data/probes/peppol/uk_cards.csv
"""

import csv
import gzip
import io
import sys

import requests

URL = "https://directory.peppol.eu/export/businesscards-csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; uk-vat-research/0.1)"}


def main(out_csv):
    # the document types column is one huge quoted cell per row
    csv.field_size_limit(50_000_000)
    rows = kept = 0
    with requests.get(URL, headers=HEADERS, stream=True, timeout=300) as r:
        r.raise_for_status()
        r.raw.decode_content = False
        text = io.TextIOWrapper(
            gzip.GzipFile(fileobj=r.raw), encoding="utf-8", errors="replace", newline=""
        )
        reader = csv.reader(text, delimiter=";")
        head = next(reader)
        col = {name: i for i, name in enumerate(head)}
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["participant", "name", "country", "reg_date", "websites"])
            for row in reader:
                rows += 1
                if "::9932:" not in row[0]:
                    continue
                kept += 1
                w.writerow([
                    row[0].split("::")[1],
                    row[col["Names (per-row)"]],
                    row[col["Country code"]],
                    row[col["Registration date"]],
                    row[col["Websites"]],
                ])  # fmt: skip
                if kept % 5000 == 0:
                    print(kept, "kept of", rows, flush=True)
    print(f"{rows} cards read, {kept} under scheme 9932")


if __name__ == "__main__":
    main(sys.argv[1])
