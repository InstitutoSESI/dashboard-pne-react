# Pacote de revisão externa — Job 5C V7

**Classificação:** `DOCUMENTATION_ONLY`
**Checkpoint:** pós-Job 5B; antes de narrativa pública, compilador e interface
**Veredito proposto pelo executor:** `JOB_5C_READY_FOR_EXTERNAL_PRODUCT_JUDGMENT`

## 1. Decisão solicitada ao julgador

Julgar se a arquitetura interna responde às duas perguntas da gestora com os
quatro módulos autorizados, preserva as lentes e os limites semânticos e define
uma camada municipal útil sem antecipar conteúdo de H2 ou autoria pública.

## 2. Arquitetura submetida

### Direção 1 — o território ajuda a compreender a educação

1. H1 — demografia, demanda e organização da oferta;
2. H4 — EJA, escolaridade adulta e distribuição da oferta.

### Direção 2 — o território coloca temas na agenda da educação

1. A3 — ocupações e formação profissional;
2. A4 — mobilidade e coordenação regional.

A arquitetura condicional reserva trajetória entre H1 e H4, mas não preenche o
espaço. O portfólio não usa “2+2” como conceito editorial.

## 3. Artefatos do Job 5C

| Artefato | Função |
|---|---|
| `ARQUITETURA_EDITORIAL_INTERNA_POS_JOB5B_V7.md` | percurso, módulos e duas visões |
| `MATRIZ_MODULOS_APROVADOS_POS_JOB5B_V7.csv` | contrato tabular dos quatro módulos |
| `ESPECIFICACAO_CAMADA_MUNICIPAL_V7.md` | bloco dinâmico e regra de seleção |
| `SINTESE_NOVA_SANTA_RITA_INTERNA_V7.md` | três leituras internas do caso obrigatório |
| `MAPA_LACUNAS_PARA_PAGINA_GESTORA_POS_JOB5B_V7.md` | lacunas, posição condicional e gates |
| `MATRIZ_FATO_MENSAGEM_FONTE_PERIODO_V7.csv` | rastreabilidade de fatos e mensagens internas |
| `PACOTE_REVISAO_EXTERNA_JOB5C_V7.md` | pacote de julgamento |
| `data_pipeline/manifests/vocacoes-pne-v7-job5c-release.json` | tamanhos, SHA-256, entradas e QA |

## 4. Evidência e precedência inspecionadas

- plano mestre de aprofundamento;
- decisão canônica de rede total;
- julgamento externo final e matriz do Job 4B;
- aditivo provisório e pré-registro/plano do Job 5A;
- contratos e manifest/pacote factual do Job 5A;
- contrato e manifest/pacote corrigido do Job 5B;
- artefatos e relatórios dos Jobs 2E, 2C, 2D e 3;
- dossiê/matriz A3 do Job 4A e correções C9;
- fatos H1/H4/A3 do Job 3 e matriz/síntese A4 do Job 5A;
- briefing mais recente do responsável pelo produto.

Os artefatos congelados anteriores foram apenas lidos. Nenhum foi corrigido ou
normalizado no lugar.

## 5. Checkpoint factual

| Módulo | Período principal | Fonte/lente | Limite decisivo |
|---|---|---|---|
| H1 | 2014–2025 | população residente + escola | não misturar com 2015–2025; sem decisão automática sobre escola |
| H4 | 2022 | residente + escola | fundamental e médio separados; medida distributiva |
| A3 | RAIS 2019–2025; formação 2023–2025; ponte 2025 | estabelecimento + escola | ponte parcial/não aditiva; somente movimento líquido observado |
| A4 | 2022 | residência do estudante | `destination_available=false` |

## 6. Nova Santa Rita

A camada contém fatos aprovados dos quatro módulos. A síntese usa três leituras:

1. ritmos locais de população, matrícula e organização da oferta;
2. sentidos distintos da distribuição de EJA no fundamental e no médio;
3. duas evidências independentes de coordenação: composição trabalho–formação e
   mobilidade por residência.

A terceira leitura não cruza pessoas ou fontes. H2 está ausente.

## 7. Lacunas preservadas

- H2 depende de denominador exato, regra de pequeno denominador, C5 integral e
  novo julgamento;
- A3 não tem teste próprio de persistência e a ponte permanece parcial;
- A4 não informa destinos;
- cenários do Vale dependem de job e decisão próprios;
- validação humana e Gate 11 permanecem pendentes.

H3, A1 e A2 não foram restauradas; contexto juvenil opcional não foi usado;
nenhuma candidata foi criada.

## 8. QA documental

O julgamento deve confirmar:

- somente H1, H4, A3 e A4 como módulos disponíveis;
- H2 apenas como lacuna/posição condicional, sem fatos editoriais;
- rede total em toda análise educacional;
- dependência administrativa somente em QA e contexto institucional não
  atributivo;
- separação entre residência, escola, mobilidade e trabalho;
- fontes e períodos em toda mensagem proposta;
- ausência de causalidade e de número inventado;
- termos proibidos presentes somente na documentação de limites, nunca como
  alegação permitida;
- Nova Santa Rita nos quatro módulos e em até três leituras de síntese;
- `publication_allowed_now=false` em todas as linhas das matrizes;
- ausência de alteração em `public/data`, React, CSS, rotas e artefatos
  congelados;
- manifest com bytes e SHA-256 e CSVs parseáveis;
- repetibilidade: sem relógio, rede, banco ou entrada mutável na geração.

## 9. Perguntas ao julgamento externo

1. A ordem H1→H4→A3→A4 produz um percurso coerente sem sugerir causalidade?
2. A posição condicional de trajetória está funcionalmente bem localizada e
   suficientemente vazia?
3. Os visuais conceituais preservam as lentes e evitam comparações indevidas?
4. A regra municipal de três leituras é útil e não cria ranking opaco?
5. A síntese de Nova Santa Rita equilibra as duas direções sem exceder o envelope
   aprovado?
6. Alguma mensagem interna antecipa uma conclusão pública que deveria continuar
   reservada?

## 10. Gate

O pacote está pronto para julgamento externo de produto. Ele não abre o Gate
11, não autoriza narrativa pública, compilador, interface, publicação ou Job 5D.
