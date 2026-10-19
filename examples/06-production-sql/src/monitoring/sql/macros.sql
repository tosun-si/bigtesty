{# Shared macros of the SQL of the team. #}

{% macro partition_filter(column, day) -%}
DATE({{ column }}) = '{{ day }}'
{%- endmacro %}
