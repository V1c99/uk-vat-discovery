"""What filed accounts say about VAT, from two days of Companies House's accounts bulk data.

python experiments/accounts_vat.py results/probes data/accounts/*.zip
"""

import csv
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from ukvat.page import text_of
from ukvat.vat import find_candidates

VAT_TAG = re.compile(rb'name="[A-Za-z0-9\-]+:([A-Za-z]*VAT[A-Za-z]*)"')
TRADING_NAME = re.compile(rb'name="[A-Za-z0-9\-]+:EntityTradingName"')
# turnover over the VAT threshold would mean "must be registered"
TURNOVER = re.compile(rb'name="[A-Za-z0-9\-]+:(?:TurnoverRevenue|Turnover)"')
SAYS = {
    "vat group": re.compile(
        r"group registration for VAT|VAT group|group VAT registration|registered for VAT as "
        r"(?:part|a member) of a group|member of a (?:VAT|group) registration",
        re.I,
    ),
    "not registered": re.compile(
        r"not (?:be )?registered for (?:VAT|value added tax)|is not VAT registered|"
        r"not VAT[- ]registered|deregistered for VAT",
        re.I,
    ),
    "registered": re.compile(r"(?<!not )(?<!not be )registered for (?:VAT|value added tax)", re.I),
}


def snippet(text, m, width=80):
    return text[max(0, m.start() - width) : m.end() + width].strip()


def main(out_dir, *zips):
    out = Path(out_dir)
    counts = Counter()
    statements, printed = [], defaultdict(set)
    for zpath in zips:
        with zipfile.ZipFile(zpath) as z:
            for name in z.namelist():
                if not name.endswith(".html"):
                    continue
                counts["filings"] += 1
                number, period = name.split("_")[2], name.split("_")[3][:8]
                raw = z.read(name)
                if VAT_TAG.search(raw):
                    counts["filings with a VAT tag"] += 1
                if TRADING_NAME.search(raw):
                    counts["filings with a trading name tag"] += 1
                if TURNOVER.search(raw):
                    counts["filings with a turnover tag"] += 1
                if b"VAT" not in raw:
                    continue
                counts["filings that mention VAT"] += 1
                text = text_of(raw.decode("utf-8", "replace"))
                for kind, rx in SAYS.items():
                    m = rx.search(text)
                    if m:
                        counts[f"filings that say: {kind}"] += 1
                        if kind != "registered":
                            statements.append([number, period, kind, snippet(text, m)])
                for vrn, _, ok in find_candidates(text):
                    if ok:
                        printed[vrn].add(number)
    counts["filings with a printed VAT number"] = len({c for cs in printed.values() for c in cs})
    counts["distinct printed numbers"] = len(printed)
    counts["printed numbers on two or more companies"] = sum(
        1 for c in printed.values() if len(c) > 1
    )
    with open(out / "accounts_vat.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["what", "count"])
        w.writerows(sorted(counts.items()))
    with open(out / "accounts_statements.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["company_number", "period_end", "says", "text"])
        w.writerows(statements)
    with open(out / "accounts_printed_numbers.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vrn", "companies"])
        for vrn, cs in sorted(printed.items()):
            w.writerow([vrn, " ".join(sorted(cs))])
    for k, v in sorted(counts.items()):
        print(f"{v:>7}  {k}")


if __name__ == "__main__":
    main(sys.argv[1], *sys.argv[2:])
