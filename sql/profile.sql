-- counts on the Companies House snapshot, written to results/ch_profile.csv

create view ch as
select * from read_csv('data/ch/BasicCompanyDataAsOneFile-*.csv',
                       header = true, normalize_names = true, all_varchar = true);

copy (
    select 'status' as what, companystatus as value, count(*) as companies
    from ch group by all
    union all
    select 'category (active)', companycategory, count(*)
    from ch where companystatus = 'Active' group by all
    union all
    select 'accounts (active)', accountsaccountcategory, count(*)
    from ch where companystatus = 'Active' group by all
    order by what, companies desc
) to 'results/ch_profile.csv' (header);
