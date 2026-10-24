{% set reference_root = var('reference_data_root', '') %}
{% set stats_reference_root = var('stats_reference_root', reference_root) %}

{% if stats_reference_root %}
    select
        meshblock_code,
        sa1_code,
        sa2_code,
        sa2_name,
        region_code,
        region_name,
        territorial_authority_code,
        territorial_authority_name,
        land_water,
        land_water_name
    from read_parquet(
        '{{ stats_reference_root }}/stg_stats__boundaries/*.parquet'
    )
{% else %}
select
    cast(meshblock_code as varchar) as meshblock_code,
    cast(sa1_code as varchar) as sa1_code,
    cast(sa2_code as varchar) as sa2_code,
    cast(sa2_name as varchar) as sa2_name,
    cast(region_code as varchar) as region_code,
    cast(region_name as varchar) as region_name,
    cast(territorial_authority_code as varchar) as territorial_authority_code,
    cast(territorial_authority_name as varchar) as territorial_authority_name,
    cast(land_water as varchar) as land_water,
    cast(land_water_name as varchar) as land_water_name
from {{ ref('reference_boundaries') }}
{% endif %}
