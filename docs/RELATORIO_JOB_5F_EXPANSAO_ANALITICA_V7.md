# RELATÓRIO DO JOB 5F — EXPANSÃO ANALÍTICA E INVENTÁRIO MÁXIMO DE RELAÇÕES — V7

## Veredito

`JOB_5F_PARTIAL_EXPANSION_WITH_DATA_GAPS`

O Job 5F encontrou valor analítico material além dos quatro módulos atuais, mas parte relevante do inventário depende de processamento adicional ou de fontes públicas ainda ausentes. O estado `COMPLETE` não seria honesto porque sete oportunidades substantivas ficaram sem dados suficientes e outras 31 ainda requerem testes.

## Objetivo e classificação

- **Objetivo:** produzir um inventário máximo, estruturado e rastreável de relações capazes de responder às duas direções da gestora, sem fechar portfólio nem implementar interface.
- **Classificação:** `DATA_LOGIC`, envolvendo demografia, educação, mobilidade, trabalho, EJA, EPT e monitoramento PNE.
- **Recorte territorial:** Vale do Sinos, dez municípios; caso obrigatório Nova Santa Rita (`4313375`).
- **Rede educacional:** `total_all_dependencies` em todas as linhas.
- **Uso de dependência administrativa:** apenas reconstrução, fechamento, disponibilidade, proveniência e QA; nunca dimensão analítica.

## Inventário reexaminado

O levantamento local confirmou 66 conjuntos lógicos de dados e 73 análises/subanálises solicitadas nos inventários anteriores. Foram reusados 20 artefatos congelados do Job 2, somando 840.105 linhas, além de contratos, decisões, matrizes e manifestos dos Jobs 3, 5A, 5B, 5D e 5E-Produto.

Séries efetivamente reprocessadas no 5F:

- taxas oficiais municipais de aprovação, reprovação, abandono e distorção;
- alunos por turma, adequação docente, conectividade, infraestrutura disponível e INSE;
- população/coortes, matrículas, escolas, turmas, mobilidade e cenários mecânicos;
- público adulto/EJA 2022 e histórico de EJA/EJA integrada;
- RAIS jovem por idade/escolaridade/CBO/CNAE, Caged jovem/aprendiz;
- cursos técnicos, eixos, concentração territorial e ponte CBO–CNCT.

Séries confirmadas no projeto, mas não reprocessadas no 5F:

- nascimentos, docentes, horas-aula, tempo integral, esforço e regularidade docente;
- SAEB, escolaridade adulta 2010/2022, EPT por modalidade;
- diagnósticos/comparadores PNE, educação especial/AEE, educação rural;
- CadÚnico, finanças educacionais e PNATE.

## Famílias examinadas

Foram representadas as 30 famílias mínimas pedidas e oito extensões sugeridas pelos dados:

1. demografia × matrículas × oferta;
2. demografia × escolas × turmas × docentes;
3. coortes × transições;
4. matrícula × rendimento;
5. matrícula × distorção;
6. trajetória × IDEB/SAEB;
7. trajetória × condições;
8. trajetória × horas-aula;
9. trajetória × alunos por turma;
10. trajetória × formação/esforço/regularidade docente;
11. trajetória × infraestrutura/conectividade;
12. trajetória × INSE;
13. trabalho juvenil × ensino médio;
14. aprendizagem profissional × jovens × educação;
15. RAIS/Caged juvenil × trajetória;
16. escolaridade dos trabalhadores × ocupações;
17. ocupações em mudança × formação profissional;
18. setores × cursos/eixos;
19. CBO × CNCT/EPT;
20. público adulto × EJA fundamental;
21. público adulto × EJA médio;
22. escolaridade adulta 2010→2022 × EJA;
23. EJA × educação profissional;
24. mobilidade × etapa;
25. mobilidade × oferta;
26. mobilidade × demografia;
27. mobilidade × trajetória;
28. nascimentos/coortes × demanda futura;
29. transformação econômica × agenda educacional;
30. cenários/coortes/tendências × indicadores PNE;
31. EPT × estrutura da rede;
32. concentração territorial da oferta e do trabalho;
33. educação especial × território;
34. ruralidade × demografia/oferta;
35. vulnerabilidade × EJA/trajetória;
36. transporte/PNATE × mobilidade;
37. finanças × capacidade de oferta;
38. diagnósticos/comparadores PNE × agenda municipal.

## Resultado da matriz mestra

Foram identificadas 67 oportunidades, 38 na Direção 1 e 29 na Direção 2:

| Estado | Quantidade |
|---|---:|
| `PROMISING` | 15 |
| `PROMISING_NEEDS_MORE_TESTING` | 31 |
| `DESCRIPTIVE_ONLY` | 9 |
| `INSUFFICIENT_DATA` | 7 |
| `REDUNDANT` | 2 |
| `REJECTED` | 3 |
| **Total** | **67** |

A matriz não usa score único. Cada linha contém os 24 campos obrigatórios, incluindo lentes, dados presentes/ausentes, período, método, evidência regional e municipal, Nova Santa Rita, limitações, planejamento, visual, indicadores, estado e motivo.

## Relações mais promissoras

1. **Ritmos demográficos, matrículas e organização da oferta.** O Vale retrai no fundamental e médio enquanto Nova Santa Rita cresce; a leitura conjunta de escolas e turmas mostra reorganização que a demografia isolada não explicaria.
2. **Coortes como pressão mecânica.** O médio em 2030 equivale a 131,47% da base regional 2025 e 164,17% em Nova Santa Rita, sem tratar o resultado como previsão.
3. **Trajetória municipal oficial descritiva.** Nova Santa Rita elevou a aprovação do médio em 20,80 pp e reduziu distorção em 18,50 pp; o Vale é descrito pela distribuição de dez municípios, nunca por taxa recomposta.
4. **Mobilidade por etapa.** O médio apresenta 15,09% no Vale e 19,11% em Nova Santa Rita, gerando agenda concreta de coordenação, ainda sem destino observável.
5. **Distribuição do público adulto e da EJA.** Nova Santa Rita concentra 2,74% do público regional sem fundamental e 5,39% das matrículas, mas 3,49% do público sem médio e apenas 0,89% das matrículas.
6. **EJA integrada à educação profissional.** A participação regional ficou em 1,37% em 2025 e Nova Santa Rita registrou zero observado, evidência útil sem afirmar ausência de acesso.
7. **Trabalho juvenil e aprendizagem.** Vínculos 15–17 cresceram de 2.483 para 4.225 no Vale; admissões de aprendizes dessa idade passaram de 1.235 para 3.157 entre 2020 e 2025.
8. **Mudança ocupacional, EPT e concentração.** Auxiliar de logística cresceu de 606 para 4.248 no Vale e de 17 para 722 em Nova Santa Rita; a EPT segue concentrada em sete municípios e a ponte CBO–CNCT cobre 90,81% das matrículas, com limite normativo explícito.

## Valor incremental além dos quatro módulos atuais

- abre uma frente descritiva legítima de trajetória oficial sem reabrir H2;
- transforma mobilidade em agenda por etapa e governança intermunicipal;
- separa EJA fundamental, EJA médio, mudança histórica e integração profissional;
- inclui docentes, jornada, tempo integral, infraestrutura, INSE, vulnerabilidade, ruralidade e educação especial como frentes próprias de teste;
- distingue trabalho juvenil, aprendizagem, escolaridade dos vínculos, ocupações, setores e concentração da EPT;
- converte coortes em painel de pressões por meta, sem apresentar previsão;
- torna explícitas as necessidades de destino da mobilidade, componentes exatos das taxas, OD trabalho e cenários demográficos validados.

## Regra específica de H2 preservada

- **Permitido:** evolução e magnitude da taxa oficial municipal, comparação entre anos do mesmo município, distribuição municipal e formulação de perguntas.
- **Proibido:** taxa regional por soma ou média, ponderação inventada, regra de pequeno denominador sem denominador, afirmação de estabilidade dependente do denominador e retrocálculo.
- **Estado congelado:** `H2_TRAJETORIA_MUNICIPAL_V2` não foi alterado nem restaurado.

## Fórmulas e métodos

Foram preservadas as fórmulas dos Jobs anteriores. O 5F apenas aplicou, conforme a pergunta:

- variação absoluta, relativa e em pontos percentuais;
- decomposição de matrícula em componente populacional e componente da relação matrícula/população, com resíduo de fechamento;
- distribuição e contribuição municipal;
- pressão mecânica de coortes relativa à matrícula-base 2025;
- HHI para concentração por município/eixo;
- correlação de postos de Spearman apenas como associação ecológica descritiva;
- ponte CBO–CNCT como correspondência normativa parcial, não aditiva.

Nenhum coeficiente aprovou automaticamente uma oportunidade e nenhuma causalidade foi inferida.

## Artefatos

### Materialização controlada

- `.tmp/vocacoes-pne/v7-job5f/master_analytical_opportunities.csv.gz` — matriz, 67 linhas;
- `.tmp/vocacoes-pne/v7-job5f/master_analytical_opportunities.json` — matriz legível e tipada;
- `.tmp/vocacoes-pne/v7-job5f/exploratory_evidence.json` — evidência numérica;
- `.tmp/vocacoes-pne/v7-job5f/source_inventory.json` — inventário de fontes;
- `.tmp/vocacoes-pne/v7-job5f/qa.json` — QA;
- `.tmp/vocacoes-pne/v7-job5f/output_inventory.json` — inventário de outputs;
- `.tmp/vocacoes-pne/v7-job5f/manifest.json` — manifesto operacional.

### Código, contrato e documentação

- `data_pipeline/contracts/vocacoes-pne-v7-job5f.json`;
- `data_pipeline/src/vocacoes_pne_job5f.py`;
- `data_pipeline/scripts/run_vocacoes_pne_v7_job5f.py`;
- `data_pipeline/tests/test_vocacoes_pne_job5f.py`;
- `data_pipeline/manifests/MANIFEST_JOB5F_ANALYTICAL_EXPANSION_V7.json`;
- `docs/MAPA_PAGINA_MAXIMA_GESTORA_V7.md`;
- `docs/MAPA_LACUNAS_ANALITICAS_POS_5F_V7.md`;
- este relatório.

Nenhum arquivo foi removido ou movido.

## Hashes principais

| Artefato | SHA-256 |
|---|---|
| Manifesto operacional 5F | `0980d08fa60ee0b15633ff58b6f4df80eaa8f5357d5c1248bf4e8f9a836d31d0` |
| Matriz CSV.GZ | `dbd1f71f41533fad3dfa2e09961cd93d8b1ea7a736a2785f775a0684069aab11` |
| Matriz JSON | `ad9e2771ef1988e6f66cf6f7cf13db0b6e91f3fdd19e7fc8f9c96182814e5c24` |
| Evidência exploratória | `43fd4e913e9e4f6f21a3caedc6e006ca9eeb3d0a1ee4b64a9968317a167185cb` |
| Inventário de fontes | `7e56bd5b4c5accdbfd74cb45da9775094088bac23e66c2304eb85d883dd8ee74` |
| QA | `a6448d026c2e6921e062ab8594b7e4a2381ee02b8c6b5546b84e7bd75611ab0b` |

Os hashes congelados de 5B, 5D e 5E-Produto foram verificados como inputs do manifesto e não foram modificados.

## QA executado

- parsing/compilação Python;
- teste focado do Job 5F: 3 testes aprovados;
- schema e 24 colunas obrigatórias;
- 67 IDs únicos, sem duplicidade;
- paridade CSV/JSON;
- chaves, tipos e campos obrigatórios sem nulos;
- distinção entre zero observado e ausência;
- rede total em todas as linhas;
- ausência de dependência administrativa analítica;
- ausência de score único;
- preservação do estado H2;
- `--check` sobre os artefatos existentes;
- segunda materialização com resultado `unchanged`;
- `npm run check:fast`: typecheck, lint, compilador narrativo em modo `--check` e build app-only aprovados;
- `git diff --check` focado no Job 5F aprovado sem saída;
- `git diff --check` global com código zero, embora o checkout preexistente tenha emitido avisos de permissão em dados já ausentes e conversão LF/CRLF em arquivos alheios;
- cobertura documental: 55/55 oportunidades elegíveis presentes no mapa máximo e nenhuma oportunidade `INSUFFICIENT_DATA`, `REDUNDANT` ou `REJECTED` incorporada.

## Efeito, ambiente e estado operacional

- **Dados públicos:** nenhum efeito do Job 5F; `public/data` não foi escrito. As deleções já presentes no checkout foram preservadas e não pertencem a este job.
- **Interface:** React, CSS, rotas e componentes não foram alterados pelo Job 5F.
- **Publicação:** não executada.
- **Job 6:** não iniciado.
- **Banco:** não utilizado.
- **Rede:** não utilizada.
- **Build completo:** não executado.
- **Git:** nenhum commit, push, tag, reset, stash ou alteração destrutiva; o checkout já estava amplamente sujo por trabalhos anteriores e essas mudanças foram preservadas.

## Pendências e parada

As lacunas prioritárias estão em `MAPA_LACUNAS_ANALITICAS_POS_5F_V7.md`. O próximo passo é exclusivamente o julgamento externo do GPT-5.6 Pro sobre quais relações merecem testes adicionais. Este job para aqui: não seleciona portfólio final, não pede decisão A/B/C e não inicia protótipo visual.
