{% macro ym_format(date_col) %}
  {% if target.type == 'snowflake' %}to_char({{ date_col }}, 'YYYY-MM'){% else %}strftime({{ date_col }}, '%Y-%m'){% endif %}
{% endmacro %}
