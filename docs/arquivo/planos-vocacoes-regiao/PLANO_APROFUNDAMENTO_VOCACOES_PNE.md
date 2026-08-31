# Orientação de implementação — aprofundamento analítico Vocações × PNE

**Destinatário principal:** ChatGPT 5.6 Sol, raciocínio `xhigh`
**Uso recomendado:** documento mestre para o Fable decompor em jobs independentes
**Piloto:** Vale do Sinos, com validação municipal prioritária em Nova Santa Rita (`4313375`)
**Base de trabalho:** implementação V6 auditada em 28/08/2026
**Natureza desta frente:** reconstrução analítica e de produto; não é uma rodada para apenas acrescentar gráficos ou relações estatísticas

---

## 0. Como usar este documento

Não execute todo este plano em um único job e não permita que o mesmo agente:

1. invente a análise;
2. implemente os cálculos;
3. escreva a narrativa pública;
4. aprove a própria entrega.

O Fable deve separar descoberta, materialização, análise, revisão metodológica, implementação da interface e validação humana. O ChatGPT 5.6 Sol `xhigh` é adequado para a maior parte da engenharia, dos cálculos, dos contratos, dos testes e da interface. As decisões de produto, a aprovação dos insights e a revisão final devem passar por um modelo julgador mais robusto — preferencialmente GPT-5.6 Pro — e, no fim, por uma pessoa usuária real.

Antes de qualquer alteração, leia integralmente e confronte com o repositório real:

- `PLANO_IMPLEMENTACAO_VOCACOES_PNE.md`;
- `AUDITORIA_PLANO_IMPLEMENTACAO_VOCACOES_PNE.md`;
- `INVENTARIO_DADOS_PNE_VOCACOES.md`;
- `MATRIZ_COBERTURA_ANALITICA.csv`;
- `MATRIZ_PRONTIDAO_INSIGHTS.csv`;
- `LACUNAS_REAIS_E_PRIORIDADES.md`;
- contratos, manifests, registries, geradores, testes e componentes atuais da página;
- artefatos R5/R6/R7 e a projeção narrativa do Vale do Sinos;
- dados municipais usados para Nova Santa Rita;
- catálogos de mecanismos, universos, lentes territoriais e linguagem já versionados.

Os nomes de arquivos e schemas deste documento são lógicos. Descubra e use os caminhos canônicos do projeto. Não crie uma segunda arquitetura paralela quando já existir uma estrutura equivalente.

---

# 1. Diagnóstico do ponto atual

A implementação existente é tecnicamente consistente, mas ainda responde apenas a uma parte pequena do pedido da gestão.

O estado auditado tem:

- 103 séries-raiz catalogadas;
- 16 mecanismos em sete famílias;
- 11 candidatas avaliadas;
- cinco cartões publicados;
- três cartões da primeira saída;
- dois cartões da segunda saída;
- Vale do Sinos como única região na experiência narrativa;
- Gate 11 ainda bloqueado;
- Gate 12 não aprovado.

A versão atual melhorou muito o baseline porque retirou a triagem automática, eliminou relações sem mecanismo, aplicou decomposição, mostrou diferenças municipais e criou linguagem pública rastreável. O problema agora não é confiabilidade. É **cobertura analítica e valor de produto**.

Os cinco cartões atuais concentram-se em:

1. população e matrículas na educação infantil;
2. população e matrículas no ensino fundamental;
3. população e matrículas no ensino médio;
4. coortes, envelhecimento e rede;
5. deslocamento para estudo.

Isso cobre bem a dimensão demográfica, mas ainda não entrega de forma suficiente:

- onde e como a trajetória escolar se rompe;
- como trabalho juvenil e permanência escolar aparecem no mesmo território;
- como o público adulto sem educação básica concluída se distribui em relação à EJA;
- como ocupações, setores e escolaridade do trabalho dialogam com a formação profissional;
- quais condições escolares diferenciam municípios e redes;
- quais transformações econômicas colocam temas concretos na agenda educacional;
- como a leitura regional se traduz em prioridade para o município selecionado;
- quais questões são próprias da rede municipal, da rede estadual ou da coordenação regional.

A auditoria já identificou dados subutilizados capazes de aprofundar o produto:

- população municipal anual por idade, 2014–2025;
- rendimento, abandono, reprovação e distorção por município, rede e etapa;
- Censo Escolar por escola, com turmas, docentes, jornada e infraestrutura;
- indicadores educacionais de condições e aprendizagem;
- EJA e EPT por modalidade e rede;
- adultos sem fundamental ou médio concluído nos Censos de 2010 e 2022;
- RAIS municipal por idade e escolaridade, 2019–2025;
- RAIS por setor e ocupações;
- Novo Caged local com idade, CBO, CNAE, escolaridade, salário, aprendiz e tipo de movimento;
- deslocamento para estudo em 2022, ainda sem destino municipal;
- diagnósticos, prioridades e comparadores já existentes no PNE.

Portanto, o próximo avanço não deve ser procurar mais correlações. Deve ser **materializar esses dados no mesmo grão, construir leituras integradas e reescrever a página em torno de decisões de planejamento**.

---

# 2. Objetivo final do produto

A página deve responder com clareza às duas direções solicitadas pela gestora.

## 2.1 Primeira direção — o território ajuda a compreender a educação

Partir de um resultado educacional relevante e responder:

1. o que mudou;
2. quanto da mudança acompanha a demografia;
3. o que a trajetória e a oferta acrescentam à compreensão;
4. quais características territoriais coexistem com o resultado;
5. em quais municípios, redes e públicos a situação se concentra;
6. que questão específica entra no planejamento.

A saída não deve provar causa. Também não deve se limitar a colocar duas séries lado a lado.

## 2.2 Segunda direção — o futuro do território coloca temas na agenda da educação

Partir de uma transformação territorial já observada, de uma tendência sustentada ou de um cenário publicado e responder:

1. o que está mudando no território;
2. quais municípios e públicos estão mais expostos;
3. qual é o ponto de partida da educação;
4. que decisão ou preparação isso exige;
5. quais temas e indicadores do PNE precisam ser acompanhados.

## 2.3 Escalas obrigatórias

Cada análise precisa funcionar em duas escalas articuladas:

- **região:** transformação, distribuição interna e coordenação territorial;
- **município selecionado:** direção local, divergência em relação à região, rede responsável e prioridade concreta.

Não criar dez mini-relatórios dentro da página regional. O município deve aparecer como uma camada dinâmica dentro de cada história e em uma síntese municipal própria.

## 2.4 Resultado mínimo para considerar o piloto completo

A experiência pública do Vale do Sinos deverá conter, no mínimo:

- quatro leituras na primeira direção;
- três questões na segunda direção;
- pelo menos duas leituras principais não demográficas;
- uma leitura de trajetória/permanência;
- uma leitura sobre trabalho juvenil ou trabalho e escolaridade;
- uma leitura de EJA ou população adulta sem educação básica concluída;
- uma leitura de trabalho e formação profissional;
- uma leitura municipal integrada para Nova Santa Rita;
- nenhuma mensagem pública de ausência, fraqueza, insuficiência ou falha técnica.

Uma candidata só conta para esse mínimo quando passa todos os gates. Não preencher quantidade com texto genérico.

---

# 3. Decisões de arquitetura analítica

## 3.1 Consolidar o que já existe

Os três cartões atuais de educação infantil, fundamental e médio não devem continuar como três histórias longas e independentes. Reaproveite seus cálculos dentro de um único módulo:

> **Como a mudança das gerações está reorganizando a demanda educacional**

O módulo deve permitir alternar entre etapas, mas sua mensagem principal precisa mostrar que:

- a região não é homogênea;
- a educação infantil, o fundamental e o médio respondem de formas diferentes;
- Nova Santa Rita segue uma trajetória distinta do agregado regional;
- a demografia é ponto de partida, não explicação completa.

Isso libera espaço editorial para as dimensões que ainda estão ausentes.

## 3.2 Criar quatro histórias centrais para a primeira direção

A primeira direção deverá investigar e publicar, quando aprovadas:

1. **demografia, demanda e organização da rede**;
2. **trajetória escolar, permanência e condições de oferta**;
3. **trabalho juvenil e ensino médio**;
4. **EJA, escolaridade adulta e distribuição da oferta**;
5. **educação profissional, ocupações e transformação econômica**.

O produto final pode mostrar quatro ou cinco delas, conforme os gates. As histórias 2, 3, 4 e 5 são as responsáveis por superar a pobreza analítica atual.

## 3.3 Criar três ou quatro agendas para a segunda direção

A segunda direção deverá investigar:

1. **coortes e respostas diferenciadas da rede**;
2. **trabalho juvenil, aprendizagem e permanência**;
3. **ocupações em transformação e formação profissional**;
4. **mobilidade e coordenação regional da oferta**;
5. **temas robustos nos cenários territoriais**, quando houver cenários do Vale do Sinos.

A ausência atual de cenários no Vale não impede publicar transformações já em curso. Contudo, o produto não deve ser declarado totalmente aderente ao pedido da gestora enquanto a integração com cenários territoriais do Vale não tiver uma decisão explícita: construir, transferir metodologia ou manter como etapa posterior aceita pela gestão.

## 3.4 Não criar um índice sintético

Não condensar trajetória, condições escolares, emprego e oferta em um score opaco. Cada leitura deve preservar seus componentes e deixar claro o que está sendo comparado.

## 3.5 Mecanismo antes de qualquer relação

Toda candidata deve nascer de uma pergunta substantiva. Correlação, concordância temporal, regressão, cluster ou qualquer outro procedimento podem ser usados internamente para testar uma hipótese, mas não podem criar a hipótese nem decidir sozinhos o conteúdo público.

---

# 4. Portfólio analítico obrigatório

## 4.1 Demografia, demanda e organização da rede

### Pergunta

Como a mudança das coortes alterou a demanda por etapa e por município, e onde a organização da oferta seguiu direção diferente?

### Dados

- população residente de 0–3, 4–5, 6–10, 11–14 e 15–17 anos;
- nascimentos por residência da mãe;
- matrículas por etapa, idade e rede;
- escolas, turmas e docentes;
- localização urbana/rural;
- município e região;
- deslocamento para estudo em 2022;
- comparação com RS.

### Cálculos internos

- decomposição já aprovada `M = P × R`;
- contribuição municipal para a mudança regional;
- mudança por rede;
- matrículas, turmas e escolas por município;
- relação aparente matrícula/população, sempre identificada internamente como lente mista;
- comparação de 2015–2025 e janelas de sensibilidade;
- tipologia territorial transparente, sem score:
  - coorte em redução e rede estável/crescente;
  - coorte e matrícula em expansão;
  - matrícula divergente da coorte;
  - presença relevante de deslocamento para estudo.

### Saída pública esperada

Uma única história regional, com etapas navegáveis, mostrando que o Vale encolhe em termos agregados, mas contém municípios com pressão crescente. Nova Santa Rita deve aparecer como exemplo central dessa divergência porque sua população de 0–14 anos e suas matrículas cresceram enquanto a região retraiu.

### Questão de planejamento

Diferenciar onde a rede precisa redistribuir oferta, onde precisa preservar acesso e onde precisa continuar ampliando capacidade de atendimento. Não recomendar fechamento ou abertura automática de escola.

---

## 4.2 Trajetória escolar, permanência e condições de oferta

### Pergunta

Em quais etapas, redes e municípios a trajetória escolar exige atenção, e quais condições da oferta diferenciam esses contextos?

### Dados

- aprovação;
- reprovação;
- abandono;
- distorção idade-série;
- idade regular no 5º, 9º e ensino médio, quando disponível;
- IDEB e SAEB;
- horas-aula diária;
- alunos por turma;
- adequação da formação docente;
- esforço e regularidade docente;
- nível socioeconômico;
- infraestrutura e conectividade;
- rede, etapa, município e ano;
- grupos de municípios semelhantes já existentes no diagnóstico PNE.

### Unidade de análise

Usar `município × ano × rede × etapa`. Não comparar uma condição da rede municipal com um resultado da rede estadual sem identificação explícita.

### Procedimento interno

1. Selecionar resultados de trajetória relevantes para o PNE e para a prioridade municipal.
2. Usar 2025 como fotografia principal e 2023–2025 como janela recente quando houver volatilidade.
3. Identificar municípios que permanecem acima ou abaixo do padrão regional em pelo menos dois anos, quando a série permitir.
4. Comparar com RS e com pares já definidos pelo produto, sem criar cluster ad hoc apenas para favorecer uma narrativa.
5. Dentro da mesma rede, etapa e contexto socioeconômico, verificar quais condições escolares diferem de forma material.
6. Publicar somente condições que acrescentem interpretação e possam orientar uma dimensão concreta da oferta.

### Regra contra pseudoexplicação

Não publicar frases como “a infraestrutura pode explicar o resultado” quando apenas houver coexistência genérica. A condição só entra quando:

- está no mesmo grão de rede e etapa;
- há diferença clara e persistente;
- a comparação com pares muda a leitura;
- existe uma implicação de planejamento específica.

### Saída pública esperada

Uma história como:

> **A redução do ensino médio não elimina o desafio de permanência**

A leitura deve combinar demografia, matrícula e trajetória, mostrando onde reprovação, abandono ou distorção se concentram e qual rede é responsável.

Para Nova Santa Rita, a narrativa municipal precisa incorporar que:

- as matrículas cresceram no fundamental e no médio;
- a reprovação e a distorção no ensino médio estão entre as maiores da região;
- os anos finais também apresentam distorção elevada;
- a oferta do ensino médio envolve majoritariamente a rede estadual;
- o planejamento municipal deve distinguir ação direta, transição do fundamental, transporte e coordenação com o estado.

### Questão de planejamento

Indicar etapa, rede, série ou público e um conjunto curto de indicadores a acompanhar. Evitar “melhorar a qualidade” ou “fortalecer políticas” sem especificação.

---

## 4.3 Trabalho juvenil e ensino médio

### Pergunta

Onde a entrada de jovens no trabalho formal e os desafios de trajetória do ensino médio aparecem no mesmo território, e que articulação isso coloca na agenda?

### Dados

- RAIS municipal 2019–2025 por faixas de 15–17 e 18–24 anos;
- escolaridade dos vínculos;
- setor e ocupação;
- Novo Caged 2020–2025 por idade, movimento, aprendiz, CBO e CNAE;
- 2026 somente como pulso parcial, nunca como ano fechado;
- matrícula, reprovação, abandono, distorção e aprovação no ensino médio;
- rede e município;
- população residente de 15–17 e 18–24 anos apenas como contexto, sem chamar vínculo localizado de taxa de emprego dos residentes.

### Materialização necessária

Criar um painel canônico de trabalho juvenil com:

```text
id_municipio_trabalho
region_id
ano
mes, quando aplicável
faixa_etaria
cnae
cbo_familia
escolaridade
vinculos_ativos
admissoes
desligamentos
saldo
aprendizes
remuneracao_agregada
source_id
status_periodo
```

Não consumir `CEI.public.estoque_emprego_faixa_etaria`, pois a auditoria confirmou duplicações conflitantes e valores inadequados.

### Procedimento interno

1. Medir a presença de vínculos de 15–17 e 18–24 entre os vínculos localizados no município.
2. Separar estoque RAIS de movimentos Caged.
3. Identificar setores e famílias ocupacionais em que jovens estão mais presentes.
4. Validar o dicionário oficial antes de publicar “primeiro emprego”.
5. Verificar, por município, a coexistência entre:
   - maior presença de trabalho juvenil;
   - reprovação, abandono ou distorção no ensino médio;
   - oferta de aprendizagem, quando o dado representar vínculo de aprendiz.
6. Testar estabilidade entre anos e retirada de municípios.
7. Não inferir que os jovens empregados são os mesmos estudantes com dificuldade escolar.

### Regra de publicação

O cartão só entra quando houver um padrão territorial concreto. Exemplos de padrões aceitáveis:

- os mesmos municípios concentram trabalho juvenil e dificuldades de trajetória;
- o crescimento recente do trabalho juvenil se concentra em setores com horários ou perfis que tornam relevante a articulação escola–trabalho;
- a aprendizagem formal cresce ou se concentra onde a trajetória do ensino médio demanda coordenação.

Se o resultado for apenas “o emprego cresceu e a matrícula mudou”, reter silenciosamente.

### Saída pública esperada

A linguagem deve falar em encontro territorial, não em causa:

> **Trabalho juvenil e permanência escolar se encontram nos mesmos municípios**

A questão de planejamento deve especificar, quando sustentado:

- articulação com aprendizagem profissional;
- horários e organização da oferta;
- transição do 9º ano para o médio;
- acompanhamento de abandono e reprovação;
- coordenação entre rede estadual, municípios e atores da formação profissional.

---

## 4.4 EJA, escolaridade adulta e distribuição da oferta

### Decisão de produto

Adotar inicialmente uma **fotografia de nível de 2022**, porque esse é o ano em que o público residente sem fundamental ou médio concluído está disponível de forma comparável. Não fingir uma série anual do público potencial.

A matrícula da EJA deve ser analisada prioritariamente em 2022 para o contraste principal. A evolução de 2014–2025 pode aparecer como contexto separado, sem combinar os dois períodos como se fossem a mesma série.

### Pergunta

A oferta de EJA está distribuída de forma semelhante à população adulta que ainda não concluiu a educação básica?

### Dados

- adultos residentes sem ensino fundamental concluído em 2022;
- adultos residentes sem ensino médio concluído em 2022;
- matrículas EJA fundamental e médio em 2022;
- rede;
- escolas e turmas, quando disponíveis;
- EJA integrada à educação profissional;
- evolução das matrículas 2014–2025;
- escolaridade dos vínculos formais;
- município, região e RS.

### Cálculos internos

Para cada etapa e município:

```text
participacao_publico_i = publico_potencial_i / publico_potencial_regiao
participacao_matriculas_i = matriculas_eja_i / matriculas_eja_regiao
diferenca_distribuicao_pp = participacao_matriculas_i - participacao_publico_i
matriculas_por_mil = 1000 × matriculas_eja_i / publico_potencial_i
```

Essas medidas não são cobertura, demanda atendida ou probabilidade de matrícula. São comparações entre moradores e matrículas localizadas.

### Procedimento interno

1. Separar fundamental e médio.
2. Verificar municípios com maior concentração do público residente.
3. Verificar municípios que concentram as matrículas e a EJA integrada à EPT.
4. Comparar distribuição, não apenas totais.
5. Identificar casos em que a região pode depender de oferta intermunicipal.
6. Usar escolaridade do emprego como contexto adicional apenas quando acrescentar uma questão concreta; não como substituto do público potencial.

### Saída pública esperada

Uma história como:

> **O público que ainda não concluiu a educação básica e a oferta de EJA estão distribuídos de forma diferente**

O cartão deve mostrar:

- onde mora a maior parte do público;
- onde estão as matrículas;
- onde existe EJA integrada à formação profissional;
- o que isso coloca na agenda regional e municipal.

Não usar na interface:

- “evidência insuficiente”;
- “não foi possível medir a demanda”;
- “relação fraca”;
- “fotografia sem tendência”.

A decisão técnica de usar 2022 fica nas fontes e na documentação. Na interface, o período deve aparecer de forma natural.

---

## 4.5 Educação profissional, ocupações e transformação econômica

### Importância

Esta é a maior lacuna de conteúdo do piloto e a principal razão de o Gate 11 continuar bloqueado. O pedido da gestora inclui setores, novas ocupações, transformação tecnológica e educação profissional. A página não estará completa enquanto essa frente permanecer ausente.

### Pergunta

A composição da formação profissional acompanha as ocupações e os setores que estão mudando na região?

### Dados já existentes

- matrículas EPT por modalidade e rede, 2013–2025;
- EJA integrada à EPT;
- RAIS por setor, ocupação, escolaridade e idade;
- Caged por CBO, CNAE, idade e movimento;
- shift-share do emprego regional;
- ponte curso–ocupação parcialmente versionada;
- dados de cursos/eixos em cobertura incompleta.

### Dados que precisam ser completados

Antes de publicar a leitura regional do Vale do Sinos, materializar uma base de oferta EPT com cobertura comprovada:

```text
id_municipio
ano
instituicao_escola
rede
modalidade
curso
codigo_curso
eixo_tecnologico
matriculas
ingressantes, se disponível
concluintes, se disponível
status_cobertura
source_id
```

Ordem obrigatória para fechar a lacuna:

1. procurar campos de curso e eixo nos microdados e tabelas locais já existentes;
2. verificar se o pipeline atual do Censo Escolar pode materializá-los para os 497 municípios;
3. verificar fontes oficiais já citadas no repositório;
4. somente depois pesquisar e incorporar uma nova fonte pública mínima;
5. documentar cobertura, comparabilidade e atualização;
6. não interpretar ausência de registro como ausência de oferta enquanto a cobertura não for completa.

Ingressantes, concluintes e vagas enriquecem a análise, mas não devem bloquear uma primeira leitura de composição se cursos/eixos e matrículas estiverem completos. Não usar dados da CAPES como substituto de EPT.

### Painel ocupacional necessário

Materializar no mínimo:

```text
id_municipio_trabalho
region_id
ano
cbo_familia
cnae_setor
vinculos_ativos
admissoes
desligamentos
participacao_jovens
escolaridade_dos_vinculos
variacao_periodo
concentracao_municipal
source_id
```

### Correspondência formação–ocupação

- preferir correspondência oficial e versionada;
- declarar internamente qualidade e abrangência da ponte;
- não fazer correspondência manual apenas para fechar um cartão;
- trabalhar, quando necessário, em famílias ocupacionais e eixos amplos;
- não comparar diretamente quantidade de vínculos com quantidade de matrículas como se fossem a mesma unidade;
- comparar composição, direção, localização e presença/ausência comprovada de oferta.

### Procedimento analítico

1. Identificar famílias ocupacionais com mudança sustentada, não apenas variação de um ano.
2. Separar expansão de estoque, rotatividade e saldo recente.
3. Identificar setores cuja dinâmica local diverge do movimento estadual usando o shift-share já aprovado.
4. Mapear ocupações às formações relacionadas.
5. Examinar onde a oferta formativa está concentrada e como mudou.
6. Produzir situações descritivas, por exemplo:
   - ocupações relacionadas em expansão e formação também em expansão;
   - ocupações em expansão com formação concentrada fora dos municípios mais expostos;
   - formação em expansão enquanto as ocupações relacionadas perdem participação;
   - mudança setorial que exige requalificação de adultos, articulando EJA e EPT.
7. Verificar estabilidade, concentração municipal e retirada de município.

### Regra de publicação

Não será suficiente publicar:

- “a indústria caiu e a matrícula técnica cresceu”;
- “emprego e EPT seguiram direções diferentes”;
- “a região precisa alinhar a formação ao mercado”.

O cartão precisa nomear:

- ocupações ou famílias ocupacionais;
- setores;
- municípios mais expostos;
- eixos, cursos ou modalidades formativas;
- período;
- questão concreta para o planejamento.

### Saída pública esperada

Uma história como:

> **As mudanças do trabalho não chegam da mesma forma à oferta de formação profissional**

O conteúdo público deve explicar onde a transformação está ocorrendo, qual oferta existe e que questão entra na agenda — expansão, redistribuição, articulação entre redes ou requalificação — sem prometer empregos futuros e sem afirmar causalidade.

---

## 4.6 Mobilidade e coordenação regional

### Pergunta

Em quais etapas e municípios o acesso à educação depende de oferta fora do município de residência?

### Dados

- residentes que estudavam fora do município em 2022;
- denominadores por etapa;
- matrículas localizadas;
- rede;
- transporte escolar e PNATE apenas como contexto de oferta, não como matriz de deslocamento;
- município e região.

### Limite

A base atual não informa o município de destino. Não inventar corredores ou municípios receptores.

### Saída pública esperada

Manter e enriquecer a história atual, conectando mobilidade a:

- etapa;
- rede;
- municípios com maior dependência de oferta externa;
- planejamento regional;
- transição e permanência.

Para Nova Santa Rita, a leitura deve incorporar a participação relevante de estudantes do ensino médio que estudavam fora do município e articular isso ao desafio de trajetória.

---

# 5. Segunda direção — agendas para os próximos anos

## 5.1 Respostas diferentes para trajetórias demográficas diferentes

Não apresentar o Vale do Sinos como um território único em retração. Construir uma agenda baseada em tipos municipais transparentes:

- municípios com coortes em retração;
- municípios com demanda estável;
- municípios em crescimento, como Nova Santa Rita;
- municípios com forte deslocamento para estudo;
- municípios em que rede, turmas e matrículas mudaram em ritmos diferentes.

A questão pública é como distribuir e coordenar a oferta, não quantas escolas abrir ou fechar automaticamente.

## 5.2 Trabalho juvenil e permanência

Partir das mudanças observadas no emprego de 15–17 e 18–24 anos e mostrar:

- setores e ocupações em que os jovens entram;
- municípios com maior presença desse movimento;
- situação atual da trajetória do ensino médio;
- aprendizagem profissional, quando validada;
- indicadores educacionais a acompanhar.

A agenda deve ser concreta: horários, transição, permanência, aprendizagem, EPT e coordenação entre atores.

## 5.3 Ocupações e formação profissional

Partir das ocupações e setores com transformação sustentada e chegar a:

- eixos ou cursos relacionados;
- distribuição municipal da oferta;
- formação de jovens;
- requalificação de adultos;
- EJA integrada;
- necessidade de coordenação regional.

Esse cartão é obrigatório para o fechamento do piloto, mas só pode ser publicado após completar a cobertura mínima da oferta EPT.

## 5.4 Mobilidade como agenda regional

Usar a fotografia de deslocamento para mostrar que algumas decisões de ensino médio e formação profissional não cabem somente dentro dos limites municipais.

Sem matriz de destino, a agenda pode tratar de coordenação e acompanhamento. Não deve propor rotas específicas.

## 5.5 Cenários do Vale do Sinos

Os cenários regionais devem enriquecer, não substituir, as leituras observadas.

Depois de fechar o piloto com dados históricos, abrir uma frente separada para decidir entre:

1. transferir a metodologia regional de cenários já usada no Vale do Rio Pardo e Noroeste;
2. construir cenários específicos do Vale do Sinos com o mesmo contrato de governança;
3. manter a página do Vale apenas com mudanças em curso até haver cenário validado.

Para afirmar que o pedido da gestora foi entregue em sua forma completa, a decisão precisa ser explicitamente aprovada. Caso sejam produzidos cenários, exigir:

- método comum;
- base e horizonte declarados internamente;
- quatro futuros coerentes;
- forças motrizes, incertezas e sinais rastreáveis;
- ligação com educação sem números futuros inventados;
- questões robustas em mais de um cenário;
- camada regional e exposição municipal sem chamar exposição de cenário municipal.

---

# 6. Camada municipal obrigatória

## 6.1 Regra geral

Cada história regional deve conter um bloco dinâmico:

> **No município selecionado**

Esse bloco deve responder:

1. a direção local foi igual ou diferente da região?
2. qual foi a contribuição do município para a mudança regional?
3. qual rede e etapa estão envolvidas?
4. qual fator adicional muda a interpretação local?
5. que questão específica entra no planejamento municipal ou na coordenação com outra rede?

## 6.2 Síntese municipal

Além dos blocos dentro dos cartões, criar uma síntese curta do município selecionado com no máximo três leituras prioritárias. A seleção deve considerar:

- prioridades do diagnóstico PNE;
- divergência em relação à região;
- intensidade da trajetória;
- contribuição para a mudança regional;
- possibilidade real de ação municipal, estadual ou regional;
- ausência de redundância.

Não criar um ranking opaco. Registrar a regra de seleção.

## 6.3 Caso de validação — Nova Santa Rita

A síntese municipal de Nova Santa Rita deverá integrar, se os dados confirmarem na reconstrução:

1. **demanda crescente:** população de 0–14 e matrículas em direção diferente da região;
2. **trajetória:** reprovação e distorção elevadas, especialmente no ensino médio e anos finais;
3. **mobilidade:** parcela relevante de residentes estudando fora, sobretudo no médio;
4. **rede responsável:** distinção entre educação municipal e ensino médio estadual;
5. **trabalho juvenil:** presença, setores e ocupações locais, após materialização;
6. **EJA:** distribuição do público potencial e da oferta local;
7. **formação profissional:** oferta disponível e relação com ocupações, quando a cobertura estiver fechada.

A síntese não deve repetir todos os dados. Deve formar uma história semelhante a:

> Nova Santa Rita amplia a demanda escolar enquanto a região encolhe; o desafio local não é apenas abrir espaço, mas assegurar trajetória e coordenação regional, sobretudo no ensino médio.

Esse texto é um exemplo editorial, não um template fixo. Reconstruir a versão final a partir dos fatos aprovados.

## 6.4 Responsabilidade institucional

Toda questão de planejamento deve ser classificada internamente como:

- ação direta da rede municipal;
- coordenação com a rede estadual;
- articulação intermunicipal/regional;
- articulação com formação profissional e trabalho;
- acompanhamento, sem atribuição direta de responsabilidade.

A classificação não precisa aparecer como código. A linguagem pública deve evitar atribuir ao município uma obrigação que pertence à rede estadual ou a outro ente.

---

# 7. Painéis canônicos a materializar

Antes de reescrever narrativas, materializar painéis reutilizáveis. Não calcular diretamente dentro do frontend.

## 7.1 `education_demography_panel`

Grão principal:

```text
id_municipio × ano × etapa × rede
```

Campos mínimos:

- `region_id`;
- `population_age_group`;
- `enrollments_local`;
- `enrollments_by_age`;
- `schools`;
- `classes`;
- `teachers`;
- `urban_rural`;
- `birth_cohort_reference`;
- `source_ids`;
- `availability_state`.

## 7.2 `trajectory_conditions_panel`

Grão:

```text
id_municipio × ano × rede × etapa
```

Campos mínimos:

- aprovação;
- reprovação;
- abandono;
- distorção;
- IDEB/SAEB;
- horas-aula;
- alunos por turma;
- adequação docente;
- esforço docente;
- regularidade docente;
- INSE e ponderador;
- infraestrutura selecionada;
- numeradores, denominadores e pesos;
- estado de disponibilidade.

## 7.3 `youth_work_panel`

Grão anual e, quando necessário, mensal:

```text
id_municipio_trabalho × período × faixa_etaria × CBO × CNAE
```

Separar:

- estoque RAIS;
- admissões Caged;
- desligamentos Caged;
- saldo;
- aprendizes;
- escolaridade;
- remuneração agregada;
- ano parcial.

## 7.4 `eja_potential_offer_panel`

Grão:

```text
id_municipio × etapa_eja × ano_referencia
```

Campos:

- público residente sem etapa concluída;
- matrículas EJA;
- rede;
- escolas/turmas, quando disponíveis;
- EJA integrada à EPT;
- participações regionais;
- matrículas por mil;
- lentes territoriais;
- fontes.

## 7.5 `occupation_training_panel`

Grão composto, com tabelas relacionadas se necessário:

- ocupações por município, ano e família CBO;
- setores por município, ano e CNAE;
- formação por município, ano, modalidade, curso e eixo;
- ponte versionada eixo/curso ↔ família ocupacional;
- cobertura e qualidade da correspondência.

## 7.6 `mobility_study_snapshot`

Grão:

```text
id_municipio_residencia × etapa × 2022
```

Campos:

- total de residentes que estudavam;
- residentes que estudavam fora;
- participação;
- comparação regional e estadual;
- destino disponível = falso;
- fonte e caráter de fotografia.

---

# 8. Regras de dados e qualidade

1. Código municipal sempre como texto IBGE de sete dígitos.
2. Região sempre pelo mapa FIERGS canônico do produto.
3. Somar contagens; recomputar taxas com numeradores e denominadores.
4. Nunca fazer média simples de taxas municipais para representar a região.
5. Valores ausentes permanecem ausentes; não converter para zero.
6. Arredondamento apenas na apresentação.
7. 2026 do Caged é parcial e não pode ser comparado como ano completo.
8. Estoque, fluxo, saldo e participação são conceitos distintos.
9. Matrículas são localizadas nas escolas; população é residente; vínculos são localizados no trabalho.
10. Taxa aparente acima de 100 não pode ser chamada de cobertura.
11. Dados de pessoa não podem sair dos bancos ou arquivos brutos; somente agregados.
12. Não usar a tabela defeituosa `estoque_emprego_faixa_etaria`.
13. Não usar CAPES como educação profissional técnica.
14. Não interpretar ausência de curso como ausência de oferta sem cobertura completa.
15. Não publicar “primeiro emprego” sem dicionário oficial validado.
16. Não chamar exposição municipal a cenário regional de cenário municipal.
17. Toda frase pública deve apontar para fatos, períodos, fontes e cálculos manifestados.
18. Toda materialização deve ser determinística e reconstruível.
19. Os artefatos de decisão devem ser versionados; não depender de CSV ignorado pelo Git sem exceção explícita ou formato canônico alternativo.
20. Preservar baseline e rollback da V6.

---

# 9. Seleção e gates de publicação

## 9.1 Gates obrigatórios

Cada candidata deve passar por:

1. **relevância:** responde a uma questão real do PNE/PME;
2. **mecanismo:** a relação foi prevista antes do resultado;
3. **universo:** população, escola, rede e trabalho estão corretamente separados;
4. **tempo:** janela e caráter de fotografia/tendência são coerentes;
5. **estabilidade:** não depende de um ano ou município isolado;
6. **integração:** acrescenta interpretação, não apenas exibe séries;
7. **território:** mostra diferenças municipais úteis;
8. **planejamento:** nomeia etapa, público, rede, ação e indicador;
9. **clareza:** pode ser compreendida sem metodologia técnica;
10. **rastreabilidade:** todos os fatos são reconstruíveis;
11. **não redundância:** não repete outra história;
12. **valor incremental:** acrescenta algo além da demografia já publicada.

## 9.2 Critérios adicionais do novo piloto

O Gate 11 só poderá ser reaberto como aprovado quando:

- houver pelo menos duas histórias não demográficas;
- houver uma leitura de trabalho e formação;
- houver leitura municipal integrada de Nova Santa Rita;
- o usuário identificar o desafio de trajetória além da demografia;
- a segunda saída não depender somente de coortes e mobilidade;
- a página permitir distinguir ação municipal, estadual e regional.

## 9.3 Ausência silenciosa

Quando uma candidata falhar:

- registrar internamente;
- preservar cálculo e motivo;
- não renderizar cartão;
- não criar aviso público;
- não preencher espaço com recomendação genérica.

---

# 10. Contrato de linguagem pública

## 10.1 Termos proibidos no percurso principal

Não exibir:

- correlação;
- Pearson;
- Spearman;
- força fraca, moderada ou forte;
- evidência E1–E5;
- p-valor;
- significância;
- universo incompatível;
- decomposição Bennet;
- `leave-one-out`;
- gate;
- candidato retido;
- não foi possível medir;
- não foi possível verificar;
- evidência insuficiente;
- relação fraca;
- ausência de dado;
- cenário indisponível;
- fallback;
- limitações metodológicas como destaque;
- mensagens defensivas repetidas de “não se conclui”.

Esses elementos pertencem à documentação, aos testes e às fontes detalhadas.

## 10.2 Regra de valor de cada frase

Cada frase pública deve realizar ao menos uma função:

- declarar uma mudança concreta;
- explicar como a leitura territorial altera a interpretação;
- mostrar diferença entre municípios ou redes;
- identificar um público ou etapa;
- formular uma questão específica de planejamento;
- indicar o que acompanhar.

Se a frase apenas protege o método, descreve o processo ou diz que algo não pôde ser feito, removê-la do percurso principal.

## 10.3 Vocabulário recomendado

Preferir:

- “ocorreu no mesmo período”;
- “conviveu com”;
- “acompanha principalmente”;
- “a mudança se concentrou em”;
- “o município seguiu direção diferente”;
- “os dados acrescentam esta leitura”;
- “isso coloca na agenda”;
- “a oferta está mais concentrada em”;
- “o público residente está mais concentrado em”;
- “as mudanças já em curso”;
- “nos próximos anos, o planejamento precisará considerar”.

Não repetir “pode estar relacionado” em todos os cartões. A cautela deve estar no desenho e na precisão do texto, não em avisos genéricos.

## 10.4 Planejamento sem recomendação vazia

Não publicar:

> É importante acompanhar os indicadores e fortalecer políticas públicas.

Preferir algo específico, por exemplo:

> A transição dos anos finais para o ensino médio, a reprovação na rede estadual e o deslocamento para estudar fora precisam ser acompanhados em conjunto em Nova Santa Rita.

## 10.5 Fontes e lentes sem jargão

Quando for necessário distinguir universos, usar rótulos públicos simples:

- **Moradores do município**;
- **Matrículas nas escolas do município**;
- **Vínculos nos estabelecimentos do município**;
- **Rede responsável pela oferta**.

A explicação técnica detalhada fica recolhida em “Dados e fontes”.

---

# 11. Arquitetura da página

## 11.1 Cabeçalho

Exibir:

- região;
- município selecionado;
- frase curta sobre as duas direções;
- três achados integrados, não quatro números soltos.

Os achados devem representar, quando aprovados:

- transformação demográfica;
- desafio de trajetória;
- transformação do trabalho/formação.

## 11.2 Duas entradas inequívocas

1. **O território ajuda a compreender a educação**
2. **O futuro do território coloca temas na agenda da educação**

Não usar “Pergunta 1”, “Pergunta 2” ou nomes metodológicos.

## 11.3 Cartões principais

Cada história deve conter no primeiro nível:

1. título com o insight;
2. síntese em até três frases;
3. um visual principal;
4. bloco “No município selecionado”;
5. questão de planejamento;
6. metas/temas do PNE relacionados.

Detalhes recolhidos:

- ver evolução;
- ver municípios;
- ver redes e etapas;
- ver indicadores para acompanhar;
- ver dados e fontes.

Não deixar, como ocorre no screenshot atual, todas as tabelas, gráficos, barras e notas expandidas simultaneamente.

## 11.4 Visualizações

Usar uma visualização principal por história:

- decomposição de mudança para demografia;
- matriz ou perfil municipal para trajetória;
- quadrante transparente para trabalho juvenil × trajetória, sem score;
- distribuição lado a lado para público da EJA × matrículas;
- composição ocupacional × composição formativa;
- mapa ou barras para mobilidade, somente quando agregarem interpretação.

Gráficos auxiliares ficam recolhidos.

## 11.5 Síntese municipal

Criar bloco específico após a síntese regional:

> **O que essa leitura significa para Nova Santa Rita**

O componente deve ser genérico para qualquer município selecionado e preenchido por fatos estruturados, não por texto manual.

## 11.6 Altura e legibilidade

A nova versão pode ter mais conteúdo analítico, mas o percurso principal não deve ser maior que o atual. Conseguir isso por:

- consolidação dos três cartões demográficos;
- detalhes recolhidos;
- um visual por história;
- textos curtos;
- navegação por seções;
- ausência de tabelas técnicas no primeiro nível.

Manter responsividade, impressão e ausência de rolagem horizontal.

---

# 12. Plano de execução em jobs

## Job 0 — preflight, preservação e mapa real

**Modelo:** Sol `xhigh`
**Objetivo:** preservar V6 e confirmar o estado operacional.

Tarefas:

1. mapear branch, working tree, arquivos não rastreados e commits locais;
2. criar baseline/commit/tag seguro sem apagar mudanças existentes;
3. confirmar caminhos reais dos artefatos V6;
4. versionar as matrizes atualmente ignoradas ou convertê-las para formato canônico;
5. rodar todos os testes existentes;
6. capturar screenshots atuais;
7. não alterar `public/data` ainda.

Gate:

- rollback comprovado;
- testes verdes;
- estado atual reconstruível;
- nenhuma perda de trabalho local.

---

## Job 1 — contrato analítico V7

**Modelo recomendado:** GPT-5.6 Pro como autor/julgador; Sol pode preparar o material.
**Objetivo:** transformar este documento em contrato do produto.

Entregáveis:

- contrato das duas saídas;
- catálogo das novas histórias;
- contrato da camada municipal;
- decisão formal da EJA 2022;
- decisão formal sobre cenários do Vale;
- regras de responsabilidade institucional;
- critérios de “valor incremental além da demografia”;
- exemplos aprovados/reprovados de texto;
- novo Gate 11.

Não implementar código antes da aprovação deste contrato.

---

## Job 2 — materializações do acervo existente

**Modelo:** Sol `xhigh`
**Pode ser dividido em worktrees independentes.**

### 2A — trajetória e condições escolares

- painel por município, ano, rede e etapa;
- ponderadores e estados de disponibilidade;
- comparação regional, RS e pares;
- QA de rede e etapa.

### 2B — trabalho juvenil

- RAIS 15–17 e 18–24;
- Caged por idade, movimento, aprendiz, CBO e CNAE;
- validação de dicionários;
- bloqueio da tabela defeituosa;
- 2026 marcado como parcial.

### 2C — EJA

- público residente 2022;
- matrícula EJA 2022;
- evolução 2014–2025 separada;
- EJA integrada;
- distribuição municipal.

### 2D — ocupações e formação

- painel ocupacional municipal;
- auditoria de dados de cursos/eixos já existentes;
- cobertura do Vale do Sinos;
- ponte formação–ocupação;
- decisão factual sobre necessidade de nova fonte.

### 2E — demografia, rede e mobilidade

- consolidar painéis já construídos;
- incluir turmas, escolas, rede e municípios;
- preservar a fotografia de deslocamento.

Gate:

- painéis determinísticos;
- todos os 10 municípios do Vale;
- Nova Santa Rita reconstruída;
- fechamento regional;
- fontes e lentes manifestadas;
- nenhuma narrativa pública ainda.

---

## Job 3 — laboratório analítico do Vale do Sinos e Nova Santa Rita

**Modelo:** Sol `xhigh` para cálculos; revisão posterior obrigatória.
**Objetivo:** produzir fatos e candidatas, sem alterar a interface.

Executar separadamente:

1. demografia e rede;
2. trajetória e condições;
3. trabalho juvenil e ensino médio;
4. EJA e oferta;
5. ocupações e formação;
6. mobilidade;
7. agendas futuras observadas.

Para cada candidata, entregar:

- pergunta;
- mecanismo;
- dados e lentes;
- períodos;
- cálculo;
- resultado regional;
- distribuição municipal;
- Nova Santa Rita;
- comparação RS/pares;
- estabilidade;
- questão de planejamento;
- PNE relacionado;
- razão para publicar ou reter;
- fatos estruturados;
- visual recomendado.

Não escrever textos finais antes da revisão independente.

---

## Job 4 — julgamento independente dos insights

**Modelo obrigatório recomendado:** GPT-5.6 Pro.
**Objetivo:** decidir se as candidatas respondem à gestora e acrescentam valor real.

O julgador deve reprovar candidatas que:

- apenas colocam séries lado a lado;
- repetem demografia;
- dependem de correlação;
- não nomeiam público, rede ou município;
- geram recomendação genérica;
- confundem residente, escola ou trabalho localizado;
- usam ausência de dado como conteúdo;
- não alteram uma questão de planejamento.

Entregável:

- matriz publicar/reter/revisar;
- justificativa por gate;
- conjunto mínimo de histórias;
- lacunas que realmente bloqueiam o produto.

---

## Job 5 — aquisição dirigida, somente se comprovadamente necessária

**Modelos:** Sol `xhigh` para engenharia; GPT-5.6 Pro para pesquisa e decisão.
**Prioridade:** fechar trabalho × formação.

Pesquisar somente a fonte mínima para:

1. cursos e eixos EPT com cobertura do Vale do Sinos e, idealmente, dos 497 municípios;
2. ingressantes/concluintes, se disponíveis e sustentáveis;
3. matriz residência–estudo, caso seja necessária para avançar além da fotografia atual;
4. cenário do Vale do Sinos, em uma frente metodológica própria.

Para cada fonte, entregar:

- pergunta que desbloqueia;
- fonte oficial;
- campos;
- período;
- cobertura;
- forma de obtenção;
- permissão de uso;
- comparabilidade;
- custo de atualização;
- QA;
- decisão incorporar/rejeitar.

Não baixar dados apenas porque são interessantes.

---

## Job 6 — compilador de fatos e narrativas V7

**Modelo:** Sol `xhigh`; textos aprovados por GPT-5.6 Pro.
**Objetivo:** gerar conteúdo público somente a partir dos fatos aprovados.

Arquitetura:

1. fatos estruturados;
2. decisão editorial aprovada;
3. templates públicos;
4. linter;
5. contrato de fontes;
6. camada municipal;
7. fallback V6.

Testar:

- bloqueio de termos proibidos;
- ausência silenciosa;
- números, períodos e unidades;
- responsabilidade de rede;
- região × município;
- texto sem metodologia;
- reconstrução byte a byte quando aplicável.

---

## Job 7 — interface e experiência

**Modelo:** Sol `xhigh`
**Objetivo:** implementar a nova arquitetura sem aumentar o percurso principal.

Tarefas:

- consolidar demografia;
- criar cartões das novas histórias;
- criar bloco municipal;
- recolher detalhes;
- adaptar visualizações;
- manter consulta de séries fora do núcleo narrativo;
- mobile, impressão e acessibilidade;
- screenshots de todas as combinações relevantes.

Não promover para produção antes do Job 8.

---

## Job 8 — validação humana do piloto

**Responsável principal:** usuário/gestora; modelo apenas prepara e registra.
**Objetivo:** verificar utilidade, não apenas correção.

Sem explicação prévia, pedir que a pessoa responda:

1. o que o território ajuda a compreender sobre a mudança das matrículas?
2. qual desafio permanece além da demografia?
3. por que Nova Santa Rita precisa de uma leitura diferente da média regional?
4. onde trabalho juvenil e ensino médio entram na mesma agenda?
5. como o público potencial da EJA e a oferta se distribuem?
6. que mudança do trabalho coloca uma questão para a formação profissional?
7. quais decisões são municipais, estaduais e regionais?
8. quais três temas deveriam entrar no planejamento dos próximos anos?

Registrar:

- resposta espontânea;
- tempo;
- dúvidas;
- termos não compreendidos;
- informação útil;
- informação ignorada;
- decisão sugerida;
- ajustes.

O Gate 11 não pode ser aprovado sem esse registro.

---

## Job 9 — transferência antes da escala

**Modelos:** Sol `xhigh` para execução; GPT-5.6 Pro para julgamento.
**Regiões:** Vale do Rio Pardo e Noroeste, ou outras duas formalmente aprovadas.

Rodar a mesma cadeia sem editar narrativas manualmente. Confirmar:

- mesmas materializações;
- mesmos gates;
- quantidades variáveis de cartões;
- integração de cenários onde já existem;
- camada municipal;
- nenhuma recomendação genérica para preencher espaço;
- fallback quando o mínimo não é alcançado.

Só depois iniciar rollout para as demais regiões.

---

# 13. Testes obrigatórios

## 13.1 Numéricos

- fechamento região × municípios;
- fechamento RS × 497 municípios;
- recomputação de taxas;
- arredondamento tardio;
- repetibilidade;
- janelas de sensibilidade;
- retirada de município;
- períodos parciais;
- duplicações e chaves.

## 13.2 Metodológicos

- mecanismo prévio;
- lente territorial;
- rede e etapa;
- fotografia versus tendência;
- estoque versus fluxo;
- estabilidade;
- concentração municipal;
- comparação com pares;
- ausência de causalidade indevida;
- ausência de score opaco.

## 13.3 Conteúdo

- pelo menos duas histórias não demográficas;
- trabalho × formação presente;
- EJA presente;
- trajetória presente;
- Nova Santa Rita integrada;
- questão de planejamento específica;
- PNE relacionado;
- responsabilidade institucional correta.

## 13.4 Linguagem

- corpus de termos proibidos;
- nenhum aviso técnico no percurso principal;
- nenhum texto genérico;
- nenhum “não foi possível”;
- nenhuma recomendação vazia;
- títulos com insight real;
- fontes e períodos acessíveis.

## 13.5 Visual e E2E

- desktop, tablet, mobile e impressão;
- município alternado;
- região alternada;
- cartões com diferentes coberturas;
- ausência silenciosa;
- fallback;
- expansão/recolhimento;
- navegação por teclado;
- sem rolagem horizontal;
- um visual principal por história.

---

# 14. Artefatos esperados

Escolher caminhos canônicos, mas produzir equivalentes a:

- `CONTRATO_PRODUTO_VOCACOES_PNE_V7.md`;
- `CONTRATO_LINGUAGEM_PUBLICA_V7.md`;
- `PAINEL_DEMOGRAFIA_REDE_V7`;
- `PAINEL_TRAJETORIA_CONDICOES_V7`;
- `PAINEL_TRABALHO_JUVENIL_V7`;
- `PAINEL_EJA_PUBLICO_OFERTA_V7`;
- `PAINEL_OCUPACOES_FORMACAO_V7`;
- `CANDIDATOS_INSIGHTS_V7.json`;
- `DECISOES_PUBLICACAO_V7.json`;
- `DOSSIE_VALE_SINOS_NOVA_SANTA_RITA_V7.md`;
- `LACUNAS_DIRIGIDAS_V7.md`;
- `RELATORIO_GA_HUMANO_V7.md`;
- `RELATORIO_TRANSFERENCIA_V7.md`;
- manifesto de publicação;
- fixtures;
- screenshots;
- testes.

Todo artefato decisório deve ser versionado.

---

# 15. Recomendação de modelos

## ChatGPT 5.6 Sol `xhigh` é suficiente para

- descoberta de paths e dependências;
- ETL e materialização;
- consultas SQL;
- cálculos e QA;
- schemas e contratos técnicos;
- testes;
- compilador;
- React/Vite e visualizações;
- documentação operacional;
- transferência parametrizada.

## Use GPT-5.6 Pro nos três gates de maior risco

1. **antes da implementação analítica:** aprovar perguntas, mecanismos e arquitetura de produto;
2. **depois dos cálculos:** julgar se cada candidata é um insight real e útil;
3. **antes da publicação:** revisar narrativa, screenshot, coerência regional/municipal e aderência ao pedido da gestora.

Também é recomendável usar GPT-5.6 Pro na pesquisa de novas fontes e na eventual construção/transferência de cenários do Vale do Sinos.

Não é necessário usar o modelo mais robusto em todos os jobs. O risco principal não está na mecânica dos cálculos; está em aprovar relações pobres, textos genéricos ou interpretações que parecem sofisticadas sem orientar decisão. Por isso, a combinação mais eficiente é:

> **Sol `xhigh` executa; Pro julga; pessoa usuária valida.**

---

# 16. Vereditos permitidos

Cada job deve terminar com um destes vereditos:

- **Aprovado**;
- **Aprovado com pendências não bloqueantes**;
- **Revisão necessária**;
- **Bloqueado por lacuna dirigida**;
- **Interrompido por baixo valor de produto**.

Não usar “concluído” quando o gate humano ou o conteúdo trabalho × formação ainda estiverem pendentes.

---

# 17. Formato obrigatório da resposta de cada job

Ao finalizar qualquer job, responder com:

1. objetivo executado;
2. paths inspecionados;
3. arquivos alterados;
4. dados e períodos usados;
5. cálculos produzidos;
6. resultados principais;
7. resultados retidos;
8. testes executados;
9. screenshots/artefatos;
10. pendências;
11. próximo job permitido;
12. veredito do gate.

Não iniciar automaticamente o job seguinte quando houver decisão de produto, nova fonte, narrativa pública ou promoção para a interface.

---

# 18. Definição final de pronto

A integração Vocações × PNE estará pronta para o piloto ampliado quando:

- a página responder claramente às duas direções da gestora;
- demografia estiver consolidada em vez de dominar a página;
- trajetória, trabalho juvenil, EJA e formação profissional estiverem presentes;
- a segunda direção tiver ao menos uma agenda econômica/ocupacional;
- Nova Santa Rita tiver leitura integrada e distinta da região;
- cada questão indicar município, etapa, rede, público e responsabilidade;
- nenhum termo técnico ou mensagem negativa ocupar o percurso principal;
- nenhuma candidata for publicada apenas por correlação;
- todos os fatos forem reconstruíveis;
- a interface mantiver percurso curto;
- o teste humano comprovar compreensão e utilidade;
- a cadeia funcionar em duas regiões contrastantes;
- cenários do Vale do Sinos tiverem uma decisão formal e, quando produzidos, integração validada;
- publicação, fallback e rollback estiverem testados.

A meta não é produzir mais cartões. É fazer com que um gestor termine a página sabendo:

1. o que mudou na educação;
2. o que o território acrescenta à compreensão;
3. por que seu município pode seguir direção diferente;
4. quais transformações já em curso afetam o planejamento;
5. quais questões educacionais precisam entrar na agenda dos próximos anos.
