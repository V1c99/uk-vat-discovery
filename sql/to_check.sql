-- Every number that needs a check in HMRC's VAT checker, with the page it came from.
--   register sample: what the website route found on the 400
--   peppol known set: what it found on the 133 companies whose number Peppol already gave
--   peppol random 20: Peppol's own numbers, to see how many HMRC still has live

copy (
    with found as (
        select 'register sample' as source_set, c.*, s.postcode
        from read_csv('results/websites/companies.csv', header = true, all_varchar = true) c
        join read_csv('sample/register.csv', header = true, all_varchar = true) s
            using (company_number)
        union all by name
        select 'peppol known set' as source_set, c.*, k.postcode
        from read_csv('results/peppol/websites/companies.csv', header = true, all_varchar = true) c
        join read_csv('results/peppol/known_set.csv', header = true, all_varchar = true) k
            using (company_number)
    ),
    pages as (
        select company_number, vrn, min(page) as page
        from read_csv(['results/websites/candidates.csv', 'results/peppol/websites/candidates.csv'],
                      header = true, all_varchar = true)
        group by all
    ),
    peppol_random as (
        select vrn, 'peppol random 20' as source_set, 'peppol' as outcome,
               company_number,
               coalesce(company_name, peppol_name, '(a person, name not kept)') as company_name,
               postcode,
               null as page
        from read_csv('results/peppol/linked.csv', header = true, all_varchar = true)
        order by md5('2026-11-13' || vrn)
        limit 20
    )
    select f.vrn, f.source_set, f.outcome, f.company_number, f.company_name, f.postcode, p.page
    from found f
    left join pages p using (company_number, vrn)
    where f.vrn is not null
    union all
    select * from peppol_random
    order by source_set, outcome, company_number
) to 'results/hmrc/to_check.csv' (header);
