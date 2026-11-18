"""The website route, company first: guessed domains, the home page and up to four legal or contact
pages, VAT candidates and company numbers.

    python -m ukvat.websites sample/register.csv results/websites
"""

import csv
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

from ukvat import fetch
from ukvat.domains import guesses
from ukvat.page import company_numbers, links_to_follow, mentions_number, text_of
from ukvat.vat import find_candidates


def snippet(text, vrn, width=70):
    # the number can be written with spaces in it, "990 1087 16"
    m = re.search(r"\s?".join(vrn), text)
    if not m:
        return ""
    return text[max(0, m.start() - width) : m.end() + width]


def bare(url):
    # query strings on redirects carry session tokens, they are not kept
    return urlsplit(url)._replace(query="", fragment="").geturl()


def read_site(company, domain):
    home = fetch.get(f"https://{domain}/")
    if not home["html"] and home["status"] not in ("robots",):
        home = fetch.get(f"http://{domain}/")
    site = {"domain": domain, "status": home["status"], "final_url": bare(home["final_url"])}
    pages = [home]
    if home["html"]:
        pages += [fetch.get(u) for u in links_to_follow(home["html"], home["final_url"])]
    site["pages"] = sum(1 for p in pages if p["html"])
    site["own_number"] = False
    found = []
    for p in pages:
        if not p["html"]:
            continue
        text = text_of(p["html"])
        own = mentions_number(text, company["company_number"])
        site["own_number"] |= own
        others = company_numbers(text) - {company["company_number"]}
        for vrn, how, ok in find_candidates(text):
            found.append(
                {
                    "company_number": company["company_number"],
                    "domain": domain,
                    "page": bare(p["final_url"]),
                    "vrn": vrn,
                    "how": how,
                    "check_digits_ok": ok,
                    "own_number_on_page": own,
                    "other_company_numbers": " ".join(sorted(others)),
                    "context": snippet(text, vrn),
                }
            )
    return site, found


def run_company(company):
    sites, found = [], []
    for d in guesses(company["company_name"]):
        if not fetch.resolves(d):
            continue
        site, cands = read_site(company, d)
        sites.append(site)
        found += cands
    return company, sites, found


def decide(company, sites, found):
    """strict: one valid number on a site that shows the company's own number. loose: one valid
    number on any guessed site. Two or more different numbers means no answer."""
    valid = [f for f in found if f["check_digits_ok"]]
    confirmed = {s["domain"] for s in sites if s["own_number"]}
    strict = {f["vrn"] for f in valid if f["domain"] in confirmed}
    loose = {f["vrn"] for f in valid}
    if not sites:
        outcome = "no_site"
    elif len(strict) == 1:
        outcome = "strict"
    # TODO: two numbers means no answer even when one of them is a platform's (EPOS on
    # kebabcity.com). a list of numbers seen on many unrelated sites would fix that
    elif len(strict) > 1:
        outcome = "ambiguous"
    elif len(loose) == 1:
        outcome = "loose_only"
    elif len(loose) > 1:
        outcome = "ambiguous_loose"
    elif confirmed:
        outcome = "own_site_no_vat"
    else:
        outcome = "no_number"
    vrn = ""
    if outcome == "strict":
        vrn = next(iter(strict))
    elif outcome == "loose_only":
        vrn = next(iter(loose))
    return {
        "stratum": company["stratum"],
        "company_number": company["company_number"],
        "company_name": company["company_name"],
        "domains_tried": len(guesses(company["company_name"])),
        "sites_live": sum(1 for s in sites if s["pages"]),
        "own_site": " ".join(sorted(confirmed)),
        "outcome": outcome,
        "vrn": vrn,
        "candidates_valid": " ".join(sorted(loose)),
    }


CANDIDATE_FIELDS = [
    "company_number", "domain", "page", "vrn", "how", "check_digits_ok",
    "own_number_on_page", "other_company_numbers", "context",
]  # fmt: skip


def write(path, rows, fields=None):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main(sample_csv, out_dir, limit=None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    companies = list(csv.DictReader(open(sample_csv, encoding="utf-8")))[:limit]
    started = time.time()
    results, all_sites, all_found = [], [], []
    with ThreadPoolExecutor(max_workers=12) as pool:
        for i, (company, sites, found) in enumerate(pool.map(run_company, companies), 1):
            results.append(decide(company, sites, found))
            for s in sites:
                all_sites.append({"company_number": company["company_number"], **s})
            all_found += found
            if i % 25 == 0:
                print(f"{i} companies, {time.time() - started:.0f}s", flush=True)
    write(out / "companies.csv", results)
    write(
        out / "sites.csv",
        all_sites,
        ["company_number", "domain", "status", "final_url", "pages", "own_number"],
    )
    write(out / "candidates.csv", all_found, CANDIDATE_FIELDS)
    fetch.save_dns()
    print(f"done, {len(companies)} companies in {time.time() - started:.0f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None)
