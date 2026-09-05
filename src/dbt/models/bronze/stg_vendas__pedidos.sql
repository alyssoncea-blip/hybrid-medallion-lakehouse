{{ config(
    materialized='view',
    tags=['bronze', 'vendas', 'raw']
) }}

{#
  Local target (DuckDB):  lê Parquet direto do disco via read_parquet()
  Snowflake target:       lê external table sobre S3 (criada pelo Terraform)

  Variável local_bronze_path é configurada em dbt_project.yml.
#}

{% set bronze_path = var('local_bronze_path') %}
{% set ts_func = 'current_timestamp' if target.type == 'snowflake' else 'now' %}

with source as (
    select
        cast(pedido_id as varchar)          as pedido_id,
        cast(cliente_id as varchar)         as cliente_id,
        cast(data_pedido as date)           as data_pedido,
        cast(valor_total as decimal(18, 2)) as valor_total,
        upper(trim(status))                 as status,
        cast(vendedor_id as varchar)        as vendedor_id,
        cast(canal_venda as varchar)        as canal_venda,
        {{ ts_func }}()                     as _ingested_at
    from read_parquet('{{ bronze_path }}/pedidos_vendas/*.parquet')
)

select * from source
