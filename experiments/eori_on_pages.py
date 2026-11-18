"""EORI numbers printed on pages. A VAT registered trader's EORI is GB, the VAT number and 000, so
an EORI on a page is a VAT number written another way. The same two piles as
says_not_registered.py: the pages the website route fetched and the four crawl text files.

    python experiments/eori_on_pages.py results/probes/eori_on_pages.csv
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
from ukvat.vat import check_digits_ok, digits, find_candidates

# the word EORI, then GB or XI (Northern Ireland) and 12 digits. Some pages drop the prefix
EORI = re.compile(r"\bEORI\b[^0-9]{0,40}?((?:GB|XI)?[\s:]*(?:\d\s?){11}\d)(?!\d)", re.I)
# a plain "eori" in the text also matched "theories" and the French "categorie"
WORD = re.compile(r"\bEORI\b", re.I)


def eoris_in(text):
    out = []
    for m in EORI.finditer(text):
        n = digits(m.group(1))
        vrn = n[:9]
        vat_inside = n.endswith("000") and check_digits_ok(vrn)
        # the VAT number somewhere else on the page, not only inside the EORI
        rest = text[: m.start()] + text[m.end() :]
        also = vat_inside and any(v == vrn for v, _, ok in find_candidates(rest) if ok)
        out.append([n, vat_inside, also])
    return out


def main(out_csv):
    rows = []
    read = {"fetched": 0, "crawl": 0}
    mention = {"fetched": 0, "crawl": 0}
    for p in Path("data/pages").glob("*.json.gz"):
        page = json.loads(gzip.decompress(p.read_bytes()))
        read["fetched"] += 1
        if page["html"] and "eori" in page["html"].lower():
            text = text_of(page["html"])
            if WORD.search(text):
                mention["fetched"] += 1
                host = urlsplit(page["final_url"]).netloc
                rows += [["fetched", host, *r] for r in eoris_in(text)]
    for f in sorted(Path("data/probes/commoncrawl/wet").glob("*.wet.gz")):
        with open(f, "rb") as fh:
            for rec in ArchiveIterator(fh):
                if rec.rec_type != "conversion":
                    continue
                read["crawl"] += 1
                text = rec.content_stream().read().decode("utf-8", "replace")
                if WORD.search(text):
                    mention["crawl"] += 1
                    host = urlsplit(rec.rec_headers.get_header("WARC-Target-URI")).netloc
                    rows += [["crawl", host, *r] for r in eoris_in(text)]
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["pile", "host", "eori", "vat_inside", "vat_also_on_page"])
        w.writerows(rows)
    summary = Path(out_csv).with_name(Path(out_csv).stem + "_summary.csv")
    with open(summary, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["what", "value"])
        for pile in ("fetched", "crawl"):
            w.writerow([f"{pile}: pages read", read[pile]])
            w.writerow([f"{pile}: pages with the word EORI", mention[pile]])
    print(read, mention, len(rows), "eori numbers")


if __name__ == "__main__":
    main(sys.argv[1])
