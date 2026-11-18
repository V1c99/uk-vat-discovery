"""UK VAT numbers: the check digit test and finding candidates in page text."""

import re

WEIGHTS = (8, 7, 6, 5, 4, 3, 2)

# GB is optional, many footers drop it. Branch traders add three digits, HMRC checks the first nine
NEAR_VAT = re.compile(
    r"\bVAT\b[^0-9]{0,40}?(?:GB)?[\s:.]*((?:\d[\s.-]?){8}\d)(?:[\s.-]?(\d{3}))?(?!\d)",
    re.I,
)
# a bare GB number with no VAT word, footers often have "GB 123 4567 89" on its own
BARE_GB = re.compile(r"\bGB[\s:]?((?:\d\s?){8}\d)(?!\d)")


def digits(s):
    return re.sub(r"\D", "", s)


def check_digits_ok(vrn):
    # mod 97 for the old numbers, mod 97 after adding 55 for the ones issued since about 2010
    if len(vrn) != 9 or not vrn.isdigit():
        return False
    total = sum(int(d) * w for d, w in zip(vrn[:7], WEIGHTS, strict=True)) + int(vrn[7:])
    return total % 97 == 0 or (total + 55) % 97 == 0


def foreign_prefix(text, start):
    """True if another country's code comes before the number, like DE 250965905."""
    m = re.search(r"\b([A-Z]{2})[\s:.]*$", text[max(0, start - 6) : start])
    return m is not None and m.group(1) not in ("GB", "XI")


def find_candidates(text):
    """Numbers next to the word VAT or after GB, each once, as (vrn, how, passes_check)."""
    seen = {}
    for m in NEAR_VAT.finditer(text):
        if foreign_prefix(text, m.start(1)):
            continue
        vrn = digits(m.group(1))
        seen.setdefault(vrn, "near_vat")
    for m in BARE_GB.finditer(text):
        vrn = digits(m.group(1))
        seen.setdefault(vrn, "bare_gb")
    return [(v, how, check_digits_ok(v)) for v, how in seen.items()]
