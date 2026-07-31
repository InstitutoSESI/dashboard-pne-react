---
name: painel-design
description: Sistema de design do Painel SESI-RS de Inteligência Analítica Municipal. Use ao criar ou alterar qualquer interface deste repositório — cartões, gráficos, tabelas, cabeçalhos, filtros, estados, cores, tipografia, espaçamento. Carrega as armadilhas da cascata CSS deste repositório, o estado das pendências e o caminho do documento de design canônico. Não use para tarefas de pipeline de dados ou cálculo de indicadores.
---

# Painel SESI-RS — guia do repositório

## Leia primeiro

**O sistema de design canônico está em [`docs/DESIGN.md`](../../../docs/DESIGN.md)** — tokens no frontmatter, oito seções em prosa, regras nomeadas. Ele é normativo; este arquivo não o repete.

Leia também `PRODUCT.md` (verdade de produto: público, posicionamento, contexto de operação, princípios).

> ⚠️ O `docs/DESIGN.md` **não é carregado automaticamente** pelo impeccable, que só procura `DESIGN.md` na raiz do projeto. Abra-o explicitamente antes de trabalho visual.

Modo: **Operate**. O gestor está numa tarefa. Escaneabilidade, consistência e densidade vencem expressão.

## Regras de ouro deste repositório

1. **Nunca escreva valor literal** de cor, raio, sombra, espaçamento ou tamanho de fonte em CSS de domínio. Consuma o token de `src/styles/design-tokens.css`.
2. **`public/data/` é saída versionada do pipeline.** Não edite nem percorra em tarefa visual.
3. **Nova regra pertence à menor camada com consumidores claros.** Não duplique em CSS de domínio a gramática que já existe em `platform-ui.css`, e não use `App.css` como origem de padrão novo.

## Cascata — as armadilhas reais

Ordem de carga: `index.css` (tokens) → `institutional-refresh.css` → `App.css` → `chart-system.css` → `pne-cycle-experience.css` → `platform-ui.css` → `financial-pages.css` → `navigation-shell.css`. **`education-pages.css` entra por último**, via import lazy da EducationPage — por isso acumulou tantos `!important`.

- Um bloco de override novo em `platform-ui.css` **perde** para `education-pages.css`. Edite a regra na origem em vez de empilhar override.
- O mesmo componente costuma ter regra em 2–3 arquivos (`.context-bar` está em `App.css`, `institutional-refresh.css` e `navigation-shell.css`). **Antes de editar, faça `grep` do seletor em todos** — foi assim que o breadcrumb da barra superior acabou renderizado com altura 0.
- Total de ~49k linhas de CSS. `App.css` (13k) e `education-pages.css` (13,4k) concentram a maior parte.

## Composição parte-todo: cartão, não barra

**Preferência declarada do dono do produto: cartões.** Para mostrar quanto cada parte pesa no total, coloque a participação **dentro do cartão, abaixo do valor** — não crie barra empilhada ao lado da tabela.

Isso já foi testado e rejeitado: uma barra de proporção com legenda foi implementada no Panorama e removida. O motivo é de leitura — a barra obrigava três saltos (segmento → legenda → tabela) e, com duas ou três categorias, dizia menos do que o número já dizia. Fatias de 2% viravam lascas ilegíveis e a legenda quebrava em duas linhas.

Padrão correto: `EducationOverviewSection.tsx`, `formatCompositionShare`.

```
Ensino Fundamental
1.624
61,8% da Educação Básica
```

Se um dia uma barra voltar a fazer sentido (série com muitas categorias), **confirme com o dono antes**.

**Ausência não é zero** em qualquer visualização: use `getOverviewNumericValue`, que devolve `null` quando o dado não é publicável. Zero observado é dado; ausente e não aplicável não são.

## Verificação

Para mudança visual, valide o domínio afetado em 1440px e 390px.

```bash
npm run test:ui-architecture && npm run test:education && npm run test:e2e
```

Depois de terminar UI, rode o detector mecânico:

```bash
node C:/Users/rnbirck/.claude/skills/impeccable/scripts/detect.mjs --json src/styles/ src/App.css
```

Achados conhecidos e **aceitos** (não são regressão): 2 `layout-transition` em barras de proporção — formato pílula distorce sob `scaleX`, então animar `width` é correto e há cobertura de `prefers-reduced-motion`; 1 `codex-grid-background` — textura de papel milimetrado do fundo, identidade deliberada.

## Anatomia de cartão: use as variantes

Contrato em `platform-ui.css` (classes) e `design-tokens.css` (tokens, bloco "Anatomia de cartao"). **Adote uma variante em vez de escrever a combinação de novo.**

| Variante | Padding | Raio | Uso |
|---|---|---|---|
| `.surface-card` | 20 | 10 | painel e cartão de entrada |
| `.surface-card--dense` | 16 | 10 | grade de indicadores |
| `.surface-card--hero` | 32 | 10 | abertura de página |
| `.surface-card--compact` | 12 | 7 | métrica pequena |
| `.surface-inset` | 12/16 | 7 | faixa interna (sem borda) |
| `.surface-emphasis` | 12/16 | 7 | bloco de leitura |

`--dense` existe de propósito separado de `--card`: 91 cartões de indicador ladrilham em grade e 16px é densidade real, não desalinho.

## Estado atual: deriva medida

Inventário de valores computados em 18 páginas, contra a escala dos tokens:

| Dimensão | Antes | Agora |
|---|---|---|
| Tamanho de fonte | 55 | **12** |
| Padding de superfície | 55 | **40** |
| Gap | 36 | **22** |
| Raio de borda | 6 | **4** |
| Fundo de superfície | 28 | **21** |
| Borda (cor + espessura) | 20 | **18** |
| Assinaturas de cartão | 32 | **28** |
| Tamanhos de ícone | 12 | **5** |
| Achados do detector | 844 | **214** |

Espaçamento foi normalizado para a escala de 4px (**1.018 declarações**), com empate resolvendo para baixo para não inflar layout. Cores convergiram para a paleta da marca (**254 substituições**): havia oito verdes distintos em `rgba`, um azul Tailwind avulso e dois cinzas quentes do tema anterior.

Os **189 achados de cor restantes** são majoritariamente `rgba` do verde da marca em opacidades variadas — o detector conta cada alfa como cor não documentada. Avalie caso a caso antes de "corrigir".

### O detector é o linter do sistema

Depois que `docs/DESIGN.md` passou a declarar tokens, o detector valida contra eles e lista exatamente o que está fora. É a ferramenta certa para continuar — não garimpe à mão.

```bash
node C:/Users/rnbirck/.claude/skills/impeccable/scripts/detect.mjs --json src/styles/ src/App.css
```

### Exceção travada por teste

`.school-infrastructure-summary-card > strong` usa **`font-size: 30px` literal**, fora da escala. `scripts/checks/education-test.mjs` verifica esse valor explicitamente. Não "normalize" para token: enfraquecer o teste para acomodar a escala inverteria a ordem das coisas. Se a escala tiver de vencer, mude o teste junto, e com aval.

## Alinhamento entre cartões irmãos

O valor em destaque tem de nascer no **mesmo ponto** em todos os cartões de uma fileira. Isso exige duas coisas, e as duas já foram quebradas uma vez:

1. **Linhas estruturais de altura fixa.** Rótulo, título e descrição variam entre uma e duas (ou três) linhas conforme o indicador. Com `auto`, cada cartão resolve a própria altura e o valor desce — mediu-se até 23px de desvio entre vizinhos. Os cartões de indicador usam `30px 38px 32px`; o cartão de meta do PNE reserva `65px` de título (três linhas, o máximo real na base). Reservar o máximo **não** deixa o cartão mais alto: a folga já existia no rodapé e só muda de lugar.
2. **Âncora no topo na linha do valor.** O alinhamento não pode depender de o cartão ter unidade ("alunos", "escolas") ou não. Havia `flex-start` com unidade e `center` sem — 12px de diferença.

As três primeiras linhas vêm de `--indicator-row-topline` / `--indicator-row-title` / `--indicator-row-description`. **Use os tokens** em vez de repetir o número.

⚠️ **Há 25 declarações de `grid-template-rows` e 11 de `align-items` para esta família de cartão**, espalhadas por `institutional-refresh.css`, `platform-ui.css` e `education-pages.css`, com anatomias de 2 a 8 trilhas e `grid-template-areas` diferentes. Antes de editar qualquer uma, descubra qual está ativa — via CDP `CSS.getMatchedStylesForNode`, **não** por `grep`. Editar a errada não produz efeito nenhum (aconteceu duas vezes).

Consolidar as 25 numa só é trabalho estrutural em aberto: as anatomias divergem de verdade, então não dá para reescrever em lote sem quebrar variantes.

Para verificar, meça o topo do valor relativo ao topo do cartão em cada fileira e compare.

## Navegação lateral: três estados

`--nav-label`, `--nav-text`, `--nav-text-hover`, `--nav-text-active`, `--nav-bg-hover`, `--nav-bg-active`, `--nav-divider`. Havia seis cores de texto e três tintas verdes para o que são apenas repouso, hover e ativo. Todos ≥7:1 sobre `--green-brand-dark`.

Texto invertido **fora** da barra lateral usa `--text-inverted`, não `--nav-text-active`.

## Ícones

`viewBox="0 0 24 24"`, traço **1,7**, quatro tamanhos (`--icon-sm/md/lg/xl` = 16/18/24/32) e quatro caixas (`--icon-box-*` = 28/32/44/48). Traço de gráfico não é ícone: linha de série, eixo e malha têm espessura própria (1, 2.25, 2.5) e ficam fora dessa escala.

## Eixo de gráfico

`getBoundedDomain` em `src/utils/chartDomain.js` é a regra única para escala limitada (percentual, IDEB, INSE). Ocupa a área disponível **e** garante vão mínimo — 20 p.p. em percentual — para não transformar variação pequena em escalada. A meta entra no cálculo; marcas de eixo saem de dentro da faixa, nunca de escala fixa.

**Não volte a fixar `{min: 0, max: 100}`.** Foi o que fazia a série de pré-escola (88–100%) virar um traço colado no topo com três quartos do gráfico vazios.

## Defeitos conhecidos ainda abertos

- **Anexo D do relatório**: tabela de 10 colunas, 1.360px em contêiner de 910px. Rola, mas sem afordância visual — parece cortada.
- **Folha de impressão não verificada.** Fontes, superfícies, raios, espaçamento e ícones mudaram; nenhum teste cobre impressão e o Relatório Técnico é impresso.

## Falhas pré-existentes na suíte

**Não introduzidas por trabalho visual — não as conserte junto de uma mudança de UI:**

- `npm run typecheck`: 3 erros (`SpecialEducationDetailView.tsx` com `number | null`; `EducationPage.tsx` usando `.at()` sem `lib` es2022).
- `npm run test:diagnostic`: 1 de 11 falha — espera a cópia "Comparação com a média dos municípios do RS neste indicador", a interface renderiza "Comparação com o RS". Um dos dois está desatualizado; é decisão do dono qual.
- `npm run test:data-sources`: falha em "Censo Escolar: partes estruturadas divergentes".
- `npm run lint`: 1 aviso de `react-hooks/exhaustive-deps` em `EducationPage.tsx`.

Todas confirmadas com `git stash`: falham igual no HEAD.
