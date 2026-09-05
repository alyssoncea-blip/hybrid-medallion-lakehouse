{{ config(
    materialized='view',
    tags=['bronze', 'vendas', 'raw']
) }}

with source as (
    select
        raw:id_pedido::varchar                as pedido_id,
        raw:id_cliente::varchar               as cliente_id,
        raw:data_pedido::timestamp_ntz        as data_pedido,
        raw:valor_total::number(18, 2)        as valor_total,
        raw:status::varchar                   as status,
        raw:id_vendedor::varchar              as vendedor_id,
        raw:canal_venda::varchar              as canal_venda,
        raw:observacoes::varchar              as observacoes,
        current_timestamp()                   as _ingested_at,
        metadata_file_name                    as _source_file
    from {{ source('bronze_raw', 'pedidos_vendas') }}
)

select * from source
