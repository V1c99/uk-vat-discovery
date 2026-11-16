"""When the UK cards in Peppol were registered. 106 of the first 200 had the same day, 25 Aug 2025,
which looked like one provider putting all its customers in at once.

    python experiments/peppol_dates.py data/probes/peppol/cards_full_2000.csv \
        results/probes/peppol_dates.csv
"""

import csv
import sys
from collections import Counter


def main(cards_csv, out_csv):
    dates = [r["reg_date"] for r in csv.DictReader(open(cards_csv, encoding="utf-8"))]
    known = [d for d in dates if d]
    years = Counter(d[:4] for d in known)
    months = Counter(d[:7] for d in known if d[:4] in ("2025", "2026"))
    days = Counter(known).most_common(5)
    rows = [("cards", len(dates)), ("cards with a date", len(known))]
    rows += [(f"year {y}", n) for y, n in sorted(years.items())]
    rows += [(f"month {m}", n) for m, n in sorted(months.items())]
    rows += [(f"busiest day {d}", n) for d, n in days]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["what", "cards"])
        w.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
