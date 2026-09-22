# Data Governance

> **Status: ✅ Atual (local, R$0)** for masking-in-dbt + alert manifest; 🔭 for catalog/lineage platforms.

## Subdirectories

| Dir | Purpose | Status |
|---|---|---|
| `data-dictionary/` | Column-level glossary per model | 🔭 Alvo (dbt `persist_docs` covers current models) |
| `glossary/` | Business terms | 🔭 Alvo |
| `policies/` | Access, retention, classification policies | 🔭 Alvo (see `04-data-governance-framework.md`) |

## What is enforced today (✅)

- **CPF masking in place** via `mask_cpf()` compat macro + singular test `assert_cpf_masked`
- **Retention vars** in `src/dbt/dbt_project.yml` (`bronze:1`, `silver:7`, `gold:90` days — canonical)
- **PII tagging** scaffolding in Terraform (`snowflake_tag.pii` — validate-only, no apply)
- **Alert severity** mapped to dbt tests in `observability/alerts/gold_alerts.yml`

## Deferred (🔭 YAGNI until Snowflake apply)

- Snowflake Horizon / Collibra / Atlan catalog integration
- Row-access policies (documented, not applied — see ADR consequences)
- Full DPIA / LGPD operational workflow

Authoritative narrative: [`04-data-governance-framework.md`](../../04-data-governance-framework.md).
