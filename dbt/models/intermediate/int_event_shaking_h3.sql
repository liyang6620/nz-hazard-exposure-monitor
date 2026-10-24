{% set event_root = var('event_data_root', '') %}

{% if event_root %}
    select * from read_parquet('{{ event_root }}/int_event_shaking_h3.parquet')
{% else %}
    select * from {{ ref('event_shaking_h3') }}
{% endif %}
