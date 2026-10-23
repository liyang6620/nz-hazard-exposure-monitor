{% macro h3_point_to_cell(latitude, longitude, resolution) -%}
  {{ return(adapter.dispatch('h3_point_to_cell', 'nz_hazard_exposure_monitor')(latitude, longitude, resolution)) }}
{%- endmacro %}

{% macro default__h3_point_to_cell(latitude, longitude, resolution) -%}
  h3_latlng_to_cell({{ latitude }}, {{ longitude }}, {{ resolution }})
{%- endmacro %}
