{{ config(
    materialized='view',
    tags=['bronze', 'cliente', 'raw']
) }}

with source as (
    select
        raw:id_cliente::varchar                as cliente_id,
        raw:nome::varchar                      as nome,
        raw:cpf::varchar                       as cpf,
        raw:email::varchar                     as email,
        raw:data_cadastro::timestamp_ntz       as data_cadastro,
        current_timestamp()                    as _ingested_at
    from {{ source('bronze_raw', 'clientes_cadastro') }}
    where raw is not null
)

select * from source
