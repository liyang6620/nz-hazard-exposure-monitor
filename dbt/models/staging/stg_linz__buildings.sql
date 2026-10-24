{% set reference_root = var('reference_data_root', '') %}

{% if reference_root %}
    select
        building_outline_id,
        building_id,
        capture_method,
        capture_source_group,
        capture_source_id,
        capture_source_name,
        capture_source_from,
        capture_source_to,
        lifecycle,
        begin_lifespan,
        end_lifespan,
        footprint_area_m2,
        longitude,
        latitude,
        meshblock_code,
        sa1_code,
        sa2_code,
        sa2_name,
        region_code,
        region_name,
        territorial_authority_code,
        territorial_authority_name,
        h3_res8,
        h3_res6
    from
        read_parquet('{{ reference_root }}/int_buildings_h3/region=*/*.parquet')
{% else %}
select
    cast(building_outline_id as bigint) as building_outline_id,
    cast(building_id as bigint) as building_id,
        cast(null as varchar) as capture_method,
        cast(null as varchar) as capture_source_group,
        cast(null as integer) as capture_source_id,
        cast(null as varchar) as capture_source_name,
        cast(null as date) as capture_source_from,
        cast(null as date) as capture_source_to,
    cast(lifecycle as varchar) as lifecycle,
    cast(begin_lifespan as date) as begin_lifespan,
    cast(end_lifespan as date) as end_lifespan,
    cast(footprint_area_m2 as double) as footprint_area_m2,
    cast(longitude as double) as longitude,
    cast(latitude as double) as latitude,
    cast(meshblock_code as varchar) as meshblock_code,
    cast(sa1_code as varchar) as sa1_code,
    cast(sa2_code as varchar) as sa2_code,
    cast(sa2_name as varchar) as sa2_name,
    cast(region_code as varchar) as region_code,
    cast(region_name as varchar) as region_name,
    cast(territorial_authority_code as varchar) as territorial_authority_code,
    cast(territorial_authority_name as varchar) as territorial_authority_name,
    cast(h3_res8 as ubigint) as h3_res8,
    cast(h3_res6 as ubigint) as h3_res6
from {{ ref('reference_buildings') }}
{% endif %}
