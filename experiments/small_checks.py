"""Nominet's WHOIS for three company domains, and schema.org's vatID on the cached pages.

python experiments/small_checks.py results/probes/small_checks.csv
"""

import csv
import gzip
import json
import re
import socket
import sys
import time
from pathlib import Path

from ukvat.vat import check_digits_ok

DOMAINS = ["ellisjones.co.uk", "hmsworks.co.uk", "crusherconsumables.co.uk"]


def whois(domain):
    with socket.create_connection(("whois.nic.uk", 43), timeout=20) as s:
        s.sendall((domain + "\r\n").encode())
        data = b""
        while chunk := s.recv(4096):
            data += chunk
    return data.decode("utf-8", "replace")


def main(out_csv):
    rows = []
    for d in DOMAINS:
        text = whois(d)
        Path(f"data/probes/whois/{d}.txt").write_text(text, encoding="utf-8")
        has_registrant = re.search(r"^\s*Registrant:", text, re.M) is not None
        has_number = re.search(r"company number|registration number", text, re.I) is not None
        born = re.search(r"Registered on:\s*(\S+)", text)
        rows.append(["whois " + d, f"registrant shown {has_registrant}, company number shown "
                     f"{has_number}, registered on {born.group(1) if born else '?'}"])  # fmt: skip
        time.sleep(2)
    pages = 0
    valid = set()
    for p in Path("data/pages").glob("*.json.gz"):
        page = json.loads(gzip.decompress(p.read_bytes()))
        m = re.findall(r'"vatID"\s*:\s*"([^"]+)"', page["html"])
        if m:
            pages += 1
            valid |= {
                re.sub(r"\D", "", v)[-9:] for v in m if check_digits_ok(re.sub(r"\D", "", v)[-9:])
            }
    rows.append(["pages with schema.org vatID", f"{pages} of the cached pages"])
    rows.append(["valid uk numbers in those", str(len(valid))])
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["check", "result"])
        w.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main(sys.argv[1])
