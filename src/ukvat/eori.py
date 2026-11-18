"""HMRC's open EORI checker, only on numbers already found, ten per request.

python -m ukvat.eori results/websites/companies.csv results/eori/websites.csv
"""

import csv
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

URL = "https://api.service.hmrc.gov.uk/customs/eori/lookup/check-multiple-eori"
HEADERS = {
    "Accept": "application/vnd.hmrc.1.0+json",
    "User-Agent": "Mozilla/5.0 (compatible; uk-vat-research/0.1)",
}


def check(vrns):
    out = []
    for i in range(0, len(vrns), 10):
        batch = [f"GB{v}000" for v in vrns[i : i + 10]]
        r = requests.post(URL, json={"eoris": batch}, headers=HEADERS, timeout=30)
        r.raise_for_status()
        out += r.json()
        time.sleep(1)  # HMRC's standard limit is 3 a second, this stays far below
    return out


def main(companies_csv, out_csv):
    rows = [r for r in csv.DictReader(open(companies_csv, encoding="utf-8")) if r["vrn"]]
    answers = {a["eori"][2:11]: a for a in check([r["vrn"] for r in rows])}
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    raw = Path("data/eori") / (Path(out_csv).stem + ".json")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(json.dumps(answers, indent=1))
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["company_number", "company_name", "outcome", "vrn", "eori_valid",
                    "eori_trader_name", "eori_postcode", "checked_at"])  # fmt: skip
        for r in rows:
            a = answers[r["vrn"]]
            details = a.get("companyDetails") or {}
            w.writerow([r["company_number"], r["company_name"], r["outcome"], r["vrn"],
                        a["valid"], details.get("traderName", ""),
                        (details.get("address") or {}).get("postcode", ""),
                        a.get("processingDate", datetime.now(UTC).isoformat())])  # fmt: skip
    print(f"{len(rows)} numbers, {sum(a['valid'] for a in answers.values())} with a live EORI")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
