-- The second list for HMRC's web checker, from the run on the 1,401 Peppol companies.
--   both numbers of every company where the site and Peppol disagree on a strict find
--   every loose find that is not Peppol's number
--   20 random strict finds that do agree, to test agreement as a stand-in for HMRC
-- Same tool as the first list:
--   python -m ukvat.handcheck results/hmrc/to_check_2.csv results/hmrc/checks_2.csv

create view c as
select c.*, k.peppol_vrn, k.postcode
from read_csv('results/peppol_2000/websites/companies.csv', header = true, all_varchar = true) c
join read_csv('results/peppol_2000/known_set.csv', header = true, all_varchar = true) k
    using (company_number);

create view pages as
select company_number, vrn, min(page) as page
from read_csv('results/peppol_2000/websites/candidates.csv', header = true, all_varchar = true)
group by all;

copy (
    select vrn, 'disagreement, the site' as source_set, outcome, company_number, company_name,
           postcode, page
    from c left join pages using (company_number, vrn)
    where outcome = 'strict' and vrn <> peppol_vrn
    union all
    select peppol_vrn, 'disagreement, peppol', outcome, company_number, company_name, postcode,
           null
    from c where outcome = 'strict' and vrn <> peppol_vrn
    union all
    select vrn, 'loose, not peppol''s', outcome, company_number, company_name, postcode, page
    from c left join pages using (company_number, vrn)
    where outcome = 'loose_only' and vrn <> peppol_vrn
    union all
    select * from (
        select vrn, 'agreement, random 20', outcome, company_number, company_name, postcode, page
        from c left join pages using (company_number, vrn)
        where outcome = 'strict' and vrn = peppol_vrn
        order by md5('2026-11-16' || vrn)
        limit 20
    )
    order by source_set, company_number
) to 'results/hmrc/to_check_2.csv' (header);
