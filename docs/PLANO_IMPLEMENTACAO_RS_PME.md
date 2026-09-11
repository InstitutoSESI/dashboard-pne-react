# Plano de implementação — nova publicação pública RS / PME

Status: E0–E9 concluídas e verificadas localmente em 2026-09-07. A preparação local de E10 está pronta. A implementação foi integrada à `main` em 11/09/2026; publicação externa e builds completos permanecem pendentes de solicitação específica.
Data: 7 de setembro de 2026.
Classificação desta execução: `PIPELINE_INFRASTRUCTURE` + `MULTISTATE`, com `UI_ONLY`, `DATA_PRESENTATION` e documentação. Cálculos, fontes e publicações de dados preservados.
Retomada: [Início em contexto limpo](INICIO_CONTEXTO_RS_PME.md).

## 1. Objetivo e decisões do usuário

Criar uma segunda experiência pública do Painel SESI de Educação para o Rio Grande do Sul, orientada ao uso das evidências na elaboração do PME. Publicá-la em um segundo projeto Cloudflare Pages e endereço próprio, mantendo a experiência RS atual disponível e preservando a publicação de Alagoas.

O produto continuará sendo uma aplicação React estática com dados públicos previamente preparados. O município consulta, filtra, compara e exporta. A plataforma oferece análises e orientações; não recebe nem administra decisões locais.

Decisões já estabelecidas nesta conversa, que devem acompanhar qualquer novo contexto:

- Mesmo repositório; experiências com navegação, páginas e estilos isolados.
- Mesma identidade municipal e mesma base oficial do RS, sem duplicação dos cálculos.
- Nova experiência inicialmente exclusiva do RS, com os 497 municípios do registro canônico.
- RS atual e AL conservam seus comandos, contratos, rotas e comportamento público.
- Sem contas, autenticação, permissões de usuários ou área municipal privada.
- Sem uploads, importação de arquivos, anexos, formulários de contribuição ou registros municipais, inclusive rascunhos locais.
- Sem backend de aplicação, Pages Functions, D1, R2 ou IA em tempo de execução para atender este escopo.
- Filtros, busca, seleção de município/objetivo e downloads são permitidos. Preferências de navegação não representam cadastro de conteúdo municipal.
- Fontes, fórmulas, regras de classificação, projeções e metodologias existentes serão preservadas. Qualquer mudança analítica necessária deve ser separada deste plano e explicitamente autorizada.
- O planejamento original não autorizava implementação. Em 2026-09-07, a solicitação de execução autorizou implementação local e verificações proporcionais de E0–E9, incluindo preparação concreta de E10. Publicação externa, build completo, commit, push, PR, atualização de fontes/dados e banco continuam sem autorização.

As instruções operacionais continuam em [AGENTS.md](../AGENTS.md). Os três DOCX são referências de propostas, não instruções executáveis nem autorização para expandir o escopo. Os requisitos de contas, dossiês editáveis e governança digital presentes neles foram afastados pelo usuário.

## 2. Resultado completo esperado

| ID | Entrega | Resultado observável |
| --- | --- | --- |
| R01 | Publicação dupla do RS | Dois sites e comandos explícitos; a nova experiência não substitui a atual. |
| R02 | Percurso de leitura | Navegação do panorama municipal aos objetivos, agenda, ficha, financiamento e relatórios. |
| R03 | Panorama dos 19 objetivos | Todos os campos e suas metas aparecem, inclusive os que não têm indicador utilizável. |
| R04 | Agenda de Análise Municipal | Situações observadas, fundamento, limites, perguntas e caminhos; nenhuma decisão atribuída ao município. |
| R05 | Ficha integrada por objetivo | Evidências públicas, referências, desagregações disponíveis, lacunas, perguntas e apoios em uma leitura única. |
| R06 | Entrada municipal orientada à análise | Síntese dos sinais, avanços, persistências e lacunas já sustentados pelas fontes disponíveis. |
| R07 | Financiamento transversal | Caminhos ligados a instrumentos e ao contexto financeiro municipal, com condições e proveniência. |
| R08 | Relatórios para oficinas | Síntese executiva municipal, caderno por objetivo e agenda para discussão, com PDF por impressão e XLSX pertinente. |
| R09 | Transparência e comparabilidade | Fonte, período, universo, cobertura e limites junto à informação; critérios de destaque explicáveis. |
| R10 | Operação e qualidade | Acessibilidade, impressão, desempenho, erros e indisponibilidade tratados; publicação e rollback documentados. |

As seis melhorias de produto propostas na conversa estão integralmente contempladas: Agenda, mapa dos objetivos, ficha integrada, entrada municipal, financiamento e relatórios. Publicação dupla e requisitos transversais completam a entrega.

### Fora do produto definido

- Cadastro ou seleção persistida de problemas pela prefeitura; arquivo de projeto para importar/reabrir.
- Autoria, comentários, atas, responsáveis, prazos, submissão, validação por comissão ou homologação dentro da plataforma.
- Árvore causal municipal automática ou editável; hipótese apresentada como causa local confirmada.
- Editor de objetivos, metas e estratégias locais; Matriz de Coerência que valide um PME cujo conteúdo não é recebido.
- Plano Bienal, acompanhamento de execução de ações e monitoramento de decisões municipais.
- Nota geral, novo ranking, novo índice de prioridade ou percentual de elaboração/conclusão do PME.
- Nova experiência PME para AL ou qualquer outra UF sem solicitação própria.
- Novo catálogo integral de estratégias nacionais como requisito automático. As relações necessárias serão curadas com fonte; não se promete cobertura das 372 estratégias citadas nos DOCX.

Pode existir um roteiro metodológico público de conferência para utilização fora da plataforma, sem preenchimento ou validação online. Essa é a adaptação da proposta de coerência ao escopo público.

## 3. Base observada e pontos de reaproveitamento

Referência da inspeção: commit `909e858a5bd5b9b4865aad41eef0b8f153e44cb8`, branch `main`. Revalidar o estado do checkout na retomada; o plano não exige voltar a esse commit.

| Área existente | Entradas verificadas | Tratamento previsto |
| --- | --- | --- |
| Build estadual | [vite.config.js](../vite.config.js), [run-state-vite.mjs](../scripts/run-state-vite.mjs), [state-build-profile.mjs](../scripts/lib/state-build-profile.mjs), [state-public-assets.mjs](../scripts/lib/state-public-assets.mjs) | Compor perfil de experiência com perfil estadual validado. |
| Identidade e publicação RS | [publicação RS](../config/publications/rs.json), [registro RS](../config/municipalities/rs.json), [stateConfig.ts](../src/config/stateConfig.ts) | Preservar identidade IBGE, raiz pública e isolamento estadual. |
| Entrada e navegação atual | [main.jsx](../src/main.jsx), [App.tsx](../src/App.tsx), [navigationRegistry.ts](../src/app/navigationRegistry.ts), [appRoutes.ts](../src/app/appRoutes.ts) | Preservar experiência atual; selecionar entrada PME na compilação. |
| Município e loaders | [MunicipalityContext.tsx](../src/context/MunicipalityContext.tsx), [staticData.ts](../src/data/staticData.ts), [useInitialAppData.ts](../src/hooks/useInitialAppData.ts) | Reutilizar contratos; inspecionar acoplamentos de rota antes de reutilizar contexto visual. |
| Contrato PNE | [contrato canônico](../contracts/pne2026-goal-indicator-contract.json), [adaptador](../src/data/pne2026GoalIndicatorContract.js), [mapa legal](../src/data/pne2026LegalGoalIndicatorMap.js) | Derivar relações públicas e permissões de comparação. |
| Diagnóstico | [loader](../src/features/diagnostic/pne2026DiagnosticLoader.js), [documento público](../src/features/diagnostic/pne2026PublicDiagnosticV3.js), [apresentação](../src/features/diagnostic/diagnosticPresentation.js) | Usar resultados publicados e suas classificações, sem recalcular o diagnóstico. |
| Matriz | [MatrizPage.tsx](../src/features/matriz/MatrizPage.tsx), [loader](../src/features/matriz/pne2026MatrizLoader.js), [tipos](../src/features/matriz/matrizTypes.ts), [leituras](../src/features/matriz/matrizInsights.ts), [caminhos](../src/features/matriz/matrizFrentes.ts) | Reaproveitar evidências e conteúdo editorial; adaptar a linguagem somente no PME. |
| Educação e financiamento | [EducationPage.tsx](../src/features/education/EducationPage.tsx), [referências PME](../src/features/education/pmeReferenceTableViewModel.ts), [panorama financeiro](../src/features/municipal-finance/MunicipalFinancePanoramaPage.tsx) | Abrir detalhes neutros e contextualizados, com links municipais consistentes. |
| Exportação | [Relatório Técnico Municipal](../src/features/education/components/MunicipalTechnicalReport.tsx), [workbook](../src/features/education/municipalTechnicalReportWorkbook.ts), [XLSX](../src/features/education/municipalTechnicalReportXlsx.ts) | Reutilizar tecnologia de impressão/exportação e critérios de fonte, período e legibilidade. |
| Visual | [tokens](../src/styles/design-tokens.css), [PnePageHeader](../src/components/PnePageHeader.jsx), [ContentState](../src/components/ContentState.jsx), [LoadingState](../src/components/LoadingState.jsx) | Preservar identidade institucional e reutilizar componentes efetivamente neutros. |

Constatações relevantes:

- O contrato canônico inspecionado contém 73 metas, referências aos objetivos `1` a `19`, 59 indicadores e 59 relações. Isso não significa que cada objetivo tenha cobertura municipal completa, nem que haja um catálogo completo de títulos dos objetivos e estratégias.
- A Matriz possui manifesto de cobertura municipal e pode faltar para um município. Não é fonte para definir o universo de municípios nem condição para carregar o restante da experiência.
- Os nomes internos `causes`, `priorityGoals` e `goalsWithoutOwnCause` não autorizam a interface a afirmar causalidade ou validação municipal. Adaptar a apresentação sem modificar o contrato publicado.
- Há código de armazenamento local e workbook da matriz; a tela inspecionada não oferece um workspace conectado a essas funções. Não introduzir esse fluxo no PME.
- O diretório público `pne2026-diagnostic-v3` é um contrato de caminho. O código inspecionado aceita schema `pne2026-public-diagnostic-v4`. Não deduzir schema pelo nome do diretório, renomeá-lo ou congelar no plano hashes que possam mudar.
- `src/main.jsx` e `src/App.tsx` importam CSS global. Importar o aplicativo atual inteiro dentro do PME pode carregar menus, rotas e estilos indevidos.

## 4. Arquitetura da publicação

### 4.1 Dois eixos independentes

Manter `PLATFORM_STATE` como UF e introduzir `PLATFORM_EXPERIENCE` com valores `atual` e `pme`. Ausência da experiência significa `atual`; valor desconhecido é erro. Os comandos explícitos devem fixar ambos os valores para evitar contaminação por variável de ambiente herdada.

| UF | Experiência | Resultado |
| --- | --- | --- |
| RS | atual | Comportamento e publicação RS existentes. |
| RS | pme | Nova experiência pública. |
| AL | atual | Comportamento e publicação AL existentes. |
| AL | pme | Falha explícita antes de servir ou construir. |
| UF ou experiência inválida | qualquer | Falha explícita; sem fallback. |

Não usar `rs-pme` como UF, novo registro municipal ou nova raiz canônica de dados. Não acrescentar campos ao schema estadual para transportar preferências de interface. Compor a configuração de experiência separadamente.

### 4.2 Entradas, navegação e CSS

Estrutura implementada e verificada nesta execução:

- `scripts/lib/experience-build-profile.mjs`: validação da experiência e seleção da entrada.
- `src/config/experienceConfig.ts`: configuração de experiência validada para o frontend.
- `src/main-entry.ts`: entrada mínima comum, contendo somente a importação do alias de aplicação selecionado no build.
- `src/main-pme.tsx`: entrada selecionada exclusivamente pelo build PME.
- `src/experiences/pme/`: aplicação, shell, rotas, páginas, modelos de apresentação, catálogos e exportação PME.
- `src/experiences/pme/styles/`: estilos próprios, com escopo de classe da experiência.
- `scripts/checks/experience-profile.test.mjs` e testes PME: contratos e verificações novas.

A seleção da entrada usa alias estático do Vite: `index.html` aponta para `src/main-entry.ts`, cuja única importação é `@platform-entry`. O perfil validado configura `resolve.alias` exclusivamente para `src/main.jsx` em `atual` ou `src/main-pme.tsx` em `pme`. O grafo compilado parte de uma única aplicação, com declaração de tipos do alias e sem fallback de runtime. A entrada mínima não importa CSS, shell ou contexto de nenhuma experiência. Os três grafos app-only foram inspecionados nos testes; os builds completos continuam reservados à release autorizada.

A entrada atual deve continuar carregando somente sua aplicação; a entrada PME deve carregar somente seu shell e registro de navegação. Não selecionar a experiência por domínio, query string, hash ou armazenamento do navegador. Não importar os dois aplicativos para escolher um em runtime. Os testes precisam verificar o alvo real do alias, o módulo efetivamente carregado e o isolamento dos dois builds app-only; conferir apenas a variável de configuração não basta.

Compartilhar loaders, contratos, formatadores e componentes neutros. Reutilizar páginas de detalhe somente depois de separar dependências de navegação e estilos; não copiar todo o domínio. O novo bundle poderá conter detalhes compartilhados necessários, mas não deve incluir automaticamente o shell ou as páginas exclusivas da outra experiência.

Preservar rotas hash e aliases atuais. A experiência PME terá registro próprio e parâmetros explícitos de município, objetivo e filtros públicos. Links internos manterão o mesmo código IBGE textual; voltar, avançar, recarregar e abrir link direto devem funcionar. Persistência local, se necessária, ficará limitada à UF e ao código IBGE do contexto de navegação já contratado; usar namespace próprio quando o contrato atual carregar rotas incompatíveis. Objetivo e filtros públicos ficam na URL. Não persistir buscas livres, anotações, seleção de problemas, decisões ou outros conteúdos editáveis, nem restaurar rotas de outra experiência.

### 4.3 Comandos e saídas

Comandos existentes continuam com sua finalidade. Os comandos abaixo estão implementados em `package.json`; os que produzem release completa ainda não foram executados:

| Comando implementado | Finalidade / saída |
| --- | --- |
| `npm run dev:rs-pme` | Desenvolvimento RS/PME; porta 5189. |
| `npm run build:app:rs-pme` | Validação leve sem copiar dados; `dist/app-only-rs-pme`. |
| `npm run build:rs-pme` | Release local RS/PME; `dist/rs-pme`. |
| `npm run preview:rs-pme` | Servir release local existente; porta 4189. |
| `npm run build:cloudflare:rs-pme` | Fixar RS/PME e gerar `dist` no ambiente isolado do novo projeto Pages. |
| `npm run test:experience-profile` | Validação da matriz UF × experiência, CLI e seleção de entrada. |
| `npm run test:rs-pme` | Suíte focada de contratos de apresentação, rotas, catálogos e exportação PME. |
| `npm run test:rs-pme:e2e` | Fluxos de leitura, identidade, estados, exportação e impressão PME. |

A nova seleção não pode interferir no modo `app-only`. Builds locais de experiências diferentes usam saídas diferentes. Dois builds completos para o mesmo `dist` não podem executar simultaneamente no mesmo checkout.

### 4.4 Dados e operação

Cada build completo receberá a mesma raiz RS validada, servida em `/data` no seu próprio endereço. Nenhum site dependerá do domínio do outro para carregar dados. Uma atualização oficial poderá alimentar ambos os builds a partir da mesma versão validada; a atualização não é parte automática do desenvolvimento de UI.

Preferir modelos de apresentação derivados em memória dos documentos existentes e catálogos editoriais versionados no código. Não criar outro pipeline municipal nem materializar centenas de fichas se a composição no frontend resolver o requisito com desempenho adequado.

Se uma evidência concreta exigir novos artefatos derivados, abrir subetapa própria: contrato aditivo, entradas enumeradas, proveniência, staging, validação integral, promoção atômica com rollback e preservação de idênticos. Isolar os artefatos da experiência PME, sem alterar ou substituir JSONs existentes. Incerteza ou erro deve interromper publicação; jamais promover lote parcial ou JSON vazio.

## 5. Contratos da nova leitura pública

### 5.1 Modelo de evidência e cobertura

Cada bloco deve referenciar, conforme disponível: código IBGE, objetivo, meta, indicador, relação canônica, valor bruto, unidade, período, fonte oficial, universo, recorte, estado do dado, limites e versão de origem. Preservar os campos existentes; o modelo PME é uma projeção, não novo cálculo oficial.

- Distinguir ausência de relação metodológica, ausência de observação municipal, supressão e não aplicabilidade.
- Preservar zero observado e os estados `null`, `unavailable`, `suppressed` e `not_applicable`.
- Respeitar `canDistance`, `canStatus`, `canProjection`, relações ocultas e complementares. Uma relação ausente não ganha permissões por default no adaptador PME.
- Comparar somente unidades, universos, métodos e períodos compatíveis segundo os contratos existentes. Quando faltarem garantias, contextualizar lado a lado com ressalva ou omitir a comparação calculada.
- Desagregações só aparecem quando já forem públicas e metodologicamente utilizáveis. Não inferir bairro, escola, grupo ou rede inexistente nas fontes.
- Um campo sem dados continua no panorama. Indisponibilidade não demonstra ausência de problema.

Não inventar um escore de cobertura por objetivo. Preferir contagens descritivas com base explícita: metas com relação utilizável, relações com observação, indisponíveis, suprimidas e não aplicáveis. Os rótulos resumidos de cobertura devem separar vínculo metodológico de disponibilidade da observação; não afirmar acompanhamento integral do objetivo apenas por haver um indicador.

### 5.2 Agenda e síntese municipal

- Consumir classificações e sinais publicados; não recalcular prioridade, gravidade, causalidade ou projeção.
- A Matriz, quando disponível, enriquece a Agenda com verificações e caminhos. Sem ela, a Agenda pode apresentar resultados do diagnóstico com origem explícita e sem inventar causas/caminhos municipais.
- Falha de integridade na Matriz deve aparecer como erro daquele módulo. Não mascarar como ausência de dado; os módulos independentes podem continuar exibindo suas próprias fontes válidas.
- Dentro dos agrupamentos, preferir ordem canônica de objetivos/metas. Se reaproveitar ordenação analítica existente, explicar a origem; não criar pontuação escondida.
- Destaques da Home usam regras determinísticas e documentadas sobre informações já publicadas. Limitar a quantidade visível é permitido com acesso ao conjunto completo; o limite não define o universo analítico.
- Mostrar avanços e persistências apenas com séries ou leituras históricas existentes e compatíveis. Uma observação isolada não demonstra tendência.
- A ausência de um cartão, inclusive por limites da Matriz original, não equivale a ausência de sinal, causa ou questão municipal.

### 5.3 Ficha integrada e linguagem

Modelo comum para os 19 objetivos, com aprofundamento proporcional à cobertura:

1. Pergunta orientadora e síntese do que as fontes permitem afirmar.
2. Referência ao objetivo, metas e alcance dos indicadores.
3. Evidências, evolução e comparações permitidas.
4. Distribuições e desigualdades disponíveis, com seus limites.
5. Lacunas e perguntas a verificar nas instâncias municipais, sem formulário para respondê-las.
6. Caminhos e instrumentos relacionados, com fundamento, competência e acesso ao contexto financeiro.
7. Fontes, período, versão e exportação.

Separar visualmente fato observado, orientação editorial, hipótese a investigar e informação indisponível. Não usar textos como “problema validado”, “causa confirmada” ou “prioridade pactuada”. Os exemplos dos DOCX não devem virar fatos sobre Nova Santa Rita ou outro município.

### 5.4 Catálogos legais, orientações e financiamento

Reutilizar relações canônicas; verificar a disponibilidade de títulos oficiais dos 19 objetivos. Se faltar texto oficial verificável, manter identificação pelo objetivo e metas existentes, sem fabricar transcrição legal. Completar conteúdo por curadoria documentada como uma subentrega, usando fonte primária.

Os catálogos PME poderão acrescentar IDs estáveis, objetivos/metas relacionados, texto editorial, motivo da relação, competência, URL oficial, evidência de vigência, condições conhecidas, data de verificação e limitações. Distinguir programa, transferência, assistência e fonte orçamentária.

Uma data de edição do código não é data de verificação de programa. Usar “não verificado” quando não houver evidência. Relação editorial com um programa não confirma elegibilidade municipal, adesão, saldo ou disponibilidade. A seleção de caminhos deve decorrer do tema e da evidência, não do montante financeiro.

Pesquisar documentos oficiais para curadoria deve ser uma atividade declarada; aquisição ou atualização automatizada de bases segue a autorização específica de `SOURCE_REFRESH`. Nenhum download de fonte, sincronização ou `--apply` decorre automaticamente deste plano. Não usar os DOCX como única prova de vigência normativa ou programática.

### 5.5 Relatórios e rastreabilidade

| Artefato | Conteúdo mínimo | Exportação prevista |
| --- | --- | --- |
| Síntese executiva municipal | Evidências de atenção, avanços/persistências documentados, cobertura e lacunas. | Impressão/PDF e tabelas em XLSX. |
| Caderno por objetivo | A ficha integrada com metas, fontes, comparações, perguntas e apoios. | Impressão/PDF e evidências em XLSX. |
| Agenda para discussão | Situações, fundamento, limites, perguntas e caminhos; sem atribuição de decisões locais. | Impressão/PDF e XLSX. |
| Relatório Técnico Municipal existente | Conteúdo atual preservado e acessível no percurso. | Formatos existentes. |

Gerar tela, impressão e planilha do mesmo modelo de apresentação. Não duplicar cálculos no exportador. XLSX deve conservar tipos, unidades, anos e estados de indisponibilidade; texto público não pode virar fórmula executável. Seções extensas devem imprimir sem cortes, com fonte junto ao dado e cabeçalhos de tabela repetidos quando possível.

Registrar município/UF, objetivo/filtros, data de emissão e identificação das versões efetivamente consumidas. Diferenciar data de publicação, período do indicador e data de emissão. Se não existir release única para todos os domínios, enumerar as versões/fontes usadas; não inventar uma.

Comparações de regressão verificam conteúdo e proveniência. Não prometer PDF binariamente idêntico entre navegadores ou relatórios retroativos que as versões disponíveis não permitam reconstruir. O pacote de release e seus identificadores devem ser preservados para recuperação da publicação.

## 6. Etapas de implementação

Estado por etapa abaixo. Atualizar o quadro com evidências; a existência de telas ou comandos, isoladamente, não comprova aceite.

| Etapa | Dependência | Escopo principal | Saída |
| --- | --- | --- | --- |
| E0 — concluída | Nenhuma | Inventário e baseline | Estado inicial, acoplamentos e casos de referência registrados no log. |
| E1 — concluída localmente | E0 | Publicação dupla | Seleção estática de experiência e builds app-only isolados verificados. |
| E2 — concluída localmente | E1 | Shell e navegação PME | URLs próprias, filtros, teclado e troca municipal verificados. |
| E3 — concluída localmente | E1 | Contratos de apresentação e catálogos | Estados, permissões, comparabilidade e proveniência testados. |
| E4 — concluída localmente | E2 + E3 | Panorama dos objetivos | 19 campos e 73 metas, incluindo ausência de indicador. |
| E5 — concluída localmente | E2 + E3 | Agenda de Análise | Classificações publicadas, limites, perguntas e critério visível. |
| E6 — concluída localmente | E4 + E5 | Fichas e financiamento | Séries, recortes da Matriz, hipóteses, instrumentos e financeiro integrados. |
| E7 — concluída localmente | E4 + E5 + E6 | Entrada municipal | Síntese, destaques e leituras históricas rastreáveis. |
| E8 — concluída localmente | E5 + E6 + E7 | Relatórios | Três materiais PDF/XLSX e Relatório Técnico Municipal preservado. |
| E9 — concluída localmente | E1–E8 | Aceite integrado | Regressões, acessibilidade, impressão, exportações e documentação verificadas; evidências abaixo. |
| E10 — preparação local pronta | E9 + autorização de publicação | Pages e operação | Ficha concreta e gate de paridade prontos; projeto/domínio/deploy e smoke remoto pendentes. |

### E0 — Retomada e baseline

Classificação: `DOCUMENTATION_ONLY`, com inspeções de implementação sem mutação.

- Ler este plano, AGENTS e documentos canônicos; comparar o HEAD atual com a referência sem resetar o checkout.
- Verificar alterações concorrentes, comandos e estrutura. Registrar somente diferenças que afetem o plano.
- Preparar branch de desenvolvimento com prefixo `codex/` em checkout seguro. Não trocar branch de um checkout em uso; usar worktree quando necessário.
- Garantir que plano, texto de início, instruções locais aplicáveis e fontes necessárias estejam no checkout escolhido. Arquivos não versionados não acompanham um worktree automaticamente.
- Inventariar a cobertura de cada bloco pelos contratos/loaders. Inspeção dirigida de dados, quando necessária, deve ter município/indicador e objetivo definidos; não fazer varredura de dados numa tarefa puramente visual.
- Usar Nova Santa Rita (`4313375`) como caso principal e Porto Alegre (`4314902`) como caso de maior volume, ambos confirmados no registro RS. Selecionar outros casos por condições de teste, sem presumir seus resultados.
- Registrar baseline de rotas, navegação, impressão e identidade nos perfis atuais com testes/fixtures existentes. Capturas visuais dirigidas quando ajudarem a detectar regressão.

Aceite: lacunas e pontos de extensão conhecidos; nenhuma alteração de fonte/dado público. Não repetir investigação completa dos DOCX se o plano e as referências forem suficientes.

### E1 — Perfil e build da nova experiência

Classificação: `PIPELINE_INFRASTRUCTURE` + `MULTISTATE`.

- Implementar a matriz UF × experiência, seleção de entrada, comandos e saídas da seção 4.
- Reutilizar validação estadual e cópia dos dados. Não alterar schemas de publicação, identidade ou diagnóstico.
- Garantir defaults e comandos antigos explícitos; preservar comportamento fail-closed e modo app-only.
- Criar testes com diretórios temporários/fixtures para validar perfil, CLI, entrada, segurança das saídas e isolamento de ativos.
- Documentar como executar RS atual, RS PME e AL lado a lado.

Aceite: combinações válidas e inválidas demonstradas; build leve PME independente; os testes de publicação e hospedagem existentes continuam válidos. A primeira validação de infraestrutura não exige regenerar dados nem executar release completo.

### E2 — Shell público e navegação

Classificação: `UI_ONLY` + `MULTISTATE` nas fronteiras compartilhadas.

- Criar shell PME com identidade SESI, tema claro, componentes neutros e estilos próprios.
- Percurso inicial: panorama municipal, objetivos do PNE, Agenda de Análise, evidências/indicadores, financiamento e relatórios. Fichas são acessadas a partir dos objetivos e da Agenda.
- Implementar rotas hash e links para detalhes, preservando município, objetivo e filtros pertinentes. Reusar detalhes atuais somente sem importar seu shell completo.
- Tratar nenhum município selecionado, carregamento, vazio, indisponibilidade e erro de integridade.
- Inspecionar os hooks/contextos compartilhados para evitar leitura ou escrita de rotas da outra experiência.

Aceite: navegação por teclado, voltar/avançar/recarregar/link direto e troca de município funcionam; nenhuma conta, campo de contribuição, upload ou workspace foi introduzido.

### E3 — Evidências, cobertura e conteúdo editorial

Classificação: `DATA_PRESENTATION`; curadoria e eventuais artefatos novos devem declarar seu domínio adicional antes de alteração.

- Criar adaptadores puros e testáveis entre os contratos existentes e os modelos PME.
- Definir proveniência por bloco, cobertura metodológica e disponibilidade da observação separadamente.
- Catalogar questões orientadoras, referências e caminhos com IDs e fontes. Priorizar reaproveitamento; registrar lacuna editorial quando não houver relação verificada.
- Preservar a lista completa de objetivos e metas canônicos e permissões de inferência.
- Enumerar dependências obrigatórias e enriquecimentos opcionais. Matriz ausente não bloqueia diagnóstico/indicadores válidos; erro de integridade não recebe fallback silencioso.

Aceite: fixtures demonstram dados disponíveis, zero, nulo, supressão, não aplicabilidade, ausência de relação e comparações incompatíveis; nenhuma fórmula ou JSON existente foi alterado.

### E4 — Panorama dos 19 objetivos

Classificação: `UI_ONLY` + `DATA_PRESENTATION`.

- Criar mapa dos 19 campos e página de objetivo com metas e evidências associadas.
- Manter filtros transversais por tema/etapa/modalidade quando houver metadados; não substituir a estrutura de objetivos por esses filtros.
- Exibir informações disponíveis, cobertura parcial e lacunas com linguagem consistente, sem nota de completude do PME.
- Permitir aprofundamento em indicadores e ficha, com fonte e período visíveis.

Aceite: 19 objetivos e 73 metas reconciliados com a versão canônica inspecionada; nenhum campo desaparece por não ter observação; sem contagens duplicadas por relações muitos-para-muitos.

### E5 — Agenda de Análise Municipal

Classificação: `UI_ONLY` + `DATA_PRESENTATION`.

- Criar a nova Agenda a partir das classificações existentes e adaptar conteúdo da Matriz quando publicado.
- Cada situação responde: o que se observa, por que examinar, o que limita a leitura, o que discutir e quais caminhos estão relacionados.
- Explicar origem e critério dos destaques. Manter acesso aos demais objetivos e informações; não instituir limite analítico de três cartões.
- Preservar a Matriz de Prioridades e seus textos/rotas na experiência atual.

Aceite: município com Matriz e município sem Matriz têm comportamentos corretos; falha do manifesto aparece como erro identificável; hipóteses não são confirmadas por associação ou sinal adverso.

### E6 — Fichas integradas e financiamento transversal

Classificação: `UI_ONLY` + `DATA_PRESENTATION`, com curadoria de conteúdo identificada.

- Implementar o modelo de ficha da seção 5.3 para todos os objetivos; profundidade varia com a evidência, sem fabricar conteúdo.
- Integrar séries, recortes, notas e referências existentes; expandir detalhes progressivamente.
- Ligar orientações a competências, programas/instrumentos e páginas financeiras municipais pertinentes.
- Acrescentar vigência, condições conhecidas e verificação do conteúdo quando houver fonte; marcar claramente o que permanece não verificado.
- Disponibilizar roteiro metodológico de discussão/conferência como leitura pública, sem editor de PME.

Aceite: percorrer de um sinal à evidência, limitação, pergunta e apoio sem perder o município; não inferir elegibilidade/saldo a partir da existência de um programa; um objetivo sem dados ainda tem referência e lacuna explícitas.

### E7 — Entrada municipal orientada à análise

Classificação: `UI_ONLY` + `DATA_PRESENTATION`.

- Criar Home PME com síntese municipal, atalhos e próximos passos de leitura.
- Mostrar sinais, avanços, persistências e lacunas apenas quando sustentados; reutilizar modelos de E3–E6.
- Publicar a explicação dos critérios de destaque e acesso à visão completa.
- Manter introdução institucional adequada antes da seleção do município e acesso ao conjunto de informações públicas.

Aceite: destaque rastreável ao dado e à regra; nenhum ranking novo, tendência inventada ou estado de trabalho da comissão. A Home atual permanece funcional.

### E8 — Relatórios e oficina

Classificação: `UI_ONLY` + `DATA_PRESENTATION`.

- Implementar síntese executiva, caderno por objetivo e agenda para discussão.
- Reaproveitar modelos de tela, impressão/PDF pelo navegador e tecnologia XLSX existentes.
- Permitir selecionar escopo público de exportação; não receber conteúdo externo.
- Incluir cabeçalho municipal, filtros, períodos, fontes, limites, emissão e versões.
- Manter acesso ao Relatório Técnico Municipal sem mudar suas fórmulas ou conteúdo por efeito colateral.

Aceite: valores e estados iguais na tela e no XLSX; conteúdo impresso legível, sem cortes e com fontes; download não exige conta e não envia dados a serviço externo. DOCX não é obrigatório neste escopo.

### E9 — Aceite integrado e documentação

Classificação: domínios alterados em E1–E8, com `MULTISTATE` na regressão das fronteiras comuns.

- Executar a matriz de verificações da seção 7, sem repetir suítes já aprovadas com insumos inalterados.
- Verificar visualmente as telas, larguras desktop/tablet, teclado, foco, contraste e impressão; respeitar o objetivo de acessibilidade do produto.
- Carregar somente o município e os dados necessários, usar cache dos loaders e carregamento sob demanda; não baixar os 497 municípios para montar a Home.
- Verificar que módulos/estilos exclusivos PME não entraram no aplicativo atual e que o PME não carrega o shell atual. Componentes deliberadamente compartilhados são permitidos.
- Atualizar README, arquitetura, operação e hospedagem com comandos efetivamente implementados, estado dos dados, limites e recuperação.
- Preparar pacote de release e uma ficha concreta de configuração do novo Pages para a etapa de publicação.

Aceite: nenhum requisito R01–R10 pendente na implementação local; riscos, evidências e eventual bloqueio externo de publicação registrados. Uma primeira fatia navegável não encerra o plano completo.

### E10 — Publicação independente no Cloudflare Pages

Executar somente quando a publicação externa for autorizada. A falta dessa autorização não bloqueia E0–E9.

- Confirmar como o projeto atual é publicado, repositório, branch de produção e endereço. Essa configuração real não foi inspecionada no planejamento; o repositório descreve o fluxo esperado.
- Preparar novo projeto RS/PME no mesmo repositório, comando `npm run build:cloudflare:rs-pme` e saída `dist`. Nome do projeto e domínio serão definidos no momento da publicação.
- Durante o desenvolvimento, usar branch própria no novo projeto. Preservar a configuração de produção atual; configurar previews/build watch paths quando pertinentes, sem excluir alterações de dependências compartilhadas.
- Depois da estabilização, ambas as experiências podem ser produzidas da mesma branch por comandos distintos. Integrar código não precisa disparar produção automaticamente: revisar os controles de deploy existentes.
- Antes da release, executar builds completos das experiências pertinentes uma vez. Comparar o conjunto e hashes dos dados RS entregues aos dois sites; verificar isolamento AL quando a fronteira compartilhada mudou.
- Publicar primeiro no endereço Pages do novo projeto; associar subdomínio institucional posteriormente, se solicitado. O site continuará público, sem login.
- Fazer smoke test de município, 19 objetivos, Agenda, ficha, dados, links e impressão no novo endereço, além de verificar o endereço atual.
- Registrar projeto, endereço, commit, comandos, versão/manifestos dos dados e identificadores de deploy.
- Conservar o deploy anterior do novo projeto para rollback. Em falha, retornar somente o projeto afetado; não sobrescrever dados nem reconfigurar o site atual como mecanismo de recuperação.

Aceite: dois endereços RS operacionais e independentes; publicação antiga preservada; recuperação do novo projeto documentada. Link entre as experiências é opcional e não precisa alterar o site atual para concluir a nova publicação.

## 7. Verificação proporcional

### Comandos existentes confirmados na preparação

`npm run check:fast` já inclui typecheck, lint, `check:vocacoes-pne-compilador` e build app-only. Executar typecheck/lint separadamente durante edição quando útil; não repetir por ritual após o mesmo `check:fast` aprovado.

| Mudança | Verificações existentes pertinentes | Complemento a criar |
| --- | --- | --- |
| Perfil/build | `test:state-publication`, `test:multistate-hosting` | `test:experience-profile`; seleção de entrada e saídas. |
| Shell/rotas | `test:app-routing`, `test:municipality-identity`, `test:ui-architecture` | Rotas e navegação PME, persistência compatível e isolamento de CSS. |
| Leitura PNE/Agenda | `test:diagnostic`, `test:matriz`, `test:data-sources` | Adaptadores, cobertura, ausência da Matriz e regras de destaque. |
| Educação/relatórios | `test:education` | Conteúdo dos três artefatos, estados e paridade de exportação. |
| Contexto financeiro | `test:municipal-finance`, `test:data-sources` | Relações editoriais, fonte/data e ausência de promessa de recurso. |
| Contratos legais compartilhados | `check:pne-contract` quando seus consumidores/artefatos forem afetados | IDs e projeção dos 19 objetivos/73 metas. |
| Encerramento de etapa implementada | Suíte do domínio, `check:fast`, `git diff --check` | `build:app:rs-pme` e testes PME pertinentes. |
| Antes de commit autorizado | `check:hygiene` e validação de escopo | Reutilizar resultados ainda válidos. |
| Release autorizada | Builds completos pertinentes e smoke test | Paridade de dados RS e validação do novo endereço. |

Os comandos `dev:rs`, `dev:al` e `dev:rs-pme` usam respectivamente as portas 5187, 5188 e 5189. `test:rs-pme:e2e` reutiliza o servidor PME em 5189 ou inicia um Vite temporário em 5197; `PME_E2E_BASE_URL` fixa outro endereço local. O runner encerra apenas o servidor que iniciou. Os E2E atuais continuam com seus próprios contratos de endereço.

Não executar atualização de dados, banco, build completo, `validate:details` integral ou toda a suíte Python em edição visual. Os cálculos, aquisição e publicação Python não mudam neste plano. Se surgir mudança real nesses domínios, reclassificar e executar testes específicos antes de qualquer fluxo integrado autorizado.

### Casos obrigatórios de aceite

- RS atual, RS PME e AL atual; rejeição de AL PME e experiência inválida.
- Nova Santa Rita e município de maior volume; caso sem Matriz publicado selecionado por evidência ou simulado por fixture.
- Nenhum município selecionado; troca rápida entre municípios sem exibir dado do município anterior.
- Um dos 19 objetivos sem indicador; indicador com zero; nulo; suprimido; não aplicável; relação apenas complementar ou oculta.
- Comparação incompatível de ano, unidade ou universo; ausência de série para tendência.
- Matriz ausente versus manifesto inválido: mensagens e comportamento distintos.
- Metas/indicadores relacionados a múltiplos blocos sem duplicar totais nem confundir IDs.
- Programa sem verificação recente ou elegibilidade conhecida; nenhuma promessa de recurso.
- Link direto, recarga, voltar/avançar, filtro, impressão e exportação conservando escopo municipal.
- Teclado, foco, texto sem depender só de cor, leitura com zoom e impressão de tabelas longas.
- Leitura da Home sem carregar a base inteira de municípios; ausência de chamadas externas de IA, coleta de contribuições ou upload.
- Aplicativos atuais continuam com suas rotas e conteúdo, inclusive os 182 slugs históricos de compatibilidade RS.

## 8. Dependências, paralelismo e retomada

E1 define as fronteiras antes de E2 e E3. E2 e E3 podem avançar em paralelo depois do contrato de identidade/experiência estar estável. E4 e E5 também podem ser divididas por arquivos. E6 integra os modelos; E7 e E8 reutilizam essa composição. E9 e E10 são integradoras e sequenciais.

Seguir a skill `quality-efficient-orchestration` disponível no ambiente: delegação seletiva, um escritor por arquivo, tarefas independentes e modelos nativos proporcionais à dificuldade. Não fixar o modelo principal, não criar tarefas na interface para subtarefas, não invocar serviços externos. A divisão deve reduzir duplicação, não obrigar paralelismo.

Cada entrega parcial deve registrar: requisito/etapa, arquivos alterados, decisões, testes executados, efeito sobre dados públicos, estado Git, riscos e próximo passo. Para tarefas de dados, completar também o formato de entrega exigido em AGENTS.

Ao interromper ou mudar de contexto, atualizar a tabela da seção 6 e acrescentar abaixo um registro curto com caminhos/commit de referência. Preservar pendências; não recomeçar etapas já aceitas.

### Registro de execução

#### Aceite local de 2026-09-07

Classificação: `PIPELINE_INFRASTRUCTURE` + `MULTISTATE`, com `UI_ONLY`, `DATA_PRESENTATION` e documentação. Nenhuma fórmula, fonte, schema analítico, metodologia ou publicação de dados foi alterada. O objetivo implementado é uma segunda experiência pública de consulta do RS, isolada por entrada de build e reutilizando as publicações oficiais existentes.

| Requisito | Resultado local e evidência |
| --- | --- |
| R01 | CLI fixa UF/experiência; rejeita AL/PME e perfis inválidos. Teste de isolamento compila e inspeciona RS atual, RS PME e AL atual em memória. Ficha Pages preparada; os dois endereços RS só serão atestados em E10. |
| R02 | Shell próprio, seis destinos principais, transparência e contexto por IBGE textual na URL. E2E verifica link direto, recarga, voltar/avançar, filtros e troca rápida Nova Santa Rita → Porto Alegre sem resultado atrasado de outro município. |
| R03 | 19 objetivos e 73 metas do contrato 1.9.0. Objetivos sem observação continuam presentes; cobertura de relações difere de disponibilidade. Títulos e perguntas editoriais estão identificados como tais. |
| R04 | Agenda reproduz classificações/leituras autorizadas e mostra o critério de até quatro destaques, limites, perguntas e caminhos da meta correspondente. Nenhuma classificação vira decisão municipal ou causa confirmada. |
| R05 | Fichas integram metas, fontes, períodos, universos, comparações compatíveis, séries anuais publicadas e recortes/hipóteses da Matriz. Comparações estadual e entre pares são validadas independentemente por ano, unidade e universo. |
| R06 | Entrada municipal combina cobertura, situações da Agenda, leituras históricas existentes e lacunas. Espera ou falha do diagnóstico não vira contagem zero; não se calcula ranking ou tendência nova. |
| R07 | Dez leituras financeiras existentes preservam valor, exercício, etapa e fonte. Instrumentos vêm da Matriz e de catálogos existentes, com condições, versão e verificação atual não confirmada; não há inferência de elegibilidade ou soma de previsões com execução. |
| R08 | Síntese, caderno e agenda compartilham o mesmo modelo de tela/impressão/XLSX. Três downloads reais validados por ZIP/XML, oito abas, IBGE textual, números brutos, estados distintos e ausência de fórmulas executáveis. Relatório Técnico Municipal preservado com links opcionais do PME. |
| R09 | Transparência expõe critérios, fontes, períodos, universos, versões/hash e diferenças entre domínios. Matriz não publicada, manifesto inválido e diagnóstico com erro têm estados independentes. Fontes das séries não recebem identificador de release inventado. |
| R10 | E2E, testes de domínio, grafos de build, teclado/foco, 320–1440 px, texto a 200%, downloads e PDFs verificados. Requisições observadas são GET no mesmo origin e limitadas aos municípios selecionados; não há upload, conta, contribuição, armazenamento de trabalho ou IA. |

Testes e verificações executados, reutilizando resultados cujos insumos permaneceram iguais:

| Verificação | Resultado |
| --- | --- |
| `npm run test:rs-pme` | 34 testes: perfil (7), apresentação (7), rotas (5), relatório técnico (3), isolamento real (1), relatórios/financeiro (5), séries (4), preparação/paridade de release (2). |
| `npm run test:rs-pme:e2e` | 7 cenários integrados; inclui ausência/integridade da Matriz, diagnóstico com falha, seletor/URL, estados, financeiro, relatórios, fontes carregadas e reflow. |
| `test:state-publication`, `test:multistate-hosting` | 11 e 8 testes aprovados. |
| `test:app-routing`, `test:municipality-identity` | 20 e 18 testes aprovados; contrato dos 182 slugs RS preservado. |
| `test:diagnostic`, `test:matriz` | 27 e 49 testes aprovados, incluindo cobertura e validação fail-closed dos loaders existentes. |
| `test:education`, `test:municipal-finance`, `test:data-sources` | 71, 38 e 15 testes aprovados. |
| `check:pne-contract` | Artefatos legais byte a byte e 9 testes de paridade aprovados. |
| `test:ui-architecture`, `check:hygiene` | Aprovados; orçamento CSS global preservado, limites individuais para os dois novos arquivos de estilos. |
| `check:fast`, `build:app:rs-pme` | Typecheck, lint, projeção congelada de Vocações e builds app-only aprovados. |
| Python focado | `data_pipeline/tests/test_update_build_decoupling.py`: 18 aprovados usando o runtime local já existente; expectativas atualizadas para os comandos explícitos e o gate de compilador já vigente. |
| Smoke no navegador RS atual/AL atual | Aceguá (`4300034`) e Maceió (`2704302`): seleção e 19 seções do relatório técnico renderizadas; nenhum módulo PME ou erro de página não tratado. |
| `git diff --check` | Aprovado; nenhum conteúdo preparado no índice para commit. |
| Documentação | 61 links locais e 62 comandos npm conferidos nos seis documentos de implementação/operação; nenhum destino ou script ausente. |

Evidências visuais ficam em `.tmp/rs-pme` (ignoradas): capturas desktop, tablet e mobile, PDFs e XLSX reais. Caderno de Nova Santa Rita/objetivo 1: 12 páginas, 111.828 bytes; agenda municipal: 34 páginas, 287.507 bytes. Inspeção visual e extração de texto verificaram fontes, identificação municipal, tabelas longas com cabeçalho repetido, ausência de texto de carregamento e palavras dentro da página. Os relatórios aguardam os módulos e as séries terminarem antes de liberar a exportação.

Fontes consumidas: registro canônico RS; contrato legal e política de apresentação existentes; diagnóstico público vigente; Matriz opcional; índice municipal para séries; documentos/catálogo financeiros e catálogos de instrumentos já publicados. A curadoria de instrumentos conserva a data registrada na fonte (inclusive `2026-07-19` quando pertinente) e não declara verificação externa nova. O contrato contém 19 objetivos/73 metas; 39 metas têm relação pública neste modelo. Casos municipais verificados: Nova Santa Rita, 41 relações observadas; Porto Alegre, 49.

Referências de integridade preservadas:

- Diagnóstico/release: `fadcfff3fb2df31a2b967989d8a45023dde03d2f6db76a40cfbee77715e7d9fc`.
- Contrato PNE 1.9.0: `c9f4baaee43a7f105863a07bcac69d2f56a90095b75d0c7bcde25ca533fedab5`.
- Política de apresentação 1.7.0: `c330fb98c727dbb461b809a5f178f92ac73661ee3fe4e9c73cfb9b38ea9f1d3b`.
- `git diff --name-only -- public/data state-publications data_pipeline/data`: vazio. Não foi feita varredura ou regeneração geral de dados para a tarefa visual.

Arquivos criados: 29 arquivos em `src/experiences/pme` (aplicação, páginas, adaptadores, séries, relatórios e estilos); entradas `src/main-entry.ts`/`src/main-pme.tsx`, configuração/tipagem de experiência; perfil de build; testes PME/perfil e gate `scripts/checks/rs-experience-data-parity.mjs`; ficha `config/hosting/rs-pme-pages.json`. Arquivos alterados: `index.html`, `vite.config.js`, `package.json`, CLI estadual, adaptação opcional de links no relatório técnico compartilhado, verificações de hospedagem/higiene/arquitetura UI/desacoplamento de build e documentação canônica. Nenhum arquivo foi removido ou movido; `AGENTS.md` e os três DOCX são conteúdo preexistente transportado com o worktree, não novas alterações de produto.

Cuidados de reprodução neste checkout Windows:

- Dependências Node locais foram reutilizadas por junction. O cache Vite é separado por UF/experiência; o servidor permite a raiz do repositório e o diretório real de dependências para servir fontes, sem liberar a pasta pai inteira. Não houve instalação pela rede.
- `.gitattributes` fixa LF em fixtures/saídas textuais cujos hashes já eram contratuais. Nove arquivos tinham apenas CRLF introduzido pelo novo checkout; seus bytes foram reconciliados com o conteúdo de `HEAD`, sem regeneração ou mudança semântica. Git pode ainda indicá-los como modificados por normalização de EOL, embora o diff de conteúdo esteja vazio.
- O teste existente da Matriz depende de `.tmp/matriz/artefato/matriz-manifest.json`. Foi recuperada somente a cópia idêntica já existente no checkout original, hash `3d355221c1f2c4fe05214875260280255af40979d56ac824993154f1f136f782`, sem gerar ou publicar Matriz. Preservar esse apoio ignorado na retomada.

Limites e pendências: E10 externa ainda não executada. A [ficha do Pages](../config/hosting/rs-pme-pages.json) contém repositório verificado, nome proposto `painel-sesi-rs-pme`, comando e saída concretos; conta, projeto real, domínio, branch de produção e deploy ficam `null`. O gate de paridade foi testado com diretórios temporários, incluindo divergência e falha; comparar os artefatos RS reais exige a release completa autorizada. O bundle inicial PME ficou em aproximadamente 633 kB (156 kB gzip), com aviso Vite acima de 500 kB; financeiro, relatório técnico e XLSX são carregados sob demanda. No smoke de AL, o aplicativo atual registrou 404 do manifesto regional opcional de Vocações; esse consumidor e a publicação AL não foram modificados nesta tarefa, e o relatório técnico continuou funcional.

Não executados: atualizações de dados/fontes, banco, suíte Python integral, `validate:details` integral, builds completos e deploy. Os cálculos e pipelines de aquisição/materialização não mudaram; essas suítes/ações não seriam proporcionais nem autorizadas. Rede usada somente em loopback para os servidores locais e testes; nenhum serviço externo foi chamado. Não houve commit, push ou PR.

Estado Git de entrega: worktree `C:/Users/rnbirck/PROJETOS/DASHBOARDS/PNE-REACT-RS-PME`, branch `codex/rs-pme`, base `909e858a5`, alterações locais sem commit e índice sem conteúdo staged. O checkout original `PNE-REACT` permaneceu em `main`, no mesmo commit, com `AGENTS.md` e os cinco documentos preexistentes preservados. Retomar a partir deste worktree e deste registro; não reaplicar E1–E9 em `main` nem sobrescrever os documentos de planejamento antigos do checkout original.

#### Histórico da implementação e do planejamento

- E1: perfil `PLATFORM_EXPERIENCE` e alias estático implementados, defaults/CLI RS/AL preservados com experiência explícita. Comandos RS/PME de desenvolvimento, app-only, release e Pages preparados. Testes de perfil, publicação estadual e hospedagem multestado aprovados; teste com três grafos reais Vite app-only em memória confirma isolamento RS atual/RS PME/AL atual, sem cópia de dados. Builds `build:app` e `build:app:rs-pme` aprovados durante a integração; release completo não executado.
- E2–E8 em integração: shell PME, URL própria com código IBGE, panorama legal, Agenda, fichas, financiamento, transparência, síntese municipal e três modelos exportáveis implementados em `src/experiences/pme`. Relatório Técnico Municipal reutilizado com adaptação opcional de links e composição de dados preservada. Testes de rotas PME (5), composição do relatório e Educação (71) aprovados. Os testes de apresentação estão sendo ampliados durante revisão semântica, especialmente para comparações incompatíveis e independência dos módulos.
- Inspeção visual inicial: Chromium em `http://127.0.0.1:5189/#inicio?municipio=4313375`, 1440×1000, renderizou a entrada municipal sem erro de JavaScript. Artefato local ignorado `.tmp/rs-pme/municipal-home.png`. Isto não encerra o aceite: ainda faltam suíte E2E integrada, exportação real, impressão longa, larguras menores, regressões finais e documentação operacional. Nenhum requisito foi considerado concluído apenas por estar navegável.
- 2026-09-07, E0: criado worktree `C:/Users/rnbirck/PROJETOS/DASHBOARDS/PNE-REACT-RS-PME`, branch `codex/rs-pme`, a partir de `909e858a5`. A `main` original permanece na mesma branch, com `AGENTS.md` modificado e os cinco documentos não rastreados preservados. Plano, retomada e DOCX foram copiados para caminhos ausentes e conferidos por SHA-256; as instruções locais foram transportadas. Dependências Node locais reutilizadas por junction, sem instalação/rede.
- E0: leitura do plano e documentação canônica; inspeção dirigida de Nova Santa Rita (`4313375`) e Porto Alegre (`4314902`), confirmados no registro canônico. Diagnóstico ativo `fadcfff3fb2df31a2b967989d8a45023dde03d2f6db76a40cfbee77715e7d9fc`; respectivamente 41 e 49 relações com observação no modelo público. Contrato 1.9.0 preservado: 19 objetivos, 73 metas; não há catálogo autônomo de títulos oficiais de objetivos. Usar identificação numérica e temas editoriais explicitamente identificados.
- E0: baseline de rotas (20 testes), identidade municipal (18 testes) e arquitetura UI aprovados. Os loaders já distinguem Matriz não publicada (`municipality_not_published`) de ponteiro/manifesto/payload inválido. O contexto e as páginas existentes possuem acoplamentos de hash/CSS: o PME terá contexto de URL próprio; detalhes neutros serão reutilizados com fronteira explícita. Nenhum dado público alterado, banco/rede/build completo não utilizados.
- 2026-09-07: plano e instrução de retomada preparados. E0–E10 pendentes. Nenhuma implementação ou publicação executada.
- Validação do planejamento: revisão independente de arquitetura/escopo, conferência de 48 links locais, nomes dos comandos existentes e distinção dos comandos propostos, hashes das cópias DOCX e verificação de whitespace. `git diff --check` aprovado; sem testes de aplicação, banco, aquisição de fontes ou build, por se tratar somente de documentação.

## 9. Riscos e decisões que não precisam bloquear o início

| Questão | Tratamento |
| --- | --- |
| Novo domínio/nome do projeto | Resolver em E10; usar nome técnico provisório somente na preparação local. Não inventar URL publicada. |
| Configuração real do Pages atual | Inspecionar em E10 ou antes da primeira integração com Git remoto; não pressupor que push é inofensivo. |
| Matriz com cobertura menor que o RS | Tratar como enriquecimento opcional; usar diagnóstico válido e mostrar lacunas. |
| Texto legal/programático não disponível ou não verificado | Usar identificação/referência confirmada e marcar lacuna; organizar curadoria sem fabricar conteúdo. |
| Reuso de componentes com CSS/rotas globais | Compartilhar primitivas; extrair somente o necessário e testar os consumidores atuais. |
| Diferença de versão entre domínios/datas de publicação | Registrar versões efetivamente consumidas; evitar comparação de snapshots incompatíveis. |
| Alteração nova de fórmula, classificação ou fonte | Isolar a demanda e obter autorização específica; continuar etapas independentes. |
| Escopo crescendo para sistema de gestão do PME | Aplicar os limites da seção 1; os fluxos municipais dos DOCX não fazem parte da entrega. |

## 10. Fontes do plano

Documentos do usuário, lidos como propostas e reconciliados com suas restrições posteriores:

- [Visão Executiva](Visao_Executiva_Nova_Arquitetura_Painel_SESI_RS_ROTA_PME.docx): percurso, divulgação progressiva, evidências, artefatos e fronteiras de decisão.
- [Arquitetura Integrada do Piloto](Arquitetura_Integrada_Piloto_ROTA_PME_Nova_Santa_Rita.docx): 19 campos, conexão entre evidência e planejamento, prudência causal e financeira.
- [Especificação Funcional e Metodológica](Especificacao_Funcional_Metodologica_Painel_ROTA_PME.docx): especialmente experiência (§2), migração (§21), explicabilidade (§16), artefatos (§18) e decisões técnicas (§24); adaptados ao produto exclusivamente público.

As cópias em `docs` foram comparadas aos originais em `C:/Users/rnbirck/Downloads` e são idênticas. Hashes SHA-256 no momento da preparação:

| Documento | SHA-256 |
| --- | --- |
| Visão Executiva | `c6b584a97390b1fdb66989908230f16edae73b129857c8c42b6dbf6c01bc644b` |
| Arquitetura Integrada | `ba20472927a1b08db4d4a7cf5849c4aca35ca4deaff7fb323c8d0e1970c11e48` |
| Especificação Funcional | `67cac785000f697665f8ef74fa5e3d610dfea20913fca8dbbcae12d7ecc8d2ad` |

Documentação canônica: [README](../README.md), [Produto](../PRODUCT.md), [Arquitetura](ARQUITETURA.md), [Operação](OPERACAO.md), [Hospedagem multestado](HOSPEDAGEM_MULTIESTADO.md), [Metodologia](METODOLOGIA.md).

Documentação oficial da Cloudflare consultada na discussão que originou o plano:

- [Vários projetos ligados ao mesmo repositório](https://developers.cloudflare.com/pages/configuration/monorepos/).
- [Controles de publicação por branch](https://developers.cloudflare.com/pages/configuration/branch-build-controls/).
- [Domínios próprios](https://developers.cloudflare.com/pages/configuration/custom-domains/).

As definições reais de conta, projeto e domínio serão verificadas na etapa de publicação. O plano não declara que o novo site já existe.

## 11. Estado Git e transferência para contexto limpo

Antes da criação deste plano, o checkout já continha `AGENTS.md` modificado e os três DOCX em `docs` não rastreados. Essas alterações são preexistentes e devem ser preservadas. O planejamento acrescenta somente este arquivo e `docs/INICIO_CONTEXTO_RS_PME.md`, sem commit.

Abrir um novo contexto não exige apagar arquivos, limpar o checkout ou reverter alterações. Na mesma pasta, os dois documentos permanecem acessíveis. Em um worktree/checkout novo, arquivos não versionados não aparecem automaticamente. Antes de transferir, confirmar os caminhos absolutos de origem/destino, consultar o estado Git do destino e comparar existência e hash/conteúdo de cada arquivo. Copiar somente para caminho ausente; arquivo idêntico pode ser reutilizado. Se houver conteúdo divergente, interromper a cópia desse arquivo e reconciliar sua origem sem sobrescrever trabalho existente. Respeitar as instruções locais aplicáveis antes de começar. Não fazer commit para resolver isso sem solicitação.

O [texto de início](INICIO_CONTEXTO_RS_PME.md) é autocontido quanto ao objetivo e às restrições e aponta para este plano. Ele não cria tarefa, branch ou publicação automaticamente.

## 12. Rodada adicional de UX/UI — 07/09/2026

Classificação: `UI_ONLY` + `DATA_PRESENTATION`. A solicitação posterior do usuário prioriza a leitura municipal, aproxima o menu, seletor, cards e gráficos da experiência anterior e substitui a exposição de detalhes internos prevista nas primeiras etapas deste plano.

| Página | Revisão aplicada |
| --- | --- |
| Panorama municipal e entrada sem seleção | Menu lateral institucional, seletor no topo, três contagens úteis, destaques em duas colunas e melhor distribuição das leituras históricas e lacunas. |
| Objetivos do PNE | Todos os 19 objetivos e as 73 metas preservados; cards compactos e explicação simples da cobertura. |
| Ficha do objetivo | Texto legal e evidências com largura disponível; valor e período em destaque; método, comparações, perguntas e instrumentos organizados. Os dados de apoio da Matriz reutilizam seus rótulos públicos, sem protocolos ou dimensões internas. |
| Agenda de Análise | Situação, cuidados e perguntas mais fáceis de localizar; caminhos associados à meta e critérios descritos em linguagem municipal. |
| Evidências | Filtros e busca na mesma barra; códigos internos retirados; gráfico com escala, anos, pontos acessíveis por teclado e valores ao foco; tabela anual compacta ao lado no desktop. |
| Financiamento | Cards em duas colunas, números alinhados, fontes e etapas com nomes legíveis. Previsão, execução, exercícios e ressalvas continuam distintos. |
| Relatórios | Três escolhas diretas de material, cabeçalho compacto, resultados antes dos cuidados de leitura, tabela de apoio com cinco colunas e oito abas de XLSX com nomes públicos. |
| Relatório Técnico Municipal | Um único título, controles com espaçamento, tabelas curtas adaptáveis no celular e apenas uma versão do anexo por meio de apresentação. A impressão oculta controles e navegação. |
| Fontes e critérios | Fontes, períodos, disponibilidade, comparabilidade e orientações de consulta em linguagem pública. |

As fontes oficiais já consumidas — diagnóstico PNE, Matriz municipal, séries educacionais e dados financeiros — permanecem as mesmas. Nenhuma fórmula, ano, classificação, identidade, schema, valor bruto ou regra de disponibilidade foi alterada. O código IBGE continua textual nas rotas e na identificação do XLSX. As publicações de origem continuam com sua proveniência; tela, PDF e planilha não expõem identificadores de indicadores, campos de cálculo, protocolos, hashes ou caminhos internos. A troca do vocábulo “snapshot” por “levantamento” é apenas de apresentação.

Arquivos revisados nesta rodada: componentes e apresentações em `src/experiences/pme`, suas folhas de estilo, testes de relatórios/E2E e este registro. Foram criadas as folhas `pme-shell.css`, `pme-evidence.css`, `pme-history.css` e `pme-finance.css`. O componente compartilhado `MunicipalTechnicalReport.tsx` recebeu textos opcionais usados apenas pelo PME; os padrões de RS atual e AL atual foram preservados. Nenhum arquivo de fonte ou dado foi removido. Os limites anteriores de CSS total, CSS principal e relatório técnico foram mantidos; foram acrescentados tetos individuais para as folhas novas.

Verificação proporcional:

- `npm run test:rs-pme`: 35 testes aprovados, incluindo valores brutos, zero/nulo, exportação real de XLSX e isolamento dos três perfis no Vite.
- `npm run test:education`: 71 testes aprovados dos consumidores compartilhados.
- `npm run test:rs-pme:e2e`: 8 testes aprovados, incluindo as nove páginas, navegação, troca de município, falhas independentes, gráfico, materiais e responsividade.
- `npm run check:fast`, `npm run build:app:rs-pme`, `npm run check:hygiene`, arquitetura de UI e `git diff --check` aprovados. Ajustes finais de impressão tiveram nova inspeção visual e build app-only do PME.
- Revisão visual em desktop e celular, texto a 200%, detalhes das 19 fichas e gráficos em 1440/1920 px. Na amostra de Nova Santa Rita, o caderno do Objetivo 1 ficou com 10 páginas após retirar espaços indevidos entre blocos; Agenda e Relatório Técnico foram conferidos sem conteúdo fora das páginas. A tabela anual permanece no PDF mesmo quando oculta na tela.

Capturas, PDFs e resultados de inspeção estão em `.tmp/rs-pme`, como evidências locais ignoradas pelo Git. O aviso de tamanho de chunk do Vite permanece informativo; seus limites não foram desativados.

O trabalho permanece sem commit, push ou PR em `codex/rs-pme`, no worktree `PNE-REACT-RS-PME`. O checkout original foi preservado. Não houve alteração de `public/data` ou fontes brutas, acesso a banco, aquisição por rede externa, atualização de dados ou build completo. Suítes Python de aquisição/cálculo e gates integrais de publicação não se aplicam a esta rodada. A publicação externa da etapa E10 continua fora deste escopo.

## 13. Segunda rodada de UX/UI: apresentação e compactação — 07/09/2026

Classificação: `UI_ONLY` + `DATA_PRESENTATION`. A revisão atende ao pedido de uma home de apresentação, gráficos menores e melhor distribuição dos cards nas dez páginas do PME, com uso do skill de frontend-design.

- Nova página **Início** em `#apresentacao`, também exibida quando a URL não especifica página: apresenta a finalidade da plataforma, o conteúdo disponível e a entrada por município. A seleção conduz ao Panorama municipal; os links existentes em `#inicio` continuam válidos e o município permanece identificado pelo código IBGE textual.
- Evidências com uma área verde restrita ao valor, largura definida e texto em coluna própria. Cabeçalhos, metadados e espaçamentos ficaram menores; valores indisponíveis mantêm sua indicação específica e zero observado continua visível.
- Gráficos com altura de 232 px nas larguras verificadas, sem ampliação dos eixos em telas largas. A tabela de 2015–2025 cabe ao lado no desktop. A impressão usa proporção própria, preserva todos os pontos e mostra a tabela anual completa.
- Perguntas e hipóteses distribuídas lado a lado, sem repetir perguntas idênticas. Agenda com leitura, perguntas e caminhos em três colunas; instrumentos organizados em linhas com colunas proporcionais ao conteúdo. Condições, fontes e cuidados de interpretação foram preservados.
- Panorama, objetivos, financiamento, relatórios, fontes e Relatório Técnico Municipal receberam distribuição mais compacta. Cards financeiros alinham seus blocos em quatro colunas nas telas maiores, duas nas intermediárias e uma no celular. O relatório técnico concentra identificação e resumos e permite rolagem local das tabelas largas.

Arquivos: criada `src/experiences/pme/PmeIntroduction.tsx` e as folhas `pme-introduction.css` e `pme-context.css`; revisados o aplicativo, rotas, componentes, apresentação, estilos e testes PME. A antiga entrada `PmeWelcome` foi substituída pela apresentação após conferência de ausência de consumidores. Nenhum componente compartilhado recebeu nova alteração nesta segunda rodada. Os limites anteriores de CSS total, folha principal e relatório técnico foram mantidos.

Verificação final: 35 testes PME e 8 testes E2E aprovados; `check:fast` (typecheck, lint, compilador e build app-only), `build:app:rs-pme`, arquitetura de UI, higiene e `git diff --check` aprovados. A auditoria visual produziu 40 capturas das dez páginas em 320, 768, 1440 e 1920 px, sem transbordamento horizontal da página ou erros de JavaScript; também verificou texto a 200%, navegação e impressão. Na amostra de Nova Santa Rita, o caderno do Objetivo 1 ficou com 8 páginas, a Agenda com 32 e o Relatório Técnico com 33, sem texto fora das páginas; todos os anos do gráfico, inclusive 2025, foram conferidos no PDF. Evidências locais ignoradas em `.tmp/rs-pme/compact`.

Fontes oficiais, fórmulas, valores, anos, classificações e publicações permanecem inalterados. Os 71 testes de Educação aprovados na rodada anterior foram reutilizados, pois esta rodada não alterou seus componentes compartilhados. Suítes Python de dados e gates integrais de publicação não se aplicam ao escopo visual. Não houve banco, rede externa, atualização de dados ou build completo. O trabalho permanece local e sem commit, push ou PR em `codex/rs-pme`; o checkout original está preservado e a publicação externa E10 segue fora do escopo.

## Preparação de commit — 9 de setembro de 2026

O usuário autorizou o commit da implementação RS PME para posterior publicação. A alteração preexistente de `AGENTS.md` permanece fora desse commit. Os três DOCX de referência acompanham o plano para preservar seus links e contexto metodológico.

Verificação: 35 testes PME, 8 E2E, 8 de hospedagem multiestado, 20 de roteamento, 71 de Educação e 18 testes Python de separação entre update e build aprovados; `check:fast`, arquitetura de UI, higiene e `git diff --check` aprovados. O E2E inicialmente falhou porque o servidor escutava em localhost enquanto o teste consultava 127.0.0.1; seu inicializador agora fixa esse host e a porta estrita, e a suíte completa passou. O lint do arquivo corrigido também passou.

Foram preservados fontes, fórmulas e dados públicos. Não houve atualização de dados, acesso a banco, rede externa, build completo, push ou deploy nesta preparação. Suítes integrais de cálculo e atualização de fontes não se aplicam ao commit da experiência de apresentação. A publicação E10 e o envio da branch ao remoto continuam pendentes.

## Integração em main — 11 de setembro de 2026

O usuário solicitou atualizar a `main` dos projetos no GitHub. A integração preserva a implementação RS PME e os registros de aceite desta branch, incluindo as orientações atuais de `AGENTS.md`. Os conflitos com as cópias iniciais do plano foram resolvidos usando os registros de implementação concluída.

Verificação: 35 testes PME, higiene e `check:fast` aprovados. O código integrado coincide com o código verificado; as diferenças adicionais são documentais. As verificações anteriores de E2E, Educação, roteamento e hospedagem registradas acima continuam aplicáveis aos mesmos arquivos. Esta integração não provisiona Cloudflare Pages, não executa deploy e não atualiza fontes ou dados públicos.
