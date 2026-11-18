"""Guessing a company's website from its registered name."""

from ukvat.names import core_words, words

# TODO: .org.uk and .net are never tried, charities and some old firms use them
TLDS = (".co.uk", ".com", ".uk")


def guesses(name):
    core = core_words(name)
    full = [w for w in words(name) if w not in {"limited", "ltd", "plc", "llp"}]
    stems = []
    for parts in (core, full):
        if parts:
            stems.append("".join(parts))
            if len(parts) > 1:
                stems.append("-".join(parts))
    if len(core) > 2:
        stems.append("".join(core[:2]))
    stems.append("".join(core) + "ltd")
    # two or three letters is somebody else's domain almost every time
    if len("".join(core)) < 4 and len("".join(full)) < 4:
        return []
    out = []
    for s in stems:
        if len(s.replace("-", "")) < 4:
            continue
        for tld in TLDS:
            d = s + tld
            if d not in out:
                out.append(d)
    return out[:12]
