-- Every number the README reports comes from here and nowhere else.
--   python -m ukvat.run_sql sql/numbers.sql
-- A number found counts as confirmed only after my check in HMRC's checker. The checks go into
-- results/hmrc/checks.csv and checks_2.csv, and python -m ukvat.score turns them into
-- results/hmrc/scored.csv and scored_2.csv.

create view sample as select * from read_csv('sample/register.csv', header = true, all_varchar = true);
create view strata as select * from read_csv('sample/strata.csv', header = true);
create view not_found as
    select * from read_csv('results/probes/not_found_split.csv', header = true, all_varchar = true);
create view reg as
    select * from read_csv('results/websites/companies.csv', header = true, all_varchar = true);
-- the known set, 1,401 companies whose number Peppol already gives (the first 133 were inside it)
create view known as
    select c.*, k.peppol_vrn
    from read_csv('results/peppol_2000/websites/companies.csv', header = true, all_varchar = true) c
    join read_csv('results/peppol_2000/known_set.csv', header = true, all_varchar = true) k
        using (company_number);
create view scored as
    select * from read_csv(['results/hmrc/scored.csv', 'results/hmrc/scored_2.csv'],
                           header = true, all_varchar = true, union_by_name = true);
-- every find of the website route that went to HMRC, each number and company once over both
-- lists. Peppol's own numbers (the random 20, Peppol's side of a disagreement) are not finds
create view finds as
    select distinct s.vrn, s.company_number, s.outcome, s.verdict,
           case when s.source_set = 'register sample' then 'register sample'
                when s.vrn = k.peppol_vrn then 'known set, equal to peppol'
                else 'known set, not peppol''s' end as kind
    from scored s left join known k using (company_number)
    where s.source_set not in ('peppol random 20', 'disagreement, peppol')
      and s.verdict <> 'not checked';
-- the 95% Wilson interval, as in experiments/legal_duty.py
create macro wilson_lo(k, n) as round(100 * (k / n + 1.96 * 1.96 / (2 * n)
    - 1.96 * sqrt(k / n * (1 - k / n) / n + 1.96 * 1.96 / (4 * n * n))) / (1 + 1.96 * 1.96 / n), 1);
create macro wilson_hi(k, n) as round(100 * (k / n + 1.96 * 1.96 / (2 * n)
    + 1.96 * sqrt(k / n * (1 - k / n) / n + 1.96 * 1.96 / (4 * n * n))) / (1 + 1.96 * 1.96 / n), 1);
create macro percent(k, n) as k || ' of ' || n || ', ' || round(100 * k / n, 1) || '% ('
    || wilson_lo(k, n) || ' to ' || wilson_hi(k, n) || ')';

create table numbers as
-- the register sample, as found
select 'register' as section, stratum as part, outcome as what, count(*)::varchar as value
from reg group by all
union all
select 'register', stratum, 'own site found', count(*) filter (where own_site is not null)::varchar
from reg group by all
union all
select 'register', 'all', 'some guessed site live',
       count(*) filter (where sites_live::int > 0)::varchar
from reg
union all
select 'register', 'all', 'own site found', count(*) filter (where own_site is not null)::varchar
from reg
union all
-- the strict rate per stratum weighted by how many companies each stratum stands for
select 'register', 'all, weighted', 'strict finds per 100 companies',
       round(100 * sum(s.companies * r.hits / 100.0) / sum(s.companies), 2)::varchar
from strata s
join (select stratum, count(*) filter (where outcome = 'strict') as hits from reg group by all) r
    using (stratum)
union all
-- the same after HMRC, strict or loose, and only the finds HMRC shows under the company's own
-- name. A group's number or a person's at the same postcode does not count here
select 'register', 'all, weighted', 'finds HMRC shows under the company''s name, per 100 companies',
       round(100 * sum(s.companies * r.hits / 100.0) / sum(s.companies), 2)::varchar
from strata s
join (select reg.stratum, count(*) filter (where v.verdict = 'right company') as hits
      from reg left join scored v on v.vrn = reg.vrn and v.source_set = 'register sample'
      group by all) r
    using (stratum)
union all
-- the known set: every company here has a VAT number, Peppol gave it
select 'known set', 'all', case when vrn is null then 'nothing found'
                               when vrn = peppol_vrn then 'same number as peppol'
                               else 'different number' end || ' (' || outcome || ')',
       count(*)::varchar
from known group by all
union all
select 'known set', 'all', 'own site found', count(*) filter (where own_site is not null)::varchar
from known
union all
select 'known set', 'all', 'some guessed site live',
       count(*) filter (where sites_live::int > 0)::varchar
from known
union all
-- my checks in HMRC's VAT checker, per list and per route
select 'hmrc checks', source_set || ', ' || outcome, verdict, count(*)::varchar
from scored group by all
union all
select 'hmrc checks', 'all', 'numbers not checked yet',
       count(distinct vrn) filter (where verdict = 'not checked')::varchar
from scored
union all
-- 4 numbers were in both lists, so 79 checks are 75 different numbers
select 'hmrc checks', 'all', 'checks in the web checker, different numbers',
       count(*) || ', ' || count(distinct vrn)
from scored where verdict <> 'not checked'
union all
-- the same per kind of find, a number checked in both lists counts once
select 'hmrc checks', 'finds, ' || kind || ', ' || outcome, verdict, count(*)::varchar
from finds group by all
union all
-- how often HMRC shows the company itself, with the 95% interval. This is the false positive
-- rate turned round, everything else counts as wrong, a group's number too
select 'hmrc checks', 'rate', what, percent(k, n)
from (select kind || ', ' || outcome || ', HMRC shows the company' as what,
             count(*) filter (where verdict = 'right company') as k, count(*) as n
      from finds group by all
      union all
      select 'every known set strict find, HMRC shows the company',
             count(*) filter (where verdict = 'right company'), count(*)
      from finds where outcome = 'strict' and kind <> 'register sample'
      union all
      select 'peppol random 20, still live',
             count(*) filter (where verdict <> 'not registered'), count(*)
      from scored where source_set = 'peppol random 20' and verdict <> 'not checked')
union all
-- HMRC's address is the VAT one, often a trading address, so a different postcode is no evidence
select 'hmrc checks', 'right company', 'postcode differs from the registered office',
       count(*) filter (where replace(upper(postcode), ' ', '')
                              <> replace(upper(hmrc_postcode), ' ', '')) || ' of ' || count(*)
from (select distinct vrn, company_number, postcode, hmrc_postcode from scored
      where verdict = 'right company' and postcode is not null and hmrc_postcode is not null)
union all
-- the frame the register sample is drawn from, and the 390 where nothing was found
select 'register', stratum, 'companies in the frame', companies::varchar from strata
union all
select 'register', 'all', 'companies in the frame', sum(companies)::varchar from strata
union all
select 'register', 'all', 'nothing found', sum(nothing_found::int)::varchar from not_found
union all
select 'register', 'all', 'nothing found, in a code that rarely registers',
       sum(in_a_rarely_registered_code::int)::varchar
from not_found
union all
select 'register', 'all', 'nothing found, nothing to say why', sum(silent::int)::varchar
from not_found
union all
select 'known set', 'all', 'peppol cards read', count(*)::varchar
from read_csv('results/peppol_2000/linked.csv', header = true, all_varchar = true)
union all
-- the probes, each file is two columns, what and value. published_figures.csv is HMRC's VAT
-- statistics for 2024 to 2025 as printed on gov.uk (see the log, 13 Nov)
select 'probe', parse_filename(filename, true), what, value
from read_csv(['results/probes/vat_number_age.csv', 'results/probes/legal_duty.csv',
               'results/probes/published_figures.csv',
               'results/probes/peppol_dates.csv', 'results/probes/registered_sectors_summary.csv',
               'results/probes/cross_sources.csv', 'results/probes/accounts_vat.csv',
               'results/probes/commoncrawl_wet.csv', 'results/probes/checksum_space.csv',
               'results/probes/unit_costs.csv', 'results/peppol/summary.csv'],
              header = true, all_varchar = true, filename = true,
              columns = {'what': 'varchar', 'value': 'varchar'})
union all
-- these two are quoted differently, so each is read on its own
select 'probe', 'gazette_vat', 'notices with ' || search, notices
from read_csv('results/probes/gazette_vat.csv', header = true, all_varchar = true)
union all
select 'probe', 'small_checks', "check", result
from read_csv('results/probes/small_checks.csv', header = true, all_varchar = true)
union all
select 'probe', parse_filename(filename, true), what, value
from read_csv(['results/probes/name_collisions.csv', 'results/probes/postcode_crowding.csv'],
              header = true, all_varchar = true, filename = true)
union all
-- the probes with a row per thing, counted here
select 'probe', 'procurement_ids', 'parties identified by ' || scheme, parties
from read_csv('results/probes/procurement_ids.csv', header = true, all_varchar = true)
union all
select 'probe', 'spend_headers', 'spend files read', count(*)::varchar
from read_csv('results/probes/spend_headers.csv', header = true, all_varchar = true)
union all
select 'probe', 'spend_headers', 'with a vat number column',
       count(*) filter (where has_vat_number_column = 'True')::varchar
from read_csv('results/probes/spend_headers.csv', header = true, all_varchar = true)
union all
select 'probe', 'spend_vat', publisher,
       rows_with_vat || ' rows filled, ' || pass_check_digits || ' numbers pass the check digits'
from read_csv('results/probes/spend_vat.csv', header = true, all_varchar = true)
union all
select 'probe', 'says_not_registered', 'pages saying it, ' || p.pile,
       count(s.pile)::varchar
from (values ('crawl'), ('fetched')) p(pile)
left join read_csv('results/probes/says_not_registered.csv', header = true, all_varchar = true) s
    using (pile)
group by all
union all
select 'probe', 'commoncrawl_coverage', what, value
from (select count(*) as sites, count(*) filter (where pages_in_crawl::int > 0) as in_crawl,
             count(*) filter (where vat_pages_found_live::int > 0) as vat_page_live,
             count(*) filter (where vat_pages_in_crawl::int > 0) as vat_page_in_crawl
      from read_csv('results/probes/commoncrawl_coverage.csv', header = true, all_varchar = true))
unpivot (value for what in (sites, in_crawl, vat_page_live, vat_page_in_crawl))
union all
select 'probe', 'commoncrawl_estimate', host, weight
from read_csv('results/probes/commoncrawl_estimate.csv', header = true, all_varchar = true)
where host like 'all hosts%'
union all
select 'probe', 'commoncrawl_pairs', 'eori says: ' || verdict, count(*)::varchar
from read_csv('results/probes/commoncrawl_pairs.csv', header = true, all_varchar = true)
group by all
union all
select 'probe', 'group_links', relation, count(*)::varchar
from read_csv('results/probes/group_links.csv', header = true, all_varchar = true)
group by all
union all
select 'probe', 'nhs_ledger', 'supplier vat numbers, in peppol',
       count(*) || ', ' || count(*) filter (where in_peppol = 'True')
from read_csv('results/probes/nhs_ledger.csv', header = true, all_varchar = true)
union all
select 'probe', 'nhs_ledger', 'suppliers linked to one company, a number found on their site',
       count(*) || ', ' || count(vrn)
from read_csv('results/probes/nhs_ledger/websites/companies.csv', header = true, all_varchar = true)
union all
select 'probe', 'vies_germany', vat_id,
       'valid ' || valid || ', name shown ' || name_shown || ', address shown ' || address_shown
from read_csv('results/probes/vies_germany.csv', header = true, all_varchar = true)
union all
-- 18 Nov, EORI numbers printed on pages, and France where the number follows from the SIREN
select 'probe', 'eori_on_pages', what, value
from read_csv('results/probes/eori_on_pages_summary.csv', header = true, all_varchar = true)
union all
select 'probe', 'eori_on_pages', 'eori numbers, with a vat number inside, vat number also on the page',
       count(*) || ', ' || count(*) filter (where vat_inside = 'True') || ', '
           || count(*) filter (where vat_also_on_page = 'True')
from read_csv('results/probes/eori_on_pages.csv', header = true, all_varchar = true)
union all
select 'probe', 'vies_france', 'companies', count(*)::varchar
from read_csv('results/probes/vies_france.csv', header = true, all_varchar = true)
union all
select 'probe', 'vies_france', 'the search shows the computed number, another number, none',
       count(*) filter (where search_vat = computed_vat) || ', '
           || count(*) filter (where coalesce(search_vat, '') not in ('', computed_vat)) || ', '
           || count(*) filter (where coalesce(search_vat, '') = '')
from read_csv('results/probes/vies_france.csv', header = true, all_varchar = true)
union all
select 'probe', 'vies_france', 'vies on the computed number: ' || vies_on_computed, count(*)::varchar
from read_csv('results/probes/vies_france.csv', header = true, all_varchar = true)
group by all
union all
select 'probe', 'vies_france', 'vies on the other number the search shows: ' || vies_on_search_vat,
       count(*)::varchar
from read_csv('results/probes/vies_france.csv', header = true, all_varchar = true)
where coalesce(vies_on_search_vat, '') <> ''
group by all
union all
select 'probe', 'vies_france', 'vies shows the name', count(*)::varchar
from read_csv('results/probes/vies_france.csv', header = true, all_varchar = true)
where name_shown = 'True'
union all
select 'probe', 'marketplace_robots', site || ', ' || page,
       'common crawl allowed ' || common_crawl_allowed || ', read on ' || read_on
from read_csv('results/probes/marketplace_robots.csv', header = true, all_varchar = true)
union all
-- every UK card in Peppol's full export, linked by the key words of the name
select 'probe', 'peppol_all',
       case when looks_like_company = 'False' then 'looks like a person'
            when matches = '0' then 'a company name, no live company'
            when matches = '1' then 'a company name, exactly one live company'
            else 'a company name, several live companies' end,
       count(*)::varchar
from read_csv('results/peppol_all/linked.csv', header = true, all_varchar = true)
group by all;

select * from numbers order by section, part, what;
