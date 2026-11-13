from ukvat.domains import guesses
from ukvat.names import core_words, same_name
from ukvat.page import company_numbers, links_to_follow, mentions_number, text_of


def test_company_number_formats():
    text = (
        "Registered in England and Wales No. 1234567. Company No: SC123456. "
        "Company registration number 09876543"
    )
    assert company_numbers(text) == {"01234567", "SC123456", "09876543"}


def test_own_number_found_without_leading_zero():
    assert mentions_number("Reg no 1234567 VAT 999", "01234567")
    assert not mentions_number("call 0121234567", "01234567")
    assert mentions_number("Company SC123456", "SC123456")


def test_text_drops_scripts():
    html = "<html><body><p>VAT No 1</p><script>var vat = 2</script></body></html>"
    assert text_of(html) == "VAT No 1"


def test_only_same_host_links_are_followed():
    html = (
        '<a href="/contact-us">Contact</a><a href="https://other.com/terms">Terms</a>'
        '<a href="/shop">Shop</a><a href="/legal#vat">Legal</a>'
    )
    assert links_to_follow(html, "https://acme.co.uk/") == [
        "https://acme.co.uk/contact-us",
        "https://acme.co.uk/legal",
    ]


def test_name_words():
    assert core_words("J. SMITH BUILDING SERVICES LIMITED") == ["j", "smith", "building"]
    assert core_words("THE GROUP LTD") == ["the", "group"]
    assert same_name("ACME WIDGETS LTD", "Acme Widgets Limited")
    assert not same_name("ACME WIDGETS LTD", "ACME WIDGET SUPPLIES LTD")
    assert same_name("YOURDESIGN.CO.UK LIMITED", "YOUR DESIGN.CO.UK LIMITED")


def test_domain_guesses():
    g = guesses("ACME WIDGETS LIMITED")
    assert g[:3] == ["acmewidgets.co.uk", "acmewidgets.com", "acmewidgets.uk"]
    assert "acme-widgets.co.uk" in g
    assert guesses("AB LTD") == []
