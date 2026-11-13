from ukvat.vat import WEIGHTS, check_digits_ok, find_candidates


def make_valid(first7, add=0):
    # builds the last two digits so the number passes, add=55 gives the newer scheme
    s = sum(int(d) * w for d, w in zip(first7, WEIGHTS, strict=True)) + add
    last2 = (-s) % 97
    return f"{first7}{last2:02d}"


def test_both_schemes_pass():
    assert check_digits_ok(make_valid("1234567"))
    assert check_digits_ok(make_valid("7654321", add=55))


def test_one_changed_digit_fails():
    vrn = make_valid("2468024")
    for i in range(9):
        changed = vrn[:i] + str((int(vrn[i]) + 1) % 10) + vrn[i + 1 :]
        assert not check_digits_ok(changed) or changed == vrn


def test_wrong_length_fails():
    assert not check_digits_ok("12345678")
    assert not check_digits_ok("1234567890")
    assert not check_digits_ok("12345678a")


def test_finds_the_usual_footer_formats():
    vrn = make_valid("1357913")
    spaced = f"{vrn[:3]} {vrn[3:7]} {vrn[7:]}"
    for text in (
        f"VAT No: GB {spaced}",
        f"VAT Reg. No. {vrn}",
        f"VAT number: GB{vrn}",
        f"Registered for VAT {spaced}",
        f"GB {spaced}",
    ):
        found = find_candidates(text)
        assert [(v, ok) for v, _, ok in found] == [(vrn, True)], text


def test_branch_suffix_is_not_part_of_the_number():
    vrn = make_valid("1112223")
    found = find_candidates(f"VAT number GB {vrn} 001")
    assert found[0][0] == vrn


def test_other_countries_are_skipped():
    vrn = make_valid("2223334")
    assert find_candidates(f"VAT ID No. DE {vrn} Registry Court Berlin") == []
    assert find_candidates(f"VAT No. XI {vrn}")[0][0] == vrn


def test_phone_numbers_and_company_numbers_are_not_vat():
    text = "Tel 0121 496 0000. Company No. 01234567. Registered in England."
    assert find_candidates(text) == []
