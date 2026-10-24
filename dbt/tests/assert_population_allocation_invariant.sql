{% set reference_root = var('reference_data_root', '') %}

{% if reference_root %}
select 'national_total' as failed_scope
from {{ ref('int_population_h3') }}
having abs(sum(allocated_population) - 4994034) >= 0.000001
{% else %}
with source as (
    select
        sa1_code,
        population
    from {{ ref('stg_stats__population') }}
    where population >= 0
),

allocated as (
    select
        sa1_code,
        sum(allocated_population) as allocated_population
    from {{ ref('int_population_h3') }}
    group by sa1_code
)

select source.sa1_code
from source
left join allocated on source.sa1_code = allocated.sa1_code
where
    abs(
        source.population - coalesce(allocated.allocated_population, 0)
    ) >= 0.000001
{% endif %}
