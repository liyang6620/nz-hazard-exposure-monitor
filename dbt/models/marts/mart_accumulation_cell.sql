select
    h3_res8,
    any_value(h3_res6) as h3_res6,
    count(case when mmi >= 6 then 1 end) as strong_event_count,
    max(current_building_count) as current_building_count,
    count(case when mmi >= 6 then 1 end)
    * max(current_building_count) as accumulation_score
from {{ ref('fct_event_exposure_cell') }}
group by h3_res8
