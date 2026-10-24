select
    *,
    year(begin_lifespan) as valid_from_year,
    year(end_lifespan) as valid_to_year
from {{ ref('stg_linz__buildings') }}
