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


LEGAL = set(
    "limited ltd plc llp lp cic llc inc gmbh ou sa bv ag trust association society "
    "partnership partners club charity foundation council".split()
)


def looks_like_company(name):
    """No legal ending, often a sole trader. Not written to anything committed."""
    return bool(LEGAL & set(words(name)))


def same_name(a, b):
    """Spaces do not count, YOUR DESIGN.CO.UK LIMITED is YOURDESIGN.CO.UK LIMITED."""
    return "".join(core_words(a)) == "".join(core_words(b))
