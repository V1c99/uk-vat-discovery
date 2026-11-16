# data/

Raw downloads, not committed. This file says how to get each one back. Everything is read from
these paths, with the commands run from the repo root.

Downloaded by hand:

| File | Source | Downloaded |
|---|---|---|
| `ch/BasicCompanyDataAsOneFile-2026-11-01.zip` (494 MB, a 2.8 GB csv inside) | Companies House free data product, https://download.companieshouse.gov.uk/en_output.html | 13 Nov 2026 |
| `probes/peppol/participants.csv` (404 MB, every participant id) | Peppol Directory, participant list from its export page, https://directory.peppol.eu | 13 Nov 2026 |
| `accounts/Accounts_Bulk_Data-2026-11-10.zip` and `-2026-11-12.zip` | Companies House accounts data product, https://download.companieshouse.gov.uk/en_accountsdata.html | 13 Nov 2026 |

Unzip the first one into `data/ch/`. The SQL in `sql/` reads `data/ch/BasicCompanyDataAsOneFile-*.csv`.

Built here, not downloaded:

- `ch_names.parquet`, every company name reduced to its key words: `python -m ukvat.chnames`
- `pages/` and `dns.json`, the cache of `ukvat.websites`, so a rerun asks no site twice

The probe scripts download what else they need into `probes/` (Peppol cards and the full export,
Common Crawl files, spend files, Find a Tender notices, VIES, WHOIS) and `psc/` (the ownership
snapshot). Each one has its command at the top and in `research/log.md`.
