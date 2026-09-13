{% macro ts_now() %}
  {% if target.type == 'snowflake' %}current_timestamp(){% else %}now(){% endif %}
{% endmacro %}
