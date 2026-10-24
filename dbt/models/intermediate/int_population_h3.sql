{% set reference_root = var('reference_data_root', '') %}

{% if reference_root %}
    select *
    from read_parquet('{{ reference_root }}/int_population_h3.parquet')
{% else %}
with current_weights as (
    select
        sa1_code,
        h3_res8,
        h3_res6,
        sum(footprint_area_m2) as footprint_area_m2
    from {{ ref('int_buildings_h3') }}
    where valid_to_year is null
    group by sa1_code, h3_res8, h3_res6
),
weighted as (
    select
        population.sa1_code,
        weights.h3_res8,
        weights.h3_res6,
        population.population,
        weights.footprint_area_m2,
        weights.footprint_area_m2
        / sum(weights.footprint_area_m2) over (partition by population.sa1_code)
        * population.population as unadjusted_population,
        row_number() over (
            partition by population.sa1_code order by weights.h3_res8 desc
        ) as correction_row
    from {{ ref('stg_stats__population') }} population
    inner join current_weights weights using (sa1_code)
    where population.population >= 0
),
adjusted as (
    select
        sa1_code,
        h3_res8,
        h3_res6,
        footprint_area_m2,
        case
            when correction_row = 1 then
                unadjusted_population
                + population
                - sum(unadjusted_population) over (partition by sa1_code)
            else unadjusted_population
        end as allocated_population,
        'building_area' as allocation_method
    from weighted
),
no_buildings as (
    select
        population.sa1_code,
        population.fallback_h3_res8 as h3_res8,
        population.fallback_h3_res6 as h3_res6,
        cast(0 as double) as footprint_area_m2,
        cast(population.population as double) as allocated_population,
        'sa1_interior_point' as allocation_method
    from {{ ref('stg_stats__population') }} population
    left join current_weights using (sa1_code)
    where population.population >= 0
        and current_weights.sa1_code is null
)
select * from adjusted
union all
select * from no_buildings
{% endif %}
