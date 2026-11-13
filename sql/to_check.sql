-- Every number that needs a check in HMRC's VAT checker, with the page it came from so the
-- evidence can be opened next to the check. I do these by hand: python -m ukvat.handcheck

copy (
    with c as (
        select * from read_csv('results/websites/companies.csv', header = true, all_varchar = true)
    ),
    s as (
        select * from read_csv('sample/register.csv', header = true, all_varchar = true)
    ),
    first_page as (
        select company_number, vrn, min(page) as page
        from read_csv('results/websites/candidates.csv', header = true, all_varchar = true)
        group by all
    )
    select c.vrn, 'register sample' as source_set, c.outcome, c.company_number, c.company_name,
           s.postcode, p.page
    from c
    join s using (company_number)
    left join first_page p using (company_number, vrn)
    where c.vrn is not null
    order by c.outcome, c.company_number
) to 'results/hmrc/to_check.csv' (header);
