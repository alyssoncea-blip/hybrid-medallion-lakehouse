-- Singular test (severity error): CPF must be masked in place in Bronze.
-- Any non-null value that is not of the form '***.***.***-NN', or that still
-- looks like a raw formatted CPF (NNN.NNN.NNN-NN), is a FAIL row.
-- NOTE: spec draft used `cpf regexp '...'` infix, which does not compile on
-- DuckDB; regexp_matches() below is semantically identical and DuckDB-native.
select cpf
from {{ ref('stg_cliente__cadastro') }}
where cpf is not null
  and (
    cpf not like '***.***.***-%'
    or regexp_matches(cpf, '^[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}$')
  )
