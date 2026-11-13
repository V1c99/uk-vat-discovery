# Research log

What I ran, in the order I ran it, with what came back. Raw downloads are in `data/` (not
committed, `data/README.md` says how to get them), everything a number comes from is in `results/`.

## 12 Nov, HMRC first

Every number I report has to go through HMRC's checker, so I read HMRC's developer pages before
anything else.

- The old open version of the VAT checking API was removed on 17 Feb 2025. Version 2 needs an
  application, HMRC says registering takes around 2 weeks, and the page says the API is for traders
  doing due diligence on VAT registered businesses.
- The EORI checking API is open, no login, up to 10 numbers per request. It says if a GB EORI is
  valid and gives the name and address when the trader agreed to share them. For a VAT registered
  trader the EORI is GB, the VAT number, then 000.
- The standard limit for HMRC APIs is 3 requests per second per application.

So the numbers I report get checked by hand in the web checker (gov.uk/check-uk-vat-number), and
the EORI API is used only on numbers I already found.

## 13 Nov, the snapshot and the sample

Companies House snapshot of 1 Nov 2026: 5,711,779 companies, 5,179,256 of them Active
(`results/ch_profile.csv`).

The frame is every Active company that is not DORMANT and not an Overseas Entity, 4,591,683
companies. Four strata by accounts category, because that is the only size signal in the snapshot
and turnover is what decides VAT registration:

| stratum | accounts categories | companies in the frame |
|---|---|---|
| micro | MICRO ENTITY | 1,686,224 |
| small | total exemption, unaudited and audited abridged, SMALL | 1,444,419 |
| large | MEDIUM, FULL, GROUP, subsidiary exemptions | 147,827 |
| new | no accounts filed yet | 1,313,213 |

100 companies from each, 400 in total (`sample/register.csv`). The order inside each stratum is md5
of a seed and the company number, so the same snapshot gives the same 400.

```
python -m ukvat.run_sql sql/profile.sql sql/sample.sql
```

## 13 Nov, the website route on the 400

Companies House has no websites, so for each company I guessed up to 12 domains from its name
(.co.uk, .com and .uk), kept the ones that resolve, read the home page and up to four contact,
terms, privacy or about pages, and looked for VAT numbers and company numbers in the text. A site
counts as the company's own only if its company number is on it. Robots.txt is respected and there
is a one second pause between requests to the same site.

```
python -m ukvat.websites sample/register.csv results/websites
```

4,068 domains guessed, 233 companies had at least one live site, but only 23 of the 400 had a site
showing their own company number. Those 23 are the ceiling of this route on the register.

| outcome | micro | small | large | new | all |
|---|---|---|---|---|---|
| own site with one VAT number (strict) | 1 | 2 | 2 | 1 | 6 |
| own site, no VAT number on it | 7 | 4 | 5 | 1 | 17 |
| a VAT number on a guessed site that is not provably theirs (loose) | 0 | 1 | 2 | 1 | 4 |
| live sites, nothing | 51 | 58 | 54 | 51 | 214 |
| no site resolved | 41 | 35 | 37 | 46 | 159 |

Of the 23 companies with their own site, 6 printed a VAT number on it.

Two problems on the way:

- A German group's site matched my regex with two German VAT IDs (DE 250965905). They failed the
  UK check digits, and the regex now also drops a number written after another country's code.
- The second run gave 6 companies fewer with a site than the first. DNS lookups were timing out
  under load and "try again" from the resolver was read as "does not exist". Answers are kept in a
  cache now, a "try again" is retried, and two runs in a row give the same file.

## 13 Nov, the EORI API on the ten numbers

```
python -m ukvat.eori results/websites/companies.csv results/eori/websites.csv
```

4 of the 10 numbers have a live EORI. Two came back with a name, and both names are a different
company from the one I found the number for:

- KEBAB CITY ORIGINAL LTD (loose): the number is on the terms page of kebabcity.com, and HMRC's EORI
  record says EPOS TECHNOLOGIES LIMITED. The site runs on their ordering platform and the terms page
  is theirs.
- HOUSING MAINTENANCE SOLUTIONS LIMITED (strict): the site shows its own company number next to the
  VAT number, and the EORI record says TORUS 62 LTD, same postcode WA9 1LD. Probably a VAT group,
  where HMRC holds the group under one member's name. For matching invoices that is the right
  number, but a check on the name would call it wrong.

## 13 Nov, Peppol

Peppol is the e-invoicing network. Its directory publishes who can receive invoices, and a UK
business can be registered under scheme 9932, which is its VAT number.

```
python -m ukvat.peppol data/probes/peppol/participants.csv results/peppol
```

- The participant export lists 9,600,319 participants for all countries. 22,654 are under 9932,
  21,795 of them written with a lower case gb in front.
- 22,446 distinct nine digit numbers, 22,431 pass the check digits. Most of the rest are company
  numbers registered under the wrong scheme (eight digits like 00883094) and one test value.
- I read 200 random business cards. My first try sent the digits without the gb and 190 of 200 came
  back empty. With the identifier as Peppol writes it, all 200 have a name.
- 140 of the 200 were registered in 2025 and 51 in 2026, 106 of them on the same day, 25 Aug 2025.
  That looks like one provider registering its customers at once.
- 31 of the 200 names have no legal ending and most look like people, sole traders. Their names are
  personal data, so they are kept in `data/` only and blank in `results/peppol/`.

Linking the 169 company names to Companies House by their key words, no fuzzy matching:

| names | exactly one company | several | none |
|---|---|---|---|
| 169 that look like a company | 133 | 19 | 17 |

```
python -m ukvat.chnames
python -m ukvat.chnames link data/probes/peppol/cards_full.csv results/peppol/linked.csv
```

## 13 Nov, the website route where the number is known

The 133 linked companies are VAT registered and I know their number, so here "not found" means the
route failed. Same code as on the register.

```
python -m ukvat.run_sql sql/peppol_set.sql
python -m ukvat.websites results/peppol/known_set.csv results/peppol/websites
```

- 33 of the 133 had a site showing their own company number, against 23 of the 400 in the register
  sample.
- 14 strict finds, and all 14 are the same number Peppol has.
- 1 loose find, and it is a different number from Peppol's.
- 118 nothing.

On companies that do have a number the route found it for 14 of 133, and every strict find matched.
Of the loose finds, the two I can already check (this one and Kebab City) are both somebody else's
number.

## 13 Nov, small counts

- OpenStreetMap: 66,608 objects in the world carry a `ref:vatin` tag. taginfo finds 200 values
  with GB in them.
- Wikidata: 351 items have an EU VAT number property starting with GB.

Both are too small to matter for 2 million registrations.

## 13 Nov, public records

The brief lists insolvency notices, public sector spend and procurement records. One run each.

```
python experiments/procurement_ids.py 2026-11-03 2026-11-10 results/probes/procurement_ids.csv
python experiments/gazette_vat.py results/probes/gazette_vat.csv
python experiments/spend_headers.py results/probes/spend_headers.csv
python experiments/spend_vat.py results/probes/spend_headers.csv results/probes/spend_vat.csv
```

- Find a Tender, one week of notices (3 to 10 Nov): 2,464 notices, 5,529 parties. The identifier
  schemes used are GB-PPON (4,071), GB-COH (1,608), GB-NHS (98) and a few others. None is a VAT
  number.
- The Gazette: 1,705,312 notices contain "Company number". "VAT No" is in 28, "VAT number" in 10,
  "VAT registration no" in 5, "VAT registration number" in 1.
- Spend files: one recent csv per publisher from the data.gov.uk catalogue, 314 publishers, 112 files
  answered with a header. 6 have a column named for a VAT number. In 4 of them the column is empty,
  in Shropshire Community Health NHS Trust's file it holds VAT amounts (2.1, 10.49, 4.4), and only St
  Helens and Knowsley Teaching Hospitals NHS Trust fills it: 34 numbers for 38 suppliers, all 34 pass
  the check digits. No spend file has a company number column.

## 13 Nov, marketplaces

Amazon and eBay show a VAT number on business sellers' pages, so I looked at whether they can be
read at all before trying anything.

```
python experiments/marketplace_robots.py results/probes/marketplace_robots.csv
```

Both robots.txt files have `Disallow: /` for CCBot, Common Crawl's crawler, so none of their seller
pages are in the corpus. A crawler under any other name is allowed by robots.txt, but both sites'
terms forbid scraping, so I did not fetch any seller page.

## 13 Nov, a German number in VIES

The website route met two German VAT IDs on a German group's Impressum page. VIES on both:

```
python experiments/vies_germany.py results/probes/vies_germany.csv 250965905 136632461
```

Both valid, and for both VIES shows "---" for the name and the address. So for Germany VIES can say a
number exists, but not whose it is.

## 13 Nov, numbers for Part 3 and the debates

```
python experiments/checksum_space.py results/probes/checksum_space.csv
python experiments/unit_costs.py results/probes/unit_costs.csv
```

- 20,615,843 nine digit numbers pass the check digits (10,304,247 on mod 97, 10,311,596 on mod 97
  plus 55). At HMRC's standard 3 requests a second that is 79.5 days for one application.
- The website route made 1,691 page requests for the 533 companies of both runs and downloaded 200 MB
  of html. 5,388 domains were looked up and 759 resolve. On the register that is 49 seconds of this
  laptop per strict find, on the known set 12 seconds.

## Waiting for the hand checks

`results/hmrc/to_check.csv` has 45 numbers for HMRC's web checker: the 10 from the register, the 15
from the known set, and 20 random Peppol numbers to see how many HMRC still has live.

```
python -m ukvat.handcheck results/hmrc/to_check.csv results/hmrc/checks.csv
```
