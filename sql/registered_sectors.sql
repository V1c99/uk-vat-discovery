-- Which kinds of company almost never show up among companies that are known to be VAT
-- registered. Known registered = Peppol cards linked to one company by name. Compared with the
-- whole frame by SIC code. Peppol leans to public sector suppliers, so this is a hint about
-- sectors, not a measurement of them.
--   python -m ukvat.run_sql sql/registered_sectors.sql

create view frame as
select companynumber as company_number, siccodesictext_1 as sic_1
from read_csv('data/ch/BasicCompanyDataAsOneFile-*.csv',
              header = true, normalize_names = true, all_varchar = true)
where companystatus = 'Active'
  and coalesce(accountsaccountcategory, '') <> 'DORMANT'
  and companycategory <> 'Overseas Entity';

create view known as
select distinct l.company_number, c.sic_1
from read_csv('results/peppol_2000/linked.csv', header = true, all_varchar = true) l
join 'data/ch_names.parquet' c using (company_number)
where l.matches = '1' and l.looks_like_company = 'True';

-- the codes everybody guesses first, and a few more
create table codes as select * from (values
    ('68209', 'letting and operating own or leased real estate'),
    ('68100', 'buying and selling own real estate'),
    ('98000', 'residents property management'),
    ('64209', 'holding companies'),
    ('74990', 'non-trading company'),
    ('99999', 'dormant company'),
    ('70229', 'management consultancy'),
    ('62020', 'it consultancy'),
    ('47910', 'retail via internet'),
    ('82990', 'other business support')) t(code, what);

copy (
    with f as (select left(sic_1, 5) as code, count(*) as n from frame group by all),
         k as (select left(sic_1, 5) as code, count(*) as n from known group by all),
         ft as (select count(*) as n from frame),
         kt as (select count(*) as n from known)
    select codes.code, codes.what,
           round(100.0 * coalesce(f.n, 0) / ft.n, 2) as pct_of_frame,
           round(100.0 * coalesce(k.n, 0) / kt.n, 2) as pct_of_known_registered,
           coalesce(k.n, 0) as known_registered,
           round((coalesce(k.n, 0) * 1.0 / kt.n) / nullif(coalesce(f.n, 0) * 1.0 / ft.n, 0), 2)
               as ratio
    from codes
    cross join ft
    cross join kt
    left join f on f.code = codes.code
    left join k on k.code = codes.code
    order by ratio
) to 'results/probes/registered_sectors.csv' (header);

-- how much of the frame sits in codes that known registered companies almost never have
copy (
    with r as (select * from read_csv('results/probes/registered_sectors.csv',
                                      header = true, all_varchar = true))
    select 'known registered companies' as what, (select count(*) from known)::varchar as value
    union all
    select 'frame share in codes with ratio under 0.2',
           sum(pct_of_frame::double)::varchar || '%' from r where ratio::double < 0.2
    union all
    select 'those codes', string_agg(code, ' ') from r where ratio::double < 0.2
) to 'results/probes/registered_sectors_summary.csv' (header);

-- the register sample's companies with nothing found, split by that
copy (
    with r as (select code from read_csv('results/probes/registered_sectors.csv',
                                         header = true, all_varchar = true)
               where ratio::double < 0.2),
         s as (select c.stratum, c.outcome, left(m.sic_1, 5) as code
               from read_csv('results/websites/companies.csv', header = true, all_varchar = true) c
               join read_csv('sample/register.csv', header = true, all_varchar = true) m
                   using (company_number)
               where c.vrn is null)
    select stratum,
           count(*) as nothing_found,
           count(*) filter (where code in (select code from r)) as in_a_rarely_registered_code,
           count(*) filter (where code not in (select code from r)) as silent
    from s group by all order by all
) to 'results/probes/not_found_split.csv' (header);

select * from read_csv(['results/probes/registered_sectors_summary.csv'], header = true,
                       all_varchar = true);
