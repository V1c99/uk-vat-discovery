# UK company VAT numbers from the open web

My take-home for the Veridion Data Assets Intern track ("VAT Identifier Discovery"). The question is
whether a dataset of UK company VAT numbers can be built from the open web, proven on a sample.

## Short answer

Partly, and not in the way I expected when I started.

The open web gives a VAT number for about 1 company in 100 on the register. On 400 live companies
drawn at random, weighted by how many companies each size band stands for, that is 1.35 strict
finds per 100, and HMRC shows 0.98 per 100 under the company's own name. Where a page proves whose
number it is, with the company's registration number next to it, the number is usually right: on
registered companies it was Peppol's number 96 times out of 98, and HMRC showed the company for
all 31 of those I checked. On the register sample it was messier. HMRC showed the company itself
for 3 of the 6 strict finds, and the other 3 were a VAT group's number, the founder's own
registration and a number that is not live any more.

Crawling more would not change this much. Only 38% of registered companies with a site I could
prove print their number, one number can belong to several companies, and sites keep old numbers.
So I would not sell a dataset built from the web as the answer to this customer. Their own invoices
already carry the number. Peppol's e-invoicing directory, a source that is not on your list, has
22,485 UK numbers today, and from 1 April 2029 VAT invoices have to be e-invoices over Peppol. The
web is useful for the gaps and as a second opinion.

## How it went

I started at HMRC and not at the data, because everything I report has to pass HMRC's checker. The
open API for that check was removed in February 2025 and the new one is only for traders doing due
diligence, so every number I count as found went through the web checker (gov.uk/check-uk-vat-number),
one at a time. HMRC's EORI checker is still open, and a VAT registered trader's EORI is GB, the VAT
number and 000, so it gave me a free second look at numbers I had already found.

Then I went company first: 400 live companies drawn at random from the register, a website guessed
from each name, and a number only counted when the site also shows the company's registration
number. 234 had some live guessed site, 23 had one that is provably theirs, and 6 of those print a
VAT number. Finding the site is where it broke, not reading the number.

The same day I found Peppol. A UK business can be in its directory under scheme 9932, and its
identifier there is its VAT number. That gave me UK numbers by the thousand, and also companies
whose number I already knew, so I could test my route where the right answer is known. Of 1,401
such companies, 255 have a site that is provably theirs, only 98 of those print the number, and 96
of the 98 are Peppol's number.

The sources you list came next, and most of them are dead ends with a number behind them:
procurement notices, the Gazette, filed accounts, marketplace sellers. The crawl is cheap and
small. One hospital's spend file has its suppliers' numbers, and my route found none of the 19 it
could link on the web.

While joining numbers to the age of their companies I noticed that a VAT number carries its own
date. That gave me a test to run before asking HMRC anything, and it picked the live number in both
cases where a site and Peppol disagree.

On 16 and 17 Nov, 79 checks went into HMRC's web checker. An automated browser typed them, one
number at a time and only numbers I had already found, and when the checker answered 429 it waited
and went on slower. On 18 Nov I added two small probes, EORI numbers printed on pages and France,
where the VAT number follows from the company number.

I kept a notebook of every run, in order, with the commands and what came back:
`research/log.md`. The pipeline is in `src/ukvat`, the probes in `experiments/` (one script each),
and every number in this README is printed by one file:

```
python -m ukvat.run_sql sql/numbers.sql
```

Python fetches and reads the pages, and DuckDB SQL does the sample, the joins and the counting.

## Research (part 1)

### Peppol, a source that is not on your list

Peppol is the e-invoicing network, and its directory lists who can receive e-invoices. Under scheme
9932 a UK business's identifier is its VAT number, so here the VAT number hides inside another
identifier. The full export has 22,485 UK cards with a valid number. 15,259 of the company names
point at exactly one live company by the words of the name alone, and 3,315 cards look like people,
sole traders, whose names I kept out of this repo.

12,148 of the cards were registered on one day, 25 Aug 2025, and in the full months of 2026 it has
been 342 to 682 new UK cards a month. HMRC's policy paper of 28 Oct 2026 makes e-invoices
compulsory for VAT invoices from 1 April 2029, with Peppol as the network and HMRC as the UK's
Peppol authority. Today that authority sits in Supply Chain Coordination Limited, the company that
runs NHS Supply Chain. HMRC shows 18 of 20 random Peppol numbers as live.

For me Peppol was also an answer key. 2,000 random UK cards gave 1,401 companies with a legal
ending that point at exactly one live company, all registered and all with a known number. On them
"not found" can only mean that my method failed, and most of what follows was measured on them.

### EORI, the other identifier

A VAT registered trader's EORI, the number used for customs, is GB, the VAT number and 000. HMRC's
EORI checker is open, with no login, and for some traders it shows the name and address. So it is a
free second look at a number already found. On the 106 numbers from the crawl pages it gave a name
for 34, and 29 of those were the company on the page. Among my first finds it caught a platform's
number and a VAT group before HMRC's VAT checker did.

As a way to find numbers it gives nothing. On 18 Nov I looked for EORI numbers printed on pages.
The word EORI is on 3 of the 6,673 pages the website route fetched and on 8 of the 83,776 crawl
pages. There are 2 EORI numbers in all, and both pages print the VAT number as well.

### A VAT number carries its own date

UK numbers pass the check digits in one of two ways, mod 97, or mod 97 after adding 55. On 13 Nov I
noticed that the numbers on young companies were all of the second kind, and my guess was that this
kind is handed out in order.

It is. I joined 15,359 numbers to the incorporation date of their company (Peppol cards, crawl
pages, my own finds). For the 11,963 of the newer kind the number rises with the date, rank
correlation 0.869. A company registers for VAT after it is incorporated, never before, so for each
band of 100,000 numbers I took the date of the newest companies holding it (90th percentile) as the
date the band was issued. The bands then move at about 282,000 numbers a year. HMRC's statistics
say 234,000 new registrations in 2024 to 2025, closer than I expected.

The chart (`results/probes/vat_number_age.png`) has two ridges. The older kind climbs until about
2010 and stops at the top of the seven digit range, and the newer kind starts again from the bottom
in 2010.

![VAT number against the incorporation date of its company](results/probes/vat_number_age.png)

This is a test before any call to HMRC. A number much older than its company is either a
registration the company took over, usually from a sole trader who incorporated and kept the
number, or a wrong link. 362 numbers look older than their company. HMRC's EORI record names 84 of
them and 76 are the company's own. One of my register finds shows the other side: CLIMETECH LTD was
incorporated in July 2025, its site prints a number of the older kind, and HMRC shows that number
under a person's name at the company's address.

### Most registered companies do not print their number

Regulation 6 of the E-Commerce Regulations 2002 asks a business that sells online to show its VAT
number. Of the 1,401 companies I know are registered, 255 have a site that shows their company
number, and 98 of those print the VAT number, 38.4% (32.7 to 44.5, Wilson interval). By size band
it is micro 39 of 105, small 51 of 125, large 2 of 9, new 5 of 14 and dormant 1 of 2.

For the 155 silent sites I read the html again. In 2 the number was there and my reader missed it,
17 link a pdf where it may be, and 136 do not have it anywhere. So even with every website known,
the web route stops at about 4 in 10 of the registered companies that have one.

### A number with proof is right, one without proof often is not

I believe a site is the company's only if it shows the company's own registration number, which the
same regulation asks for. A find is strict when there is exactly one valid VAT number on such a
site, and loose when the one number is on a guessed site with no such proof. On the known set the
strict finds equal Peppol's number 96 times in 98 and the loose ones 3 times in 13. On the register
sample HMRC put 3 of the 4 loose finds under another name: the ordering platform behind a takeaway's
site (EPOS Technologies on Kebab City's terms page), the registrar of a parked domain (Freeola), and
a different company with the same initials.

### Sites go out of date

Both strict disagreements with Peppol are sites showing an older number. Virtus IT's site has a
number of the older kind, from around 2009 when the company was incorporated, and Peppol has one
from the newest band on a card of 28 Oct 2026. Invatech Health's site has a number from a band of
about 2014, older than the company (2019), and Peppol one from early 2026. HMRC shows both of
Peppol's numbers live under the company's own name, and it has no registration at all for either
of the old numbers on the sites. In both pairs the age of the number already said which one to
trust.

ETORROS LTD on the register sample is the same story. Its site shows a number in the band of its
own incorporation year (2020), and HMRC says it is not a live registration, so I think it was the
company's and was cancelled.

### One number, several companies

In a VAT group one number covers many companies, and HMRC shows one member's name, sometimes a name
the company does not use any more. Of 7 numbers I found where HMRC's EORI name was another company,
Companies House's control data explains 3: a former owner, a sister company and an old holding
company. One number, 204979488, is on the sites of two companies of the Sykes Cottages group.
For an invoice the group's number is right. As a key for a company it is not, and a customer who
merges suppliers on it merges two real suppliers.

### Names and postcodes prove less than they look

A third of live companies (32.8%) are registered at a postcode shared with 100 or more others, and
WC2H 9JQ alone has 75,154. 11.4% of companies share their name with another once the legal ending
and filler words go, 3.9% with only the legal ending dropped. The worst are families where only a
bracket differs, NAMECO (NO. x) 623 times. This is how the customer matches today.

### The buyer already has the number

St Helens and Knowsley Teaching Hospitals NHS Trust publishes its spending with a VAT number next to
each supplier, 34 numbers. That is this customer's situation, in public. Only 4 of the 34 are in
Peppol, 19 of the suppliers link to one company, and my website route finds the number for none of
the 19. They are big medical suppliers, and they put the number on the invoice, not on the site.

### Sources that gave something

| source | what I ran | what came back | verdict |
|---|---|---|---|
| company websites, company first | 400 sampled companies, domains guessed from the name | 23 provably theirs, 6 strict and 4 loose finds | works where the site is known, which is rare |
| the same route on known numbers | 1,401 Peppol companies | 255 own sites, 98 strict finds, 96 equal to Peppol | the proof test works |
| Peppol Directory | the full export | 22,485 valid UK numbers, 15,259 names link to one live company | the best open source, and growing |
| HMRC's EORI checker | numbers I had already found | a name for 34 of 106 crawl pairs, 29 of them the company | a free second look, not a source |
| Common Crawl text | 4 of the 100,000 files of CC-MAIN-2026-43 | 172 pages with a valid number, about 22,000 hosts in a whole crawl | cheap, and small |
| Common Crawl index | the 58 sites that showed their company number live | 31 are in the crawl, and of the 21 with a VAT page live, 9 have that page in it | a corpus alone misses half |
| one hospital's spend file | its 34 supplier numbers | the web route finds 0 of the 19 it can link | the buyer's own data wins |

The crawl figure is a floor. Every host in the slice counts as one over its chance of being in four
files, and it assumes the pair is on every page of the host (standard error about 4,000).

### Dead ends

| where | what I expected | what came back |
|---|---|---|
| Find a Tender, 3 to 10 Nov | award notices name their suppliers, maybe by VAT number | parties identified by PPON 4,071 times and by company number 1,608 times, never by a VAT number |
| The Gazette | insolvency notices name the business with its numbers | "Company number" in 1,705,312 notices, "VAT No" in 28 |
| spend files, one per publisher on data.gov.uk | buyers publish their suppliers' numbers | 6 of 112 have a VAT number column, 4 of those are empty |
| filed accounts, two days | some small companies tag the number | none in 23,751 filings |
| Amazon and eBay seller pages | business sellers have to show a VAT number | both disallow Common Crawl's crawler and forbid scraping, so I fetched none |
| Nominet WHOIS | it ties a guessed domain to a company | no registrant and no company number, and the .uk WHOIS stops on 9 Feb 2027 |
| pages saying "not VAT registered" | a way to tell "not registered" from "I failed" | 0 of 1,382 fetched pages, 2 of 83,776 crawl pages |
| EORI numbers on pages | importers and exporters print their EORI, sometimes without the VAT number | the word on 3 of 6,673 fetched pages and 8 of 83,776 crawl pages, 2 EORI numbers, both next to the VAT number |

Two of these taught me more than the table says. In the spend files Shropshire Community Health NHS
Trust's VAT number column is full of VAT amounts (2.1, 10.49, 4.4), and only St Helens and Knowsley
fills it with numbers. The data is held by every buyer and publishing it is a choice. In the
accounts my first scan said 15 filings had a VAT tag, because the regex was case blind and matched
"DeriVATives". There are none. The accounts do say other things: 5 filings note the company is in a
VAT group and 4 that it is not registered.

## Proof of concept (part 2)

### The samples

The register sample is drawn from every Active company in the snapshot of 1 Nov 2026 that is not
dormant and not an Overseas Entity, 4,591,683. Accounts category is the only thing in the snapshot
that says anything about size, and turnover decides VAT registration, so I split by it: micro
1,686,224, small 1,444,419, large (medium, full, group and the subsidiary exemptions) 147,827, new
(no accounts yet) 1,313,213. 100 from each. The order inside a band is md5 of a seed and the company
number, so anyone with the snapshot draws the same 400, and nothing in it depends on what a company
publishes. Rates for the whole register are weighted by the size of each band.

The known set is 2,000 random UK Peppol cards, linked to Companies House when the key words of the
name point at exactly one live company and the name has a legal ending. That gives 1,401 companies,
all registered, all with a known number.

### Method

For each company, up to 12 domains guessed from the name (.co.uk, .com, .uk), the home page and up
to four contact, terms, privacy or about pages, a regex for VAT numbers, the check digits, and the
company's own registration number on the page as the proof that the site is theirs. Robots.txt is
respected and there is a pause of a second before every request. One number on a proven site is a
strict find, one number on any guessed site is a loose find, two different numbers is no answer.

Then HMRC's checker. I fixed the outcomes of a check in `src/ukvat/score.py` on 13 Nov, three days
before the first check: HMRC shows the company (the same key words of the name, spaces ignored),
another name at the company's postcode (only where fewer than 100 companies share it, a VAT group
looks like this), someone else, or not registered.

### Results

| | register sample | known set |
|---|---|---|
| companies | 400 | 1,401 |
| some guessed site live | 234 | 1,082 |
| a site provably theirs | 23 | 255 |
| strict finds | 6 | 98, 96 of them Peppol's number |
| loose finds | 4 | 13, 3 of them Peppol's number |

What HMRC's checker said, each number counted once:

| finds | checked | HMRC shows the company | another name, same postcode | someone else | not registered |
|---|---|---|---|---|---|
| register sample, strict | 6 | 3 | 2 | 0 | 1 |
| register sample, loose | 4 | 1 | 0 | 3 | 0 |
| known set, strict, Peppol's number | 31 | 31 | 0 | 0 | 0 |
| known set, strict, not Peppol's number | 2 | 0 | 0 | 0 | 2 |
| known set, loose, not Peppol's number | 10 | 0 | 1 | 6 | 3 |

On the register that is 1.35 strict finds per 100 companies before HMRC, weighted over the four
bands, and 0.98 finds per 100 that HMRC shows under the company's own name.

Peppol is not clean either. Of 20 random Peppol numbers HMRC shows 18 as live, the other 2 are not
registered any more.

### How I measured the false positive rate

A find counts as right only when HMRC's checker shows the company's own name. Everything else is
wrong here, a group's number too, even though it is the right number for an invoice.

The sample is every find on the register sample, every find on the first 133 companies of the known
set, both numbers of every disagreement with Peppol, every loose find that is not Peppol's number,
and 20 random agreements out of the 96. The rates with their 95% intervals:

| finds | HMRC shows the company | interval |
|---|---|---|
| register sample, strict | 3 of 6 | 18.8% to 81.2% |
| register sample, loose | 1 of 4 | 4.6% to 69.9% |
| known set, strict, Peppol's number | 31 of 31 | 89.0% to 100% |
| known set, strict, all checked | 31 of 33 | 80.4% to 98.3% |
| known set, loose, not Peppol's number | 0 of 10 | 0% to 27.8% |

HMRC's checker answered 429 after about 45 checks on the morning of 16 Nov and again after a few in
the afternoon. I did not try to get round it, and the rest of the second list went through slowly
that evening and the next one. None of the 10 loose finds that are not Peppol's number is the
company. 6 are another company, mostly the one that owns the obvious domain, 3 are not registered,
and 1 is another name at the same postcode.

So on companies that are registered under their own number the proof test is close to perfect, and
agreeing with Peppol can stand in for a check, 31 of 31. On the register it is not, and the reason
is the population more than the reading. Of the 3 strict finds that are not the company, one is a
group's number (TORUS62 for Housing Maintenance Solutions, at the same head office), one is the
founder's own registration on CLIMETECH LTD's site, and one is a number HMRC no longer has (ETORROS
LTD). The age test had put the second on its list of numbers older than their company before the
check. Six finds is too few to say how often this happens on the whole register, and it is the
weakest number in this proof of concept.

### What these numbers do not capture

Guessing domains stands in for the company to website links a data company already holds, so the
register numbers are a floor for the route. Numbers in pdfs and images are not read, at most 19 of
the 155 silent sites. Peppol leans to companies that sell to other companies and to the public
sector, and every company in it is registered under its own number, so the known set is easier than
the register. Of the 390 register companies where nothing was found, only 30 sit in the four SIC
codes that almost never register (residents' management, dormant, non trading, buying and selling
own property). The other 360 I cannot split into "not registered" and "I failed". And a single rate
hides the numbers that are right for an invoice and wrong as a key for a company, the group numbers
and the ones a company took over from its owner.

## With real resources (part 3)

### What I would build

Not a bigger crawl. In this order:

1. Peppol's directory linked to Companies House. 22,485 numbers today, 15,259 of them linked to
   exactly one live company by the name alone, a full export every day, and by April 2029 every
   VAT registered business. An address match can settle some of the names that point at several
   companies, and the people stay out.
2. The customer's own invoices. Every VAT invoice they receive carries the supplier's number, the
   two thirds they match by name included. So what I would offer this customer is the match from
   the number on their invoice to a company record, with Peppol and the register behind it, more
   than a list of numbers. Their invoices are also a test set with the right answers in it.
3. The web route only for companies with a known site and no number from either. Strict finds only,
   through the age test and the EORI name before HMRC's checker.
4. A person for the cases a rule cannot decide.

### What each resource changes

Veridion's own company to website links fix the step that failed most here, only 23 of the 400
sampled companies had a site I could prove. They do not move the 38% of registered companies with a
site that print the number.

A crawl budget and a cluster make a whole Common Crawl cheap to read. Four of its 100,000 text
files were 251 MB and took this laptop 9 seconds to scan once they were downloaded, so one crawl is
about 6.3 TB and about 62 hours of one core. The yield stays near 22,000 hosts a crawl with both
numbers on a page, and the crawl had only 9 of the 21 VAT pages I found live, so live fetching stays
in.

Commercial sources I could not test, I had no access to any. The first thing I would do with one is
put 100 of its numbers through my checks (HMRC's checker, the age test and the proof on the page)
before reading anything else about it.

Proxies are not needed for the website route. It makes about 3 page requests per company, spread
over millions of different sites, so no single site's limit comes near. Proxies would only help
with getting round HMRC's 429 or the marketplaces' terms, and I would not do either for a product.

An annotation team is where I would spend. The cases a rule cannot decide are the group numbers,
the numbers a company took over from its owner and a person's number on a company's site. On the
register sample that was 3 of the 6 strict finds, and each one needs someone to read ownership
records.

### Cost per company

On this laptop, with 12 threads and the pause of a second, the website route took 49 seconds per
strict find on the register sample and 12 seconds on the known set. Almost all of it is waiting for
other people's servers. It is about 3 page requests and 10 DNS lookups per company, so on a cluster
the fetching costs close to nothing.

The person is the cost. Per 100 companies on the register the route gives 1.35 numbers to check
and 0.98 that HMRC shows under the company's own name. My guess is half a minute for one check in
HMRC's web checker and a few minutes for each case in between. So one confirmed number from the web
costs the fetching of about 100 companies, which is cheap, and one to a few minutes of a person,
which is not.

### What breaks first

1. Knowing the site. 23 of 400, and the reason most of the register has no answer.
2. The 38%. Even a perfect site finder stops there, no budget moves it.
3. The key. Group numbers, numbers taken over from an owner, a sole trader's number on the company's
   site. A dataset of one number per company is wrong for these, it has to be a company, a number
   and what kind of link it is.
4. Verification at volume. HMRC's API is for due diligence and the web checker slows down after a
   few dozen checks.

### What I would monitor

- A random sample of the dataset through HMRC's checker every month, the share still live. 2 of 20
  random Peppol numbers were already not live in November.
- Disagreements between sources that do not copy each other, the site and Peppol above all.
- The share of numbers older than their company, by the age test.
- Numbers that end up on more than one company.
- The customer's invoices that still fail to match.

## Debate topics

### Brute forcing the checksum against HMRC's checker

20,615,843 nine digit numbers pass the check digits, 79.5 days at 3 checks a second for one
application. It would work technically, and the issued numbers sit in bands whose dates can be read
from public data, so most of the 20.6 million could be skipped. I think that is why HMRC put the
API behind a login in 2025 and wrote that it is for due diligence. The web checker has its own
brake, it answered 429 after about 45 of my checks in 12 minutes. And a valid number only gives a
name, the matching to Companies House is still the hard part when 11.4% of names are shared. So no.

### Keeping it current

The snapshot is monthly and Peppol cards carry a date. The top of the newer band says how many
numbers HMRC has issued so far, a free count of new registrations. A number older than its company,
or different from Peppol's, gets checked again first. HMRC's own statistics say 218,000
registrations are cancelled in a year out of 2.33 million, so about one number in eleven goes stale
in a year, which fits 2 of 20 Peppol numbers already not live. From 2029 e-invoicing turns most of
this into reading a directory.

### Knowing it is wrong at scale

There is no complete list to compare with, but there are sources that do not copy each other. The
site and Peppol agreed 96 times in 98. HMRC's EORI names are an open audit, 29 of the 34 crawl pairs
with a name were the company. The age test and numbers on two companies cost nothing to run. The
customer's own invoices are a test set with a known answer. A small monthly sample through HMRC's
checker by hand tells the error rate.

### Sources I would not use in a product

Marketplace seller pages, their terms forbid scraping. Sole traders' names from Peppol, a person's
name next to a tax number is personal data even if Peppol publishes it, and I kept them out of this
repo too. Numbers from terms pages of platforms, they belong to the platform. HMRC's API for anything
other than due diligence, and the web checker at volume.

## Beyond the UK

Germany is close to the mirror image of the UK. VIES confirmed
both German numbers I tried and showed "---" as the name and the address, so the part HMRC's checker
gives me for free, whose number it is, is missing. Discovery should be easier. A German business
site has to carry an Impressum with its register entry and its VAT ID if it has one, which is the
pair my proof test looks for, so that half of the pipeline moves over. I did not measure how often
the rule is followed there. The checking half I would build again, from sources that agree with each
other, because VIES will not say whose number it is.

France is a country where the number is barely discovered. A French VAT number is FR, a two digit
key and the SIREN, the company's number in the national register, and the key is normally computed
from the SIREN. On 18 Nov I took 18 live SARL and SAS from ten departements in the state's open
company search and asked VIES about each number. The search itself prints a VAT number for 14 of
them, and VIES says valid for all 14 and shows the name every time. 13 of the 14 are the number I
computed. The other one, GLB PIZZAS, has a key with a letter in it, FR0A477804645, which the formula
cannot give. For the 4 where the search prints nothing, VIES says the computed number is not valid,
so those companies have no live number. In France "not found" means "not registered", which is the
split I could not make for 360 of the 390 UK companies where I found nothing.

Of the three I looked at, the UK is hard on discovery and easy on verification, Germany looks like
the other way round, and France is easy on both. So I would start with the countries where the number follows
from the register, a join and a VIES call per company. France is one, and I expect Belgium to be
another, where the VAT number is the enterprise number with BE in front, but I did not check it.
Countries like Germany need the website route and another way of checking. The really hard ones are
hard on both sides: a number with no link to the register like the UK's, and a checker that shows
no name like Germany's.

## How to run

The Companies House snapshot goes in `data/ch/` first, see `data/README.md`.

```
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev,probes]
python -m ukvat.run_sql sql/profile.sql sql/sample.sql
python -m ukvat.websites sample/register.csv results/websites
python -m ukvat.run_sql sql/to_check.sql
python -m ukvat.handcheck results/hmrc/to_check.csv results/hmrc/checks.csv
python -m ukvat.score results/hmrc/to_check.csv results/hmrc/checks.csv results/hmrc/scored.csv
python -m ukvat.run_sql sql/numbers.sql
pytest
```

`handcheck` shows each found number and asks what HMRC's checker said about it. `numbers.sql` only
reads the committed `results/` and `sample/`, so it runs on a fresh clone without any download. The
probes are in `experiments/`, each one with its command at the top and in the log, and most of them
need the name index first (`python -m ukvat.chnames`).
