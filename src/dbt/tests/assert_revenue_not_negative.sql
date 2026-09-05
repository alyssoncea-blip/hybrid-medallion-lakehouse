-- Generic singular test: revenue must be non-negative.
-- Negative revenue is a data quality issue (more cancellations than sales in a month).
-- Severity is 'warn' because in early development with synthetic data, the distribution
-- may produce negative values for some (canal, cliente, month) combinations.
-- In production, change to 'error' to block promotion.
{{ config(severity='warn') }}

select
    ano_mes,
    canal_venda,
    cliente_sk,
    receita_liquida
from {{ ref('gld_vendas__receita_mensal') }}
where receita_liquida < 0
