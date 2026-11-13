"""Company names reduced to the words that matter, for guessing domains and comparing names."""

import re

# legal endings and filler that never appear in a domain or differ between registers
DROP = set(
    "limited ltd plc llp lp cic uk the co company and of group holdings services "
    "international trading enterprises".split()
)


def words(name):
    # dots go without a space, A.M.I. is one word on a website
    s = name.lower().replace("&", " and ").replace("'", "").replace(".", "")
    s = re.sub(r"\(.*?\)", " ", s)
    return re.findall(r"[a-z0-9]+", s)


def core_words(name):
    """Words of a name without legal endings. Keeps everything if nothing would be left."""
    w = words(name)
    core = [x for x in w if x not in DROP]
    return core or [x for x in w if x not in {"limited", "ltd", "plc", "llp"}]


def same_name(a, b):
    """Loose comparison for HMRC's registered name against Companies House."""
    return core_words(a) == core_words(b)
