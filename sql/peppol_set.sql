-- The known set: Peppol cards with a company's name that points at exactly one live company.
-- Their VAT number is known before the website route looks, so a miss there means the route
-- failed, not that the company has no number. A card with a person's name is left out, a sole
-- trader called John Smith is not JOHN SMITH LTD.

copy (
    select case
               when accounts = 'MICRO ENTITY' then 'micro'
               when accounts in ('TOTAL EXEMPTION FULL', 'TOTAL EXEMPTION SMALL',
                    'UNAUDITED ABRIDGED', 'SMALL', 'AUDITED ABRIDGED', 'PARTIAL EXEMPTION') then 'small'
               when accounts in ('MEDIUM', 'FULL', 'GROUP',
                    'AUDIT EXEMPTION SUBSIDIARY', 'FILING EXEMPTION SUBSIDIARY') then 'large'
               when accounts = 'DORMANT' then 'dormant'
               else 'new'
           end as stratum,
           company_number, company_name, postcode, vrn as peppol_vrn
    from read_csv('results/peppol/linked.csv', header = true, all_varchar = true)
    where matches = '1' and looks_like_company = 'True'
    order by company_number
) to 'results/peppol/known_set.csv' (header);
