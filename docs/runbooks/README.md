# Operational Runbooks

> **Status: 🔭 Alvo** — no runbooks are operational yet (Phase 5 / handover deliverable).

## Planned runbooks (from roadmap D5.3–D5.5)

- Incident response (dbt build failure, stale Bronze, failed freshness gate)
- Capacity / cost review (Snowflake resource monitors — 🔭, needs apply)
- Security incident (secret leak, unauthorized access)
- Disaster recovery drill (RPO ≤ 1h, RTO ≤ 4h — 🔭)

## Interim guidance (✅ local)

| Situation | Action |
|---|---|
| CI `dbt-build-local` fails | Download artifact `lakehouse-health`; failing tests listed with alert names |
| Bronze fixtures stale | `python scripts/generate_bronze.py --rows-pedidos 2000 --rows-customeres 500` |
| Local build green but WARN on revenue | Expected with synthetic data — `assert_revenue_not_negative` is warn-by-design |

Contribute new runbooks here as PRs (CODEOWNERS routes `docs/` for review).
