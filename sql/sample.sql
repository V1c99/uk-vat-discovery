-- The register sample. Live companies only, dormant ones and overseas entities out, four strata
-- by accounts category, 100 companies each, in md5 order of a seed and the company number.

create view ch as
select * from read_csv('data/ch/BasicCompanyDataAsOneFile-*.csv',
                       header = true, normalize_names = true, all_varchar = true);

create table frame as
select *,
       case
           when accountsaccountcategory = 'MICRO ENTITY' then 'micro'
           when accountsaccountcategory in ('TOTAL EXEMPTION FULL', 'TOTAL EXEMPTION SMALL',
                'UNAUDITED ABRIDGED', 'SMALL', 'AUDITED ABRIDGED', 'PARTIAL EXEMPTION') then 'small'
           when accountsaccountcategory in ('MEDIUM', 'FULL', 'GROUP',
                'AUDIT EXEMPTION SUBSIDIARY', 'FILING EXEMPTION SUBSIDIARY') then 'large'
           else 'new'  -- no accounts filed yet, most are under two years old
       end as stratum
from ch
where companystatus = 'Active'
  and coalesce(accountsaccountcategory, '') <> 'DORMANT'
  and companycategory <> 'Overseas Entity';

-- how many companies each stratum stands for, needed to weight the estimate later
copy (select stratum, count(*) as companies from frame group by all order by all)
to 'sample/strata.csv' (header);

copy (
    select stratum,
           companynumber as company_number,
           companyname as company_name,
           regaddressaddressline1 as address_1,
           regaddressaddressline2 as address_2,
           regaddressposttown as post_town,
           regaddresspostcode as postcode,
           companycategory as category,
           incorporationdate as incorporated,
           accountsaccountcategory as accounts,
           siccodesictext_1 as sic_1,
           siccodesictext_2 as sic_2
    from frame
    qualify row_number() over (partition by stratum
                               order by md5('2026-11-13' || companynumber)) <= 100
    order by stratum, company_number
) to 'sample/register.csv' (header);
