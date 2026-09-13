{% macro ts_now() %}
  {% if target.type == 'snowflake' %}cast(current_timestamp() as timestamp){% else %}cast(now() as timestamp){% endif %}
{% endmacro %}
