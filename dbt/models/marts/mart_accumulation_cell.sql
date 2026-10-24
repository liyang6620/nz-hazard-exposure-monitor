select
    h3_res8,
    any_value(h3_res6) as h3_res6,
    count(*) filter (where mmi >= 6) as strong_event_count,
    max(current_building_count) as current_building_count,
    count(*) filter (where mmi >= 6)
    * max(current_building_count) as accumulation_score
from {{ ref('fct_event_exposure_cell') }}
group by h3_res8
