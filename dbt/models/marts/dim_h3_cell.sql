with cells as (
    select
        h3_res8,
        h3_res6
    from {{ ref('int_buildings_h3') }}

    union

    select
        h3_res8,
        h3_res6
    from {{ ref('int_population_h3') }}
)

select
    h3_res8,
    h3_res6
from cells
where h3_res8 is not null
