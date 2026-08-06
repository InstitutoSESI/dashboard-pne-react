---
name: Painel SESI-RS de Inteligência Analítica Municipal
description: Painel institucional onde a gestão municipal lê metas do PNE, indicadores educacionais, financiamento e o relatório técnico do seu município.
colors:
  green-primary: "#2f7057"
  green-deep: "#22523f"
  green-brand-dark: "#10382f"
  green-accent: "#98b0a9"
  green-soft: "#e1f2e8"
  classy-sage: "#657c75"
  classy-navy: "#1c334a"
  classy-slate: "#4c627b"
  surface-card: "#fcfefd"
  surface-raised: "#f3f7f5"
  surface-muted: "#e6ece9"
  bg-app: "#e2e8e5"
  bg-body: "#dae1dd"
  border-faint: "#dfe3e1"
  border-card: "#cfd5d2"
  border-line: "#c6ceca"
  border-strong-line: "#98b0a9"
  text-strong: "#1c334a"
  text: "#2e3632"
  text-body: "#505753"
  text-muted: "#616965"
  text-inverted: "#f5faf6"
  status-ok-ink: "#245c47"
  status-warn-ink: "#7f5b23"
  status-far-ink: "#8e4536"
  status-muted-ink: "#5e6b62"
  signal-ochre: "#8e5e00"
  signal-clay: "#9d533f"
  signal-blue: "#4c627b"
  chart-series-1: "#307057"
  chart-series-2: "#1c334a"
  chart-series-3: "#9d671c"
  chart-series-4: "#4c627b"
  chart-series-5: "#9c4f44"
  chart-series-6: "#657c75"
  chart-axis: "#657c75"
  chart-grid: "#d4d9d6"
typography:
  display:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "2.375rem"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.018em"
  page:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "2rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.012em"
  headline:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "1.75rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.012em"
  title:
    fontFamily: "Source Sans 3, system-ui, Segoe UI, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "0"
  body:
    fontFamily: "Source Sans 3, system-ui, Segoe UI, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0"
  support:
    fontFamily: "Source Sans 3, system-ui, Segoe UI, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0"
  label:
    fontFamily: "Source Sans 3, system-ui, Segoe UI, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.35
    letterSpacing: "0.01em"
  data:
    fontFamily: "Source Sans 3, system-ui, Segoe UI, sans-serif"
    fontSize: "2rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.018em"
    fontFeature: "tnum"
icon:
  sm: "16px"
  md: "18px"
  lg: "24px"
  xl: "32px"
  box-sm: "28px"
  box-md: "32px"
  box-lg: "44px"
  box-xl: "48px"
rounded:
  xs: "4px"
  sm: "7px"
  md: "10px"
  lg: "14px"
  xl: "18px"
  pill: "999px"
spacing:
  1: "4px"
  2: "8px"
  3: "12px"
  4: "16px"
  5: "20px"
  6: "24px"
  8: "32px"
  10: "40px"
  12: "48px"
  16: "64px"
components:
  card:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "20px"
  card-inset:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text-body}"
    rounded: "{rounded.sm}"
    padding: "12px 16px"
  card-emphasis:
    backgroundColor: "{colors.green-soft}"
    textColor: "{colors.green-deep}"
    rounded: "{rounded.sm}"
    padding: "12px 16px"
  button-primary:
    backgroundColor: "{colors.green-primary}"
    textColor: "{colors.text-inverted}"
    rounded: "{rounded.sm}"
    padding: "9px 12px"
    height: "44px"
  button-secondary:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "9px 12px"
    height: "44px"
  chip:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "9px 12px"
  chip-selected:
    backgroundColor: "{colors.green-soft}"
    textColor: "{colors.green-deep}"
    rounded: "{rounded.sm}"
    padding: "9px 12px"
  input:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "9px 12px"
    height: "44px"
  table-header:
    backgroundColor: "{colors.green-soft}"
    textColor: "{colors.green-deep}"
    rounded: "{rounded.xs}"
    padding: "12px 16px"
  sidebar:
    backgroundColor: "{colors.green-brand-dark}"
    textColor: "{colors.text-inverted}"
    rounded: "{rounded.xs}"
    padding: "12px 16px"
---

# Design System: Painel SESI-RS de Inteligência Analítica Municipal

Este painel não é um dashboard de monitoramento: é o dossiê que a equipe da Secretaria Municipal de Educação leva para uma reunião de conselho e usa para defender um orçamento. Tema claro porque é lido em tela e impresso sob luz de escritório. A tabela nunca sai de cena, porque o número exato é o que se cita numa ata. E nada na interface julga a gestão — a cor descreve, o texto explica, e a conclusão fica com quem lê.

Um dossiê de verdade também se folheia sem se perder: cinco frentes de indicador (Atendimento, Trajetória, Profissionais, Infraestrutura, Modalidades), cada uma com um selo próprio que aparece na barra lateral e no alto da página. É a peça de identidade nova deste guia — ver [Assinatura](#assinatura-selos-de-domínio).

## Sumário

1. [Visão geral](#visão-geral)
2. [Cores](#cores)
3. [Tipografia](#tipografia)
4. [Layout](#layout)
5. [Profundidade](#profundidade)
6. [Formas e ícones](#formas-e-ícones)
7. [Assinatura: selos de domínio](#assinatura-selos-de-domínio)
8. [Componentes](#componentes)
9. [Fazer e evitar](#fazer-e-evitar)

## Visão geral

A densidade é alta e assumida. O leitor é técnico, está numa tarefa, e prefere ver quinze indicadores de uma vez a navegar por quinze telas. A marca vive na precisão dos detalhes — no alinhamento de uma coluna numérica, no verde exato de uma borda, no selo que identifica em que frente da leitura o usuário está — e não em ornamento. Quando há dúvida entre expressar e informar, informa.

A rampa de neutros é tingida no próprio verde institucional, não em bege quente. Isso não é preferência estética: o bege deixava cartão e página a 1,11 de contraste e a interface inteira virava um borrão. O verde-neutro dá aos cartões separação real (1,23) e mantém a identidade em vez de diluí-la.

**Características-chave:**
- Documento antes de dashboard: imprime, cita, arquiva.
- Densidade alta para leitor técnico em tarefa.
- Descreve, não julga: sem semáforo de mérito, sem ranking competitivo.
- Cada frente de indicador tem cor de acento **e** selo próprio — orientação por dois canais, não só por cor.
- Zero, ausência e não aplicabilidade são três estados distintos, nunca colapsados.
- Todo texto atinge WCAG 2.2 AA sobre a superfície mais escura em que assenta.

## Cores

Uma família verde institucional sobre uma rampa de neutros tingida na mesma matiz (hue OKLCH ~162), complementada pela Classy Palette em navy, slate e sage. O verde continua sendo ação e identidade; os tons azulados acrescentam hierarquia e variedade a títulos, orientação e séries de dados.

### Primária
- **Verde Institucional** (`#2f7057`): a cor de ação e seleção. Botão primário, item de navegação ativo, linha de referência em gráfico, borda de foco. Nunca decorativo.
- **Verde Profundo** (`#22523f`): texto sobre superfície verde clara, títulos dentro de blocos de ênfase, e o degrau escuro quando o primário não tem contraste suficiente.
- **Verde Institucional Escuro** (`#10382f`): exclusivo da barra lateral. É a segunda camada neutra do sistema — separa navegação de conteúdo sem competir com ele.

### Secundária
- **Verde Névoa** (`#98b0a9`): bordas de blocos de ênfase, divisores de navegação e destaques de leitura. Por ter baixo contraste sobre superfícies claras, nunca carrega texto principal.
- **Navy Editorial** (`#1c334a`): títulos, valores fortes e séries de dados escuras. Introduz contraste frio sem disputar com o verde de ação.
- **Azul Ardósia** (`#4c627b`): acento secundário, orientação e comparação em gráficos. Pode carregar texto sobre superfícies claras e texto invertido quando usado como fundo.
- **Sálvia Mineral** (`#657c75`): séries auxiliares, eixos e acentos gráficos. Não deve ser usado como texto sobre a Mesa porque não atinge o piso de 4,5:1 nessa combinação.
- **Verde Sereno** (`#e1f2e8`): fundo de bloco de leitura, cabeçalho de tabela, chip selecionado. Marca "isto é interpretação", não dado bruto. É uma tinta para **superfície pequena**: em bloco amplo — um total de destaque, um painel que embrulha cartões — o mesmo verde vira menta cheia e destoa do resto, que é cartão branco sobre neutro. Nesses casos, use Papel Elevado e um fio de acento para a hierarquia.

### Neutra
- **Papel** (`#fcfefd`): a superfície de todo cartão. É o documento.
- **Papel Elevado** (`#f3f7f5`): faixa interna dentro de um cartão — cabeçalho de seção, subtotal, agrupamento; também o fundo do painel que acomoda uma grade de cartões (ver [Layout](#layout)).
- **Mesa** (`#e2e8e5`): o fundo da página sobre o qual painel e cartões repousam.
- **Mesa Profunda** (`#dae1dd`): a borda externa do corpo, atrás da mesa.
- **Tinta Forte** / **Tinta** / **Tinta Suave** / **Tinta Discreta** (`#1c334a` → `#2e3632` → `#505753` → `#616965`): o primeiro degrau usa o navy editorial; os demais preservam a rampa neutra. `#616965` é o piso — abaixo dele nada carrega texto.
- **Fios** (`#dfe3e1` → `#cfd5d2` → `#c6ceca` → `#98b0a9`): quatro pesos de borda, do mais discreto ao mais estrutural.

### Regras nomeadas

**A Regra do Piso de 4,5.** Todo token de texto atinge no mínimo 4,5:1 sobre `--bg-app` (`#e2e8e5`), a superfície mais escura em que texto assenta — não sobre o cartão, que é mais permissivo. `--text-soft` e `--text-faint` são aliases semânticos de `--text-muted` no contrato visual atual e **nunca** devem receber um cinza mais claro.

**A Regra do Não-Julgamento.** Vermelho, âmbar e verde nunca formam semáforo de mérito. Aprovação usa verde; reprovação e abandono usam neutros da mesma família. Variação positiva não significa bom, nem negativa significa ruim: o rótulo e o texto explicam o sentido do indicador.

**A Regra da Matiz Própria.** Superfícies e neutros de apoio são tingidos no verde da marca, nunca em bege ou cinza puro. Um novo neutro nasce da mesma matiz (~162) com croma entre 0,002 e 0,009. Navy, slate e sage são acentos nomeados da Classy Palette, não novos neutros genéricos.

## Tipografia

**Fonte de destaque:** Source Serif 4 (alternativas Georgia, Times New Roman, serif)
**Fonte de texto:** Source Sans 3 (alternativas system-ui, Segoe UI, sans-serif)

Um par contrastante e deliberado: serifa editorial para o título que abre um documento, sem serifa funcional para tudo que é trabalho — rótulo, dado, controle, tabela. A serifa dá autoridade de publicação institucional; a sem serifa dá legibilidade em densidade alta e em número tabular.

### Hierarquia
- **Display** (600, 2,375rem, 1.1, -0,018em): abertura editorial de landing page. Serifa.
- **Page** (600, 2rem, 1.2, -0,012em): título principal de página. Serifa, sempre na mesma escala independentemente do layout.
- **Detail** (600, 1,75rem, 1.2, -0,012em): título de uma leitura analítica dentro da página. Serifa.
- **Section** (600, 1,5rem, 1.2, -0,012em): abertura de seção. Serifa.
- **Subsection** (600, 1,25rem, 1.2): agrupamento funcional interno. Sem serifa.
- **Compact title** (600, 1,125rem, 1.2): título curto intermediário. Sem serifa.
- **Title** (600, 1rem, 1.35): título de cartão e de painel. Sem serifa.
- **Body** (400, 0,9375rem, 1.5): texto corrido, descrição de página e célula de tabela. Prosa longa fica em 62–72ch; tabela pode passar disso.
- **Support** (400, 0,875rem, 1.5): fonte, metodologia, nota técnica e descrição auxiliar.
- **Label / Micro** (500, 0,8125rem, 1.35, 0,01em): rótulo de contexto, legenda, nome de campo e texto de gráfico. **Caixa normal.** Status e identidade podem usar 600.
- **Data** (700, 2rem ou 1,5rem, 1.2, tnum): valor principal ou compacto de indicador. Sempre com numeral tabular.

### Regras nomeadas

**A Regra da Escala Fixa.** Tamanhos vêm em `rem` fixo da escala de tokens, nunca de `clamp()`, `em` ou `%`. UI de produto é lida em DPI constante, e título fluido encolhe onde não deveria. Herança em `em` foi a origem de dezenas de tamanhos quebrados como 13,76px e 35,57px — valores que ninguém escolheu.

**A Regra do Rótulo Silencioso.** Rótulo de contexto é legenda, não banner: caixa normal, peso 500, cor `--text-muted`. Peso 600 fica reservado a status e identidade. Caixa alta tracked é reservada a exatamente dois lugares — a assinatura do produto no topo da Home e o rótulo da barra de navegação. Uma seção que abre com kicker em caixa alta está errada.

## Layout

Casca de duas colunas: barra lateral fixa de 280px em verde escuro, e área de conteúdo com largura máxima de 1440px e respiro lateral de 40px (24px em tablet, 16px em celular). A barra superior de contexto tem 72px e é fixa no topo.

O ritmo de espaçamento parte de 4px, com o passo principal em 8px: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64. Cartão respira 20px por dentro; painel maior, 24px; faixa interna, 12px por 16px.

Uma grade de cartões de indicador pousa sobre um painel em Papel Elevado, não direto na Mesa: Mesa (`--bg-app`) → painel (`--surface-raised`) → cartão (`--surface-card`) são três camadas, não duas. Painel transparente sobre a Mesa crua faz o vão entre cartões virar um buraco cinza sem definição — testado e revertido.

Responsividade é **estrutural**, não tipográfica: colapsa coluna, empilha grade, faz tabela rolar. O texto não encolhe. Grades preferem `repeat(auto-fit, minmax(min(Npx, 100%), 1fr))` a colunas proporcionais fixas — proporção fixa sem variante mobile foi o que espremeu cartões em 90px a 390px.

A página nunca rola horizontalmente. Tabela larga e gráfico denso rolam **dentro do próprio contêiner**, e todo elemento com `min-width` precisa de um pai com `overflow-x: auto`.

## Profundidade

O sistema é **tonal, não sombreado**. A profundidade vem do degrau de luminosidade entre Mesa, Papel Elevado e Papel, reforçado por uma borda de 1px. Sombra é acessório, não estrutura: existe para responder a estado, não para criar hierarquia.

### Vocabulário de sombra
- **Repouso** (`0 1px 2px rgba(22, 42, 31, 0.04)`): o padrão de cartão. Quase imperceptível; a borda é que define.
- **Hover** (`0 10px 22px rgba(22, 42, 31, 0.07)`): resposta a ponteiro em cartão navegável.
- **Sobreposição** (`0 16px 34px` / `0 24px 48px`): dropdown e camada flutuante, onde a separação precisa ser inequívoca.

**A Regra da Borda Antes da Sombra.** Se um elemento precisa se destacar, a ordem é: degrau tonal → borda → só então sombra. Sombra nunca substitui hierarquia.

## Formas e ícones

Cantos suavemente arredondados, em cinco degraus: 4px para célula e marcador, 7px para controle e bloco interno, 10px para cartão e painel, 14px e 18px para superfícies grandes, e pílula (999px) só em chip e barra de proporção.

Bordas são de 1px por padrão, 2px quando o elemento precisa de peso estrutural. Blocos de destaque com fundo usam **borda completa**; regra tipográfica lateral fina é permitida apenas em texto sem fundo, como nota marginal de documento.

**A Regra da Tarja Deliberada.** A faixa lateral colorida acima de 1px é o tell mais reconhecível de interface gerada por máquina *quando é decoração avulsa* — uma cor qualquer na borda de um cartão qualquer. Foram removidas 25 dessas; não reintroduza. Há **uma** exceção sancionada: a barra de acento da seção (3px em cartão de indicador, 4px em cabeçalho de agrupamento e no total de destaque do Panorama), sempre na tinta `--education-section-accent` da frente e sempre nas mesmas fatias estruturais. Ela não é ornamento: é o sistema de identidade por seção, aplicado com disciplina. A diferença entre device e tell é a consistência — uma cor por seção, nos mesmos lugares, ou nada.

### Ícones de interface

Todo ícone de UI vem de `lucide-react`, usa a malha 24×24, traço de **1,7** e cantos arredondados. Quatro degraus de tamanho — 16px ao lado de rótulo, 18px como padrão de UI, 24px em cabeçalho de seção, 32px em cartão de entrada — e quatro de caixa (28/32/44/48px). Setas, chevrons, marcas de seleção e indicadores de expansão também usam Lucide; não use glifos Unicode nem SVGs desenhados no componente. Traço de gráfico é outra coisa: linha de série, eixo e malha têm espessura própria e não seguem a escala de ícone.

## Assinatura: selos de domínio

O elemento que este guia introduz para tornar a navegação reconhecível de relance: cada frente de indicador educacional ganha um **glifo próprio**, além da cor de acento que já existia. Cor sozinha exige ler o rótulo para confirmar onde se está; forma soma um segundo canal, mais rápido de reconhecer e que não depende de percepção de cor.

| Seção | Glifo | O que evoca |
|---|---|---|
| Atendimento e oferta | escola | matrícula e rede de ensino |
| Trajetória escolar | rota | fluxo entre etapas |
| Profissionais da educação | quadro de apresentação | corpo docente |
| Infraestrutura escolar | prédio com grade de janelas | condições físicas da escola |
| Modalidades | camadas sobrepostas | pluralidade — especial, indígena, EJA, Sistema S |

Implementação de referência: `EducationDomainIcon` (`src/components/icons/EducationDomainIcon.tsx`), que mapeia os domínios para componentes Lucide e preserva a escala (`--icon-sm/md/lg`) do restante do sistema de ícones.

**A Regra do Selo Único.** O selo de domínio aparece em exatamente dois lugares por seção: o item correspondente na barra lateral, e o eyebrow do cabeçalho da página. Não se repete em cartão de indicador, em cabeçalho de agrupamento interno, nem em rodapé. Um selo que aparece em todo nível da hierarquia deixa de orientar e vira papel de parede — a disciplina de "um só lugar por página" é o que faz o sinal valer alguma coisa.

### Selo de domínio × glifo de orientação

São duas camadas de ícone com trabalhos diferentes, na mesma convenção visual (viewBox 24×24, traço 1,7), fáceis de confundir:

- **Selo de domínio** carrega *identidade*. Existe só para as cinco frentes, e reaparece no cabeçalho (a Regra do Selo Único acima). É `EducationDomainIcon`.
- **Glifo de orientação** carrega só *wayfinding*. Dá a cada subitem de navegação uma silhueta reconhecível a 16px, e vive apenas na barra lateral — nunca sobe para o cabeçalho. É `NavGlyphIcon` (`src/components/icons/NavGlyphIcon.tsx`), usado nos subitens de PNE, Financiamento e nas páginas de Educação que não são uma das cinco frentes (Visão geral, Panorama, Educação Superior, Cenários, Metodologia). Cada glifo nasce do vocabulário da própria aba — balança para metas legais, ônibus para transporte escolar, bússola para a visão geral — e nenhum repete o ícone do próprio grupo.

A distinção é o que evita que a novidade do selo se dilua: uma tela onde *tudo* tem selo não orienta mais que uma sem nenhum. Selo é para as cinco frentes; para o resto, um glifo mais quieto basta.

## Componentes

### Botões
- **Forma:** cantos de controle (7px), altura de alvo de 44px.
- **Primário:** fundo Verde Institucional, texto invertido, padding 9px 12px.
- **Secundário:** fundo Papel, texto Tinta, borda 1px em `--border-card`.
- **Hover / Foco:** transição de 120ms em `cubic-bezier(0.22, 1, 0.36, 1)`; foco visível com anel de 3px em verde a 24% de opacidade. Foco nunca é removido.

### Chips
- **Estilo:** fundo Papel, borda 1px, cantos de 7px. Usados como filtro de tema e de etapa.
- **Estado:** selecionado troca para fundo Verde Sereno, texto Verde Profundo e borda Verde Institucional. A seleção nunca depende só de cor — o contorno também muda.

### Cartões e contêineres
- **Cantos:** 10px para cartão de página e de indicador; 7px para bloco interno.
- **Fundo:** Papel. Faixa interna em Papel Elevado. Bloco de leitura/interpretação em Verde Sereno.
- **Sombra:** Repouso por padrão; Hover apenas quando o cartão é navegável.
- **Borda:** 1px em `--border-card`.
- **Respiro interno:** 20px no cartão, 24px no painel maior, 12px por 16px na faixa interna.
- **Medida compartilhada:** cartões de indicador alinham por `min-height` e linhas mínimas (`minmax(x, auto)`), **nunca** por altura travada. Altura fixa truncava o valor do indicador e abria vazios em cartão de conteúdo curto.

### Campos
- **Estilo:** fundo Papel, borda 1px, cantos de 7px, altura de 44px.
- **Foco:** borda passa a Verde Institucional e o anel de foco aparece.
- **Placeholder:** segue o mesmo piso de 4,5:1 do corpo de texto — não é um cinza mais claro.

### Navegação
Barra lateral em Verde Institucional Escuro, com grupos expansíveis. Item ativo ganha fundo mais claro e peso 600. Todo subitem leva um ícone: nas cinco frentes de indicador é o selo de domínio da seção; nos demais — PNE, Financiamento e as páginas de Educação fora das cinco frentes — é o glifo de orientação (ver [Assinatura](#assinatura-selos-de-domínio)). O ícone herda a cor do rótulo nos três estados de navegação, sem uma quarta tinta própria. Em celular vira menu sob botão, com foco preso enquanto aberto.

### Gráficos
Eixo Y de escala limitada (percentual, IDEB, INSE) usa `getBoundedDomain` em `src/utils/chartDomain.js`. A regra ocupa a área disponível **e** impõe um vão mínimo visível — 20 p.p. em percentual, 2 pontos em IDEB/INSE — para que variação pequena não vire escalada. A referência normativa entra no cálculo do domínio, de modo que a linha de meta nunca caia fora do gráfico. Marcas de eixo são geradas dentro da faixa do domínio, nunca em escala fixa.

A linha do **gráfico principal do detalhe** ("Evolução do indicador") assume a tinta escura da seção — a mesma família do acento — dando ao gráfico a identidade da frente em que se está, com contraste ≥3:1 sobre o cartão. Só a série principal segue esse acento; gráficos de apoio e comparações por recorte mantêm cores próprias, para não perder a distinção entre séries. A cor da linha é decidida em CSS, não no atributo inline do SVG: `var()` de escopo de seção não resolve dentro de atributo de apresentação, só variável de `:root`.

### Tabelas
O componente de assinatura do sistema. Cabeçalho em Verde Sereno com texto Verde Profundo, altura de linha de 44px, célula com 12px por 16px, numeral tabular e alinhamento à direita em coluna numérica. Toda tabela larga vive dentro de uma região rolável com nome acessível. A tabela é o registro preciso: quando houver visualização ao lado, ela é que carrega o valor exato e a alternativa textual.

### Propriedade dos estilos de Educação

`src/styles/education-pages.css` é somente o manifesto ordenado do domínio. A sequência de `@import` preserva a cascata e é um contrato validado por `npm run test:ui-architecture`; não coloque seletores nesse arquivo nem importe seus módulos filhos diretamente em componentes.

- Gramática compartilhada: `education-pages-base.css`, `education-page-shell.css`, `education-compact-entry.css`, `education-detail-layout.css` e `education-pages-refinements.css`.
- Rotas e experiências: `education-higher-education.css`, `education-demand.css`, `education-methodology.css`, `education-sistema-s.css`, `education-overview.css`, `education-landing.css`, `education-attendance-summary.css` e `education-technical-report.css`.
- Composições de detalhe: `education-indicator-support-data.css`, `education-school-infrastructure.css` e `education-school-infrastructure-report.css`.

Uma regra nova entra no arquivo responsável pela superfície que a consome. Quando uma regra compartilhada precisar mudar, edite sua origem canônica e preserve a posição do módulo no manifesto; não crie um override tardio em outro arquivo apenas para vencer especificidade.

## Fazer e evitar

### Fazer
- Consumir cor, raio, sombra, espaçamento e tamanho de fonte dos tokens em `src/styles/design-tokens.css`. Valor literal em CSS de domínio é regressão.
- Colocar participação e proporção **dentro do cartão**, abaixo do valor (`61,8% da Educação Básica`), em vez de criar gráfico separado ao lado da tabela.
- Dar `overflow-x: auto` ao contêiner de qualquer elemento com `min-width`.
- Preservar zero, ausência, não aplicabilidade, carregamento, erro e vazio como estados visualmente distintos.
- Verificar contraste no resultado renderizado, não na intenção.
- Usar `getBoundedDomain` para eixo de escala limitada, em vez de fixar 0–100.
- Manter ícone de UI em viewBox 24×24, traço 1,7 e um dos quatro tamanhos da escala.
- Usar o selo de domínio só na barra lateral e no eyebrow do cabeçalho — os dois lugares definidos, nem mais nem menos.
- Dar ícone a todo subitem de navegação: selo nas cinco frentes, glifo de orientação (`NavGlyphIcon`) no restante — mas o glifo fica só na barra lateral, não vira identidade.

### Evitar
- `clamp()`, `em` ou `%` para tamanho de fonte. Só `rem` da escala.
- Abrir seção com kicker em caixa alta tracked.
- Tarja lateral colorida avulsa acima de 1px. A única exceção é a barra de acento da seção, nas fatias definidas (ver A Regra da Tarja Deliberada).
- Menta cheia (Verde Sereno) em bloco de destaque amplo — em superfície grande ela destoa; prefira Papel Elevado com um fio de acento.
- Aninhar cartão dentro de cartão. Se precisa de agrupamento interno, use faixa em Papel Elevado.
- Travar altura de cartão para alinhar uma grade.
- Vermelho/âmbar/verde como semáforo de mérito sobre resultado municipal.
- Empilhar override em CSS de domínio para vencer a cascata — o manifesto `education-pages.css` carrega por último e vence. Edite a regra no módulo responsável listado pelo próprio manifesto.
- Repetir o selo de domínio em cartão de indicador ou em cabeçalho de agrupamento interno.
