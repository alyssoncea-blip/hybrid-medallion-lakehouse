# Data Governance Framework

## Projeto: Hybrid Medallion Lakehouse

> **Status:** v1.0 — Aprovação pendente pelo Comitê de Dados
> **Owner:** Chief Data Officer (CDO)
> **Vigência:** Anual (revisão a cada 12 meses ou em mudanças regulatórias)
> **Classificação do documento:** Interno

---

## 1. Framework Overview

### 1.1 Propósito

Estabelecer o modelo de governança de dados para o **Hybrid Medallion Lakehouse**, garantindo que dados provenientes de fontes Oracle, SAP e APIs externas, processados via camadas **Bronze → Silver → Gold** em **Snowflake** com armazenamento híbrido em **S3/GCS**, sejam tratados como **ativo estratégico** com qualidade, segurança, linhagem e conformidade (LGPD, SOX) mensuráveis.

### 1.2 Princípios Norteadores

| # | Princípio | Descrição |
|---|-----------|-----------|
| 1 | **Dados como ativo** | Todo dataset possui owner, valor de negócio e custo documentados. |
| 2 | **Federated accountability** | Negócio é dono do dado; TI/engineer é custodião da plataforma. |
| 3 | **Shift-left quality** | Qualidade é tratada na ingestão (Bronze), não apenas no consumo. |
| 4 | **Catalogação obrigatória** | Nenhum dataset chega à Gold sem estar catalogado e classificado. |
| 5 | **Privacy by design** | Controles LGPD embarcados em pipelines e políticas de acesso. |
| 6 | **Linhagem fim-a-fim** | Da linha do Oracle/SAP até o dashboard/ML é rastreável. |
| 7 | **Automação primeiro** | Regras de qualidade, classificação e lineage são código (IaC + tests). |
| 8 | **Medir para evoluir** | KPIs de maturidade publicados mensalmente ao Comitê. |

### 1.3 Escopo

**In-scope:**

- Dados no Snowflake (todas as camadas e warehouses)
- Objetos em S3 e GCS consumidos pelo lakehouse
- Pipelines de ingestão (Oracle, SAP, APIs REST, eventos)
- Modelos semânticos Gold (BI, ML, reverse-ETL)
- Metadados em catálogo (Collibra/Atlan) e Horizon Catalog

**Out-of-scope:**

- Planilhas departamentais não integradas ao lakehouse
- Dados pessoais em sistemas legados sem interface com Snowflake
- Dados de fornecedores/clientes sob contrato próprio (avaliação caso a caso)

---

## 2. Governance Operating Model (RACI)

### 2.1 Estrutura Organizacional

```
┌─────────────────────────────────────────┐
│       DATA STEERING COMMITTEE           │  ← Estratégico (mensal)
│  CDO • CFO • CTO • Head of Risk • DPO   │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│       DATA GOVERNANCE COUNCIL           │  ← Tático (semanal)
│  Data Owners • Steward Lead • Eng Lead  │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│      DATA DOMAIN TEAMS (x N)            │  ← Operacional (daily)
│  Owner • Steward • Custodian • Eng     │
└─────────────────────────────────────────┘
```

### 2.2 Matriz RACI Consolidada

| Atividade | Steering Committee | Data Owner | Data Steward | Data Custodian | Engenheiro de Dados | Analista/Consumer |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|
| Definir estratégia de governança | **A** | C | C | I | I | I |
| Aprovar políticas mestres | **A/R** | C | C | I | I | I |
| Classificar dataset (sensibilidade) | I | **A/R** | R | C | C | I |
| Definir SLA de qualidade por domínio | I | **A** | **R** | C | C | I |
| Implementar testes de qualidade | I | C | C | **A/R** | I | I |
| Resolver incidente de qualidade | I | A | **R** | R | R | I |
| Aprovar acesso a dados restritos | I | **A/R** | R | I | C | I |
| Revisar logs de acesso (LGPD) | I | C | **R** | C | I | I |
| Catalogar novo dataset | I | C | **A/R** | C | R | C |
| Publicar métrica de maturidade | **A** | C | **R** | C | R | I |
| Responder solicitação titular LGPD | I | A | R | I | I | I |

**R = Responsible | A = Accountable | C = Consulted | I = Informed**

---

## 3. Roles & Responsibilities

### 3.1 Data Steering Committee

- **Composição:** CDO (chair), CFO, CTO, Head of Risk/Compliance, DPO, 1 Head de domínio.
- **Cadência:** Mensal.
- **Responsabilidades:**
  - Aprovar e revisar políticas mestres anualmente.
  - Alinhar governança com estratégia corporativa.
  - Aprovar investimentos em catálogo, qualidade e privacidade.
  - Acompanhar KPIs de maturidade e risco regulatório.

### 3.2 Data Owner (1 por domínio de negócio)

- **Quem:** Diretor ou coordenador da área de negócio (ex.: CFO para Financeiro).
- **Mandato:** Anual, formalizado no Confluence/SharePoint.
- **Responsabilidades no lakehouse:**
  - Definir regras de negócio e criticidade dos datasets.
  - Classificar dados (público/interno/confidencial/restrito).
  - Aprovar acessos a dados restritos e confidenciais.
  - Nomear e supervisionar Data Stewards.
  - Assumir accountability em auditoria (LGPD/SOX).

### 3.3 Data Steward (1 a 2 por domínio)

- **Quem:** Analista sênior ou coordenador técnico da área.
- **Reporta:** Funcional ao Data Owner; tático ao Steward Lead.
- **Responsabilidades:**
  - Manter o glossário de negócio do domínio.
  - Documentar linhagem de dados em Catálogo (Collibra/Atlan).
  - Validar regras de qualidade e investigar exceções.
  - Conduzir triage de tickets Jira no escopo do domínio.
  - Ser ponto focal LGPD para a área.

### 3.4 Data Custodian (TI/Engenharia)

- **Quem:** Equipe de Engenharia de Dados / Plataforma.
- **Responsabilidades:**
  - Implementar RBAC/ABAC no Snowflake (roles, row access policies).
  - Configurar classification automática (Horizon Catalog).
  - Operar pipelines de qualidade (dbt, Great Expectations/DQX).
  - Garantir imutabilidade e auditoria em S3/GCS.
  - Aplicar políticas de retenção e descarte.

### 3.5 Engenheiro de Dados

- **Responsabilidades:**
  - Desenvolver pipelines Bronze→Silver→Gold seguindo padrões de catálogo.
  - Instrumentar testes de qualidade em código (CI/CD).
  - Documentar linhagem técnica e tags no commit.
  - Reportar incidentes ao Custodian + Steward.

### 3.6 Analista / Consumer

- **Responsabilidades:**
  - Consumir apenas dados Gold catalogados.
  - Reportar anomalias ou dúvidas ao Steward via Jira.
  - Não compartilhar credenciais ou exportar dados restritos sem aprovação.

---

## 4. Policies (Políticas Mestres)

### 4.1 Política de Classificação de Dados

| Classe | Definição | Exemplos no Lakehouse | Controles mínimos |
|--------|-----------|------------------------|-------------------|
| **Público** | Divulgável sem restrição. | Catálogo de produtos, preços públicos. | Sem criptografia adicional. |
| **Interno** | Apenas colaboradores. | Estoques agregados, dashboards operacionais. | Acesso por grupo AD/SSO. |
| **Confidencial** | Acesso por necessidade. | Receita por unidade, salários, dados de cliente (nome+email). | RBAC + row access + mascaramento. |
| **Restrito** | Regulado/LGPD/SOX. | CPF, dados financeiros auditáveis, PII sensível. | ABAC + encryption + audit log + approval workflow. |

**Regra:** Classificação é atribuída pelo **Data Owner** e validada pelo **Steward**. É obrigatória para todo dataset na Silver; datasets Gold só podem ser **públicos, internos ou confidenciais** (nunca restrito direto da fonte).

### 4.2 Política de Qualidade de Dados

- Toda tabela Gold deve ter ≥ 95% de score nas 6 dimensões (ver Seção 7).
- Toda tabela Silver deve ter ≥ 85%.
- Bronze é avaliada por completeness e schema conformity (≥ 99%).
- Falha em teste crítico bloqueia promoção para a próxima camada.

### 4.3 Política de Retenção e Descarte

| Camada | Retenção | Destino após TTL |
|--------|----------|------------------|
| Bronze (raw) | 90 dias | S3/GCS Glacier → expurgo |
| Silver (curated) | 2 anos | S3 IA → expurgo |
| Gold (curated) | 5 anos | Snowflake + backup off-platform |
| PII / LGPD | Conforme base legal | Descarte imediato após exercício de direito |
| Logs de auditoria | 7 anos (SOX) | Imutável (Object Lock) |

- Execução automatizada via Snowflake `TIME_TRAVEL` + S3 Lifecycle Policies.
- Toda exclusão precisa de ticket Jira aprovado pelo Owner.

### 4.4 Política de Acesso (RBAC + ABAC)

- **RBAC por papel:** `ROLE_DOMAIN_<X>_READER`, `ROLE_DOMAIN_<X>_WRITER`, `ROLE_GOLD_CONSUMER`, etc.
- **ABAC por atributos:** tags de classificação, departamento, projeto, geografia.
- **Just-in-time access:** privilégios elevados requerem aprovação via Jira + expiração em 8h.
- **MFA obrigatório** para acesso a dados restritos.
- **Revisão trimestral** de acessos pelo Steward.

### 4.5 Política de Privacidade e LGPD

- **Bases legais** mapeadas por dataset no catálogo (consentimento, execução de contrato, obrigação legal, legítimo interesse).
- **RIPD (Relatório de Impacto)** obrigatório para novos casos de uso com PII.
- **Direitos do titular** (acesso, correção, exclusão, portabilidade) atendidos em até **15 dias** via workflow Jira.
- **DPO** envolvido em qualquer incidente com PII (até 72h para ANPD).
- **Transferência internacional** (S3 US, GCS) requer contrato com cláusulas-padrão.

### 4.6 Política de Catálogo e Metadados

- 100% dos datasets Gold e Silver devem estar no catálogo.
- Metadados obrigatórios: owner, steward, classificação, domínio, base legal, SLA, tags técnicas.
- Atualização ≤ 7 dias após mudança de schema.
- Catálogo é a **fonte única de descoberta** (search-first).

### 4.7 Política de Linhagem de Dados

- Linhagem fim-a-fim (origem → Bronze → Silver → Gold → consumer).
- Captura automática via OpenLineage + Marquez (ou similar).
- Mudanças de schema devem refletir em até 24h no catálogo.
- Linhagem é requisito para promoção Silver→Gold.

---

## 5. Data Domains (Proposta Inicial)

| Domínio | Data Owner | Criticidade | Fontes principais | Casos de uso Gold |
|---------|-----------|-------------|-------------------|-------------------|
| **Vendas** | Diretor Comercial | Alta | SAP SD, Oracle OMS, API e-commerce | Receita, funil, churn |
| **Estoque** | Diretor de Operações | Alta | SAP MM, WMS | Giro, ruptura, cobertura |
| **Fiscal** | CFO | Crítica | SAP FI, Oracle GL | Obrigações fiscais, SPED |
| **Cliente** | CMO + DPO | Alta | CRM (Salesforce), API, web | 360° cliente, segmentação |
| **Produto** | Diretor de Produto | Média | PIM, ERP | Catálogo, margem por SKU |
| **Fornecedor** | Diretor de Compras | Média | SAP SRM, portais | Avaliação, risco |
| **Financeiro** | CFO | Crítica | Oracle GL, SAP FI, APIs bancárias | DRE, fluxo de caixa, SOX |
| **RH (restrito)** | CHRO | Crítica | SuccessFactors, API folha | Headcount, turnover (PII) |
| **Marketing** | CMO | Média | Ads APIs, GA4, CRM | Atribuição, LTV |

> Novos domínios requerem aprovação do Steering Committee e entrada no catálogo.

---

## 6. Glossary & Data Dictionary Standards

### 6.1 Template de Entrada do Glossário

```yaml
- term: Receita Líquida
  domain: Financeiro
  definition: "Valor faturado menos devoluções, descontos e impostos sobre vendas."
  synonyms: ["Net Revenue", "Receita Líqua"]
  formula: "SUM(faturamento) - SUM(devoluções) - SUM(descontos) - SUM(impostos)"
  owner: cfo@empresa.com
  steward: fs.analytics@empresa.com
  classification: confidencial
  legal_basis: "execução de contrato"
  source_systems: [SAP FI, Oracle GL]
  gold_table: GOLD_FIN.RECEITA_LIQUIDA_DIARIA
  version: 1.3
  approved_at: 2026-01-15
  approved_by: cfo@empresa.com
```

### 6.2 Regras de Nomenclatura

| Camada | Padrão | Exemplo |
|--------|--------|---------|
| Bronze | `BRZ_<source>_<entity>_<freq>` | `BRZ_SAP_SD_VENDAS_HORA` |
| Silver | `SLV_<domain>_<entity>_<freq>` | `SLV_VENDAS_PEDIDO_DIARIO` |
| Gold | `GOLD_<domain>_<concept>_<freq>` | `GOLD_VENDAS_RECEITA_MENSAL` |
| Tags técnicas | `snake_case` | `pii=true`, `classification=confidencial` |

### 6.3 Ownership

- Toda entrada do glossário tem **1 owner + 1 steward**.
- Mudança de definição precisa de aprovação do Owner + publicação no Confluence.

---

## 7. Data Quality Framework

### 7.1 Seis Dimensões

| Dimensão | Definição | Métrica típica |
|----------|-----------|----------------|
| **Accuracy** | Dados refletem a realidade. | % de valores que batem com fonte de controle |
| **Completeness** | Campos obrigatórios preenchidos. | % NOT NULL em colunas críticas |
| **Consistency** | Mesma regra entre sistemas. | % divergência entre fontes equivalentes |
| **Timeliness** | Dados disponíveis no SLA. | Latência ingestion→Gold |
| **Validity** | Valores conforme formato/domínio. | % fora do domínio esperado |
| **Uniqueness** | Sem duplicidades indevidas. | % chaves duplicadas |

### 7.2 SLAs por Camada

| Camada | Accuracy | Completeness | Consistency | Timeliness | Validity | Uniqueness |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|
| **Bronze** | ≥ 90% | ≥ 99% (schema) | ≥ 85% | ≤ 1h | ≥ 99% | ≥ 95% |
| **Silver** | ≥ 95% | ≥ 95% | ≥ 95% | ≤ 4h | ≥ 99% | ≥ 99% |
| **Gold** | ≥ 98% | ≥ 98% | ≥ 98% | ≤ 24h | ≥ 99,5% | ≥ 99,9% |

### 7.3 Stack de Testes

| Ferramenta | Uso | Camada |
|------------|-----|--------|
| **dbt tests** (`not_null`, `unique`, `accepted_values`, `relationships`) | Testes de contrato e regras simples | Silver, Gold |
| **Great Expectations / DQX** | Expectativas avançadas, ML-driven | Silver, Gold |
| **Reconcile jobs** (Python/Snowflake) | Comparação Bronze↔Oracle/SAP | Bronze |
| **Schema drift detection** | Alerta em mudança de schema | Bronze, Silver |
| **Anomaly detection** (statistical) | Detecção de outliers em métricas | Gold |

### 7.4 Template de Teste (dbt)

```yaml
models:
  - name: GOLD_VENDAS_RECEITA_MENSAL
    columns:
      - name: receita_liquida
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0
      - name: cliente_id
        tests:
          - not_null
          - relationships:
              to: ref('DIM_CLIENTE')
              field: cliente_id
```

---

## 8. Metadata Management

### 8.1 Tags Obrigatórias (técnicas)

| Tag | Valores | Aplicação |
|-----|---------|-----------|
| `classification` | publico/interno/confidencial/restrito | Toda tabela/coluna |
| `pii` | true/false | Toda coluna |
| `domain` | nome do domínio | Toda tabela |
| `layer` | bronze/silver/gold | Toda tabela |
| `source_system` | oracle/sap/api/... | Toda tabela Bronze |
| `data_owner` | email | Toda tabela |
| `data_steward` | email | Toda tabela |
| `legal_basis` | texto (LGPD) | Toda coluna PII |
| `retention_days` | inteiro | Toda tabela |

### 8.2 Tags de Negócio (exemplos)

- `campanha:verao2026`, `segmento:B2B`, `regiao:SP`, `produto:linha_premium`

### 8.3 Classificação Automática

- Regras Snowflake Horizon + regex/DLP para detectar CPF, CNPJ, email, cartão, salário.
- Score de confiança ≥ 0,85 aplica tag automaticamente; abaixo disso vira ticket Jira.
- Auditoria semanal do Steward para validar classificação automática.

---

## 9. Access Control Matrix

### 9.1 Matriz por Camada × Grupo

| Grupo | Bronze | Silver | Gold (Interno) | Gold (Confidencial) | Gold (Restrito) |
|-------|:---:|:---:|:---:|:---:|:---:|
| `DATA_ENGINEER` | RWD | RWD | R | I | I |
| `DATA_ANALYST_<DOMAIN>` | R | R | R | R (aprovação) | I |
| `DATA_SCIENTIST` | R | R | R | R (aprovação) | I |
| `BUSINESS_USER_<DOMAIN>` | I | I | R | R (aprovação) | I |
| `DPO_AUDITOR` | R | R | R | R | R |
| `EXTERNAL_PARTNER` | I | I | R (específico) | I | I |
| `CI_CD_BOT` | RWD (apenas stage) | I | I | I | I |

**R = Read | W = Write | D = Delete | I = sem acesso**

### 9.2 Matriz por Tipo de Operação

| Operação | PII visível | Mascaramento | Audit Log | Approval |
|----------|:---:|:---:|:---:|:---:|
| SELECT em coluna PII | Apenas com role específica | Dinâmico (ABAC) | Obrigatório | Para restrito |
| Export (COPY/UNLOAD) | Proibido por padrão | — | Alerta DPO | Sempre |
| CREATE TABLE | Apenas Eng/Steward | — | Obrigatório | — |
| DROP/TRUNCATE | Nunca em PII sem approval | — | Crítico | Owner + DPO |

---

## 10. Issue & Exception Management

### 10.1 Workflow Jira (Projeto `DGOV`)

```
[NEW] → [TRIAGE] → [IN_PROGRESS] → [VALIDATION] → [DONE]
                ↘ [ESCALATED] → [BLOCKED] ↗
                                       ↓
                                 [POST_MORTEM]
```

| Status | SLA | Responsável |
|--------|-----|-------------|
| Triage | 1 dia útil | Data Steward |
| In Progress (S3) | 5 dias úteis | Engenheiro |
| In Progress (S2) | 10 dias úteis | Engenheiro + Steward |
| In Progress (S1) | 24h | Engenheiro + Custodian |
| Validation | 2 dias úteis | Steward + Owner |
| Post-mortem (S1) | 5 dias úteis | Council |

### 10.2 Templates Jira

| Tipo | Quando usar | Campos obrigatórios |
|------|-------------|---------------------|
| **Bug - Qualidade** | Score de DQ abaixo do SLA | Dataset, dimensão afetada, % atual vs. SLA, impacto |
| **Request - Acesso** | Pedido de RBAC/ABAC | Solicitante, dataset, justificativa, prazo |
| **Request - LGPD** | Direitos do titular | Tipo de direito, titular, prazo legal |
| **Risk - Schema drift** | Mudança detectada | Fonte, breaking change?, owner acionado? |
| **Task - Catalogação** | Dataset sem owner/descrição | Dataset, responsável |

### 10.3 Escalation Path

1. **N1 — Steward** (1 dia)
2. **N2 — Data Owner** (3 dias)
3. **N3 — Council** (5 dias)
4. **N4 — Steering + DPO** (crítico/LGPD)

---

## 11. Metrics & KPIs de Maturidade

### 11.1 KPIs Operacionais (mensal)

| KPI | Meta | Fonte |
|-----|------|-------|
| **% datasets catalogados (Gold)** | 100% | Collibra/Atlan |
| **% datasets com Data Owner atribuído** | 100% | Catálogo |
| **% datasets com classificação** | 100% | Horizon Catalog |
| **Score médio de qualidade (Gold)** | ≥ 95% | dbt + DQX |
| **% PII com `legal_basis` mapeado** | 100% | Catálogo |
| **Tempo médio de resolução (LGPD)** | ≤ 10 dias | Jira |
| **Tempo médio de resolução (qualidade)** | ≤ 7 dias | Jira |
| **% acessos revisados (quarter)** | 100% | Steward report |
| **Cobertura de linhagem** | ≥ 90% | OpenLineage |
| **Taxa de schema drift tratada em 24h** | ≥ 95% | Monitoramento |

### 11.2 Dashboard Executivo (mensal ao Steering)

- Heatmap de qualidade por domínio.
- Top 10 exceções abertas por aging.
- Status de conformidade LGPD (pedidos vs. prazo).
- Tendência de score de maturidade (trimestral).

---

## 12. Tooling Stack

| Categoria | Ferramenta | Uso | Owner |
|-----------|------------|-----|-------|
| **Documentação** | Confluence | Políticas, playbooks, atas, glossário | Steward Lead |
| **Workflow/tickets** | Jira (projeto `DGOV`) | Issues, exceptions, approvals, LGPD requests | Council |
| **Repositório de políticas formais** | SharePoint | PDFs assinados, contratos, base legal | DPO + Jurídico |
| **Catálogo técnico** | Snowflake Horizon Catalog | Classificação automática, linhagem técnica | Eng. Plataforma |
| **Catálogo de negócio** | Collibra / Atlan | Glossário, business glossary, stewardship | Steward Lead |
| **Qualidade** | dbt + Great Expectations / DQX | Testes e expectativas | Eng. Dados |
| **Linhagem** | OpenLineage + Marquez | Captura e visualização de linhagem | Eng. Plataforma |
| **Privacidade** | OneTrust / ferramenta LGPD interna | RIPD, gestão de consentimento | DPO |
| **Observabilidade** | Monte Carlo / Bigeye | Anomalia e freshness | Eng. Plataforma |

---

## 13. Communication Plan

### 13.1 Cadência

| Fórum | Frequência | Participantes | Objetivo |
|-------|:---:|---|---|
| **Daily de Dados** | Diária (15 min) | Eng. Dados + Custodian | Bloqueios operacionais |
| **Weekly Domain Sync** | Semanal | Owner + Steward + Eng do domínio | Status de exceções |
| **Council Meeting** | Semanal (45 min) | Council + DPO | Decisões táticas |
| **Steering Committee** | Mensal | Steering | Estratégia e KPIs |
| **All-Hands de Dados** | Trimestral | Toda a empresa | Cultura, awareness |
| **LGPD Post-mortem** | Ad-hoc | DPO + Council + Jurídico | Incidentes PII |

### 13.2 Canais

| Canal | Uso | Ferramenta |
|-------|-----|------------|
| `#data-governance` | Operacional, dúvidas rápidas | Slack/Teams |
| `#lgpd-alerts` | Alertas PII, requests de titulares | Slack/Teams |
| `DGOV` (Jira) | Tickets formais | Jira |
| `Data Governance Space` | Documentação | Confluence |
| `/Políticas/Data Governance` | PDFs assinados | SharePoint |

### 13.3 Templates

- **Template de Ata** (Council/Steering) — Confluence
- **Template de Post-mortem** (incidente LGPD) — Confluence
- **Template de Policy Update** — SharePoint + versionamento semântico
- **Template de Status Report Mensal** — Confluence macro

---

## 14. Maturity Model

### 14.1 Cinco Níveis

| Nível | Nome | Características | Critérios para o Lakehouse Híbrido |
|:---:|------|-----------------|------------------------------------|
| **1** | **Inicial** | Processos ad-hoc, dados em planilhas, sem owner. | Existe lakehouse mas sem catálogo; decisões por SRE/DBA isoladamente. |
| **2** | **Repetível** | Papéis definidos, classificação básica, qualidade reativa. | Stewards nomeados, classificação em ≥ 50% das tabelas, testes dbt pontuais, LGPD reativo. |
| **3** | **Definido** *(meta 12 meses)* | Políticas formais, catálogo ≥ 80%, qualidade automatizada, RACI ativo. | Catálogo ≥ 90% em Gold, SLAs de qualidade publicados, RACI assinado, Council operando, Linhagem fim-a-fim. |
| **4** | **Gerenciado** *(meta 18 meses)* | Métricas dirigem decisões, automação avançada, ABAC maduro. | ABAC em dados restritos, score DQ ≥ 95% sustentado, LGPD proativo (RIPD), revisão trimestral de acesso automatizada. |
| **5** | **Otimizado** *(meta 24+ meses)* | Data mesh parcial, self-service governado, marketplace interno. | Domínio como produto, discoverability 1-clique, ML feature store governado, DPO embedded nos squads, AI Governance operacional. |

### 14.2 Roadmap de Maturidade (24 meses)

| Marco | Mês | Entregáveis |
|-------|:---:|-------------|
| Quick wins | M1–M3 | RACI assinado, catálogo ≥ 50%, policies v1, Jira DGOV live, KPIs baseline. |
| Foundation | M4–M6 | Classificação automática, dbt em 100% Gold, ABAC piloto, LGPD workflow. |
| Scale | M7–M12 | Linhagem fim-a-fim, score DQ ≥ 95%, revisão de acesso automatizada, DPO dashboard. |
| Optimize | M13–M18 | Data contracts, marketplace, AI governance, RIPD automatizado. |
| Innovate | M19–M24 | Data mesh por domínio, feature store governado, self-service com guardrails. |

---

## 15. Anexos e Referências

### 15.1 Documentos Relacionados

- Política de Segurança da Informação
- Política de Classificação da Informação
- Política de Retenção (jurídico)
- DPIA/RIPD templates
- Contratos de transferência internacional (S3/GCS)

### 15.2 Glossário de Siglas

- **CDO** — Chief Data Officer
- **DPO** — Data Protection Officer (encarregado LGPD)
- **PII** — Personally Identifiable Information
- **RACI** — Responsible, Accountable, Consulted, Informed
- **RIPD** — Relatório de Impacto à Proteção de Dados
- **ABAC** — Attribute-Based Access Control
- **RBAC** — Role-Based Access Control
- **DQX** — Data Quality eXpectations
- **SLA** — Service Level Agreement

### 15.3 Aprovação

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| CDO | | | |
| CFO | | | |
| CTO | | | |
| DPO | | | |
| Head of Risk | | | |

---

> **Próxima revisão:** M+12 ou em caso de mudança regulatória/material.
