{% snapshot slv_clientes_snapshot %}
{{ config(target_schema='cliente', unique_key='cliente_id', strategy='check', check_cols=['nome','cpf','email'], invalidate_hard_deletes=True) }}
select cliente_id, nome, cpf, email from {{ ref('stg_cliente__cadastro') }}
{% endsnapshot %}
