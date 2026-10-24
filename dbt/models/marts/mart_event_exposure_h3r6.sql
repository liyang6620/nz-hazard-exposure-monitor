select
    event_id,
    h3_res6,
    max(mmi) as mmi,
    any_value(mmi_source) as mmi_source,
    any_value(source_version) as source_version,
    sum(event_building_count) as event_building_count,
    sum(event_footprint_area_m2) as event_footprint_area_m2,
    sum(event_building_count) as event_time_building_count,
    sum(event_footprint_area_m2) as event_time_footprint_area_m2,
    sum(as_if_today_building_count) as as_if_today_building_count,
    sum(as_if_today_footprint_area_m2) as as_if_today_footprint_area_m2,
    sum(current_building_count) as current_building_count,
    sum(current_footprint_area_m2) as current_footprint_area_m2,
    sum(population_2023) as population_2023
from {{ ref('fct_event_exposure_cell') }}
group by event_id, h3_res6
