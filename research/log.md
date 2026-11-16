# Research log

My notebook for this, in the order things happened. Raw downloads are in `data/` (not committed,
`data/README.md` says how to get them back), every number below comes from a file in `results/`.
Commands are run from the repo root.

## 12 Nov, before anything

Everything I report has to be confirmed with HMRC's checker, so I started with HMRC's own
developer pages and not with any data.

The old open API for checking VAT numbers was removed on 17 Feb 2025. Version 2 needs an
application, HMRC says registering takes around 2 weeks, and the page says the API is only for
traders doing due diligence on VAT registered businesses. Building a dataset to sell is not that.

The EORI checker is a different HMRC API and it is open, no login, up to 10 numbers per request. A
VAT registered trader's EORI is GB, the VAT number, then 000, so it can say something about a VAT
number too. HMRC's standard limit for an application is 3 requests a second.

So the numbers I report get checked by hand in the web checker, and I use the EORI API only on
numbers I already found, never to try numbers out.

## 13 Nov, the sample

Companies House snapshot of 1 Nov 2026: 5,711,779 companies, 5,179,256 of them Active
(`results/ch_profile.csv`).

I took every Active company that is not DORMANT and not an Overseas Entity, 4,591,683, and split
them by accounts category, because that is the only thing in the snapshot that says anything about
size, and turnover is what decides VAT registration. Micro 1,686,224, small 1,444,419, large
(medium, full, group and the subsidiary exemptions) 147,827, new (no accounts yet) 1,313,213. 100
from each.

The order inside a stratum is md5 of a seed and the company number. Anyone with the same snapshot
gets the same 400, and it does not depend on duckdb's random numbers.

```
python -m ukvat.run_sql sql/profile.sql sql/sample.sql
```

## 13 Nov, websites for the 400

Companies House has no websites, so I guess up to 12 domains from the name and only believe a site
is the company's if its company number is on it. Then home page plus up to four contact, terms,
privacy or about pages, a regex for VAT numbers, the check digits.

```
python -m ukvat.websites sample/register.csv results/websites
```

The first run found two numbers on erk-systems.com that were German VAT IDs (DE 250965905), nine
digits like ours. The check digits threw them out, and now the regex also drops a number written
after another country's code.

The second run gave 6 companies fewer with a site than the first. DNS lookups were timing out under
load and Windows' "try again" was read as "does not exist". Answers are cached now, a "try again"
is retried, and a second look made 45 more of the 4,068 guessed domains resolve. Two runs in a row
give the same file since.

| | micro | small | large | new |
|---|---|---|---|---|
| own site, one VAT number on it (strict) | 1 | 2 | 2 | 1 |
| own site, no VAT number | 7 | 4 | 5 | 1 |
| a number on a guessed site that does not show their company number (loose) | 0 | 1 | 2 | 1 |
| live guessed sites but nothing | 51 | 58 | 54 | 51 |
| no guessed domain resolves | 41 | 35 | 37 | 46 |

234 of the 400 had some live guessed site. Only 23 had one that is provably theirs, and 6 of those
23 print a VAT number. Finding the site is where this breaks, not reading the number.

## 13 Nov, a second look at the ten numbers

```
python -m ukvat.eori results/websites/companies.csv results/eori/websites.csv
```

4 of the 10 have a live EORI, 2 came back with a name, and both names are a different company. The
number on kebabcity.com's terms page belongs to EPOS TECHNOLOGIES LIMITED, the ordering platform
the site runs on. The one on Housing Maintenance Solutions' own site is under TORUS 62 LTD, same
postcode WA9 1LD. I think that is a VAT group, which would make it the right number for an invoice
and still a wrong one for a name check.

## 13 Nov, Peppol

Peppol is the e-invoicing network and its directory lists who can receive invoices. A UK business
can be in it under scheme 9932, and the identifier is then its VAT number.

The participant export has 9,600,319 participants for all countries, 22,654 of them under 9932.
22,446 distinct nine digit numbers, 22,431 pass the check digits. Most of the rest are company
numbers registered under the wrong scheme.

I read 200 random business cards through the search API and the first try gave 190 empty answers.
Peppol writes 21,795 of the 22,654 as gb123456789, I had sent the digits alone. With the identifier
as written, all 200 have a name.

140 of the 200 were registered in 2025 and 51 in 2026, and 106 on the same day, 25 Aug 2025. 31
names have no legal ending and look like people, sole traders. Their names are personal data, so
they stay in `data/` and are blank in `results/peppol/`.

Linking the other 169 to Companies House by the words of the name, no fuzzy matching: 133 point at
exactly one company, 19 at several, 17 at none.

```
python -m ukvat.peppol data/probes/peppol/participants.csv results/peppol
python -m ukvat.chnames
python -m ukvat.chnames link data/probes/peppol/cards_full.csv results/peppol/linked.csv
```

## 13 Nov, the same route where I know the answer

The 133 are registered and I know their number, so here "not found" means the route failed.

```
python -m ukvat.run_sql sql/peppol_set.sql
python -m ukvat.websites results/peppol/known_set.csv results/peppol/websites
```

33 had a site showing their company number, 14 printed their VAT number on it, and all 14 are the
number Peppol has. The one loose find is a different number. 118 nothing.

## 13 Nov, things too small to matter

OpenStreetMap has 66,608 objects with a `ref:vatin` tag in the whole world and taginfo finds 200
values with GB in them. Wikidata has 351 items with an EU VAT number starting with GB.

## 13 Nov, public records

The brief lists insolvency notices, public sector spend and procurement.

```
python experiments/procurement_ids.py 2026-11-03 2026-11-10 results/probes/procurement_ids.csv
python experiments/gazette_vat.py results/probes/gazette_vat.csv
python experiments/spend_headers.py results/probes/spend_headers.csv
python experiments/spend_vat.py results/probes/spend_headers.csv results/probes/spend_vat.csv
```

Find a Tender, the week of 3 to 10 Nov: 2,464 notices with 5,529 parties. Suppliers are identified
by GB-PPON (4,071) and GB-COH (1,608), a few by GB-NHS and charity numbers, none by a VAT number.

The Gazette: "Company number" is in 1,705,312 notices. "VAT No" in 28, "VAT number" in 10, "VAT
registration no" in 5, "VAT registration number" in 1.

Spend files were the interesting one. One recent csv per publisher from the data.gov.uk catalogue,
112 answered. 6 have a column called something like VAT Registration Number. Four leave it empty.
Shropshire Community Health NHS Trust's is full of VAT amounts (2.1, 10.49, 4.4). Only St Helens and
Knowsley Teaching Hospitals NHS Trust fills it, 34 numbers for 38 suppliers, all valid. So the
numbers are held by the buyer, and publishing them is somebody's choice.

## 13 Nov, marketplaces

Business sellers on Amazon and eBay show a VAT number, so I read their robots.txt first. Both say
`Disallow: /` to CCBot, Common Crawl's crawler, so no seller page is in the corpus. Other crawlers
are allowed there, but both sites' terms forbid scraping, so I did not fetch a single seller page.

```
python experiments/marketplace_robots.py results/probes/marketplace_robots.csv
```

## 13 Nov, the two German numbers in VIES

Both valid, and VIES shows "---" as the name and the address. For Germany the EU checker says a
number exists but not whose it is, which is the part the UK gives for free.

```
python experiments/vies_germany.py results/probes/vies_germany.csv 250965905 136632461
```

## 13 Nov, numbers for later

20,615,843 nine digit numbers pass the check digits (10,304,247 on mod 97, 10,311,596 on mod 97 plus
55). At 3 checks a second that is 79.5 days for one application.

The website route made 1,691 page requests for 533 companies, 200 MB of html, 5,388 domains looked
up and 759 resolving. On the register that is 49 seconds of this laptop per strict find, on the
known set 12.

```
python experiments/checksum_space.py results/probes/checksum_space.csv
python experiments/unit_costs.py results/probes/unit_costs.csv
```

## 13 Nov, the October crawl

Four of the 100,000 text files of CC-MAIN-2026-43, picked by md5:

```
python experiments/commoncrawl_wet.py CC-MAIN-2026-43 4 results/probes/commoncrawl_wet.csv
```

83,776 pages, 1,792 on .uk hosts. 172 pages have a valid UK VAT number, 122 also a company number,
117 exactly one of each. That is 106 distinct numbers on 107 hosts.

My first script multiplied the 105 linkable numbers by 25,000 and printed 2.6 million. That is wrong,
a footer is on every page of a site, so only pages scale with the crawl. The fix is further down.

Do the two numbers on one page belong together. EORI on the 106:

```
python experiments/commoncrawl_pairs_eori.py data/probes/commoncrawl/wet_pairs.csv results/probes/commoncrawl_pairs.csv
```

31 have no EORI, 41 have one without a shared name. Of the 34 with a name, 29 are the company on the
page, 3 are another name at the same postcode (IVC, Interlink, Pure Collection), 2 are another
company. It said 28 first. YOURDESIGN.CO.UK LIMITED against YOUR DESIGN.CO.UK LIMITED failed on a
space, names are compared without spaces since.

Is the crawl a replacement for fetching. The index server answered 504 most of the time and once
cut a line in half, so I stopped using it and read the index files through `cluster.idx` instead,
fetching only the blocks I need. Same answers as the server on the four hosts I compared, and a
lookup takes 0.3 seconds.

```
python experiments/commoncrawl_coverage.py results/probes/commoncrawl_coverage.csv
python experiments/commoncrawl_estimate.py 4 results/probes/commoncrawl_estimate.csv
```

Of the 58 sites that showed their own company number live, 31 are in the crawl and 18 with their
home page. 21 had the VAT page live, 9 of those pages are in the crawl. A corpus alone would have
missed more than half.

For the whole crawl, every host seen in the slice counts as 1 over its chance of being in a four
file slice, from its page count in the index. About 22,283 hosts with a VAT number next to a company
number, standard error 4,075. It is a floor, because it assumes the pair is on every page, and 11
small hosts carry half of it.

## 13 Nov, evening, filed accounts

My guess was that some small company accounts carry the VAT number as a tag. The first scan of a
day of accounts said 15 files had a VAT tag. The regex was case blind and it was matching
"DeriVATives". With the tag name read properly there are none.

```
python experiments/accounts_vat.py results/probes data/accounts/Accounts_Bulk_Data-2026-11-12.zip data/accounts/Accounts_Bulk_Data-2026-11-10.zip
```

23,751 filings from two days. No VAT tag and no VAT number printed anywhere in the text. 1,439
mention VAT, mostly "turnover is stated net of VAT". 5 say the company is in a VAT group (the
contingent liability note), 4 say it is not registered: a charity, a residents' management company,
a council's trading company and an orthodontist, which fits, those are the exempt kinds.

210 of the 23,751 tag a turnover. I wanted turnover above the threshold as a second sample of
companies that must be registered, and it is not there for small companies.

## 13 Nov, evening, names and postcodes

```
python -m ukvat.run_sql sql/crowding.sql
```

3.9% of all companies share their name with another once "Ltd" is dropped, 11.4% with the looser key
I used for Peppol. The worst are families where only the bracket differs: NAMECO (NO. x) 623 times,
BROOKSON 468, COMPANION CARE 146, MKM BUILDING SUPPLIES 138. An invoice from "Companion Care" cannot
be matched by name, that is the customer's problem exactly.

A third of live companies (32.8%) are registered at a postcode shared with 100 or more others, 10.6%
at one with 1,000 or more. WC2H 9JQ has 75,154 companies, EC1V 2NX 61,011.

On the 29 pairs where HMRC's name was the company's own, HMRC's postcode was the registered office
in 21. The other 8 are a trading address, and 4 of those registered offices sit at a crowded
postcode. So in `score.py` a postcode match only counts below 100 companies, and a different postcode
never counts against a match.

## 13 Nov, evening, sites that say they are not registered

The brief's hardest point is telling "not registered" from "I failed". Some businesses could just say
it.

```
python experiments/says_not_registered.py results/probes/says_not_registered.csv
```

0 of the 1,382 pages the route fetched, 2 of the 83,776 crawl pages. One is a garden builder selling
it as a saving, the other is a form asking "Are you VAT registered". Nobody writes it down.

## 13 Nov, evening, who the other names are

When HMRC's name for a number is another company, is it the owner. Companies House's persons with
significant control, 33 files, only the owners that are companies or other legal persons kept.

```
python experiments/psc_corporate.py 2026-11-13 33 data/psc_corporate.csv
python experiments/group_links.py results/probes/group_links.csv
```

The first run kept only corporate entities and found no link at all for the seven cases. Two things
were missing. A housing association is a "legal person", not a corporate entity. And HMRC's name can
be one the company does not use any more, so the other company has to be looked for under previous
names too.

After both:

- Inspiring Vet Care: HMRC's name, Independent Vetcare Limited, is a former owner, found under a
  previous name.
- The Despatch Company and Despatch Cloud have the same owner.
- Pure Collection Cashmere: HMRC's name is close to its former holding company, Project Pure Holdco.
- Housing Maintenance Solutions and TORUS 62, Interlink Digital and Interlink Advertising: no owner
  on record, but the same head office postcode.
- EPOS Technologies and Kebab City: nothing, as it should be.

## 13 Nov, evening, a number on two companies

Across the 131 valid numbers found next to a company, by every route, one number shows up for two
companies: 204979488, on two Sykes Cottages sites, for Sykes Cottages Ltd and Lake District Lodge
Holidays Ltd. Following owners three levels up, they are the same group.

```
python experiments/cross_sources.py results/probes/cross_sources.csv
```

The sources barely overlap. 3 of the 106 crawl numbers are in Peppol, none of the 10 register sample
numbers. The two list estimate from Peppol and the crawl slice comes to about 605,000, which is a
rough size and not a measurement. The lists are not independent and an overlap of 3 is nothing to
lean on.

## 13 Nov, evening, ten minute checks

Nominet's WHOIS for three company domains shows no registrant and no company number, only that
Nominet validated the registrant, the registrar and the dates. It also says the .uk WHOIS stops on
9 Feb 2027. schema.org's `vatID` is on 5 of the cached pages, with one valid UK number.

```
python experiments/small_checks.py results/probes/small_checks.csv
```

## 13 Nov, evening, one buyer's supplier list

St Helens and Knowsley's spend file is the customer's situation in public, a buyer with the VAT
number next to each supplier.

```
python experiments/nhs_ledger.py results/probes/nhs_ledger.csv results/probes/nhs_ledger
python -m ukvat.websites results/probes/nhs_ledger/linked.csv results/probes/nhs_ledger/websites
```

34 numbers, 4 of them in Peppol. HMRC's EORI name is the same as the hospital's for the 5 that share
one. 19 suppliers link to one company, and the website route finds the number for none of the 19.
These are big medical suppliers. They do not print a VAT number on their sites, it is on the
invoice.

46 of the 112 spend files are from NHS bodies and 5 of those have the VAT column.

## 13 Nov, evening, who registered the Peppol wave

I tried to find which service provider put 106 of 200 cards in on 25 Aug 2025, from Peppol's DNS
records. Every name I tried was NXDOMAIN, even Peppol's own test participant, so either my naming is
wrong or the registry moved. Left open.

What I did find is HMRC's policy paper of 28 Oct 2026 (gov.uk, "VAT: electronic invoicing"). VAT
invoices have to be sent as e-invoices from 1 April 2029, Peppol is the network, and HMRC is to
become the UK Peppol Authority. The authority today sits in Supply Chain Coordination Limited, which
runs NHS Supply Chain, which would explain why the hospital suppliers are the ones in Peppol so far.

HMRC's VAT statistics for 2024 to 2025: 2,330,400 registered traders, 234,000 new registrations and
218,000 deregistrations in the year.

## 16 Nov, 2,000 Peppol cards

I read 2,000 random UK cards instead of 200 (the same md5 order, so the first 200 are inside). All
2,000 have a name. 1,401 point at exactly one live company with a legal ending, 192 at several, 142
company names at none, and 265 look like people.

```
python -m ukvat.peppol data/probes/peppol/participants.csv results/peppol_2000 2000
python -m ukvat.chnames link data/probes/peppol/cards_full_2000.csv results/peppol_2000/linked.csv
python experiments/peppol_dates.py data/probes/peppol/cards_full_2000.csv results/probes/peppol_dates.csv
```

The dates are stranger than I thought from 200. 1,141 of the 2,000 were registered on 25 Aug 2025
and 74 on 22 Aug, so 1,258 in August 2025 alone. Only 71 cards are from before 2025. Since then it
is a steady 40 to 56 a month in the sample, which is roughly 450 to 630 new UK businesses a month in
the whole directory. Somebody put most of the UK in at once in August 2025, and the rest is a
trickle that will turn into a flood before April 2029.

## 16 Nov, a VAT number dates itself

On 13 Nov I noticed the numbers on young companies all passed the check only after adding 55, and
the old ones passed plain mod 97. My guess was that the plus 55 kind is issued in order, so its
first digits are a date.

With 1,512 pairs of a VAT number and a company number (Peppol, crawl pages, strict finds) and the
incorporation date from the snapshot:

```
python experiments/vat_number_age.py results/probes
```

- Plus 55: 1,146 pairs, incorporated 2011 to 2024 (10th to 90th percentile), median 2019.
- Plain: 366 pairs, 1988 to 2010, median 2004.
- Rank correlation between the number and the incorporation date: 0.87 for plus 55 (companies from
  2010 on), 0.685 for plain.

A company registers after it is incorporated, never before, so for each band of numbers the newest
companies holding it are the ones that registered straight away. Taking their date (90th
percentile) as the band's issue date: band 20 about Feb 2015, 30 about Sep 2018, 40 about Mar 2022,
50 about Oct 2025, 52 about Aug 2026. A band is 100,000 serials, so that is about 279,000 serials a
year between band 20 and 50. HMRC's own statistics say 234,000 new registrations in 2024 to 2025. I
did not expect it to land that close.

The chart (`results/probes/vat_number_age.png`) shows more than I was looking for. The plain numbers
climb a sharp edge from about 1990 to 2010 and stop at the top of the seven digit range, and the
plus 55 numbers start again from the bottom in 2010 and climb their own edge to now. It looks like
HMRC ran out of numbers on the old check around 2010 and started a second series.

What it gives, without asking HMRC anything:

- A number far older than the company it is printed for is suspicious. 30 pairs are like that.
  The EORI API knows the name for 7 of them and all 7 are the company's own, for example PRICE
  PLASTERING LIMITED, incorporated 2019 with an old plain number. That is a sole trader who
  incorporated and kept the registration, which HMRC allows. So an old number on a young company is
  either an inherited registration or a wrong link, and the EORI name says which.
- The top of the range says how many numbers HMRC has issued, today.
- It changes the checksum debate. 20.6 million numbers pass the check, but the issued ones sit in a
  band that grows by about a quarter of a million a year, and the dates of that band can be read off
  public data. I think that is a reason HMRC closed the open API.

## 16 Nov, sectors that do not register

Known registered companies (the 1,401 linked Peppol cards) against the whole frame, by SIC code:

```
python -m ukvat.run_sql sql/registered_sectors.sql
```

Residents' property management (98000) is 1.76% of the frame and none of the 1,401. Buying and
selling own real estate (68100) is 4.86% of the frame and 0.71% of the known ones. Holding companies,
dormant and non trading are a quarter of their share. IT consultancy, business support and management
consultancy are over represented, which is Peppol's B2B lean. Together the two codes under a fifth of
their share are 6.62% of the frame, companies that will mostly never have a number.

Of the 390 sampled companies where nothing was found, 27 are in those two codes. That is the only
part of "not found" I can call "probably not registered" with something behind it.

## 16 Nov, the whole directory

Peppol's export answered this time. The first stream died on a byte that was not UTF-8 (0xe9, an
é from somewhere in France), now bad bytes are replaced. 9,621,402 cards read, 22,681 under 9932,
22,485 with a valid number.

```
python experiments/peppol_export.py data/probes/peppol/uk_cards.csv
python experiments/peppol_all.py data/probes/peppol/uk_cards.csv results/peppol_all
```

15,259 company names link to exactly one live company, 2,319 to several, 1,592 to none, and 3,315
cards look like people. 12,148 cards were registered on 25 Aug 2025 and 844 on 22 Aug. In 2026 it
has been between 342 and 682 new UK cards a month.

I reran the number ages and the sectors on all of it. 15,359 pairs with an incorporation date,
rank correlation 0.869 for the plus 55 kind, about 282,000 serials a year between band 20 and 50.
362 numbers look older than their company, and HMRC's EORI record gives a name for 84 of them: 76
are the company's own (inherited registrations), 8 are another company. The rarely registered codes
are now four (residents' management, non trading, dormant, buying and selling own property), 7.55%
of the frame, and 30 of the 390 "nothing found" in the register sample sit in them.

## 16 Nov, how often the law is followed

Regulation 6 asks a business that sells online to show its VAT number. On the 1,401 linked Peppol
companies, all registered and all with a known number:

```
python -m ukvat.websites results/peppol_2000/known_set.csv results/peppol_2000/websites
python experiments/legal_duty.py results/peppol_2000 results/probes/legal_duty.csv
```

255 have a site showing their company number. 98 of those print one VAT number, 38.4% (32.7 to
44.5). Micro 39 of 105, small 51 of 125, large 2 of 9. So even a perfect site finder would stop at
about 4 in 10 of the registered companies that have a site, and the 255 are only 18% of the 1,401.

For the 155 with a site and no number, I looked at the html again. In 2 the number is there and my
reader missed it, 17 link a pdf where it may be, 136 do not have it anywhere in the page.

Strict finds equal Peppol's number 96 times out of 98. Loose finds 3 out of 13. That is the same
story as on the first 133, just with enough companies to say it.

The 2 strict disagreements are the best thing in this run. Both sites show an older number and
Peppol a new one:

- Virtus IT, incorporated 2009. The site has 945274602, a plain number from around 2009. Peppol has
  530943791, from the newest band, and its card is from 28 Oct 2026.
- Invatech Health, incorporated 2019. The site has 184392679, a band from about 2014, older than the
  company. Peppol has 512587393 from early 2026, card from 14 Apr 2026.

So the site is out of date, and the number's age already says which one to trust. They go to HMRC
in the second list with everything else that disagrees.

```
python -m ukvat.run_sql sql/to_check_2.sql
python -m ukvat.handcheck results/hmrc/to_check_2.csv results/hmrc/checks_2.csv
```

34 numbers: the 4 of the two disagreements, the 10 loose ones that are not Peppol's, and 20 random
agreements to see whether agreeing with Peppol can stand in for an HMRC check.

## 16 Nov, afternoon, HMRC's checker

Both lists went through HMRC's web checker one number at a time. An automated browser typed them
instead of me with `handcheck`, and the times in `checks.csv` and `checks_2.csv` are the ones HMRC
prints on its result page (GMT). About 45 went through in 12 minutes in the morning, then the result
page answered 429. After a pause it took a few more. In the afternoon it answered 429 again after
only 4, so it remembers more than the last few minutes. From then on every try was at least ten
minutes after the last 429.

```
python -m ukvat.score results/hmrc/to_check.csv results/hmrc/checks.csv results/hmrc/scored.csv
python -m ukvat.score results/hmrc/to_check_2.csv results/hmrc/checks_2.csv results/hmrc/scored_2.csv
python -m ukvat.run_sql sql/numbers.sql
```

The register sample first, because it is the one that says what the route does on the register.
HMRC shows the company itself for 3 of the 6 strict finds and 1 of the 4 loose ones, which is 0.98
finds per 100 companies once the bands are weighted. The other 3 strict finds are each something
else:

- Housing Maintenance Solutions: HMRC shows TORUS62 LIMITED at the same postcode, the housing group
  it belongs to. Right for an invoice, wrong as a key for the company.
- CLIMETECH LTD, incorporated in July 2025: the number is of the older kind and HMRC shows a
  person's name at the company's address. The founder's own registration, printed on the company's
  site. It was already on the list of numbers older than their company, committed this morning.
- ETORROS LTD: not registered. The number sits in the band of 2020, the year the company was
  incorporated, so I think it was the company's and was cancelled.

The 3 loose ones that are not the company are EPOS Technologies (the ordering platform on Kebab
City's terms page), Freeola (the registrar of a parked domain) and Male Transport Services for
M.T.S Logistics.

18 of the 20 random Peppol numbers are live, 2 are not registered any more.

In the morning numbers.sql counted another name at the same postcode as right. I wrote that after
the first list was checked, so I took it out again. Only HMRC showing the company counts as right
now, and the cases in between are described one by one.

On the known set every strict find that is Peppol's number and was checked came back under the
company's name, 17 of 17. That is the 14 of the first list and 3 more of the 20 random agreements
(3 others were already in the first list). For the two disagreements HMRC shows both of Peppol's
numbers live under the company's name, and the old number on Virtus IT's site is not found at all.
So in both pairs the younger number is the live one, as the age test said.

The checker stopped before the rest of the second list. 24 numbers have no check yet: 14 random
agreements, the old number on Invatech Health's site and 9 loose finds. They are not counted
anywhere, and they go first on the next day.
