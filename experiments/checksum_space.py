"""How many 9 digit numbers pass the VAT check digits.

python experiments/checksum_space.py results/probes/checksum_space.csv
"""

import csv
import sys

from ukvat.vat import WEIGHTS


def main(out_csv):
    old = new = both = 0
    for prefix in range(10**7):
        s = str(prefix).zfill(7)
        total = sum(int(d) * w for d, w in zip(s, WEIGHTS, strict=True))
        for last2 in range(100):
            a = (total + last2) % 97 == 0
            b = (total + last2 + 55) % 97 == 0
            old += a
            new += b
            both += a and b
    passing = old + new - both
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["what", "count"])
        w.writerows([("nine digit numbers", 10**9), ("pass mod 97", old),
                     ("pass mod 97 after adding 55", new), ("pass either", passing),
                     ("days at 3 checks a second", round(passing / 3 / 86400, 1))])  # fmt: skip
    print(passing, round(passing / 3 / 86400, 1), "days")


if __name__ == "__main__":
    main(sys.argv[1])
