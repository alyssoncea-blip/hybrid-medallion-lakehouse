{#--
mask_cpf(col_name): LGPD masking for the CPF column (compat macro).

Role concept: raw CPF is restricted to a privileged role (e.g. a
Snowflake role holding PII access). dbt never decides who the caller is;
it only shapes the value per target:
  - DuckDB (local): mask in place unless var('unmask_pii', false) is true.
    Local runs default to masked so fixtures stay LGPD-safe by default.
  - Snowflake: return the column untouched. Real enforcement is deferred to
    a Snowflake Dynamic Data Masking policy owned by Terraform (out of dbt).

Usage: {{ mask_cpf('cpf') }} as cpf  (mask IN PLACE, same column name, so
no downstream ref can ever read the raw value; cliente_id stays the join key).
--#}
{% macro mask_cpf(col_name) %}
  {% if target.type == 'snowflake' %}
    {# Snowflake: defer to masking policy (Terraform); dbt passes the column through. #}
    {{ col_name }}
  {% elif var('unmask_pii', false) %}
    cast({{ col_name }} as varchar)
  {% else %}
    case when {{ col_name }} is null then null else '***.***.***-' || right(cast({{ col_name }} as varchar), 2) end
  {% endif %}
{% endmacro %}
