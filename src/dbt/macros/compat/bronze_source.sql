{% macro bronze_source(table_name) %}
  {% if target.type == 'snowflake' %}{{ source('bronze_raw', table_name) }}{% else %}read_parquet('{{ var('local_bronze_path') }}/{{ table_name }}/*.parquet'){% endif %}
{% endmacro %}
