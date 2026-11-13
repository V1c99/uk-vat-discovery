-- Two ways the register makes matching harder than it looks.
-- Names: how many companies share their name with another company once "Ltd" or "Limited" is
-- dropped, and with the looser key the Peppol link used.
-- Postcodes: how many companies sit at a postcode shared with hundreds of others, which is what
-- a formation agent's or an accountant's address looks like.
--   python -m ukvat.run_sql sql/crowding.sql

create view names as select * from 'data/ch_names.parquet';

create view frame as
select companynumber, regaddresspostcode as postcode
from read_csv('data/ch/BasicCompanyDataAsOneFile-*.csv',
              header = true, normalize_names = true, all_varchar = true)
where companystatus = 'Active'
  and coalesce(accountsaccountcategory, '') <> 'DORMANT'
  and companycategory <> 'Overseas Entity';

copy (
    with k as (select key_ending_only, count(*) as n from names group by all),
         l as (select key, count(*) as n from names group by all)
    select 'companies' as what, count(*)::varchar as value from names
    union all
    select 'share sharing their name without the legal ending',
           round(100.0 * sum(n) filter (where n > 1) / sum(n), 1)::varchar || '%' from k
    union all
    select 'share sharing the looser key (filler words dropped too)',
           round(100.0 * sum(n) filter (where n > 1) / sum(n), 1)::varchar || '%' from l
    union all
    select 'most shared name ' || row_number() over (order by n desc), key_ending_only || ' (' || n || ')'
    from (select * from k where key_ending_only <> '' order by n desc limit 10)
) to 'results/probes/name_collisions.csv' (header);

copy (
    with p as (select upper(replace(postcode, ' ', '')) as pc, count(*) as n
               from frame where postcode is not null group by all)
    select 'companies in the frame with a postcode' as what, sum(n)::varchar as value from p
    union all
    select 'at a postcode with 100 or more companies',
           round(100.0 * sum(n) filter (where n >= 100) / sum(n), 1)::varchar || '%' from p
    union all
    select 'at a postcode with 1,000 or more companies',
           round(100.0 * sum(n) filter (where n >= 1000) / sum(n), 1)::varchar || '%' from p
    union all
    select 'postcodes with 1,000 or more companies', count(*) filter (where n >= 1000)::varchar from p
    union all
    select 'busiest postcode ' || row_number() over (order by n desc), pc || ' (' || n || ')'
    from (select * from p order by n desc limit 5)
) to 'results/probes/postcode_crowding.csv' (header);

-- every postcode with 100 or more companies, score.py does not count a postcode match there
copy (
    select upper(replace(postcode, ' ', '')) as postcode, count(*) as companies
    from frame where postcode is not null group by all having count(*) >= 100 order by 2 desc
) to 'results/probes/crowded_postcodes.csv' (header);

select * from read_csv(['results/probes/name_collisions.csv', 'results/probes/postcode_crowding.csv'],
                       header = true, all_varchar = true);
