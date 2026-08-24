# Caderno de hipóteses — validação da curadoria em amostra municipal (2026-08-17)

Registro da validação proposta após a revisão de seletividade: aplicar a curadoria
universal a uma amostra diversa de municípios do RS e verificar, antes de avançar
às fases seguintes da rota (`docs/CADERNO_BALANCO_E_ROTA.md`), quatro riscos:

1. as mesmas hipóteses aparecerem excessivamente em todos os municípios;
2. cartões que quase nunca possuem sinal público;
3. títulos específicos por meta deixarem de fazer sentido fora de Nova Santa Rita;
4. o volume por objetivo deixar de ser manejável.

Tudo rodou **em área de rascunho**, fora dos artefatos publicados: nenhum arquivo de
`public/data`, do snapshot oficial da pesquisa ou das fichas do piloto foi alterado.

## Método

- Amostra de **14 municípios** do release `fadcfff3…` (497 municípios, contrato
  v1.9.0), escolhida por diversidade: Porto Alegre, Caxias do Sul, Pelotas, Canoas,
  Passo Fundo, Uruguaiana, Alegrete, Tramandaí, Redentora, Benjamin Constant do Sul,
  Engenho Velho, Westfália, Santo Augusto (caso-limite de arredondamento) e Nova
  Santa Rita (âncora).
- Para cada um: ficha diagnóstica + caderno v2 gerados pelo pipeline determinístico
  da pesquisa (referência 2026-08-14), com o snapshot oficial replicado em rascunho.
- Harness de QA: `.tmp/caderno-audit/audit_caderno_sample.py` (construção mecânica
  delegada ao Codex `gpt-5.6-sol/xhigh` sob spec; execução e conferência da revisão).
  Saídas em `audit-out/` no scratchpad da sessão. Aceitação: a linha do piloto
  reproduz o publicado (meta 4 → 7 cartões; metas 15 e 16 → 0). **Confirmado.**
- Os 14 builds completaram sem erro.

## Resultados

### 1. Repetição entre municípios

- 83 pares meta×fator observados; **65 caem na mesma camada nos 14 municípios**.
- Toda a camada de contexto e os 15 cartões de oficina são universais **por
  construção** (curadoria e ausência de base pública não variam por município).
- O achado relevante: **14 pares "com indício" são adversos em 14 de 14** —
  frequência/busca ativa (metas 3, 4, 5, 11), bases de leitura e matemática (3, 5),
  reprovação (4), desastres (4, pós-enchente estadual), infraestrutura (6, 8, 19),
  inclusão/AEE (10), oferta de EJA (11) e professores fora da área (17). Causa
  estrutural: metas legais de 100% (ou quase) que praticamente todo município viola,
  mais sinal agregado municipal.
- **18 pares discriminam de verdade** entre municípios, com giro completo de camada:
  distância/transporte (adverso em 12, protetivo em 2), custo da creche na meta 1
  (adverso 7 · oficina 1 · protetivo 6), tempo de aula (10/4), internet e
  equipamentos (6 adversos/8 protetivos), trabalho (13/1), participação (12/2).

Leitura: não é defeito da curadoria — é o **teto do sinal municipal agregado**. A
consequência prática está em "Implicações".

### 2. Cartões sem sinal público

- Os **15 cartões da camada "verificar na oficina" têm zero sinal valorado nos 14
  municípios** — coerente com a definição da camada, mas confirma que são idênticos
  no estado inteiro: seu conteúdo é roteiro de verificação, não leitura local.
- Nenhuma patologia na camada "com indício": todo cartão exibido tem sinal valorado
  em 87,5–100% dos municípios em que aparece (piso: custo da creche 87,5%;
  trabalho 92,9%; o restante 100%).

### 3. Títulos específicos por meta

- **Defeito real encontrado e corrigido.** Os títulos e textos específicos por meta
  (`FACTOR_TITLE_BY_GOAL`/`FACTOR_PLAIN_BY_GOAL`) são formulados como causa e eram
  aplicados também a cartões protetivos: em 6 dos 14 municípios (Caxias do Sul,
  Passo Fundo, Uruguaiana, Westfália, Engenho Velho, Benjamin Constant do Sul), a
  meta 1 exibiria "Ponto forte a proteger — **Custo para a família manter a criança
  na creche**", com corpo afirmando que a família "adia ou desiste da vaga".
- Correção aplicada (2026-08-17, `UI_ONLY`): `resolvePlainCause` ganhou a variante
  `protective`, que ignora a reescrita específica por meta e usa o título/corpo
  neutros do fator. `typecheck`, `test:caderno` (27), `test:app-routing` (17),
  lint dirigido e `build:app` verdes. O piloto não muda (lá o fator é adverso).
- Nos demais vínculos com título específico (metas 6, 8, 17, 19) não houve
  contradição observada na amostra — na amostra inteira eles caem como causa.

### 4. Volume por objetivo

- Máximo continua **7 cartões-causa** (meta 4, que reúne 4 metas legais), idêntico
  ao piloto; todas as demais metas ficam com ≤ 5 em todos os municípios.
- Total de cartões-causa por município: **36 a 47**. O teto do catálogo (47) é
  atingido por 4 municípios; os menores exibem menos porque indicadores sem dado
  suprimem a meta ou porque o sinal vira protetivo.

## Veredito

**A curadoria de seletividade sobrevive fora do piloto.** Volume manejável em toda
a amostra, nenhum cartão "com indício" órfão de sinal, e o único defeito real
(título por meta em cartão protetivo) era de camada editorial, já corrigido.

**As fases 1 e 3 da rota deixam de ser desejáveis e passam a ser necessárias**: com
14 dos cartões de indício idênticos no estado inteiro e os 15 de oficina universais
por construção, a diferenciação municipal que o gestor precisa não virá da camada de
curadoria — virá de **"onde isso aparece"** (por escola, etapa e disciplina, Fase 1)
e dos **instrumentos disponíveis** por causa (Fase 3). A validação confirma a ordem
proposta na rota e não recomenda nenhuma mudança na tabela de curadoria.

Pendência conhecida que a amostra reforça: os textos genéricos de alguns fatores
agora exibíveis como protetivos (distância, internet, tempo de aula, participação)
são legíveis, mas foram escritos em enquadramento de causa; uma revisão editorial
curta desses corpos na variante protetiva é recomendável junto da Fase 3.

## Reprodução

```
# venv do pipeline de pesquisa
C:\Users\rnbirck\PROJETOS\SESI\PNE\data_pipeline\.venv\Scripts\python.exe ^
  .tmp\caderno-audit\audit_caderno_sample.py
```

O script copia os municípios da amostra para um snapshot de rascunho, gera ficha e
caderno por município e agrega `cards.csv`, `indicators.csv`, as quatro tabelas Q1–Q4
e `REPORT.md`. Ele escreve somente no scratchpad da sessão; os caminhos estão
fixados no cabeçalho do script.
