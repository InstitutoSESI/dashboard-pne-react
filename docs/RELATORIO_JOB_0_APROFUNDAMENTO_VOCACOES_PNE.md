# Relatório do Job 0 — preflight, preservação e mapa real

**Data:** 28 de agosto de 2026
**Plano:** `docs/arquivo/planos-vocacoes-regiao/PLANO_APROFUNDAMENTO_VOCACOES_PNE.md`
**Classificação:** `CLEANUP`, com escopo de preservação, reprodutibilidade e baseline visual
**Piloto preservado:** Vale do Sinos, com validação municipal prioritária em Nova Santa Rita (`4313375`)

## 1. Objetivo executado

O Job 0 confirmou e preservou o estado operacional da implementação V6 antes de qualquer aprofundamento analítico. A etapa:

- mapeou o `HEAD`, os commits locais e todo o working tree;
- preservou o histórico Git e os 42 arquivos modificados ou novos existentes no início do job;
- confirmou os caminhos canônicos dos artefatos R5, R6, R7 e R9;
- trouxe para o repositório as quatro evidências analíticas que existiam somente na camada de pesquisa sem Git;
- reexecutou todas as suítes e verificações determinísticas do domínio Vocações;
- capturou o baseline atual em desktop, tablet, mobile e impressão;
- confirmou que `public/data` e `state-publications` permaneceram intocados.

Nenhuma análise nova, narrativa pública, fórmula, fonte, ano, indicador, schema ou metodologia foi introduzida.

## 2. Estado Git e preservação

O preflight encontrou:

- branch `main` em `4b62e17ff83e811e6826dee6c268e6b2974c9824`;
- cinco commits locais à frente de `origin/main`;
- tag existente `baseline-pre-v6` em `d881436d6`;
- 42 arquivos-folha pertencentes ao trabalho V6 ainda não commitado: sete rastreados modificados e 35 novos;
- nenhuma mudança staged;
- nenhuma mudança sob `public/data` ou `state-publications`.

Foram criados fora do repositório, em
`C:\Users\rnbirck\.codex\visualizations\2026\08\28\01a04847-0137-72b3-ae73-d8f5703349aa`:

| Artefato | Bytes | SHA-256 | Verificação |
|---|---:|---|---|
| `job0-preflight-head.bundle` | 715.425.034 | `739b2faf4b6c7c6f58d0c7e6ca4dbace2258dc597f22df5d7501e073d387f9c4` | `git bundle verify`: histórico completo, `HEAD` exato |
| `job0-preflight-working-tree-relative.zip` | 211.986 | `950604242762f2e7f5b6520fc8ed7b8251ce25c47e74c20daaef4eee982a4fb4` | 42 entradas, caminhos relativos preservados, zero divergência de hash |

O bundle recompõe o histórico até o `HEAD`; o ZIP recompõe os arquivos modificados e novos sobre esse `HEAD`. Não foram usados `stash`, `reset`, `restore`, limpeza, commit ou tag novos.

## 3. Evidências analíticas agora versionadas

As fontes abaixo estavam em `SESI\PNE\foresight\base_conhecimento\06_inventario_dados`, uma árvore sem repositório Git. Foram copiadas byte a byte para `docs/`, sem transformação:

| Arquivo | Bytes | SHA-256 |
|---|---:|---|
| `docs/INVENTARIO_DADOS_PNE_VOCACOES.md` | 57.588 | `2418e243587c5599516afecb44423efa5da26a9fea07df24ff27f506dec66983` |
| `docs/MATRIZ_COBERTURA_ANALITICA.csv` | 35.136 | `ba8a3e56ec49efc4d0325ca7e16a7016361ffebf70de125cbc4fb08f757e55e` |
| `docs/MATRIZ_PRONTIDAO_INSIGHTS.csv` | 6.053 | `3846db7e4f2c32f796b22319d51511b22d548fff2f3610ae2e9baa23a34d7169` |
| `docs/LACUNAS_REAIS_E_PRIORIDADES.md` | 10.044 | `0b203937446fa67737e9714b89827ccf09980e2b7b2d8f714dd07d5739ef468b` |

A matriz de cobertura contém 73 análises: 29 `PRONTA`, 14 `DERIVÁVEL`, 20 `PARCIAL`, oito `AUSENTE` e duas `INADEQUADA`. A matriz de prontidão contém 11 leituras candidatas. A importação CSV confirmou essas contagens.

Esses arquivos são evidência documental e não entrada operacional do frontend ou do pipeline de publicação.

## 4. Mapa real confirmado

| Camada | Paths canônicos confirmados |
|---|---|
| Contrato e auditoria | `docs/CONTRATO_PRODUTO_VOCACOES_PNE.md`, `docs/AUDITORIA_PLANO_IMPLEMENTACAO_VOCACOES_PNE.md` |
| Catálogos e universos | `scripts/checks/fixtures/vocacoes-pne/catalogo-mecanismos.json`, `registro-series.json`, `regras-universo.json`, `catalogo-referencias.json`, `vocabulario.json` |
| Primeira saída R5 | `scripts/checks/fixtures/vocacoes-pne/primeira-saida-*.json`, `scripts/lib/vocacoes-pne-primeira-saida.mjs` |
| Segunda saída R6 | `scripts/checks/fixtures/vocacoes-pne/segunda-saida-*.json`, `scripts/lib/vocacoes-pne-segunda-saida.mjs` |
| Compilador e projeção R7 | `scripts/lib/vocacoes-pne-compilador.mjs`, `src/features/vocacoes-regiao/generated/vocacoesPneValeDoSinos.json` |
| Registro e fila regional | `src/features/vocacoes-regiao/generated/vocacoesPneNarrativeRegistry.json`, `vocacoesPnePublicationQueue.json` |
| Runtime da página | `src/features/vocacoes-regiao/VocacoesPneNarrativeReport.tsx`, `vocacoesPneNarrativeContract.js`, `vocacoesPneNarrativeRegistry.js`, `VocacoesRegiaoPage.tsx` |
| Estilos | `src/styles/vocacoes-pne-narrative-page.css`, com fallback legado preservado em `src/styles/vocacoes-regiao-page.css` |
| Baseline legado | `public/data/vocacoes-regiao/regioes/*.json` e `.tmp/vocacoes-pne/rodada-00/baseline-290`, somente leitura durante este job |

Os hashes centrais continuam iguais aos registrados na auditoria V6:

- pesquisa R5: `9852d0d106deaa3df3dcefc587a08bf3f5e14d2909d159ebe013593d55d213cd`;
- saída R5: `cc7989a0d3417f0ba5f39f29283de9f61b1c734b03238e0ded252c1d59f7e9ea`;
- pesquisa R6: `bee5d4b7a255631eb6dd49a8c0cb80e7ae68d2f8ff0c5ccc26e78047e31754b8`;
- saída R6: `daae50bcb85294af78c3fabdfa9ce233fc42f05bc904082ec8ccb74c35118078`;
- projeção narrativa R7: `8f9515bf35283bb2622f823830dc1c5ff5cad4aa711158ce120edc07eab64f2c`;
- fila regional R9: `8e118bfe1e9cf7e3566bd03b783808c3168bff76f0b9332e1d834ab35cdf7274`.

## 5. Dados, períodos e cálculos

O Job 0 não consultou banco e não recalculou indicadores. Foram apenas inspecionados artefatos já materializados, que cobrem principalmente:

- matrículas e população por idade em 2015–2025 nas leituras R5;
- trajetória escolar até 2025;
- fotografia censitária de deslocamento em 2022;
- tendências observadas de coortes e rede, sem cenário numérico futuro para o Vale do Sinos.

A decomposição já aprovada `M = P × R`, seus componentes simétricos, os limiares de concentração, as janelas de sensibilidade e as regras de universos foram preservados sem alteração. Nenhum arredondamento, taxa ou decisão de publicação foi recalculado neste job.

## 6. Testes executados

| Comando | Resultado |
|---|---|
| `npm run test:vocacoes-pne` | 98/98 |
| `npm run test:vocacoes-regiao` | 132/132 |
| `npm run test:vocacoes-pne-publication` | 12/12 |
| `npm run check:vocacoes-pne-primeira-saida` | bytes idênticos |
| `npm run check:vocacoes-pne-segunda-saida` | duas publicadas, três retidas; artefato válido |
| `npm run check:vocacoes-pne-compilador` | projeção e registro idênticos byte a byte |
| `npm run check:vocacoes-pne-publication` | fila idêntica byte a byte |
| `npm run check:vocacoes-regiao` | dez regiões legadas conferidas |
| `npm run check:fast` | typecheck, lint, compilador e build app-only aprovados |
| `npm run test:vocacoes-pne-page:e2e` | desktop, tablet, mobile, navegação, detalhes, fallback e impressão aprovados |
| `npm run test:vocacoes-layout` | desktop, tablet, mobile e impressão aprovados |
| `git diff --check` | aprovado; apenas avisos preexistentes de normalização LF/CRLF |
| `npm run check:hygiene` | falha preexistente: o regex exige “registro municipal canônico”, enquanto `AGENTS.md` usa a forma semanticamente equivalente “registros municipais canônicos” |

Não foram executados testes Python, build completo, atualização de dados ou validação integral de `public/data`, pois não há mudança em pipeline, contrato de dados ou publicação analítica neste job.

`AGENTS.md` e `scripts/checks/repository-hygiene-test.mjs` estão idênticos ao
`HEAD`; a divergência de flexão já existia antes do Job 0. Ela foi preservada
para não alterar regras permanentes nem o gate fora do escopo desta etapa.

## 7. Baseline visual

Os artefatos estão no mesmo diretório externo do baseline Git:

| Artefato | Bytes | SHA-256 |
|---|---:|---|
| `job0-desktop-1440x900.png` | 511.059 | `a1e2d6fbdc2cbedaf112c9d11c3d3bde527bbc0f9396e033b79dd5d147c1f2a4` |
| `job0-tablet-768x1024.png` | 467.740 | `a68e520773ee777fee4e24da37c89cf9d58b381064fa5e7a3763a68df4ee1673` |
| `job0-mobile-390x844.png` | 452.895 | `fb98cd0d90600ff03f53e44dab8363ce6712a723829fe7053ec872739dcb2f83` |
| `job0-print-1440x900.png` | 504.429 | `cf562ec7abcf7a317f82076c1a6c47cb80a48a2da650f1dcd3a815ed47b09aa7` |
| `job0-print-a4.pdf` | 259.696 | `11410535b8dc4038e8c4f67038aab66524cba0a109c2425f862a01859f5f9146` |

Métricas do percurso fechado:

| Viewport | Cartões | Detalhes | Altura da página | Altura do percurso |
|---|---:|---:|---:|---:|
| desktop 1440 × 900 | 5 | 20 | 6.076 px | 5.928 px |
| tablet 768 × 1024 | 5 | 20 | 5.893 px | 5.779 px |
| mobile 390 × 844 | 5 | 20 | 9.314 px | 9.208 px |

A inspeção visual confirmou ausência de corte horizontal e preservação da hierarquia, dos cinco visuais principais, dos detalhes recolhidos e do fallback legado.

## 8. Resultados retidos e pendências

Nenhuma candidata analítica foi reaberta neste job. Permanecem como fatos do baseline:

- Gate 11 bloqueado por ausência da leitura trabalho × formação e do teste humano;
- Gate 12 não aprovado por falta dos artefatos R5/R6/R7 em Vale do Rio Pardo e Noroeste;
- trabalho juvenil, EJA, trajetória e ocupações/formação são os principais domínios do aprofundamento V7;
- decisão formal sobre cenários do Vale do Sinos ainda pertence ao Job 1;
- commit, tag e push não foram criados; exigem instrução explícita e organização temática do working tree já existente.
- o contrato textual entre `AGENTS.md` e `check:hygiene` precisa ser reconciliado em tarefa própria, sem enfraquecer a invariável de identidade municipal.

## 9. Efeito operacional

- Arquivos públicos alterados: nenhum.
- Banco: não usado.
- Rede: não usada.
- Build completo: não executado.
- Build app-only: executado e aprovado.
- Fórmulas e metodologia: preservadas.
- Arquivos removidos ou movidos: nenhum.
- Arquivos criados pelo Job 0: as quatro evidências em `docs/` e este relatório.
- Artefato temporário ignorado: `.tmp/vocacoes-pne/job0-capture-print.cjs`.

## 10. Próximo job permitido e veredito

**Próximo job permitido:** Job 1 — contrato analítico V7, com julgamento independente das decisões de produto antes de qualquer materialização ou alteração de interface.

**Veredito:** **Aprovado com pendências não bloqueantes**.

O baseline está recuperável, os testes do domínio estão verdes, as evidências decisórias deixaram de depender de uma árvore sem Git e nenhuma mudança de dados ocorreu. A pendência de commit/tag não bloqueia a preservação técnica, mas deve ser resolvida antes de uma entrega Git formal.
