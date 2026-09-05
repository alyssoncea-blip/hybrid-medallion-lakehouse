{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key=['pedido_id', '_dbt_valid_from'],
    on_schema_change='append_new_columns',
    tags=['silver', 'vendas', 'conformed']
) }}

with bronze as (
    select * from {{ ref('stg_vendas__pedidos') }}
    {% if is_incremental() %}
      where data_pedido >= dateadd('day', -3, current_date)
    {% endif %}
),

renamed as (
    select
        md5(pedido_id)                                       as pedido_sk,
        pedido_id,
        md5(cliente_id)                                      as cliente_sk,
        cast(data_pedido as date)                            as data_pedido,
        cast(valor_total as number(18, 2))                   as valor_total,
        upper(trim(status))                                  as status,
        coalesce(vendedor_id, 'UNASSIGNED')                  as vendedor_id,
        coalesce(canal_venda, 'DESCONHECIDO')                as canal_venda,
        observacoes,
        current_timestamp()                                  as _dbt_valid_from,
        cast(null as timestamp_ntz)                          as _dbt_valid_to
    from bronze
)

select * from renamed
