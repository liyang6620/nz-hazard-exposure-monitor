{% set event_root = var('event_data_root', '') %}

{% if var('adapter_name', 'duckdb') == 'snowflake' %}
    select * from {{ source('curated', 'int_event_shaking_h3') }}
    {% if var('benchmark_event_id', '') %}
    where event_id = '{{ var('benchmark_event_id') }}'
    {% endif %}
{% elif event_root %}
    select * from read_parquet('{{ event_root }}/int_event_shaking_h3.parquet')
    {% if var('benchmark_event_id', '') %}
        where event_id = '{{ var('benchmark_event_id') }}'
    {% endif %}
{% else %}
    select * from {{ ref('event_shaking_h3') }}
    {% if var('benchmark_event_id', '') %}
    where event_id = '{{ var('benchmark_event_id') }}'
    {% endif %}
{% endif %}
