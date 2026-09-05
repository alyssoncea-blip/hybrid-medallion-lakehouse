# Project Charter — Hybrid Medallion Lakehouse

**Versão:** 1.0
**Status:** Para aprovação da Steering Committee
**Confidencialidade:** Interno — Distribuição Restrita

---

## 1. Project Identification

| Campo | Valor |
|---|---|
| **Nome do Projeto** | Hybrid Medallion Lakehouse |
| **Código do Projeto** | HYB-MED-2026 |
| **Tipo** | Plataforma de Dados — Arquitetura Híbrida (Lake + Warehouse) |
| **Sponsor** | CDO / VP de Tecnologia — Grupo Autoglass |
| **Project Manager** | a definir — Coordenadoria de Dados & Analytics |
| **Data de Início Estimada** | 02/03/2026 (M0) |
| **Data de Término Estimada** | 28/02/2027 (M12) |
| **Duração Total** | 12 meses |
| **Orçamento Total Estimado** | R$ 4.850.000 (CAPEX + OPEX 12 meses) |
| **Patrocínio Executivo** | Comitê de Transformação Digital |

---

## 2. Business Case

### 2.1 Problema

O Grupo Autoglass opera com dados de vendas, estoque, fiscal, CRM, ERP e múltiplas APIs externas em silos heterogêneos (legados on-premise, bancos transacionais, planilhas e APIs SaaS). A camada analítica atual baseada em Data Warehouse tradicional apresenta três gargalos críticos:

- **Custo de storage elevado:** dados quentes e frios convivem no mesmo warehouse, pagando o mesmo preço por TB/mês.
- **Time-to-insight lento:** ciclos de ingestão levam em média 48–72h, impedindo decisões operacionais em janelas críticas (ex.: ruptura de estoque, giro de peças).
- **Governança fragmentada:** ausência de catálogo unificado, linhagem e controle de acesso consistente, expondo o grupo a riscos regulatórios (LGPD) e a retrabalho de auditoria.

### 2.2 Oportunidade

Adotar o padrão **Medallion Architecture (Bronze → Silver → Gold)** combinando:

- **Object Storage (S3/GCS)** como camada Bronze de baixo custo para dados brutos, imutáveis e versionados.
- **Snowflake** como camada Silver/Gold para transformação, modelagem dimensional e consumo analítico de alta performance.
- **dbt + Snowpark** para transformação versionada, testável e orientada a engenharia de software.
- **Snowpipe + External Stages** para ingestão contínua e near-real-time.
- **Horizon Catalog + Collibra/Atlan/Purview** para governança unificada, linhagem e classificação de dados sensíveis.

### 2.3 Valor Esperado

| Dimensão | Benefício |
|---|---|
| **Redução de Custo** | -45% no custo de storage analítico em 12 meses, via separação Bronze (object storage) e Silver/Gold (Snowflake). |
| **Time-to-Insight** | Redução de ingestão de ~72h para <2h em dados críticos; dashboards near-real-time para vendas e estoque. |
| **Governança & LGPD** | 100% dos datasets catalogados com linhagem, classificação e controle de acesso baseado em papéis (RBAC). |
| **Confiabilidade** | Acordo de nível de serviço (SLA) de disponibilidade analítica de 99,5% e testes de qualidade automatizados em 100% das tabelas Silver/Gold. |
| **Velocidade de Entrega** | Redução de 60% no tempo de onboard de novas fontes de dados via templates reutilizáveis. |

---

## 3. Objectives & Success Metrics

### 3.1 Objetivos SMART

| # | Objetivo | Métrica (KPI) | Baseline | Meta (M9) |
|---|---|---|---|---|
| O1 | Reduzir custo de storage analítico | Custo por TB/mês (BRL) | R$ 480/TB | R$ 265/TB (-45%) |
| O2 | Acelerar ingestão de dados críticos | Latência média Bronze→Silver (h) | 72h | <2h |
| O3 | Garantir governança e LGPD | % datasets catalogados com linhagem | 15% | 100% |
| O4 | Aumentar confiabilidade dos dados | % tabelas Silver/Gold com testes de qualidade automatizados | 10% | 100% |
| O5 | Padronizar o desenvolvimento analítico | % modelos transformados em dbt versionado | 5% | 95% |
| O6 | Reduzir tempo de onboarding de novas fontes | Tempo médio para nova fonte em produção (dias) | 30 dias | 10 dias |
| O7 | Disponibilizar camada Gold para consumo | # dashboards/contratos servidos pela camada Gold | 12 | 60+ |

### 3.2 Critérios de Sucesso Global

O projeto será considerado **bem-sucedido** quando, em produção por 90 dias consecutivos, atingir todas as metas M9 listadas acima, sem violação de compliance LGPD registrada.

---

## 4. Scope

### 4.1 In-Scope

| Domínio | Entregáveis |
|---|---|
| **Camada Bronze** | Raw zone em S3/GCS, versionada, particionada por domínio (vendas, estoque, fiscal, CRM, ERP, APIs externas), com política de retenção e lifecycle. |
| **Camada Silver** | Dados limpos, deduplicados, tipados e enriquecidos no Snowflake, com Surrogate Keys e regras de SCD2. |
| **Camada Gold** | Modelos dimensionais (Kimball) e Data Marts por área de negócio: Comercial, Operações, Financeiro, Fiscal. |
| **Ingestão** | Snowpipe, External Stages, conectores nativos Snowflake, ingestão batch via Airflow/Glue. |
| **Transformação** | dbt Core/Cloud com testes (schema, freshness, custom), documentação e exposures. Snowpark para lógicas avançadas em Python/Java/Scala. |
| **Catálogo & Governança** | Snowflake Horizon Catalog + integração com Collibra/Atlan/Purview. Linhagem ponta-a-ponta, classificação de PII, RBAC/Row-Level Security. |
| **Qualidade de Dados** | Framework de DQ com Great Expectations / dbt tests, alertas e SLA por tabela. |
| **IaC & CI/CD** | Terraform para provisionamento de Snowflake, buckets e IAM. Pipelines em GitHub Actions ou Azure DevOps. |
| **Observabilidade** | Logs, métricas (custo, latência, falhas) e dashboards de operação da plataforma. |

### 4.2 Out-of-Scope

| Domínio | Justificativa |
|---|---|
| **Migração do BI corporativo (Power BI / Qlik / Looker)** | Será tratada em projeto paralelo; o lakehouse provê a camada Gold consumida pelos BIs existentes. |
| **ML Ops e modelos preditivos em produção** | Modelos podem consumir a Gold, mas o ciclo de vida de ML, treinamento e serving fica fora deste charter. |
| **Substituição do ERP/CRM** | Integração via APIs/exports é in-scope; substituição de sistemas transacionais não é. |
| **Data Lakehouse open-source (Databricks, Iceberg, Trino)** | Avaliação não compete com este projeto; Snowflake é a decisão arquitetural aprovada. |
| **Reestruturação organizacional** | Mudanças de papéis, headcount e governança de dados ficam em programa paralelo de Data Governance. |
| **Streaming em tempo real sub-segundo** | O escopo cobre near-real-time (minutos). Latência sub-segundo exige stack Kafka/Flink dedicada. |

---

## 5. Stakeholders

| Papel | Área | Nome / Função | Influência | Interesse |
|---|---|---|---|---|
| **Sponsor Executivo** | Diretoria | CDO / VP de Tecnologia | Alta | Alto |
| **Steering Committee** | Diretoria + TI + Negócios | C-level sponsorado | Alta | Alto |
| **Project Manager** | Dados & Analytics | PM Lead — Híbrido | Alta | Alto |
| **Data Engineer Lead** | Engenharia de Dados | Tech Lead | Alta | Alto |
| **Analytics Engineer (dbt)** | Engenharia de Dados | Squad | Média | Alto |
| **Cloud Architect** | Arquitetura / Cloud | Arquiteto Sênior | Alta | Alto |
| **Data Governance Lead** | Governança & Compliance | DPO + Data Owner | Alta | Alto |
| **Snowflake Admin** | TI / DBA | Admin Snowflake | Média | Alto |
| **Finanças** | FP&A | Controller + Analista | Média | Médio |
| **Negócio — Comercial** | Vendas / Autopeças | Diretor Comercial | Alta | Alto |
| **Negócio — Operações** | Logística / Estoque | Diretor de Operações | Alta | Alto |
| **Negócio — Fiscal** | Contabilidade / Fiscal | Gerente Fiscal | Média | Alto |
| **Segurança da Informação** | Segurança / TI | CISO / Gerente Sec | Alta | Alto |
| **LGPD / Jurídico** | Compliance | Encarregado de Dados | Média | Alto |
| **Fornecedor — Snowflake** | Vendor | Account Executive + SE | Baixa | Alto |
| **Fornecedor — Object Storage** | Vendor | AWS/GCS Account Team | Baixa | Médio |
| **Usuários Finais — Analytics** | BI / Ciência de Dados | analistas, cientistas | Baixa | Alto |

**Legenda:** Influência = poder de decisão. Interesse = impacto no dia-a-dia.

---

## 6. High-Level Milestones

| Marco | Mês | Data Estimada | Entregável Principal | Status |
|---|---|---|---|---|
| **M0 — Kickoff & Funding** | M0 | 02/03/2026 | Charter aprovado, equipe contratada, ambientes provisionados. | Planejado |
| **M1 — Foundation Landing** | M2 | 01/05/2026 | Conta Snowflake production-grade, buckets S3/GCS, Terraform baseline, pipelines CI/CD ativos, Horizon Catalog habilitado. | Planejado |
| **M2 — Bronze Layer em Produção** | M4 | 01/07/2026 | Camada Bronze ingerindo 6 fontes: Vendas, Estoque, Fiscal, CRM, ERP, 2 APIs externas. Retenção e versionamento definidos. | Planejado |
| **M3 — Silver Layer & Qualidade** | M6 | 01/09/2026 | Camada Silver com regras de DQ, SCD2, deduplicação e 100% das tabelas com testes automatizados. | Planejado |
| **M4 — Gold Layer & Consumidores** | M8 | 01/11/2026 | Data Marts dimensionais publicados, 60+ dashboards migrados/novos consumindo a Gold, latência <2h. | Planejado |
| **M5 — Governança & LGPD** | M10 | 02/01/2027 | 100% dos datasets catalogados com linhagem, classificação PII, RBAC e Row-Level Security auditáveis. | Planejado |
| **M6 — Estabilização & Handover** | M12 | 28/02/2027 | Operação assistida por 30 dias, retrospectiva, handover para sustentação, baseline de FinOps validado. | Planejado |

---

## 7. Budget Estimate

| Categoria | Tipo | Descrição | Estimativa (R$) | % Total |
|---|---|---|---|---|
| **Cloud — Object Storage** | OPEX | S3/GCS, classes Standard/IA/Glacier para Bronze, tráfego de saída. | 360.000 | 7,4% |
| **Cloud — Snowflake Compute & Storage** | OPEX | Créditos de warehouse (XS–L), storage Silver/Gold, Snowpipe. | 1.450.000 | 29,9% |
| **Licenças Snowflake** | OPEX | Enterprise edition, recursos avançados (Horizon, Snowpark, Secure Data Sharing). | 540.000 | 11,1% |
| **Ferramentas de Engenharia** | OPEX | dbt Cloud/Enterprise, Airflow, Great Expectations, ferramentas de observabilidade (Monte Carlo / Elementary). | 280.000 | 5,8% |
| **Catálogo & Governança** | OPEX | Collibra/Atlan/Purview — licenças anuais. | 320.000 | 6,6% |
| **Headcount — Equipe dedicada** | CAPEX/OPEX | 1 PM, 1 Tech Lead, 3 DE, 2 AE, 1 DG, 1 Snowflake Admin (12 meses). | 1.645.000 | 33,9% |
| **Treinamento & Certificação** | CAPEX | SnowPro, dbt Analytics Engineering, Terraform, LGPD aplicada a dados. | 90.000 | 1,9% |
| **Contingência** | Reserva | 3% sobre o total para riscos materializados. | 165.000 | 3,4% |
| **TOTAL** | | | **4.850.000** | **100,0%** |

**Observações:**

- Valores referenciais, sem impostos diretos.
- Headcount considera mix de contratação CLT + 1–2 consultorias especializadas pontuais.
- Custo de cloud assume FinOps ativo a partir de M3.

---

## 8. Risks & Mitigations

| # | Risco | Categoria | Probabilidade | Impacto | Estratégia | Mitigação |
|---|---|---|---|---|---|---|
| **R1** | Custos de Snowflake acima do orçamento (consumo descontrolado, warehouses ociosos) | Técnico / Financeiro | Alta | Alto | Mitigar | Implementar FinOps desde M1: auto-suspend, resource monitors, tagging por domínio, alertas diários; orçamento revisado quinzenalmente. |
| **R2** | Resistência organizacional à adoção de dbt e Snowpark (skill gap e cultura) | Organizacional | Alta | Alto | Mitigar | Programa de treinamento M0–M2, pair-programming, "dbt office hours" semanais, métricas de adoção por squad. |
| **R3** | Atraso na contratação de Snowflake ou bloqueio contratual (LGPD, residência de dados) | Fornecedor / Compliance | Média | Alto | Mitigar | Due diligence jurídica em M0, fallback para GCP se necessário, cláusulas de SLA e exit plan no contrato. |
| **R4** | Qualidade dos dados das fontesBronze baixa (schemas instáveis, PII não mapeada) | Técnico / Dados | Alta | Alto | Mitigar | Discovery sprint em M1–M2, Data Contracts com áreas de origem, framework de DQ desde Bronze, equipe de DG dedicada. |
| **R5** | Risco de LGPD: exposição de dados pessoais em ambientes não-governados | Compliance / Segurança | Média | Crítico | Mitigar | DPO no squad desde M0, mascaramento e tokenização, Row-Level Security obrigatória, auditoria trimestral. Plano de resposta a incidentes definido. |

---

## 9. Assumptions & Constraints

### 9.1 Assumptions

- **A1.** A direção executiva mantém o patrocínio e o orçamento aprovado até M9.
- **A2.** Equipe núcleo (PM, Tech Lead, 1 DE, 1 DG) disponível em M0; demais contratações onboard em até 30 dias.
- **A3.** As áreas de origem (Comercial, Operações, Fiscal, CRM, ERP) designam Data Owners e disponibilizam acesso às APIs/banco em até 15 dias após solicitação.
- **A4.** Snowflake está aprovado como vendor padrão para workloads analíticos no grupo.
- **A5.** A região de cloud será Sudamérica (São Paulo) para Snowflake e AWS sa-east-1 / GCP southamerica-east1 para object storage, em conformidade com LGPD.
- **A6.** O contrato com o provedor de object storage (AWS ou GCP) já existe e suporta expansão de capacidade.
- **A7.** A área de Segurança da Informação proverá IAM, chaves e rede em até 10 dias úteis para cada requisição formal.
- **A8.** O BI corporativo (Power BI/Qlik/Looker) será consumido como camada de apresentação — sem mudança no M9.

### 9.2 Constraints

- **C1.** Orçamento total aprovado de **R$ 4.850.000**, com tolerância de **±10%** sem nova aprovação.
- **C2.** Dados pessoais devem permanecer em região brasileira; nenhum dado de vendas/estoque pode cruzar fronteira internacional sem aprovação do DPO.
- **C3.** Prazo máximo de entrega: **28/11/2026**. Atrasos superiores a 60 dias exigem replanejamento formal e nova aprovação da Steering Committee.
- **C4.** A plataforma deve cumprir o princípio de **least privilege** em 100% dos acessos produtivos.
- **C5.** Toda tabela Gold deve ter **Data Owner formalmente designado** antes de ir para produção.
- **C6.** Mudanças em produção passam por **pull request + aprovação de 2 reviewers + pipeline CI/CD**; nenhum deploy manual é permitido.

---

## 10. Approval

| Papel | Nome | Assinatura | Data |
|---|---|---|---|
| **Sponsor Executivo (CDO/VP TI)** | _________________________ | _________________________ | ****/****/2026 |
| **Diretor Comercial (Negócio)** | _________________________ | _________________________ | ****/****/2026 |
| **Diretor de Operações (Negócio)** | _________________________ | _________________________ | ****/****/2026 |
| **CISO / Segurança da Informação** | _________________________ | _________________________ | ****/****/2026 |
| **DPO / Encarregado de Dados (LGPD)** | _________________________ | _________________________ | ****/****/2026 |
| **CFO / Controller (Finanças)** | _________________________ | _________________________ | ****/****/2026 |
| **Project Manager** | _________________________ | _________________________ | ****/****/2026 |

---

**Fim do documento — HYB-MED-2026 — v1.0**
