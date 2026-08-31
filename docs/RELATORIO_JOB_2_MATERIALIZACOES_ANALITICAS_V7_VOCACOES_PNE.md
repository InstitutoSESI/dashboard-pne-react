# Relatório consolidado — Job 2 Materializações analíticas V7 Vocações × PNE

## 1. Classificação e objetivo

Classificação obrigatória: `DATA_LOGIC`, com impactos subordinados em infraestrutura de materialização, QA e documentação; escopo territorial `RS`, exclusivamente Vale do Sinos. O objetivo foi executar sequencialmente os subjobs 2A–2E, produzir artefatos analíticos reprodutíveis e parar antes do Job 3. Nenhuma fórmula, fonte, ano, indicador público, narrativa ou metodologia existente foi alterado.

## 2. Preflight e estado inicial

Foram lidos `AGENTS.md`, `README.md`, `PRODUCT.md`, `docs/ARQUITETURA.md`, `docs/OPERACAO.md`, o contrato V7, relatórios dos Jobs 0 e 1, planos, auditoria, inventário e matrizes de cobertura/prontidão. O repositório estava em `main`, HEAD `4b62e17ff8`, cinco commits à frente de `origin/main` e com alterações anteriores de outro trabalho. Essas alterações foram preservadas.

O preflight confirmou dez municípios canônicos no Vale do Sinos, PostgreSQL SESI e CEI disponíveis em modo somente leitura, arquivos locais do Novo CAGED, suplementos locais de cursos técnicos 2023–2025, ponte curso–CBO R6 e evidência R6 de mobilidade/demografia. A tabela CEI `public.estoque_emprego_faixa_etaria` foi classificada como proibida por defeitos estruturais.

Uma primeira execução após a troca da ponte falhou no 2D por coluna de rótulo inexistente. A falha ocorreu antes da promoção, preservou o lote anterior e descartou o staging. Após corrigir a projeção codificada e validar o 2D isoladamente, o fluxo integral foi reexecutado com sucesso. Esse evento comprovou o comportamento fail-closed.

## 3. Job 2A — trajetória escolar e condições

Estado `READY`: quatro artefatos, 13.637 linhas. O bloco cobre rendimento, distorção, turmas, adequação docente, INSE, SAEB/IDEB e condições censitárias. Comparações são recompostas por componentes, ponderadas por estudantes ou apresentadas como distribuição municipal; média regional simples não foi usada. Água potável, biblioteca e quadra ficaram indisponíveis no recorte 2025, sem conversão para zero. Detalhes: `docs/RELATORIO_JOB_2A_TRAJETORIA_ESCOLAR_CONDICOES_V7_VOCACOES_PNE.md`.

## 4. Job 2B — trabalho jovem

Estado `READY`: quatro artefatos, 338.008 linhas. RAIS 2019–2025 representa estoque formal; CAGED local 2020–2025 representa fluxo. Foram consumidos 211 arquivos CAGED, 2026 parcial foi excluído e dois arquivos opcionais `FOR` vazios foram registrados. Não houve claim de primeiro emprego. As 52 células hiperfinas com ajuste negativo são correções rastreáveis; nenhum agregado mensal de admissão/desligamento ficou negativo. A fonte defeituosa proibida não foi usada. Detalhes: `docs/RELATORIO_JOB_2B_TRABALHO_JOVEM_V7_VOCACOES_PNE.md`.

## 5. Job 2C — EJA

Estado `READY`: dois artefatos, 166 linhas. A série integrada cobre 2014–2025; a relação entre público potencial residente e matrícula por localização da escola está ancorada em 2022. As fórmulas canônicas foram preservadas, inclusive `diferenca_distribuicao_pp` armazenada como fração 0–1 e denominador zero como `null`. Detalhes: `docs/RELATORIO_JOB_2C_EJA_V7_VOCACOES_PNE.md`.

## 6. Job 2D — ocupações e formação

Estado `READY`: cinco artefatos, 486.512 linhas. A oferta técnica detalhada cobre 2023–2025; o painel ocupacional RAIS cobre 2019–2025. A projeção versionada preserva exatamente os 115 pares e 22 cursos não mapeados da ponte R6, com nomes de curso e ocupação derivados das fontes oficiais. Em 2025, 39 de 44 cursos regionais e 12.664 de 13.945 matrículas foram cobertos. Nenhuma claim de adequação ou suficiência foi materializada. Detalhes: `docs/RELATORIO_JOB_2D_OCUPACOES_FORMACAO_V7_VOCACOES_PNE.md`.

## 7. Job 2E — demografia, rede e mobilidade

Estado `READY`: cinco artefatos, 1.782 linhas contabilizáveis mais um JSON contextual. Coortes e rede cobrem 2014–2025; mobilidade reutiliza a evidência preliminar de 2022 da R6, sem destino; o cenário 2026–2030 é envelhecimento mecânico da coorte de 2025, explicitamente não uma previsão. Detalhes: `docs/RELATORIO_JOB_2E_DEMOGRAFIA_REDE_MOBILIDADE_V7_VOCACOES_PNE.md`.

## 8. Matriz de fontes

| Fonte | Uso | Período | Acesso/lente | Classe ou limite |
|---|---|---|---|---|
| PostgreSQL SESI | 2A, 2C e 2E | 2011–2025 conforme tabela | transação `READ ONLY`; escola ou residência conforme variável | observado/estimado conforme fonte |
| PostgreSQL CEI, RAIS | 2B e 2D | 2019–2025 | transação `READ ONLY`; local de trabalho | estoque formal observado |
| Novo CAGED local | 2B | 2020–2025 | 211 arquivos locais; local de trabalho | fluxo formal; ajustes preservados |
| Suplementos Censo Escolar | 2D | 2023–2025 | arquivos/ZIP locais; localização da escola | oferta e matrícula observadas |
| Ponte curso–CBO R6 | 2D | oferta 2025 | projeção codificada versionada | correspondência normativa, não aderência |
| Evidência R6 | 2E | 2022/2024 e séries de contexto | fixture versionada | mobilidade preliminar, destino indisponível |
| Registros RS | todos | vigente | códigos IBGE textuais | identidade canônica |

Não houve consulta a API, FTP, BigQuery, Supabase ou internet.

## 9. Manifestos e reprodutibilidade

O manifesto operacional completo está em `.tmp/vocacoes-pne/v7-job2/manifest.json`, contém schemas de artefato, grãos, períodos, lentes, unidades, regras de agregação, inventário de fontes e validações. Seu SHA-256 é `28ca53d020af6eb8168eef15af2a7752034c149ada942b4323756e55ef8f8d85`.

O manifesto compacto versionado está em `data_pipeline/manifests/vocacoes-pne-v7-job2-release.json`, SHA-256 `81296d78b97b0418b89d2ed7b2bb353eedf0c10fda3f7af62570cfc33c537f51`. Ele registra os 20 hashes e os fingerprints essenciais sem versionar os 840.105 registros grandes.

A serialização CSV gzip fixa `mtime=0`, ordena dados de forma estável e explicita `null`. O manifesto não usa relógio operacional. A repetição integral produziu o mesmo hash e terminou com `promotion: unchanged`, provando idempotência byte a byte.

## 10. Fórmulas e escalas

- Razões: `numerador / denominador`; denominador zero → `null`.
- Agregação regional: soma de numeradores sobre soma de denominadores, ponderação explícita ou distribuição municipal; nunca média simples silenciosa.
- EJA: participações municipal/regional, diferença `matrículas - público` em fração 0–1 e matrículas por mil.
- CAGED: `MOV + FOR - EXC`; saldo mensal `admissões - desligamentos`.
- Oferta/ocupação: somas preservadas por lente; matrículas repetidas em pares curso–CBO são não aditivas.
- Cenário mecânico: coorte fixa de 2025 envelhecida até o ano-alvo, dividida pela matrícula-base de 2025 apenas como contexto.
- Arredondamento ocorre somente em apresentação/serialização; decisões usam valores brutos. Percentuais acima de 100% não são truncados.

## 11. Cobertura e períodos

| Subjob | Cobertura municipal | Período principal | Saídas |
|---|---:|---|---:|
| 2A | 10; RS até 497 conforme fonte | 2011–2025 variável | 4 |
| 2B | 10; comparação estadual no CAGED | RAIS 2019–2025; CAGED 2020–2025 | 4 |
| 2C | 10 | EJA 2014–2025; demanda 2022 | 2 |
| 2D | 10 | cursos 2023–2025; ocupações 2019–2025 | 5 |
| 2E | 10 | coortes/rede 2014–2025; mobilidade 2022; cenário 2026–2030 | 5 |

## 12. Identidade e região

O código IBGE textual de sete dígitos é a única chave municipal. Não houve `int`, `float`, `Number`, `parseInt`, join por nome, diretório por slug nem uso de `public/data/municipios_index.json` para definir universo. O Vale do Sinos usa os dez códigos de `config/regions/rs.json`, incluindo Nova Santa Rita `4313375`, validados contra `config/municipalities/rs.json`.

## 13. Tabela de estados

| Subjob | Estado | Artefatos | Razão resumida |
|---|---|---:|---|
| 2A | `READY` | 4 | séries e comparações sem média simples |
| 2B | `READY` | 4 | estoque e fluxo formal completos no recorte; 2026 excluído |
| 2C | `READY` | 2 | fórmulas EJA e escala fracionária preservadas |
| 2D | `READY` | 5 | oferta, ocupações e ponte materializadas sem claim de adequação |
| 2E | `READY` | 5 | coortes, rede, cenário mecânico e mobilidade com caveats |

Não há subjob `BLOCKED` nem lote parcial promovido.

## 14. QA e testes executados

- Materialização integral: 2A→2E `READY`, 20 artefatos, 840.105 linhas.
- Reexecução integral idempotente: `promotion=unchanged`, mesmo manifesto e mesmos hashes.
- Verificação independente de SHA-256: 20/20 artefatos sem divergência.
- Teste direto do 2D após correção: 337 + 30 + 486.005 + 138 + 2 linhas, sem erro.
- Pytest focado final: 40 testes e 7 subtestes aprovados, cobrindo Job 2, EJA, registro municipal e configuração estadual.
- `npm run check:fast`: aprovado; inclui typecheck, lint, verificação do compilador Vocações e `build:app` app-only.
- `git diff --check`: aprovado no encerramento.

Não foram enfraquecidos ou removidos testes.

## 15. Hashes e contagens relevantes

| Item | Valor |
|---|---|
| Artefatos | 20 |
| Linhas contabilizáveis | 840.105 |
| Estados `READY` | 5 |
| Arquivos finais no diretório | 22 (20 artefatos + manifesto + estado) |
| Manifesto operacional | `28ca53d020af6eb8168eef15af2a7752034c149ada942b4323756e55ef8f8d85` |
| Estado de execução | `fd01f128773367598a1b36d190439029a91af1757bce6c6807cd53ded1869425` |
| Manifesto versionado | `81296d78b97b0418b89d2ed7b2bb353eedf0c10fda3f7af62570cfc33c537f51` |
| Inventário CAGED | `4a62c4586ffd910c3cb78434a55870547a71f0ff229df25a5794892708ed94b2` |
| Ponte R6 fonte/projeção | `e11a6d1…21cf8f` / `bb3d437e…ee97e0` |
| Evidência R6 | `bee5d4b7…1754b8` |

Os hashes individuais estão no manifesto versionado e nos relatórios de cada subjob.

## 16. Efeito sobre dados públicos

Nenhum. `public/data` não foi lido como fonte do universo, não foi gerado, editado, promovido ou removido. Não houve alteração em UI, runtime, cards, narrativa, fixtures públicas ou publicação.

## 17. Arquivos criados, alterados, removidos ou movidos

Foram criados 13 arquivos finais:

- núcleo, executor, contrato, projeção curso–CBO, manifesto de release e testes em `data_pipeline`;
- cinco relatórios de subjob, este relatório consolidado e `docs/LACUNAS_REAIS_V7_VOCACOES_PNE.md`.

Nenhum arquivo preexistente foi alterado por este Job 2; nenhum arquivo do repositório foi removido ou movido. Os 22 arquivos grandes/operacionais permanecem somente em `.tmp/vocacoes-pne/v7-job2`. Stagings de tentativa foram transitórios e não fazem parte da entrega.

## 18. Estado do Git

Branch `main`, HEAD `4b62e17ff8`, `ahead 5`, worktree sujo. Os 13 arquivos do Job 2 estão não rastreados e não houve `git add`, commit, push, pull, stash, reset ou troca de branch. Modificações e arquivos não rastreados anteriores — contrato do produto, `package.json`, fixtures, linter, UI e materiais dos Jobs 0/1/V6 — foram preservados e não apropriados por esta entrega.

## 19. Lacunas e riscos pendentes

As lacunas completas estão em `docs/LACUNAS_REAIS_V7_VOCACOES_PNE.md`. As principais são: componentes censitários auxiliares indisponíveis; ausência de primeiro emprego/informalidade; diferença territorial em EJA; cinco cursos regionais não mapeados; ponte normativa sem validade de aderência; mobilidade sem destino e preliminar; cenário mecânico não preditivo; nascimentos observados somente até 2024.

Essas lacunas não impedem a materialização, mas impedem claims públicos mais fortes sem nova fonte e novo contrato metodológico.

## 20. Confirmações finais e limite de escopo

- Banco: usado apenas para leitura, em transações PostgreSQL `READ ONLY`; zero escrita.
- Rede/internet/API/FTP/BigQuery: não usados.
- Supabase: não usado.
- Build completo: não executado. Apenas `build:app` app-only dentro de `check:fast`.
- Dados públicos: inalterados.
- Publicação/narrativa/UI/runtime: inalterados.
- Job 3: não iniciado.
- Commit/push/PR: não realizados.

O Job 2 está concluído e a execução parou no limite solicitado.
