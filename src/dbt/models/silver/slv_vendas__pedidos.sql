{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key='pedido_id',
    on_schema_change='append_new_columns',
    tags=['silver', 'vendas', 'conformed']
) }}

with bronze as (
    select * from {{ ref('stg_vendas__pedidos') }}
    {% if is_incremental() %}
      where data_pedido >= current_date - 3
    {% endif %}
),

renamed as (
    select
        md5(pedido_id)                                       as pedido_sk,
        pedido_id,
        md5(cliente_id)                                      as cliente_sk,
        cast(data_pedido as date)                            as data_pedido,
        cast(valor_total as decimal(18, 2))                  as valor_total,
        upper(trim(status))                                  as status,
        coalesce(vendedor_id, 'UNASSIGNED')                  as vendedor_id,
        coalesce(canal_venda, 'DESCONHECIDO')                as canal_venda,
        {% if target.type == 'snowflake' %}current_timestamp(){% else %}now(){% endif %} as _dbt_valid_from,
        cast(null as timestamp)                              as _dbt_valid_to
    from bronze
),

deduplicated as (
    select *,
        row_number() over (partition by pedido_id order by data_pedido desc) as rn
    from renamed
)

select
    pedido_sk,
    pedido_id,
    cliente_sk,
    data_pedido,
    valor_total,
    status,
    vendedor_id,
    canal_venda,
    _dbt_valid_from,
    _dbt_valid_to
from deduplicated
where rn = 1
