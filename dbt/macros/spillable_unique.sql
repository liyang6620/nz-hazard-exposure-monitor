{% test spillable_unique(model, column_name) %}
with ordered_values as (
    select
        {{ column_name }} as current_value,
        lag({{ column_name }}) over (order by {{ column_name }}) as previous_value
    from {{ model }}
    where {{ column_name }} is not null
)

select current_value
from ordered_values
where current_value = previous_value
{% endtest %}
