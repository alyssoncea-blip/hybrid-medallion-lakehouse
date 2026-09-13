{#--
gold_watermark(grain_col='ano_mes', months=3, relation=none): incremental
watermark for Gold monthly models (compat macro).

Returns a 'YYYY-MM' string: max(grain_col) in the Gold relation minus N
whole months, computed as date arithmetic over
cast(<grain> || '-01' as date) — never as an inline `current_date - N`
window, so the validator ban on inline date windows in models/ holds.

  - DuckDB: strftime(<first-of-max-month> - interval 'N months', '%Y-%m').
  - Snowflake: to_char(dateadd('month', -N, <first-of-max-month>), 'YYYY-MM').

Typical use (inside is_incremental()): recompute the last N whole months so
in-window late-arriving Silver rows are absorbed by the merge.
LIMIT (documented): Silver rows older than the watermark window are skipped
on incremental runs; a --full-refresh is required to pick them up.

`relation` defaults to `this` (the calling model). Singular tests have no
`this`, so they pass relation=ref('...') explicitly.
--#}
{% macro gold_watermark(grain_col='ano_mes', months=3, relation=none) %}
  {% if relation is none %}
    {% set watermark_rel = this %}
  {% else %}
    {% set watermark_rel = relation %}
  {% endif %}
  {% if target.type == 'snowflake' %}
    to_char(dateadd('month', -{{ months }}, cast((select max({{ grain_col }}) from {{ watermark_rel }}) || '-01' as date)), 'YYYY-MM')
  {% else %}
    strftime(cast((select max({{ grain_col }}) from {{ watermark_rel }}) || '-01' as date) - interval '{{ months }} months', '%Y-%m')
  {% endif %}
{% endmacro %}
