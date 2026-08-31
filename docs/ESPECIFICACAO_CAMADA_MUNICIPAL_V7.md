# Especificação da camada municipal — V7

**Classificação:** `DOCUMENTATION_ONLY`
**Uso:** contrato editorial interno; sem texto público, interface ou publicação

## 1. Bloco dinâmico obrigatório

Cada módulo disponível deve conter “No município selecionado” com os campos:

1. `municipality_ibge_code`: texto de sete dígitos;
2. `module_id` e `approved_fact_ids`;
3. fato municipal e contraste com o Vale na mesma etapa, período, unidade e lente;
4. período e fontes;
5. indicador de acompanhamento;
6. questão específica de planejamento;
7. contexto de ação, acompanhamento ou articulação;
8. inferências proibidas;
9. `publication_allowed_now=false`.

Nome e slug são apenas apresentação e rota. O bloco não faz join por nome, não
usa o índice público como universo e não expõe dependência administrativa como
dimensão analítica.

## 2. Regra comum de seleção

O fato municipal precisa ser aprovado, reconstruível e produzir diferença útil
ou questão específica. O contraste usa o Vale quando o agregado compatível
existe; ausência de agregado não pode ser substituída por mediana municipal sem
rótulo. Se não houver fato aprovado no módulo, o módulo não inventa conteúdo
municipal.

A ordem de preferência é: mesmo período e etapa; mesma unidade; mesma lente;
diferença útil; questão concreta; não redundância. A regra não produz score,
ranking ou prioridade numérica.

## 3. Especificação por módulo

| Módulo | Fato municipal | Diferença para o Vale | Acompanhamento | Questão | Contexto permitido | Não inferir |
|---|---|---|---|---|---|---|
| H1 | população compatível, matrícula, escolas e turmas por etapa, 2014–2025 | direção e intensidade na mesma etapa e janela | série anual das quatro grandezas | onde preservar acesso, reorganizar oferta e acompanhar transições | planejamento municipal, diálogo com Estado e coordenação regional | causa, taxa individual, dependência responsável, decisão automática sobre escola |
| H4 | participações de público residente e matrícula localizada, por etapa, 2022 | diferença distributiva de cada etapa no universo regional | próxima fotografia compatível; matrícula anual em contexto separado | como acompanhar a distribuição local e regional de cada etapa | articulação entre atores da EJA | medida individual, sentido único, proximidade sem limiar |
| A3 | movimentos RAIS de ocupações/setores e composição formativa observada | composição local do trabalho e distribuição regional da formação, em lentes separadas | estoque RAIS, cursos/eixos, matrículas, concentração e cobertura da ponte | que observação e articulação territorial organizar | municípios, Estado, ofertantes e Sistema S | pessoa, efeito do curso, necessidade futura, destino do estudante |
| A4 | total de residentes estudantes, total que estudava fora e participação, por etapa, 2022 | diferença em pontos percentuais para Vale e RS | mesma tríade na próxima fotografia compatível | que rotina de transição e diálogo territorial organizar | transporte como contexto, monitoramento e coordenação | destino, rota, receptor, vaga, capacidade ou ente responsável |

## 4. Nova Santa Rita — IBGE `4313375`

### H1

- Fatos: fundamental 3.873→3.957 matrículas (`+2,1689%`) enquanto o Vale foi
  117.469→104.328 (`-11,1868%`); médio 799→840 (`+5,1314%`) enquanto o Vale foi
  31.789→26.911 (`-15,3449%`); escolas 24→28 no recorte municipal agregado.
- Período/fontes: 2014–2025; população por residência e Censo Escolar por escola,
  materializações Job 2E e fatos Job 3.
- Acompanhamento: população compatível, matrículas, escolas e turmas por etapa.
- Questão: como organizar ritmos de oferta e transições quando o município segue
  direção diferente do Vale?
- Contexto: ação municipal e diálogo estadual/regional conforme a etapa, sem
  estratificar resultados.
- Limite: não inferir causa nem abertura/fechamento automático de escola.

### H4

- Fundamental: público residente 6.068; matrículas 298; participação no público
  regional `2,742475%`; participação nas matrículas `5,390738%`; diferença
  `+2,648263 pp`.
- Médio: público residente 4.447; matrículas 82; participação no público regional
  `3,491485%`; participação nas matrículas `0,886391%`; diferença `-2,605095 pp`.
- Período/fontes: fotografia 2022; população residente por escolaridade e EJA por
  localização da escola; Jobs 2C, 3 e correção C9.
- Acompanhamento: duas participações por etapa; série anual de matrículas apenas
  em contexto independente.
- Questão: que articulação acompanhará os sentidos distintos do fundamental e
  do médio?
- Contexto: EJA em rede total e coordenação territorial.
- Limite: não produzir uma direção única nem medida individual.

### A3

- Fatos: vínculos RAIS por estabelecimento 8.473→11.591 entre 2019 e 2025
  (`+36,7992%`); motorista de caminhão 941→1.193, auxiliar de logística 17→722,
  conferente de carga e descarga 202→385 e operador de empilhadeira 115→292.
- Contraste: a composição municipal envolve logística, transporte, administração
  e comércio; os cursos/eixos mapeados observados estão distribuídos no Vale. O
  zero observado local no recorte de cursos não é a conclusão.
- Período/fontes: RAIS 2019–2025 por estabelecimento; oferta por escola
  2023–2025; ponte 2025; Jobs 2D, 3 e dossiê 4A.
- Acompanhamento: estoque por subgrupo/ocupação/setor; composição regional de
  cursos/eixos; concentração e cobertura da ponte.
- Questão: que observação e articulação entre território e instituições
  ofertantes deve acompanhar essas composições separadas?
- Contexto: articulação municipal, estadual, regional, ofertantes e Sistema S.
- Limite: não inferir deslocamento, efeito formativo, resultado laboral ou
  necessidade de oferta.

### A4

- Total: 1.349 de 7.666 residentes estudantes estudavam fora (`17,5972%`), ante
  `14,7611%` no Vale e `8,8148%` no RS.
- Fundamental: 355 de 4.090 (`8,6797%`), ante `7,0120%` no Vale e `3,3018%` no RS.
- Médio: 220 de 1.151 (`19,1138%`), ante `15,0898%` no Vale e `8,2202%` no RS.
- Período/fonte: fotografia 2022, residência do estudante; Job 2E e matriz A4 do
  Job 5A.
- Acompanhamento: contagem e participação por etapa na próxima fotografia.
- Questão: como acompanhar transição, transporte como contexto e diálogo
  territorial, sobretudo no médio?
- Contexto: monitoramento municipal e coordenação regional/estadual.
- Limite: `destination_available=false`; estudar fora não é falha em si.

## 5. Síntese municipal de até três leituras

A seleção combina cinco critérios, sem pontuação: diferença útil frente ao
Vale; questão específica; cobertura das duas direções; não redundância; e
preservação das lentes. Se quatro módulos tiverem fatos, dois podem ser
articulados numa leitura somente quando permanecerem explicitamente
independentes e não houver inferência conjunta.

Para Nova Santa Rita, a arquitetura seleciona:

1. demanda e organização observada (H1);
2. distribuição da EJA por etapa (H4);
3. duas razões independentes para coordenação territorial (A3 e A4).

Essa seleção não rebaixa o módulo não destacado em outros municípios e não cria
ranking de prioridades.
