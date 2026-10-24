select building_outline_id
from {{ ref('int_buildings_h3') }}
where
    valid_from_year != year(begin_lifespan)
    or valid_to_year != year(end_lifespan)
    or (end_lifespan is null and valid_to_year is not null)
