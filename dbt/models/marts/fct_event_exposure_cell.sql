{% set event_root = var('event_data_root', '') %}

{% if event_root %}
    select *
    from read_parquet(
        '{{ event_root }}/fct_event_exposure_cell.parquet'
    )
{% else %}
    select * from {{ ref('event_exposure_cell') }}
{% endif %}
