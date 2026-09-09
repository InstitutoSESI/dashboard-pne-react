# Plano de implementação — nova publicação pública RS / PME

Status: plano preparado; implementação não iniciada.
Data: 7 de setembro de 2026.
Classificação desta entrega: `DOCUMENTATION_ONLY`.
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
- Esta solicitação é para preparar o plano. Nenhuma implementação, publicação, criação de projeto Cloudflare, commit, push ou PR foi autorizada por ela.

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

Estrutura proposta, ainda a criar; ajustar nomes locais se houver conflito sem mudar as fronteiras:

- `scripts/lib/experience-build-profile.mjs`: validação da experiência e seleção da entrada.
- `src/config/experienceConfig.ts`: configuração de experiência validada para o frontend.
- `src/main-entry.ts`: entrada mínima comum, contendo somente a importação do alias de aplicação selecionado no build.
- `src/main-pme.tsx`: entrada selecionada exclusivamente pelo build PME.
- `src/experiences/pme/`: aplicação, shell, rotas, páginas, modelos de apresentação, catálogos e exportação PME.
- `src/experiences/pme/styles/`: estilos próprios, com escopo de classe da experiência.
- `scripts/checks/experience-profile.test.mjs` e testes PME: contratos e verificações novas.

A seleção da entrada será feita por alias estático do Vite: o script de módulo de `index.html` apontará para `src/main-entry.ts`, cuja única importação será `@platform-entry`. O perfil validado configurará `resolve.alias` para resolver esse nome exclusivamente para `src/main.jsx` em `atual` ou `src/main-pme.tsx` em `pme`. Assim, o grafo compilado parte de uma única aplicação tanto em desenvolvimento quanto no build completo e app-only. Ajustar a declaração/resolução do alias para as ferramentas de tipagem sem criar fallback de runtime. A entrada mínima não importa CSS, shell ou contexto de nenhuma experiência.

A entrada atual deve continuar carregando somente sua aplicação; a entrada PME deve carregar somente seu shell e registro de navegação. Não selecionar a experiência por domínio, query string, hash ou armazenamento do navegador. Não importar os dois aplicativos para escolher um em runtime. Os testes precisam verificar o alvo real do alias, o módulo efetivamente carregado e o isolamento dos dois builds app-only; conferir apenas a variável de configuração não basta.

Compartilhar loaders, contratos, formatadores e componentes neutros. Reutilizar páginas de detalhe somente depois de separar dependências de navegação e estilos; não copiar todo o domínio. O novo bundle poderá conter detalhes compartilhados necessários, mas não deve incluir automaticamente o shell ou as páginas exclusivas da outra experiência.

Preservar rotas hash e aliases atuais. A experiência PME terá registro próprio e parâmetros explícitos de município, objetivo e filtros públicos. Links internos manterão o mesmo código IBGE textual; voltar, avançar, recarregar e abrir link direto devem funcionar. Persistência local, se necessária, ficará limitada à UF e ao código IBGE do contexto de navegação já contratado; usar namespace próprio quando o contrato atual carregar rotas incompatíveis. Objetivo e filtros públicos ficam na URL. Não persistir buscas livres, anotações, seleção de problemas, decisões ou outros conteúdos editáveis, nem restaurar rotas de outra experiência.

### 4.3 Comandos e saídas

Comandos existentes continuam com sua finalidade. Os comandos abaixo são PROPOSTOS e ainda não existem:

| Comando a criar | Finalidade / saída |
| --- | --- |
| `npm run dev:rs-pme` | Desenvolvimento RS/PME; porta sugerida 5189, verificar disponibilidade. |
| `npm run build:app:rs-pme` | Validação leve sem copiar dados; `dist/app-only-rs-pme`. |
| `npm run build:rs-pme` | Release local RS/PME; `dist/rs-pme`. |
| `npm run preview:rs-pme` | Servir release local existente; porta sugerida 4189. |
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

Todas as etapas estão PENDENTES. Atualizar este quadro e registrar evidências à medida que forem concluídas; não marcar pronto com base apenas na existência de telas ou comandos.

| Etapa | Dependência | Escopo principal | Saída |
| --- | --- | --- | --- |
| E0 | Nenhuma | Inventário e baseline | Estado inicial, acoplamentos e casos de referência registrados. |
| E1 | E0 | Publicação dupla | Seleção de experiência e builds isolados. |
| E2 | E1 | Shell e navegação PME | Percurso público navegável com identidade municipal preservada. |
| E3 | E1 | Contratos de apresentação e catálogos | Adaptadores, cobertura e relações rastreáveis. |
| E4 | E2 + E3 | Panorama dos objetivos | 19 campos, metas, filtros e lacunas. |
| E5 | E2 + E3 | Agenda de Análise | Leituras existentes adaptadas sem decisão municipal automática. |
| E6 | E4 + E5 | Fichas e financiamento | Evidências, limites, perguntas e apoios integrados. |
| E7 | E4 + E5 + E6 | Entrada municipal | Síntese e destaques com origem e regras explícitas. |
| E8 | E5 + E6 + E7 | Relatórios | Três novos artefatos e acesso ao relatório atual. |
| E9 | E1–E8 | Aceite integrado | Regressão, acessibilidade, desempenho e impressão verificados. |
| E10 | E9 + autorização de publicação | Pages e operação | Novo endereço publicado, smoke test e rollback documentados. |

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

Testes E2E precisam de aplicação ativa. Os comandos `dev:rs`, `dev:al` e o futuro `dev:rs-pme` devem usar portas distintas. Conferir como cada script atual aceita endereço base; não presumir que um E2E da experiência atual serve ao PME.

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
