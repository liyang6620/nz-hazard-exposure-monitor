{% set event_root = var('event_data_root', '') %}

{% if event_root %}
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
