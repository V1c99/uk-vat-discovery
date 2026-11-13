"""Records my checks in HMRC's VAT checker. It does not touch HMRC: I type each number into
https://www.gov.uk/check-uk-vat-number myself and this only asks what the page said.

    python -m ukvat.handcheck results/hmrc/to_check.csv results/hmrc/checks.csv
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

FIELDS = ["vrn", "checked_at", "valid", "hmrc_name", "hmrc_postcode", "note"]


def done(path):
    if not Path(path).exists():
        return set()
    return {r["vrn"] for r in csv.DictReader(open(path, encoding="utf-8"))}


def main(todo_csv, checks_csv):
    todo = list(csv.DictReader(open(todo_csv, encoding="utf-8")))
    left = [r for r in todo if r["vrn"] not in done(checks_csv)]
    print(f"{len(left)} of {len(todo)} left. Empty answer to stop.")
    new_file = not Path(checks_csv).exists()
    with open(checks_csv, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        for r in left:
            print(f"\nGB {r['vrn']}   (found for {r['company_name']}, {r['postcode']})")
            valid = input("valid? y/n: ").strip().lower()
            if not valid:
                break
            name = input("name HMRC shows: ").strip() if valid == "y" else ""
            postcode = input("postcode HMRC shows: ").strip().upper() if valid == "y" else ""
            note = input("note (enter for none): ").strip()
            w.writerow({"vrn": r["vrn"], "checked_at": datetime.now().isoformat(timespec="minutes"),
                        "valid": valid == "y", "hmrc_name": name, "hmrc_postcode": postcode,
                        "note": note})  # fmt: skip
            f.flush()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
