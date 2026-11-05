select
    evt.event_name,
    evt.event_id,
    evt.origin_time,
    evt.magnitude,
    evt.depth_km,
    evt.latitude,
    evt.longitude,
    evt.mmi_source,
    evt.shaking_version,
    evt.valid_buildings,
    evt.as_if_today_buildings,
    evt.event_time_status,
    evt.validation_station_count,
    evt.validation_mae,
    max(exposure.mmi) as max_mmi,
    coalesce(
        sum(
            case
                when exposure.mmi >= 6
                    then exposure.as_if_today_building_count
                else 0
            end
        ),
        0
    ) as buildings_mmi_ge_6,
    coalesce(
        sum(
            case
                when exposure.mmi >= 6
                    then exposure.event_building_count
                else 0
            end
        ), 0
    ) as event_time_buildings_mmi_ge_6,
    coalesce(
        sum(
            case
                when exposure.mmi >= 6
                    then exposure.as_if_today_footprint_area_m2
                else 0
            end
        ),
        0
    ) as footprint_m2_mmi_ge_6,
    coalesce(
        sum(
            case
                when exposure.mmi >= 6
                    then exposure.population_2023
                else 0
            end
        ), 0
    ) as population_mmi_ge_6
from {{ ref('dim_event') }} as evt
left join {{ ref('fct_event_exposure_cell') }} as exposure
    on evt.event_id = exposure.event_id
group by
    evt.event_name,
    evt.event_id,
    evt.origin_time,
    evt.magnitude,
    evt.depth_km,
    evt.latitude,
    evt.longitude,
    evt.mmi_source,
    evt.shaking_version,
    evt.valid_buildings,
    evt.as_if_today_buildings,
    evt.event_time_status,
    evt.validation_station_count,
    evt.validation_mae
