{{ config(
    materialized='view',
    tags=['bronze', 'cliente', 'raw']
) }}

with source as (
    select
        cast(cliente_id as varchar)   as cliente_id,
        cast(nome as varchar)         as nome,
        cast(cpf as varchar)          as cpf,
        cast(email as varchar)        as email,
        cast(data_cadastro as date)   as data_cadastro,
        {{ ts_now() }}                as _ingested_at
    from {{ bronze_source('clientes_cadastro') }}
)

select * from source
