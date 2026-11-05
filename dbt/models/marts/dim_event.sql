{% set event_root = var('event_data_root', '') %}

{% if var('adapter_name', 'duckdb') == 'snowflake' %}
    select * from {{ source('curated', 'dim_event') }}
    {% if var('benchmark_event_id', '') %}
    where event_id = '{{ var('benchmark_event_id') }}'
    {% endif %}
{% elif event_root %}
    select * from read_parquet('{{ event_root }}/dim_event.parquet')
{% else %}
    select * from {{ ref('event_catalog') }}
{% endif %}
