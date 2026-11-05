{% set event_root = var('event_data_root', '') %}

{% if var('adapter_name', 'duckdb') == 'snowflake' %}
    select *, abs(estimated_mmi - observed_mmi) as absolute_error
    from {{ source('curated', 'mart_mmi_validation') }}
    {% if var('benchmark_event_id', '') %}
    where event_id = '{{ var('benchmark_event_id') }}'
    {% endif %}
{% elif event_root %}
    select
        *,
        abs(estimated_mmi - observed_mmi) as absolute_error
    from read_parquet('{{ event_root }}/mart_mmi_validation.parquet')
{% else %}
    select
        *,
        abs(estimated_mmi - observed_mmi) as absolute_error
    from {{ ref('mmi_validation') }}
{% endif %}
