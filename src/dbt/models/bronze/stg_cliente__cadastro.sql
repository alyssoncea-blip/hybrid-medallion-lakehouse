{{ config(
    materialized='view',
    tags=['bronze', 'cliente', 'raw']
) }}

{% set bronze_path = var('local_bronze_path') %}
{% set ts_func = 'current_timestamp' if target.type == 'snowflake' else 'now' %}

with source as (
    select
        cast(cliente_id as varchar)   as cliente_id,
        cast(nome as varchar)         as nome,
        cast(cpf as varchar)          as cpf,
        cast(email as varchar)        as email,
        cast(data_cadastro as date)   as data_cadastro,
        {{ ts_func }}()               as _ingested_at
    from read_parquet('{{ bronze_path }}/clientes_cadastro/*.parquet')
)

select * from source
