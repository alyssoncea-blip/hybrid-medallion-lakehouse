# Hybrid Medallion Lakehouse — Matriz de Riscos e Plano de Conformidade

> Documento vivo. Versão 1.0. Revisão trimestral. Owner: Risk & Compliance Lead.
> Escopo: arquitetura híbrida Snowflake + S3/GCS, integração Oracle on-prem/SAP, governança LGPD para varejo/autopeças.

---

## 1. Risk Management Approach

### 1.1 Metodologia

Adotamos abordagem híbrida baseada em **ISO 31000:2018** (framework de gestão de riscos) com taxonomia de probabilidade/impacto alinhada ao **NIST SP 800-30**. Cada risco é classificado em uma matriz 5x5, gerando score (P × I) e nível (Low/Medium/High/Critical). Respostas padronizadas: **Avoid, Reduce, Transfer, Accept**. Todos os riscos residuais com score ≥ 15 obrigam plano de mitigação documentado, owner designado e data de revisão.

### 1.2 Categorias de Risco

| Código | Categoria |
|--------|-----------|
| RC | Regulatory & Compliance (LGPD, fiscais, consumidor) |
| TS | Technical & Security |
| OP | Operational |
| FI | Financial & Vendor Lock-in |
| LG | Legal & Contractual |
| DA | Data & Privacy |

### 1.3 Cadência

| Atividade | Frequência | Owner |
|-----------|------------|-------|
| Risk review meeting | Semanal (15 min, stand-up) | Risk Lead |
| Risk register audit | Mensal | Risk Lead + CISO |
| Top risks deep-dive | Quinzenal | Comitê Executivo |
| Board risk report | Trimestral | CRO / Diretor |
| Annual risk assessment | Anual (janeiro) | Risk Lead + Auditoria |
| Risk reassessment ad-hoc | Por trigger (incidente, mudança regulatória, novo vendor) | Risk Lead |

### 1.4 Critérios de Escoragem

- **Probabilidade (P)**: 1=Raro (<5%), 2=Improvável (5-30%), 3=Possível (30-60%), 4=Provável (60-85%), 5=Quase Certo (>85%)
- **Impacto (I)**: 1=Insignificante (<R$10k), 2=Menor (R$10k-100k), 3=Moderado (R$100k-1M), 4=Maior (R$1M-10M), 5=Catastrófico (>R$10M ou reputacional grave)
- **Score**: P × I (1-25). Níveis: 1-4 Low, 5-9 Medium, 10-14 High, 15-25 Critical.

---

## 2. Risk Matrix

| ID | Descrição | Categoria | P | I | Score | Nível | Resposta | Mitigação Resumida | Owner |
|----|-----------|-----------|---|---|-------|-------|----------|--------------------|-------|
| R-01 | **Vendor lock-in Snowflake** — dificuldade de migração futura para Databricks/Redshift/BigQuery devido a uso extensivo de Snowpark, Dynamic Tables e Tasks | FI | 4 | 4 | 16 | Critical | Reduce | Arquitetura de ingestão desacoplada (S3/GCS + Iceberg), contratos de 1 ano, cláusula de portabilidade de dados, PoCs anuais com vendor alternativo | CTO |
| R-02 | **Violação LGPD com exposição de PII** — vazamento de dados pessoais de clientes brasileiros sem base legal adequada | RC/DA | 3 | 5 | 15 | Critical | Reduce | Criptografia at-rest/in-transit, tokenização de CPF, DPO ativo, RIPD obrigatório, auditoria trimestral | DPO |
| R-03 | **Falha de integração Oracle on-prem → Snowflake** — latência ou quebra na replicação CDC via HVR/Qlik impactando camadas Bronze/Silver | OP/TS | 3 | 4 | 12 | High | Reduce | Dual pipeline (CDC + batch fallback), SLO de lag < 15min, runbook documentado, alerta PagerDuty | Data Eng Lead |
| R-04 | **Ransomware em S3/GCS com criptografia comprometida** — ataque comprometendo keys KMS ou buckets com dados Bronze | TS | 3 | 5 | 15 | Critical | Reduce | BYOK com HSM, MFA delete, Object Lock (WORM), immutable backups em região secundária, IRP testado | CISO |
| R-05 | **SAP extraction overhead** — uso de SLT/SDI impactando performance do ECC e gerando lentidão em transações OLTP | OP | 4 | 3 | 12 | High | Reduce | Janelas de extração fora do horário comercial, throttling configurado, SLT replicador dedicado, monitor SAP ST03N | SAP Basis Lead |
| R-06 | **Custo Snowflake descontrolado** — créditos consumidos acima do orçamento por queries mal-otimizadas ou warehouses idle | FI/OP | 4 | 3 | 12 | High | Reduce | Resource monitors, auto-suspend agressivo, FinOps dashboard, tagging por domínio, alertas em 80%/100% budget | FinOps Lead |
| R-07 | **Mudança regulatória ANPD/Receita/Consumidor** — novas instruções da ANPD, alterações no SPED, normas do Código de Defesa do Consumidor ou em regulações de autopeças exigindo controles não implementados | RC | 3 | 4 | 12 | High | Reduce | Monitoramento regulatório (ANPD, Receita Federal, CONAR, Sindipeças), consultoria jurídica retainer, sandbox regulatório | DPO + Legal |
| R-08 | **Indisponibilidade Snowflake** — SLA da região BR/aws-sa-east-1 não cumprido, impactando relatórios críticos | OP | 2 | 4 | 8 | Medium | Transfer | Multi-region DR, contrato SLA 99.9% com créditos, runbook failover testado trimestralmente | SRE Lead |
| R-09 | **Acesso privilegiado excessivo** — admins Snowflake com ACCOUNTADMIN sem MFA, criando vetor de ataque insider | TS | 3 | 5 | 15 | Critical | Reduce | RBAC granular (SysAdmin por domínio, não ACCOUNTADMIN), MFA obrigatório, MFA enforcement via SCIM, sessão recorded | CISO |
| R-10 | **Falha de classificação de dados** — dados sensíveis em camadas Bronze sem mascaramento/tag, violando princípio de minimização LGPD | DA/RC | 3 | 4 | 12 | High | Reduce | Snowflake Dynamic Data Masking + Row Access Policies automatizados, tag-based masking, scanner PII | Data Gov Lead |
| R-11 | **Vendor Snowflake falência/M&A** — mudança de estratégia do vendor impactando pricing ou descontinuidade de features | FI | 2 | 4 | 8 | Medium | Accept/Reduce | Dados em formato aberto (Parquet/Iceberg), contrato com cláusulas de continuidade, due diligence anual do vendor | Procurement |
| R-12 | **Falha de auditoria interna / controles SOX-like** — controles de TI não evidenciados adequadamente durante auditoria externa ou interna, especialmente para processos fiscais e financeiros | RC/TS | 3 | 4 | 12 | High | Reduce | Logs imutáveis em CloudTrail + Snowflake ACCOUNT_USAGE, evidências automatizadas via GRC tool, auditoria interna semestral | CISO |

---

## 3. Top 5 Critical Risks (Expansão)

### R-01 — Vendor Lock-in Snowflake

- **Descrição**: Arquitetura intensiva em features proprietárias Snowflake (Snowpark Python, Dynamic Tables, Tasks, Cortex AI) dificulta migração para alternativas como Databricks, BigQuery ou Redshift.
- **Categoria**: FI/TS — Estratégico
- **Score**: 16 (Critical) — P=4 (Provável em horizonte 3 anos), I=4 (R$5M-15M em custos de migração + perda de velocidade de inovação)
- **Trigger**: Aquisição Snowflake por hyperscaler com mudança de pricing; descontinuidade de feature crítica.
- **Mitigação Detalhada**:
  1. Camadas Bronze/Silver em formato aberto (Apache Iceberg) sobre S3/GCS — agnóstico de compute.
  2. Snowflake usado como **query engine opcional**, não como única camada de armazenamento.
  3. Contratos plurianuais evitados (renovação anual com cláusula de saída 90 dias).
  4. **Portabilidade**: export semanal completo de tabelas críticas em Parquet/Iceberg.
  5. PoCs anuais com Databricks (1 sprint dedicado) para validar paridade funcional.
  6. Manter **abstração de transformações em dbt** (portável) ao invés de Snowpark puro.
- **Plano de Contingência**: Re-arquitetura em 6-9 meses para Databricks se trigger ativado. Budget contingência aprovado: R$ 2M.
- **Owner**: CTO. **Review**: Trimestral.
- **KRIs**: % de tabelas em Iceberg vs Snowflake-managed (alvo: >70% em Iceberg); custo de migração estimado atualizado anualmente.

### R-02 — Violação LGPD com Exposição de PII

- **Descrição**: Vazamento ou exposição não autorizada de dados pessoais (CPF, dados financeiros, saúde) de titulares brasileiros, gerando multa ANPD de até 2% do faturamento (limitada a R$ 50M por infração) e dano reputacional.
- **Categoria**: RC/DA — Regulatório
- **Score**: 15 (Critical) — P=3 (Possível), I=5 (Catastrófico — multa + reputação + bloqueio operacional)
- **Base Legal Aplicável**: Art. 7º (consentimento, execução de contrato, legítimo interesse, obrigações legais) e Art. 11º (dados sensíveis).
- **Mitigação Detalhada**:
  1. **Criptografia**: AES-256 at-rest (S3 SSE-KMS + Snowflake Tri-Secret Secure), TLS 1.3 in-transit, BYOK com AWS KMS.
  2. **Tokenização**: CPF, CNPJ, dados bancários tokenizados via Hashicorp Vault ou Protegrity.
  3. **Mascaramento dinâmico**: Snowflake Dynamic Data Masking aplicado a colunas PII com policies baseadas em role.
  4. **DSAR automatizado**: workflow Jira Service Desk → query automatizada → resposta em até 15 dias.
  5. **Breach response plan**: notificação ANPD em até 2 dias úteis + titulares em 72h (Art. 48 LGPD).
  6. **Auditoria trimestral** de acessos a dados sensíveis.
  7. **Treinamento** anual de todos os engenheiros em LGPD.
- **Owner**: DPO + CISO. **Review**: Mensal.
- **KRIs**: Número de acessos anômalos a PII (meta: <10/mês); tempo médio de resposta DSAR (meta: <15 dias); % tabelas com PII classificadas e mascaradas (meta: 100%).

### R-04 — Ransomware em S3/GCS

- **Descrição**: Atacante obtém credenciais AWS/GCP ou compromete endpoint on-prem, exfiltrando e/ou criptografando dados Bronze com chaves comprometidas.
- **Categoria**: TS — Cibersegurança
- **Score**: 15 (Critical) — P=3 (Possível — crescente no setor financeiro brasileiro), I=5 (Catastrófico — parada operacional + LGPD breach)
- **Mitigação Detalhada**:
  1. **BYOK com HSM CloudHSM/Azure Dedicated HSM** — chaves fora do controle direto da cloud.
  2. **MFA Delete + Object Lock** habilitado em todos os buckets Bronze/Silver.
  3. **Versionamento imutável** + lifecycle policy de 7 anos para compliance.
  4. **Cross-region backup** em conta AWS isolada (síndrome air-gap).
  5. **IRP (Incident Response Plan)** testado 2x/ano via tabletop exercise.
  6. **Ransomware tabletop** anual com mesa executiva (CISO, CTO, Legal, Comunicação).
  7. **Dwell time monitoring** via GuardDuty/Chronicle Security, alvo <24h.
- **Owner**: CISO. **Review**: Mensal.
- **KRIs**: Tempo médio de detecção (MTTD) < 24h; tempo de recuperação (MTTR) < 8h; cobertura de backups imutáveis (meta: 100% buckets críticos).

### R-09 — Acesso Privilegiado Excessivo

- **Descrição**: Conta ACCOUNTADMIN ou usuários com roles elevadas (SECURITYADMIN, SYSADMIN) comprometidos por phishing, insider threat ou má configuração, permitindo exfiltração ou destruição de dados.
- **Categoria**: TS — Identity & Access
- **Score**: 15 (Critical) — P=3, I=5
- **Mitigação Detalhada**:
  1. **Eliminação de ACCOUNTADMIN humano** — uso de Snowflake MFA Service com role escalation just-in-time (JIT) via Okta/Ping.
  2. **RBAC granular**: roles customizados por domínio (FINANCE_RO, FINANCE_RW, etc.), princípio de menor privilégio.
  3. **SCIM provisioning** com revisão trimestral de acessos (attestation campaign).
  4. **Session recording** de sessões Snowflake admin via session-based policy.
  5. **Break-glass procedure** documentado com aprovação CISO + log de auditoria dedicado.
  6. **Separação de duties**: quem cria usuário ≠ quem aprova ≠ quem tem acesso a dados sensíveis.
- **Owner**: CISO + IAM Lead. **Review**: Mensal.
- **KRIs**: Número de usuários com ACCOUNTADMIN ativo (meta: 0 humanos, apenas service accounts); tempo de revisão de acessos (meta: <30 dias).

### R-07 — Mudança Regulatória ANPD / Fiscal / Consumidor

- **Descrição**: Novas instruções da ANPD, alterações no SPED/Nota Fiscal, normas do Código de Defesa do Consumidor aplicáveis a e-commerce de autopeças, ou regulações do setor (Sindipeças, CONAR, Inmetro) exigindo controles não implementados, gerando não-conformidade e autuações.
- **Categoria**: RC — Regulatório Setorial
- **Score**: 12 (High) — P=3 (Provável — varejo e proteção de dados em transformação regulatória contínua), I=4
- **Mitigação Detalhada**:
  1. **Monitoramento regulatório contínuo**: assinatura de clippings especializados (ANPD, Receita Federal, CONAR, Sindipeças, Mattos Filho, Lex Atlas).
  2. **Comitê regulatório mensal** com DPO, Legal, CISO, área Fiscal.
  3. **Sandbox regulatório**: testar novos controles em ambiente isolado antes de produção.
  4. **Consultoria jurídica retainer** com escritório especializado em direito digital e proteção ao consumidor.
  5. **Mapping controles↔regulamentações** em GRC tool (Vanta/Drata) atualizado por demanda.
- **Owner**: DPO + Legal. **Review**: Trimestral ou por evento.
- **KRIs**: % de regulamentações aplicáveis com controles implementados (meta: 100%); tempo de adaptação pós-publicação (meta: <90 dias para High impact).

---

## 4. LGPD Compliance Plan

### 4.1 Bases Legais por Categoria de Tratamento

| Categoria de Dados | Base Legal (Art. 7º) | Finalidade | Retenção |
|--------------------|----------------------|------------|----------|
| Dados cadastrais de clientes (CPF, endereço, contato) | Execução de contrato (V) | Gestão de relacionamento, vendas, pós-venda, garantias | Enquanto durar relação + 5 anos (Art. 173 CC / CDC) |
| Dados de transações comerciais (vendas, pagamentos) | Cumprimento de obrigação legal (II) | Obrigações fiscais (SPED, NF-e), contabilidades, garantia de autopeças | 5-10 anos (CTN, Lei 8.021/90, Decreto 1.800/96) |
| Dados de navegação/cookies no e-commerce | Consentimento (I) | Analytics, personalização de ofertas | 6 meses |
| Dados de RH (funcionários e prestadores) | Execução de contrato (V) + legítimo interesse (IX) | Folha, benefícios, SST, treinamentos | 5-20 anos conforme legislação trabalhista |
| Dados de saúde (benefícios, afastamentos) | Tutela da saúde (Art. 11º II, f) | Plano de saúde, atestados, ergonomia | 20 anos (Resolução CFM 1.821/2007) |
| Dados de telemetria veicular (IoT) | Legítimo interesse (IX) | Manutenção preditiva, recalls, garantia estendida | 5 anos após desvinculação do veículo |
| Logs de auditoria | Legítimo interesse (IX) + obrigação legal | Segurança, investigação, garantia de origem | 5 anos |

### 4.2 RIPD (Relatório de Impacto à Proteção de Dados)

- **Obrigatório** para todos os novos tratamentos que envolvam dados sensíveis, larga escala, monitoramento sistemático ou perfilização.
- **Template padronizado** armazenado em Confluence + versionado.
- **Workflow**: Engenheiro preenche template → DPO revisa (SLA 10 dias úteis) → CISO aprova quando aplicável → Comitê de Ética para casos de alto risco.
- **RIPDs vigentes**: Cadastro de clientes, Análise de crédito, BI analítico (Bronze/Silver/Gold), Treinamento de modelos ML, Auditoria interna.
- **Revisão**: anual ou por mudança substancial.

### 4.3 DPO (Encarregado de Dados)

- **Designação**: Encarregado interno com equipe (1 DPO + 2 analistas de privacidade).
- **Credenciais**: Certificação EXIN PDPP ou equivalente; conhecimento do setor de varejo/e-commerce é diferencial.
- **Comunicação**: Canal dedicado `dpo@empresa.com.br` + formulário web + atendimento telefônico em horário comercial.
- **Atribuições** (Art. 41 §2º LGPD): aceitar reclamações, receber comunicações ANPD, orientar colaboradores, executar RIPD.
- **Report**: reporta ao CEO com linha direta ao Conselho de Administração.
- **Independência**: autonomia decisória em matéria de privacidade; veto suspensivo em lançamentos que violem LGPD.

### 4.4 DSAR (Data Subject Access Request) Process

| Etapa | SLA | Responsável | Sistema |
|-------|-----|-------------|---------|
| 1. Recebimento via canal único (e-mail/formulário) | T+0 | DPO | Jira Service Desk + Confluence |
| 2. Triagem e verificação de identidade | 3 dias úteis | DPO | Jira workflow |
| 3. Identificação dos dados (catalog search) | 5 dias úteis | Data Eng + DPO | Snowflake ACCOUNT_USAGE + Unity Catalog-like + Collibra |
| 4. Coleta e anonimização para entrega | 5 dias úteis | Data Eng | Script automatizado dbt + Snowflake |
| 5. Revisão Legal (dados de terceiros) | 2 dias úteis | Legal | Manual |
| 6. Entrega ao titular (formato estruturado JSON/CSV) | 2 dias úteis | DPO | E-mail criptografado (PGP) ou portal |
| **Total** | **15 dias úteis** | — | — |

**Tipos de DSAR atendidos**: Acesso (Art. 18 I-II), Correção (III), Anonimização (IV), Eliminação (VI), Portabilidade (V), Revogação de consentimento (IX).

**Exceções**: Quando dados são necessários para cumprimento de obrigação legal ou exercício regular de direitos (Art. 16 LGPD) — DPO documenta e comunica titular.

### 4.5 Retenção e Descarte

| Camada | Retenção Hot | Retenção Cold | Descarte |
|--------|--------------|---------------|----------|
| Bronze (raw) | 90 dias S3 Standard | 7 anos S3 Glacier | Purge automático via lifecycle policy |
| Silver (curated) | 1 ano S3 Standard-IA | 7 anos Glacier | Purge após retenção legal |
| Gold (aggregated) | 3 anos | Indefinido (anonimizado) | Revisão anual |
| Snowflake Time Travel | 1 dia | — | Automático |
| Snowflake Fail-safe | 7 dias | — | Automático |
| Logs de auditoria | 90 dias hot | 5 anos S3 Glacier | Purge após 5 anos |
| Backups de banco | 30 dias hot | 5 anos | — |

**Descarte seguro**: shredding de mídias físicas, cryptographic erase (apagar chaves KMS) para cloud, certificação de descarte por fornecedor.

### 4.6 Direitos dos Titulares e Atendimento

- **Política de privacidade** publicada em `empresa.com.br/privacidade` com linguagem clara.
- **Banner de cookies** opt-in (exceto essenciais).
- **Opt-out de marketing**: link de descadastro em todos os e-mails + central de preferências.
- **Comunicação de incidentes**: notificação titular em até 72h para dados sensíveis (Art. 48).

---

## 5. Security Controls — CIS Controls v8 Mapeados

| CIS Control | Implementação | Evidência |
|-------------|---------------|-----------|
| **CIS 1** — Inventory of Assets | AWS Config + GCP Asset Inventory + Snowflake ACCOUNT_USAGE | Relatório mensal CMDB |
| **CIS 2** — Software Inventory | Wiz/Tenable para cloud, Snyk para IaC | Dashboard semanal |
| **CIS 3** — Data Protection | Collibra/Atlan (catalog) + Snowflake DDM + tokenização | Scan trimestral PII |
| **CIS 4** — Secure Configuration | AWS Config Rules + GCP SCC + Snowflake Parameter controls | Auditoria mensal |
| **CIS 5** — Account Management | Okta SSO + SCIM + revisão trimestral | Attestation campaign |
| **CIS 6** — Access Control Management | RBAC Snowflake + IAM least privilege + JIT elevation | Relatório IAM |
| **CIS 7** — Continuous Vulnerability Management | Qualys + Wiz scan semanal | Tickets Jira automáticos |
| **CIS 8** — Audit Log Management | CloudTrail + Snowflake LOGIN_HISTORY + Splunk SIEM | Retenção 5 anos |
| **CIS 9** — Email & Web Browser Protections | Proofpoint + Zscaler + extensão browser MGMT | Logs Proofpoint |
| **CIS 10** — Malware Defenses | CrowdStrike + EDR em endpoints + GuardDuty | Telemetria CrowdStrike |
| **CIS 11** — Data Recovery | S3 cross-region + Object Lock + Snowflake Fail-safe | DRP testado semestral |
| **CIS 12** — Network Infrastructure Mgmt | VPC privada + PrivateLink Snowflake + GuardDuty | Diagrama rede atualizado |
| **CIS 13** — Network Monitoring | VPC Flow Logs + Splunk + Chronicle | SIEM dashboards |
| **CIS 14** — Security Awareness | KnowBe4 + phishing simulation trimestral + treinamento LGPD | Relatórios KnowBe4 |
| **CIS 15** — Service Provider Mgmt | Vendor risk assessment anual (SIG Lite) + DPA assinado | Contracts database |
| **CIS 16** — Application Security | SAST (Snyk) + DAST (OWASP ZAP) + code review obrigatório | Pipeline CI/CD |
| **CIS 17** — Incident Response | Playbooks em Confluence + PagerDuty + IRP testado 2x/ano | Post-mortems |
| **CIS 18** — Penetration Testing | Pentest externo anual + red team semestral | Relatório pentester |

---

## 6. Audit & Logging

### 6.1 O Que é Logado

| Origem | Eventos | Destino | Retenção |
|--------|---------|---------|----------|
| **AWS CloudTrail** | API calls (S3, KMS, IAM, EC2) | S3 + Splunk | 5 anos |
| **AWS S3 Access Logs** | GET/PUT/DELETE em buckets Bronze/Silver/Gold | S3 + Splunk | 2 anos hot, 5 cold |
| **Snowflake LOGIN_HISTORY** | Logins, MFA, falhas | Snowflake ACCOUNT_USAGE + Splunk | 1 ano Snowflake, 5 Splunk |
| **Snowflake ACCESS_HISTORY** | Queries, tabelas acessadas, usuários | Snowflake + Splunk | 1 ano Snowflake, 5 Splunk |
| **Snowflake QUERY_HISTORY** | Queries executadas, warehouses, bytes scanned | Snowflake + Splunk | 1 ano, 5 Splunk |
| **Snowflake GRANTS_HISTORY** | Mudanças de privilégios | Snowflake + Splunk | 5 anos |
| **Snowflake STORAGE_USAGE** | Consumo de storage | FinOps dashboard | 3 anos |
| **Okta** | Logins, MFA, provisionamento | Okta logs + Splunk | 1 ano Okta, 5 Splunk |
| **Oracle on-prem** | DB audit (DDL, DML, priv) | Splunk via rsyslog | 5 anos |
| **SAP** | SM20, ST03N, audit log | Splunk via SAP ETD | 5 anos |
| **GCP** | Cloud Audit Logs (S3 GCS alternative) | Splunk | 5 anos |
| **Aplicações (Airflow, dbt)** | DAG runs, modelos, falhas | Splunk + CloudWatch | 2 anos |

### 6.2 Retenção e Armazenamento

- **Hot storage** (queries ativas, 90 dias): Splunk indexer + S3 Standard.
- **Warm storage** (6 meses a 2 anos): S3 Standard-IA + Splunk frozen.
- **Cold storage** (5 anos para compliance): S3 Glacier + Glacier Deep Archive para >2 anos.
- **Integridade**: SHA-256 hash diário dos logs + assinatura digital armazenada em cartório digital (certisign ou similar).
- **WORM**: logs críticos em S3 Object Lock com retention legal hold durante investigações.

### 6.3 SIEM e Correlação

- **Plataforma**: Splunk Cloud (alternativa: Chronicle Security, Elastic SIEM).
- **Use Cases** (mínimo 25 implementados):
  1. Detecção de login Snowflake anômalo (geo, horário, IP).
  2. Exfiltração massiva de dados (bytes scanned > threshold).
  3. Mudança de role ADMIN fora do change window.
  4. Acesso a tabelas PII por usuários sem necessidade.
  5. Falhas de MFA repetidas.
  6. AWS root account usage.
  7. Disable de CloudTrail ou GuardDuty.
  8. Criação de chaves IAM fora do padrão.
  9. Modificação de KMS keys.
  10. Object Lock desabilitado.
  11. Bucket policy permissiva (0.0.0.0/0).
  12. Cryptojacking detection (CPU anômalo).
  13. DNS exfiltration.
  14. Ransomware indicators (Mass DELETE + ENCRYPT).
  15. Snowflake credential em pastebin.
- **MTTR alvo**: 4h para High, 1h para Critical.
- **24x7 SOC**: interno em horário comercial + MSSP (e.g., Trustwave, IBM) para fora.

### 6.4 Evidências para Auditoria

- **Coleta automatizada** via GRC tool (Vanta/Drata) sincronizado com AWS, GCP, Snowflake, Okta.
- **Continuous compliance monitoring**: testes CIS automatizados diários.
- **Auditoria interna** semestral com checklist ISO 27001 + SOC 2 + LGPD.
- **Auditoria externa** anual por Big 4 (Deloitte, EY, PwC, KPMG) para SOC 2 Type II.

---

## 7. Vendor Risks — Snowflake

### 7.1 SLA Analysis

| Item | SLA Snowflake | Nosso Requisito | Gap |
|------|---------------|------------------|-----|
| Uptime mensal | 99.9% (Enterprise+) | 99.95% | Aceitável com DR multi-region |
| Créditos de serviço | 10% para uptime <99% | 25% | Renegociar no renewal |
| Performance | Não garantido (best-effort) | Query P95 <30s | SLO interno, contrato separado |
| Suporte | 24x7 P1, business hours demais | 24x7 P1+P2 | Upgrade para Premier Support |
| RPO / RTO | Fail-safe 7 dias, Time Travel 1 dia | RPO 1h, RTO 4h | Cobertura via S3 backup próprio |
| Segurança | SOC 2 Type II, ISO 27001 | + ISO 27701, LGPD adequacy | Aceito com DPA |
| Data residency | Regional (escolha cliente) | Brasil (LGPD) | Snowflake AWS sa-east-1 ✓ |
| Portabilidade | Export CSV/Parquet nativo | Iceberg tables | Adotar Iceberg para reduzir lock-in |

### 7.2 Cláusulas Contratuais Críticas

| Cláusula | Status | Observação |
|----------|--------|------------|
| **Data Processing Agreement (DPA)** com cláusulas LGPD | Obrigatório | Subprocessor list atualizado trimestralmente |
| **Confidencialidade e não-revelação** | Padrão | OK |
| **Auditoria de cliente** (right to audit) | Limitado | Snowflake permite auditoria via SOC 2 + penetration test summary; auditoria custom sob custo |
| **Notificação de breach** | 72h | OK, alinhado com LGPD |
| **Subprocessors disclosure** | OK | Lista em snowflake.com/legal/subprocessors |
| **Exit clause** | Anual | Cláusula de portabilidade de dados garantida |
| **Pricing protection** | Não garantido em renovações | Mitigado com termos plurianuais opcionais (1+1 ano) |
| **Cyber insurance** | Snowflake possui | Aceitável |
| **LGPD adequacy** | DPA compliance | Validado por Legal |
| **Sovereign cloud option** | Disponível em algumas regiões | Snowflake AWS sa-east-1 ✓ |

### 7.3 Multi-Cloud Strategy

- **Estratégia**: Snowflake como primary + **Databricks standby** (não ativo, mas com PoC validado) para compute alternativo.
- **Armazenamento**: 100% em **S3/GCS formato Iceberg** (não Snowflake-managed). Snowflake lê Iceberg tables nativamente.
- **Vendor diversification**: Pelo menos 2 provedores de cloud (AWS primary, GCP secondary). Snowflake roda em ambos.
- **Annual PoC budget**: R$ 200k reservado para validar alternativas (Databricks, BigQuery, Redshift) em workloads não-críticos.
- **Abstraction layer**: dbt Core como camada de transformação (portável entre Snowflake, Databricks, BigQuery).
- **Reversibilidade**: Capacidade técnica de migrar workloads críticos em ≤9 meses estimada e validada anualmente.

### 7.4 Avaliação de Outros Vendors Críticos

| Vendor | Função | Risco | Mitigação |
|--------|--------|-------|-----------|
| AWS | Compute, storage | Vendor lock-in parcial | Multi-cloud com GCP |
| Oracle | ERP fonte on-prem | Falha técnica legacy | HVR CDC redundante, batch fallback |
| SAP | ERP fonte | Performance, custo licença | SLT dedicado, monitor contínuo |
| HashiCorp Vault | Secrets mgmt | Vendor lock-in | Migração possível para AKeyless/Thycotic |
| Datadog/Splunk | Observabilidade | Custo elevado | Avaliação anual de alternativas (Grafana Cloud) |

---

## 8. Compliance Roadmap

### 8.1 Timeline de Certificações

| Marco | Certificação | Status | Deadline | Owner |
|-------|--------------|--------|----------|-------|
| **Q1 2027** | SOC 2 Type I — Security, Availability, Confidentiality | Planejado | Mar/2027 | CISO + GRC Lead |
| **Q3 2027** | ISO/IEC 27001:2022 — Certificação inicial | Planejado | Set/2027 | CISO |
| **Q1 2028** | SOC 2 Type II (período de observação 6-12 meses) | Planejado | Mar/2028 | CISO + Auditoria |
| **Q3 2028** | ISO/IEC 27701:2019 — Privacy Management | Planejado | Set/2028 | DPO + CISO |
| **Q1 2029** | PCI-DSS 4.0 (se aplicável a dados de pagamento processados na plataforma) | TBD | Mar/2029 | CISO |
| **Q3 2029** | Adequação avançada LGPD (programa Art. 50) | Planejado | Set/2029 | DPO |

### 8.2 Detalhamento por Framework

#### SOC 2 Type II

- **Escopo**: Plataforma Lakehouse (Snowflake + S3/GCS + integrações).
- **Trust Service Criteria**: Security (obrigatório), Availability, Confidentiality.
- **Período de observação**: mínimo 6 meses (target 12 meses para Type II robusto).
- **Auditor**: Big 4 ou Tier 1 boutique (Schellman, A-LIGN).
- **Custo estimado**: USD 80k-150k para Type II.
- **Automação**: Vanta ou Drata para coleta contínua de evidências.

#### ISO/IEC 27001:2022

- **Escopo**: Toda a operação de dados do Lakehouse + infraestrutura.
- **Statement of Applicability (SoA)**: 93 controles da Annex A.
- **Risk Treatment Plan**: derivado desta matriz de riscos.
- **Auditor certificador**: Bureau Veritas, TÜV ou DNV.
- **Certificação válida**: 3 anos com surveillance audits anuais.
- **Custo estimado**: BRL 250k-400k para certificação inicial.

#### ISO/IEC 27701:2019

- **Extensão** do ISO 27001 para PII.
- **PIMS** (Privacy Information Management System).
- **Alinhado** com LGPD, GDPR.
- **Pré-requisito**: ISO 27001 vigente.

#### LGPD (Autoavaliação ANPD)

- **Não é certificação**, mas sim programa de adequação.
- **Adoção de programas de governança** conforme Art. 50 LGPD gera atenuante de multas.
- **Documentação**: RIPD, política de privacidade, DPO ativo, gestão de incidentes.

### 8.3 Investimento Anual Estimado

| Item | Custo Anual (BRL) |
|------|-------------------|
| Auditoria externa (SOC 2 + ISO) | 800k - 1.2M |
| GRC tool (Vanta/Drata) | 150k - 300k |
| Consultoria jurídica especializada | 200k - 400k |
| Pentest externo + red team | 300k - 500k |
| Treinamento (LGPD, segurança, ISO) | 100k - 200k |
| DPO + equipe privacidade (2 FTEs) | 600k - 900k |
| **Total** | **~2.1M - 3.5M** |

---

## 9. Risk Register Maintenance

### 9.1 Ferramenta

- **Plataforma primária**: **Jira Software** com project dedicado "RISK" + app **Risk Register by DEIS** ou **Jira Service Management** com asset "Risk".
- **Custom fields**: Probability, Impact, Score, Category, Owner, Mitigation Status, Next Review Date, KRI Status.
- **Integração**: links bidirecionais com Confluence (detalhes de mitigação), Datadog/Grafana (KRIs), AWS Security Hub (riscos técnicos).
- **Alternativa complementar**: GRC tool dedicada (Vanta, Tugboat, ServiceNow GRC) para compliance reporting.

### 9.2 Workflow Jira

```
Created → Triaged → Risk Assessment → Mitigation Planning → 
In Treatment → Monitoring → Closed / Accepted / Transferred
```

- **Status**: Open, In Treatment, Monitoring, Accepted, Closed, Escalated.
- **Prioridade**: Bloco visual conforme score (Critical = vermelho, High = laranja, Medium = amarelo, Low = verde).
- **SLA**: Riscos Critical com atualização semanal; High quinzenal; Medium mensal.

### 9.3 Campos Obrigatórios por Risco

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| Risk ID | Texto (R-XX) | Sim |
| Title | Texto | Sim |
| Description | Texto longo | Sim |
| Category | Select (RC, TS, OP, FI, LG, DA) | Sim |
| Probability (1-5) | Number | Sim |
| Impact (1-5) | Number | Sim |
| Score (calc) | Auto | Sim |
| Level (calc) | Auto | Sim |
| Response | Select (Avoid, Reduce, Transfer, Accept) | Sim |
| Mitigation Summary | Texto | Sim |
| Mitigation Owner | User picker | Sim |
| Linked Controls | Multi-link (CIS, ISO, SOC2) | Não |
| KRIs | Texto | Sim |
| Next Review Date | Date | Sim |
| Status | Select | Sim |
| Linked Incidents | Multi-link | Não |
| Linked Audits | Multi-link | Não |
| Risk Treatment Plan (RTP) | Attachment (PDF/Confluence link) | Sim se score ≥15 |

### 9.4 Processo de Atualização

| Trigger | Ação | SLA |
|---------|------|-----|
| Incidente grave | Criar/atualizar risco relacionado | T+1 dia |
| Mudança regulatória | Risk Lead avalia impacto | T+5 dias |
| Novo vendor onboarding | Risk assessment + entry no register | T+10 dias |
| Mudança arquitetural | Revisão de riscos TS e DA | T+10 dias |
| Resultado de pentest/auditoria | Novo risco ou atualização | T+5 dias |
| Mudança de mercado (M&A vendor) | Risk Lead avalia FI | T+15 dias |
| Revisão periódica | Update de probabilidade/impacto | Mensal/Trimestral |

### 9.5 Reporting

| Relatório | Frequência | Audiência | Conteúdo |
|-----------|------------|-----------|----------|
| Risk Dashboard | Tempo real (Confluence + Jira) | Equipe técnica | Todos os riscos, status, KRIs |
| Top Risks Report | Semanal | Comitê diretivo | Critical + High com mudanças |
| Risk Heatmap | Mensal | C-Level | Visualização matriz P×I |
| Compliance Posture | Mensal | CISO + DPO | Status controles, gaps |
| Board Risk Report | Trimestral | Conselho | Top 10, KRIs, budget |
| Annual Risk Assessment | Anual | Todos stakeholders | Revisão completa, novas categorias |

### 9.6 Governança do Risk Register

- **Steering Committee**: CTO, CISO, DPO, CRO, Head of Data.
- **Decision rights**: aceitação de risco com score ≥15 requer aprovação do Steering Committee.
- **Bypass**: nenhum risco Critical pode ser aceito sem plano de mitigação aprovado.
- **Audit trail**: todas as mudanças no register logadas (who, when, what) para auditoria.
- **Retention**: histórico de riscos retido por 7 anos para compliance e lições aprendidas.

---

## Anexo A — Glossário

| Termo | Definição |
|-------|-----------|
| BACEN | Banco Central do Brasil (referência regulatória de mercado de pagamentos e meio de pagamento; pode ser relevante conforme produtos financeiros ofertados) |
| ANPD | Autoridade Nacional de Proteção de Dados |
| BYOK | Bring Your Own Key (criptografia) |
| CIS | Center for Internet Security (controls) |
| CDC | Change Data Capture |
| DPA | Data Processing Agreement |
| DPO | Data Protection Officer (Encarregado LGPD) |
| DSAR | Data Subject Access Request |
| GRC | Governance, Risk, Compliance |
| IRP | Incident Response Plan |
| KRI | Key Risk Indicator |
| LGPD | Lei Geral de Proteção de Dados (Lei 13.709/2018) |
| MSSP | Managed Security Service Provider |
| PII | Personally Identifiable Information |
| RIPD | Relatório de Impacto à Proteção de Dados |
| RPO | Recovery Point Objective |
| RTO | Recovery Time Objective |
| SIEM | Security Information and Event Management |
| SLA | Service Level Agreement |
| WORM | Write Once Read Many |

---

## Anexo B — Referências Normativas

- LGPD — Lei 13.709/2018
- ISO/IEC 27001:2022
- ISO/IEC 27701:2019
- ISO 31000:2018
- NIST SP 800-30 Rev. 1
- CIS Controls v8
- SOC 2 (AICPA Trust Services Criteria)
- Resolução CMN 4.658/2018 (referência de mercado; verificar aplicabilidade conforme arranjo de pagamento)
- Resolução BCN 4.893/2021 (referência de mercado; verificar aplicabilidade)
- Resolução BCB 89/2021 (Política de Cibersegurança — referência para fornecedores de meios de pagamento)
- PCI-DSS 4.0
- Marco Civil da Internet — Lei 12.965/2014

---

**Última revisão**: 2026-09-05
**Próxima revisão obrigatória**: 2026-12-05 (trimestral)
**Aprovado por**: Comitê de Risco e Compliance
**Classificação**: Interno — Confidencial
