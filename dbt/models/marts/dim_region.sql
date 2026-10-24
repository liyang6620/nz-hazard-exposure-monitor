select distinct
    region_code,
    region_name,
    territorial_authority_code,
    territorial_authority_name,
    sa2_code,
    sa2_name
from {{ ref('stg_stats__boundaries') }}
where land_water = '12'
