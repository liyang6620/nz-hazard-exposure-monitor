{% set reference_root = var('reference_data_root', '') %}

{% if reference_root %}
    select * from read_parquet('{{ reference_root }}/dim_h3_cell.parquet')
{% else %}
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
{% endif %}
