{% set event_root = var('event_data_root', '') %}

{% if event_root %}
    select * from read_parquet('{{ event_root }}/dim_event.parquet')
{% else %}
    select * from {{ ref('event_catalog') }}
{% endif %}
