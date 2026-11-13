"""What one web page says: its text, the links worth following, company numbers on it."""

import re
from urllib.parse import urljoin, urlsplit

from selectolax.lexbor import LexborHTMLParser as HTMLParser

# the pages where the law puts the company and VAT details, in practice
FOLLOW = re.compile(r"contact|about|terms|privacy|legal|imprint|company|policy|conditions", re.I)

# "Company No. 01234567", "Registered in England No 1234567", "Reg. No: SC123456"
COMPANY_NO = re.compile(
    r"\b(?:company|registration|registered|reg\.?|crn)\b[^0-9A-Za-z]{0,30}"
    r"(?:(?:number|no\.?|in\s+england(?:\s+and\s+wales)?|in\s+scotland)[^0-9A-Za-z]{0,10}){0,3}"
    r"((?:SC|NI|OC|SO|NC|R0|LP|SL)?\s?\d{6,8})\b",
    re.I,
)


def text_of(html):
    tree = HTMLParser(html)
    for tag in tree.css("script, style, noscript, svg"):
        tag.decompose()
    body = tree.body or tree.root
    if body is None:
        return ""
    return re.sub(r"\s+", " ", body.text(separator=" ")).strip()


# TODO: terms often sit in a pdf and some footers are an image. both are skipped, so a site
# counted as "no vat number" may just have it where this cannot read
def links_to_follow(html, base_url, limit=4):
    host = urlsplit(base_url).netloc
    out = []
    for a in HTMLParser(html).css("a[href]"):
        href = a.attributes.get("href") or ""
        label = a.text(strip=True)
        if not (FOLLOW.search(href) or FOLLOW.search(label)):
            continue
        url = urljoin(base_url, href).split("#")[0]
        if urlsplit(url).netloc == host and url.startswith("http") and url not in out:
            out.append(url)
        if len(out) == limit:
            break
    return out


def normalise_company_no(raw):
    s = raw.replace(" ", "").upper()
    if s.isdigit():
        return s.zfill(8)
    return s[:2] + s[2:].zfill(6)


def company_numbers(text):
    return {normalise_company_no(m.group(1)) for m in COMPANY_NO.finditer(text)}


def mentions_number(text, company_number):
    """The company's own number anywhere on the page, with or without its leading zeros."""
    short = company_number.lstrip("0") if company_number.isdigit() else company_number
    return re.search(rf"(?<![0-9A-Za-z])0*{re.escape(short)}(?![0-9])", text) is not None
