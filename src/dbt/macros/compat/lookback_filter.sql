{% macro lookback_filter(date_col, days) %}
  {% if target.type == 'snowflake' %}{{ date_col }} >= dateadd('day', -{{ days }}, current_date){% else %}{{ date_col }} >= current_date - {{ days }}{% endif %}
{% endmacro %}
