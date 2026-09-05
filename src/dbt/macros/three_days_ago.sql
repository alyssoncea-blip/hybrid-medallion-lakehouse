{% macro three_days_ago() %}
  {% if target.type == 'snowflake' %}
    dateadd('day', -3, current_date)
  {% else %}
    current_date - 3
  {% endif %}
{% endmacro %}
