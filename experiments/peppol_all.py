"""All UK cards from Peppol's export, in the same shape as the 2,000 and linked the same way.

python experiments/peppol_all.py data/probes/peppol/uk_cards.csv results/peppol_all
"""

import csv
import sys
from pathlib import Path

from ukvat.chnames import link
from ukvat.vat import check_digits_ok


def main(uk_cards, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows, skipped = [], 0
    for r in csv.DictReader(open(uk_cards, encoding="utf-8")):
        vrn = r["participant"].split(":", 1)[1].upper().replace("GB", "")
        if len(vrn) != 9 or not vrn.isdigit() or not check_digits_ok(vrn):
            skipped += 1
            continue
        # "Beic Parcio Cymru Ltd (en)", the language tag goes
        name = r["name"].split("\n")[0].removesuffix(" (en)").strip()
        rows.append({"vrn": vrn, "name": name, "reg_date": r["reg_date"]})
    full = Path("data/probes/peppol/cards_all.csv")
    with open(full, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["vrn", "name", "reg_date"])
        w.writeheader()
        w.writerows(rows)
    link(str(full), str(out / "linked.csv"))
    print(f"{len(rows)} cards with a valid number, {skipped} skipped")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
