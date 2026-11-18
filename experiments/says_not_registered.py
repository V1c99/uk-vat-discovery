"""Pages that say the business is not VAT registered, in the fetched pages and the four crawl
files.

    python experiments/says_not_registered.py results/probes/says_not_registered.csv
"""

import csv
import gzip
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

from warcio.archiveiterator import ArchiveIterator

from ukvat.page import text_of

SAYS = re.compile(
    r"not (?:currently )?(?:VAT[- ]registered|registered for VAT)|"
    r"no VAT (?:is |will be )?(?:charged|added)|we do not charge VAT|"
    r"VAT is not (?:charged|applicable)|below the VAT threshold",
    re.I,
)


def hits_in(text):
    m = SAYS.search(text)
    return text[max(0, m.start() - 80) : m.end() + 80] if m else None


def main(out_csv):
    rows = []
    for p in Path("data/pages").glob("*.json.gz"):
        page = json.loads(gzip.decompress(p.read_bytes()))
        if page["html"] and "VAT" in page["html"]:
            s = hits_in(text_of(page["html"]))
            if s:
                rows.append(["fetched", urlsplit(page["final_url"]).netloc, s])
    crawl_pages = 0
    for f in sorted(Path("data/probes/commoncrawl/wet").glob("*.wet.gz")):
        with open(f, "rb") as fh:
            for rec in ArchiveIterator(fh):
                if rec.rec_type != "conversion":
                    continue
                crawl_pages += 1
                text = rec.content_stream().read().decode("utf-8", "replace")
                if "VAT" in text:
                    s = hits_in(text)
                    if s:
                        host = urlsplit(rec.rec_headers.get_header("WARC-Target-URI")).netloc
                        rows.append(["crawl", host, s])
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["pile", "host", "text"])
        w.writerows(rows)
    for pile in ("fetched", "crawl"):
        hosts = {r[1] for r in rows if r[0] == pile}
        print(pile, len([r for r in rows if r[0] == pile]), "pages,", len(hosts), "hosts")
    print("crawl pages read:", crawl_pages)


if __name__ == "__main__":
    main(sys.argv[1])
