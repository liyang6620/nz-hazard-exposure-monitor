select sa1_code
from {{ ref('int_population_h3') }}
where
    (
        allocation_method = 'unlocated_no_geometry'
        and (h3_res8 is not null or h3_res6 is not null)
    )
    or (
        allocation_method != 'unlocated_no_geometry'
        and (h3_res8 is null or h3_res6 is null)
    )
