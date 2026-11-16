-- Every number the README reports comes from here and nowhere else.
--   python -m ukvat.run_sql sql/numbers.sql
-- A number found counts as confirmed only after my check in HMRC's checker. The checks go into
-- results/hmrc/checks.csv and checks_2.csv, and python -m ukvat.score turns them into
-- results/hmrc/scored.csv and scored_2.csv.

create view sample as select * from read_csv('sample/register.csv', header = true, all_varchar = true);
create view strata as select * from read_csv('sample/strata.csv', header = true);
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

create table numbers as
-- the register sample, before the hand checks
select 'register' as section, stratum as part, outcome as what, count(*)::varchar as value
from reg group by all
union all
select 'register', stratum, 'own site found', count(*) filter (where own_site is not null)::varchar
from reg group by all
union all
-- the strict rate per stratum weighted by how many companies each stratum stands for
select 'register', 'all, weighted', 'strict finds per 100 companies',
       round(100 * sum(s.companies * r.hits / 100.0) / sum(s.companies), 2)::varchar
from strata s
join (select stratum, count(*) filter (where outcome = 'strict') as hits from reg group by all) r
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
-- my hand checks in HMRC's VAT checker, per set and per route
select 'hmrc checks', source_set || ', ' || outcome, verdict, count(*)::varchar
from scored group by all
union all
-- the probes, each file is two columns, what and value
select 'probe', parse_filename(filename, true), what, value
from read_csv(['results/probes/vat_number_age.csv', 'results/probes/legal_duty.csv',
               'results/probes/peppol_dates.csv', 'results/probes/registered_sectors_summary.csv',
               'results/probes/cross_sources.csv', 'results/probes/accounts_vat.csv',
               'results/probes/commoncrawl_wet.csv', 'results/probes/checksum_space.csv',
               'results/probes/unit_costs.csv', 'results/peppol/summary.csv'],
              header = true, all_varchar = true, filename = true,
              columns = {'what': 'varchar', 'value': 'varchar'})
union all
select 'probe', parse_filename(filename, true), what, value
from read_csv(['results/probes/name_collisions.csv', 'results/probes/postcode_crowding.csv'],
              header = true, all_varchar = true, filename = true);

select * from numbers order by section, part, what;
