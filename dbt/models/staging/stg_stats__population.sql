{% set reference_root = var('reference_data_root', '') %}
{% set stats_reference_root = var('stats_reference_root', reference_root) %}

{% if stats_reference_root %}
    select
        sa1_code,
        land_water,
        land_water_name,
        population,
        population_status,
        cast(null as ubigint) as fallback_h3_res8,
        cast(null as ubigint) as fallback_h3_res6
    from read_parquet(
        '{{ stats_reference_root }}/stg_stats__population/*.parquet'
    )
{% else %}
select
    cast(sa1_code as varchar) as sa1_code,
    cast(land_water as varchar) as land_water,
    cast(land_water_name as varchar) as land_water_name,
    cast(population as integer) as population,
    cast(population_status as varchar) as population_status,
    cast(fallback_h3_res8 as ubigint) as fallback_h3_res8,
    cast(fallback_h3_res6 as ubigint) as fallback_h3_res6
from {{ ref('reference_population') }}
{% endif %}
