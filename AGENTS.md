# AGENTS.md

Estas instruções se aplicam a todo o repositório. Instruções específicas do usuário têm precedência. Antes de trabalhar, consulte também [README.md](README.md), [docs/ARQUITETURA.md](docs/ARQUITETURA.md) e [docs/OPERACAO.md](docs/OPERACAO.md) conforme o escopo.

## 1. Propósito da plataforma

Esta é uma plataforma municipal de acompanhamento educacional dos 497 municípios do Rio Grande do Sul, voltada principalmente a gestores municipais. Priorize dados oficiais, rastreabilidade da origem ao artefato publicado e uma experiência de impressão confiável. Alagoas e outros estados estão fora do escopo atual; não generalize o sistema para novos estados sem pedido explícito.

## 2. Fontes canônicas de identidade

- O código IBGE textual com sete dígitos é a única identidade municipal.
- `config/states/rs.json` é a configuração estadual ativa.
- `config/municipalities/rs.json` é o registro municipal canônico.
- Slugs são metadados públicos de rota, nunca identidade. A compatibilidade dos 182 slugs em `config/compatibility/education-municipality-routes/rs.json` é um contrato ativo.
- Nomes servem somente para apresentação e validação.
- `public/data/municipios_index.json` é uma projeção publicada, não uma fonte canônica de identidade.

Nunca converta código IBGE com `int`, `float`, `Number` ou `parseInt`; não faça join por nome; não crie diretório municipal por slug; não use o índice público para definir o universo municipal.

## 3. Regras de dados

- Zero observado, `null`, `unavailable`, `suppressed` e `not_applicable` têm significados diferentes e devem permanecer distintos.
- Denominador zero produz `null`.
- Arredonde somente na apresentação ou serialização final; cálculos e decisões usam o valor bruto.
- Não limite percentuais acima de 100% sem um contrato metodológico explícito.
- Preserve fontes oficiais e sua proveniência. Não remova bruto, manifesto ou hash sem uma rota de recuperação comprovada.
- Nenhuma fórmula, fonte, ano, indicador, schema ou metodologia pode ser alterada em tarefa visual ou de infraestrutura.
- Não edite manualmente `public/data`; dados publicados devem ser produzidos pelo fluxo controlado correspondente.

## 4. Classificação obrigatória da tarefa

Antes de modificar arquivos, classifique a tarefa e registre a classificação no andamento como uma destas categorias:

- `UI_ONLY`;
- `DATA_PRESENTATION`;
- `DATA_LOGIC`;
- `SOURCE_REFRESH`;
- `PIPELINE_INFRASTRUCTURE`;
- `DOCUMENTATION_ONLY`;
- `CLEANUP`;
- `MULTISTATE`.

A classificação define comandos, validações e limites. Se a tarefa cruzar categorias, use a classificação de maior impacto e explicite os domínios envolvidos.

## 5. Fluxo eficiente por tipo de alteração

### UI_ONLY

Use `npm run typecheck`, `npm run lint`, `npm run check:fast` e testes de UI, roteamento ou domínio afetado. Antes de alterar a interface, consulte `docs/DESIGN.md`, reutilize tokens e componentes existentes e mantenha exceções no CSS do domínio correspondente. Preserve foco, hover e estados de carregamento, erro, vazio e indisponibilidade. Não percorra `public/data` em tarefas visuais. Não execute `update:data`, `update:education-data`, acesso ao banco, build completo nem `validate:details` integral, salvo quando o contrato de dados também mudar.

Entradas usuais: UI compartilhada em `src/app`, `src/components` e `src/styles`; Educação em `src/features/education`; Financeiro em `src/features/municipal-finance`; Diagnóstico em `src/features/diagnostic`; PNE em `src/pages`, `src/components/Indicator*` e `src/utils/pne*`.

### DATA_PRESENTATION

Quando apenas textos, labels, cards ou visualizações mudarem sem alterar JSON, execute testes frontend focados. Não regenere dados, não acesse banco e não mude metodologia.

### DATA_LOGIC

Durante o desenvolvimento, execute testes Python focados no cálculo e, quando existir, um probe dirigido por município e indicador. Não rode update completo a cada tentativa. Ao final, execute a suíte do domínio, valide o contrato e faça uma única atualização controlada somente se ela for necessária e autorizada.

O `.ignore` exclui dados e artefatos volumosos das buscas comuns. Em tarefa de dados, pesquise a árvore necessária explicitamente, por exemplo com `rg --no-ignore "termo" public/data data_pipeline/data`.

### EDUCAÇÃO

Prefira:

```powershell
npm run update:education-data:incremental
```

Uma mudança real em fonte, código, contrato, runtime, configuração ou output causa full run automaticamente. Um hit válido reutiliza os 499 outputs. O fluxo tradicional continua disponível por `npm run update:education-data`, e a medição sem skip por `npm run update:education-data:fingerprint-shadow`.

No pipeline geral, prefira `npm run update:data:education-incremental`. Não use `npm run update:data` tradicional sem justificativa: os demais domínios continuam integrais e somente Educação possui skip incremental hoje.

### SOURCE_REFRESH

Separe aquisição, normalização, validação, materialização e promoção. Nunca acesse rede nem execute `--apply` sem instrução explícita. Preserve fonte bruta, URL, hash, data de referência, layout ou versão, manifesto e evidência de cobertura.

### PIPELINE_INFRASTRUCTURE

Preserve cálculos, contratos, outputs e comportamento fail-closed. Valide primeiro as unidades de infraestrutura alteradas e só depois os fluxos integrados pertinentes. Não use uma mudança de infraestrutura para regenerar dados sem necessidade e autorização.

### DOCUMENTATION_ONLY e CLEANUP

Valide links, comandos e paths citados. Em limpeza, prove ausência de consumidores antes de remover e preserve arquivos ignorados que sustentem reprodução, testes ou recuperação. Documentação e limpeza não autorizam update de dados, banco, rede ou build completo.

### MULTISTATE

O único estado ativo é o RS. Implementação para outro estado exige solicitação explícita, configuração, registro municipal, contratos de compatibilidade e testes próprios; não copie pressupostos do RS silenciosamente.

### BUILD E DEPLOY

Update de dados não executa build. `npm run build` é explícito e copia `public/data`; `npm run build:app` serve à validação leve, e `npm run check:fast` usa esse build app-only. Execute build completo somente antes de deploy, preview de release ou por pedido explícito.

## 6. Publicação transacional

Toda publicação nova ou modificada deve:

1. gerar em staging;
2. validar integralmente;
3. falhar com código não zero em qualquer erro;
4. promover somente depois da validação;
5. usar escrita atômica;
6. preservar arquivos idênticos;
7. possuir rollback quando administrar vários arquivos;
8. não alterar `public/data` durante a geração;
9. não publicar lote parcial;
10. não substituir falha por JSON vazio.

O comportamento deve ser fail-closed. Preserve a implementação transacional existente da Educação.

## 7. Incremental e fingerprints

- Fingerprints devem cobrir fonte, código, contrato, runtime, configuração e outputs.
- Qualquer incerteza causa full run.
- O task state é local e ignorado: não o versione e não apague o task state incremental em limpezas comuns.
- Timestamp operacional não equivale a alteração analítica.
- Somente Educação é incremental hoje. Não crie comando genérico que sugira incrementalidade em todos os domínios.

## 8. Testes em camadas

### Durante a edição

Execute o teste focado e, quando aplicável, typecheck e lint.

### Encerramento da implementação

Execute a suíte do domínio, `npm run check:fast` e `git diff --check`.

### Antes do commit

Execute `npm run check:hygiene`, a validação específica e os testes focados finais. Isso não autoriza criar o commit.

### Antes do merge em main

Execute o gate completo uma única vez, quando o escopo justificar. Não rode centenas de testes após cada pequena alteração. Na entrega, explique quais suítes não têm relação com o escopo e por que não foram executadas.

Não trate avisos de análise estática como erros automaticamente: preserve entradas dinâmicas, contratos, tipos compartilhados e símbolos exercitados por testes. Nunca apague nem enfraqueça teste ou script de validação para fazer uma suíte passar.

## 9. Git e trabalho paralelo

- Nunca use `git add -A` quando houver trabalho paralelo; prepare paths explícitos.
- Não use stash, reset ou restore sobre mudanças de outro agente e não troque a branch de um checkout em uso.
- Use worktrees distintos para pipeline e UI em paralelo e preserve status sujo pertencente a outro trabalho.
- Não faça commit, push ou pull request sem solicitação.
- Não reescreva o histórico Git.
- Em limpeza, nunca use `git clean -fdx`.

## 10. Arquivos que não devem ser removidos automaticamente

Preserve automaticamente:

- `public/data` e `data_pipeline/data`; fontes não reproduzíveis não devem ser movidas para outro repositório;
- `config/states/rs.json`, `config/municipalities/rs.json` e a configuração de compatibilidade dos slugs;
- `education_task_fingerprint.py`, `education_transactional_publication.py`, `pipeline_profiling.py`, `state_config.py`, `municipality_registry.py` e `education_municipality_routes.py`;
- arquivos `sync_*`, manifests, fontes brutas e snapshots;
- `.env` local e task state incremental;
- contratos PNE e `pne2026-diagnostic-v3`;
- qualquer arquivo apenas porque o nome contém `legacy`, `v1`, `v2` ou `v3`.

## 11. Critério de remoção

Um arquivo só pode ser apagado após prova positiva de ausência de consumidor estático, tardio, dinâmico ou humano; ausência de comando, subprocesso, path e documentação; ausência de contrato público; ausência de função de recuperação, rollback ou produção de snapshot; ausência de valor metodológico ou histórico; e aprovação dos testes relacionados após a remoção. Ausência de import não basta.

## 12. Formato da entrega

Toda tarefa de dados deve terminar informando:

- objetivo;
- fontes;
- fórmulas preservadas ou alteradas;
- arquivos alterados, criados, removidos ou movidos;
- efeito sobre dados públicos;
- testes executados;
- hashes ou contagens relevantes;
- estado do Git;
- pendências;
- confirmação de uso ou não de banco, rede e build completo.
