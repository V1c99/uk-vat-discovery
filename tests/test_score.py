from ukvat.score import verdict

FOUND = {"company_name": "GRV MEDIA LTD", "postcode": "WA8 0WN"}


def check(valid=True, name="", pc=""):
    return {"valid": str(valid), "hmrc_name": name, "hmrc_postcode": pc}


def test_no_check_yet():
    assert verdict(FOUND, None) == "not checked"


def test_hmrc_says_not_registered():
    assert verdict(FOUND, check(valid=False)) == "not registered"


def test_same_name_in_other_words():
    assert verdict(FOUND, check(name="GRV Media Limited", pc="X1 1XX")) == "right company"


def test_other_name_at_the_same_postcode_is_kept_apart():
    # a VAT group looks like this, so does a virtual office, both get read by hand
    assert verdict(FOUND, check(name="TORUS 62 LTD", pc="WA8 0WN")) == "same postcode only"


def test_someone_else():
    assert verdict(FOUND, check(name="EPOS TECHNOLOGIES LIMITED", pc="EN3 4TA")) == "someone else"
