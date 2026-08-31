# MAPA DA PÁGINA MÁXIMA PARA A GESTORA — V7

## Estado e finalidade

Este documento é um mapa analítico de trabalho do Job 5F. Ele não é arquitetura editorial aprovada, não define módulos finais, não contém copy pública e não inicia o Job 6. Os 28 núcleos abaixo emergem do agrupamento das 55 oportunidades classificadas como `PROMISING`, `PROMISING_NEEDS_MORE_TESTING` ou `DESCRIPTIVE_ONLY` com utilidade de planejamento. Um núcleo pode reunir mais de uma linha da matriz sem fundir universos.

Regras permanentes:

- toda evidência educacional municipal usa `network_scope = total_all_dependencies`;
- dependência administrativa não é dimensão analítica;
- população é observada por residência, educação por localização da escola, mobilidade por residência do estudante e trabalho por localização do estabelecimento;
- taxas oficiais do Inep podem sustentar leitura municipal descritiva, mas não taxa regional recomposta, estabilidade por pequeno denominador ou ponderação inventada;
- cenários de coortes são pressões mecânicas, não previsões;
- nenhuma associação ecológica descrita abaixo é causal.

## Sequência potencial

### Direção 1 — O que o território ajuda a compreender sobre a educação?

#### 1. Ritmos demográficos e matrículas por etapa

- **Analysis IDs:** `D1_DEMOGRAFIA_MATRICULAS_ETAPA`.
- **Título de trabalho:** Ritmos diferentes entre população escolar e matrículas.
- **Pergunta respondida:** em quais etapas a oferta acompanhou, ficou aquém ou se moveu em direção diferente da população residente compatível?
- **Fatos que apareceriam:** no Vale, fundamental 117.469→104.328 matrículas e população compatível -10,20%; médio 31.789→26.911 matrículas e população compatível -23,51%; creche e pré-escola cresceram mesmo com retração das coortes regionais.
- **Visual sugerido:** pequenos múltiplos por etapa com população, matrícula e decomposição população/relação.
- **Bloco municipal:** Nova Santa Rita diverge do Vale no fundamental (3.873→3.957) e médio (799→840); creche 319→591 e pré-escola 459→823.
- **Ligação PNE/PME:** acesso à educação infantil, universalização e permanência nas etapas obrigatórias.
- **Questão de planejamento:** onde a capacidade precisa crescer, ser redistribuída ou ter uso revisto?
- **Limitações:** população residente e matrícula na escola não representam necessariamente as mesmas pessoas.

#### 2. Como escolas e turmas responderam à transformação

- **Analysis IDs:** `D1_DEMOGRAFIA_ESCOLAS_TURMAS`.
- **Título de trabalho:** A organização da oferta mudou junto com a demanda?
- **Pergunta respondida:** a mudança em matrículas foi acompanhada por abertura, fechamento ou reorganização de escolas e turmas?
- **Fatos que apareceriam:** escolas totais do Vale 737→734; no médio, turmas 1.075→1.193 apesar da redução de matrículas; em Nova Santa Rita, escolas 24→28 e turmas do médio 29→31.
- **Visual sugerido:** quadrantes de mudança em matrículas e turmas, com contribuição municipal.
- **Bloco municipal:** comparação de Nova Santa Rita com Vale e pares de crescimento demográfico defensáveis.
- **Ligação PNE/PME:** capacidade física, dimensionamento da rede total e continuidade da oferta.
- **Questão de planejamento:** a configuração atual é coerente com o volume e a distribuição futura dos estudantes?
- **Limitações:** contagens agregadas não medem ocupação física, distância nem qualidade.

#### 3. Coortes, passagens entre etapas e demanda mecânica

- **Analysis IDs:** `D1_COORTES_TRANSICOES_ETAPAS`, `D1_COORTES_DEMANDA_FUTURA_MECANICA`.
- **Título de trabalho:** O tamanho das coortes muda a pressão entre etapas.
- **Pergunta respondida:** que pressão mecânica a estrutura etária atual colocaria sobre cada etapa se aplicada sem modelar migração, retenção ou mobilidade?
- **Fatos que apareceriam:** em 2030, médio regional equivalente a 131,47% da matrícula-base 2025, fundamental 93,68% e pré-escola 45,61%; em Nova Santa Rita, médio 164,17%, fundamental 97,78% e pré-escola 47,27%.
- **Visual sugerido:** fluxo de coortes por etapa e índice relativo à base 2025.
- **Bloco municipal:** todas as pressões mecânicas de Nova Santa Rita, sem limitar a três leituras.
- **Ligação PNE/PME:** acesso, conclusão, tempo integral, docentes e infraestrutura a acompanhar.
- **Questão de planejamento:** quais etapas exigem monitoramento antecipado de capacidade?
- **Limitações:** não é previsão; não incorpora migração, fluxo escolar, escolha de rede ou deslocamentos.

#### 4. Nascimentos e educação infantil

- **Analysis IDs:** `D1_NASCIMENTOS_EDUCACAO_INFANTIL`.
- **Título de trabalho:** Os nascimentos antecipam mudança na procura da educação infantil?
- **Pergunta respondida:** a série de nascidos vivos antecede inflexões observadas em creche e pré-escola?
- **Fatos que apareceriam:** trajetória anual de nascimentos e defasagens coerentes com as idades das etapas, após nova materialização.
- **Visual sugerido:** linhas defasadas de nascimentos, população por idade e matrículas.
- **Bloco municipal:** defasagens específicas de Nova Santa Rita versus Vale.
- **Ligação PNE/PME:** expansão planejada da educação infantil.
- **Questão de planejamento:** em que horizonte a procura potencial muda e onde a oferta deve responder?
- **Limitações:** oportunidade real, mas o teste integrado não foi executado no 5F; migração pode quebrar a correspondência.

#### 5. Docentes, turmas e jornada diante da demografia

- **Analysis IDs:** `D1_DEMOGRAFIA_DOCENTES`, `D1_DOCENTES_TURMAS_JORNADA`.
- **Título de trabalho:** A força de trabalho docente acompanha a organização da oferta?
- **Pergunta respondida:** docentes, turmas e jornada se reorganizam no mesmo ritmo das matrículas?
- **Fatos que apareceriam:** mudanças por etapa em docentes, turmas, estudantes por docente/turma e horas-aula, após processamento conjunto.
- **Visual sugerido:** matriz etapa × recurso, com direção e magnitude das mudanças.
- **Bloco municipal:** Nova Santa Rita comparada ao Vale e a pares de trajetória demográfica.
- **Ligação PNE/PME:** valorização, formação, adequação e suficiência docente.
- **Questão de planejamento:** quais etapas combinam pressão de demanda com necessidade de reorganizar equipes?
- **Limitações:** fontes confirmadas, mas ainda não integradas aos artefatos congelados reutilizados pelo 5F.

#### 6. Trajetória municipal oficial

- **Analysis IDs:** `D1_FAMILIA_RENDIMENTO_MUNICIPAL`, `D1_MATRICULA_RENDIMENTO_OFICIAL`.
- **Título de trabalho:** Como a trajetória escolar mudou em cada município?
- **Pergunta respondida:** qual foi a direção e a magnitude municipal de aprovação, reprovação e abandono?
- **Fatos que apareceriam:** 10/10 municípios elevaram a aprovação do médio entre 2018 e 2025, mediana +17,50 pp; Nova Santa Rita +20,80 pp na aprovação e -1,50 pp no abandono.
- **Visual sugerido:** distribuição dos deltas municipais e série local oficial.
- **Bloco municipal:** evolução completa de Nova Santa Rita e posição na distribuição do Vale; comparação oficial com RS quando disponível no mesmo contrato.
- **Ligação PNE/PME:** permanência, conclusão e redução do insucesso.
- **Questão de planejamento:** a melhora foi ampla, persistente e semelhante entre etapas?
- **Limitações:** uso descritivo oficial; o estado formal de `H2_TRAJETORIA_MUNICIPAL_V2` permanece congelado e nenhuma taxa regional foi recomposta.

#### 7. Matrículas e distorção idade-série

- **Analysis IDs:** `D1_MATRICULA_DISTORCAO_OFICIAL`, `D1_DISTORCAO_PERSISTENCIA_DESCRITIVA`.
- **Título de trabalho:** Menor distorção mudou o perfil da trajetória?
- **Pergunta respondida:** a queda da distorção ocorreu de forma generalizada e em que ritmos?
- **Fatos que apareceriam:** 10/10 municípios reduziram a distorção do médio; mediana -13,70 pp; Nova Santa Rita 43,3%→24,8% no médio e 32,2%→22,7% nos anos finais.
- **Visual sugerido:** slopegraph municipal por etapa, acompanhado de matrículas.
- **Bloco municipal:** evolução local e diferença para a distribuição municipal do Vale.
- **Ligação PNE/PME:** fluxo, correção de trajetória e conclusão na idade adequada.
- **Questão de planejamento:** onde a distorção permanece alta mesmo após melhora?
- **Limitações:** leitura municipal oficial; não há componentes para regras de pequeno denominador ou recomposição regional.

#### 8. Organização das turmas e trajetória

- **Analysis IDs:** `D1_TRAJETORIA_ALUNOS_TURMA`.
- **Título de trabalho:** Mudanças no tamanho das turmas coincidem com mudanças de trajetória?
- **Pergunta respondida:** municípios com mudanças distintas em alunos por turma também apresentam trajetórias distintas?
- **Fatos que apareceriam:** correlação de postos entre deltas de alunos por turma e aprovação do médio = 0,25, `n=10`; Nova Santa Rita 32,9→27,1 alunos/turma.
- **Visual sugerido:** dispersão municipal de deltas, com série local ao lado.
- **Bloco municipal:** Nova Santa Rita destacada sem atribuição causal.
- **Ligação PNE/PME:** condições de oferta e permanência.
- **Questão de planejamento:** quais combinações merecem investigação escolar qualitativa?
- **Limitações:** associação ecológica fraca, poucos municípios, sem causalidade.

#### 9. Formação, esforço e regularidade docente

- **Analysis IDs:** `D1_TRAJETORIA_ADEQUACAO_DOCENTE`, `D1_TRAJETORIA_ESFORCO_DOCENTE`, `D1_TRAJETORIA_REGULARIDADE_DOCENTE`.
- **Título de trabalho:** A trajetória evolui em contextos docentes diferentes?
- **Pergunta respondida:** adequação de formação, esforço e regularidade ajudam a distinguir contextos municipais?
- **Fatos que apareceriam:** AFD do médio em Nova Santa Rita 52,4%→78,1%; associação de deltas AFD×aprovação = 0,18, `n=10`; esforço e regularidade aguardam integração.
- **Visual sugerido:** painel de condições docentes com séries e dispersões exploratórias.
- **Bloco municipal:** perfil docente completo de Nova Santa Rita versus Vale e pares.
- **Ligação PNE/PME:** formação específica, condições de trabalho e estabilidade das equipes.
- **Questão de planejamento:** que condição docente deve ser monitorada por etapa?
- **Limitações:** AFD não explica causalmente trajetória; IED e IRD ainda precisam de processamento.

#### 10. Horas-aula e tempo integral

- **Analysis IDs:** `D1_TRAJETORIA_HORAS_AULA`, `D1_TRAJETORIA_TEMPO_INTEGRAL`.
- **Título de trabalho:** A ampliação do tempo educativo aparece na trajetória territorial?
- **Pergunta respondida:** jornada diária e tempo integral mudaram de modo territorialmente desigual?
- **Fatos que apareceriam:** evolução por etapa e município, a calcular no recorte total.
- **Visual sugerido:** série de jornada/tempo integral alinhada às taxas municipais oficiais.
- **Bloco municipal:** posição e evolução de Nova Santa Rita.
- **Ligação PNE/PME:** educação em tempo integral e qualidade da jornada.
- **Questão de planejamento:** a ampliação ocorre nas etapas e territórios de maior necessidade?
- **Limitações:** fontes existem, mas o teste integrado ainda não foi executado.

#### 11. Infraestrutura, conectividade e contexto socioeconômico

- **Analysis IDs:** `D1_TRAJETORIA_CONECTIVIDADE`, `D1_TRAJETORIA_INFRAESTRUTURA`, `D1_TRAJETORIA_INSE`, `D1_CRESCIMENTO_INFRAESTRUTURA`.
- **Título de trabalho:** Quais condições distinguem os contextos da trajetória?
- **Pergunta respondida:** conectividade, infraestrutura e INSE funcionam como contexto útil, sem serem tratados como causa?
- **Fatos que apareceriam:** em 2025, 3/10 municípios tinham internet em 100% das escolas e 1/10 banda larga em 100%; Nova Santa Rita chegou a 100% em ambos; INSE×distorção do médio em 2023 = -0,55, `n=10`.
- **Visual sugerido:** perfil contextual municipal e mapa de lacunas de infraestrutura.
- **Bloco municipal:** conectividade local e itens efetivamente observados.
- **Ligação PNE/PME:** infraestrutura, equidade e inclusão digital.
- **Questão de planejamento:** quais lacunas materiais persistem apesar de indicadores agregados favoráveis?
- **Limitações:** associações ecológicas; vários itens de infraestrutura permanecem indisponíveis no recorte atual e conectividade apresenta saturação.

#### 12. Mobilidade educacional por etapa

- **Analysis IDs:** `D1_MOBILIDADE_POR_ETAPA`.
- **Título de trabalho:** Em quais etapas estudar fora do município pesa mais?
- **Pergunta respondida:** qual a intensidade da mobilidade por etapa e como ela varia entre municípios?
- **Fatos que apareceriam:** Vale total 14,76%, fundamental 7,01% e médio 15,09%; Nova Santa Rita total 17,60% e médio 19,11%.
- **Visual sugerido:** barras por etapa e município, com Vale, RS e Nova Santa Rita.
- **Bloco municipal:** perfil completo local por etapa.
- **Ligação PNE/PME:** acesso territorial, transporte e articulação intermunicipal.
- **Questão de planejamento:** em que etapa a coordenação regional é mais necessária?
- **Limitações:** origem do estudante sem destino; não mede qualidade, preferência ou ausência de oferta.

#### 13. Mobilidade, demografia, oferta e trajetória

- **Analysis IDs:** `D1_MOBILIDADE_ESTRUTURA_OFERTA`, `D1_MOBILIDADE_CRESCIMENTO_DEMOGRAFICO`, `D1_MOBILIDADE_TRAJETORIA`.
- **Título de trabalho:** Mobilidade é resposta a crescimento, oferta local ou outros mecanismos?
- **Pergunta respondida:** os padrões municipais sugerem perguntas mais específicas sobre pressão demográfica e oferta?
- **Fatos que apareceriam:** mobilidade do médio × mudança da matrícula local = -0,01; mobilidade × mudança da população 15–17 = 0,25; ambos `n=10` e exploratórios.
- **Visual sugerido:** matriz de dispersões e tipologia transparente de perfis.
- **Bloco municipal:** Nova Santa Rita posicionada nos quadrantes.
- **Ligação PNE/PME:** colaboração regional e continuidade de trajetórias.
- **Questão de planejamento:** que informação de destino deve ser buscada para orientar pactuação?
- **Limitações:** universos distintos, um único ano de mobilidade e ausência do destino; uso apenas para formular questões.

#### 14. Público adulto e distribuição da EJA fundamental

- **Analysis IDs:** `D1_EJA_FUNDAMENTAL_PUBLICO_ADULTO`.
- **Título de trabalho:** Onde estão o público adulto e as matrículas da EJA fundamental?
- **Pergunta respondida:** as distribuições territoriais de público potencial residente e matrículas localizadas coincidem?
- **Fatos que apareceriam:** Vale com público de 221.260 e 5.528 matrículas em 2022; Nova Santa Rita concentra 2,74% do público e 5,39% das matrículas.
- **Visual sugerido:** duas distribuições municipais paralelas e diferença em pontos percentuais.
- **Bloco municipal:** público 6.068, 298 matrículas e 49,1 matrículas por mil pessoas do universo definido.
- **Ligação PNE/PME:** alfabetização, elevação de escolaridade e EJA.
- **Questão de planejamento:** em que territórios oferta, alcance e articulação precisam ser investigados?
- **Limitações:** não é cobertura nem demanda; pessoa residente e matrícula na escola podem ser diferentes.

#### 15. Público adulto e distribuição da EJA médio

- **Analysis IDs:** `D1_EJA_MEDIO_PUBLICO_ADULTO`.
- **Título de trabalho:** Onde a EJA médio alcança o público potencial?
- **Pergunta respondida:** a distribuição municipal das matrículas acompanha a do público residente com fundamental e sem médio concluído?
- **Fatos que apareceriam:** Vale com público de 127.367 e 9.251 matrículas em 2022; Nova Santa Rita concentra 3,49% do público e 0,89% das matrículas.
- **Visual sugerido:** distribuição comparada com destaque para divergências.
- **Bloco municipal:** público 4.447, 82 matrículas e 18,4 matrículas por mil pessoas do universo definido.
- **Ligação PNE/PME:** conclusão do ensino médio e educação ao longo da vida.
- **Questão de planejamento:** que barreiras ou deslocamentos podem explicar a divergência local?
- **Limitações:** não identifica as mesmas pessoas, o destino da matrícula ou a demanda efetiva.

#### 16. Redistribuição histórica entre EJA fundamental e médio

- **Analysis IDs:** `D1_EJA_FUNDAMENTAL_HISTORICA`, `D1_EJA_MEDIO_HISTORICA`.
- **Título de trabalho:** A composição da EJA mudou de etapa.
- **Pergunta respondida:** como o volume e a composição das matrículas se transformaram desde 2014?
- **Fatos que apareceriam:** Vale fundamental 6.510→4.178 (-35,82%) e médio 2.325→7.269 (+212,65%); Nova Santa Rita total 309→208, com surgimento do médio e posterior retração.
- **Visual sugerido:** áreas empilhadas e contribuição municipal para a mudança.
- **Bloco municipal:** série completa 2014–2025 de Nova Santa Rita.
- **Ligação PNE/PME:** busca ativa, conclusão e adequação da oferta adulta.
- **Questão de planejamento:** a configuração atual responde ao perfil de escolaridade do público adulto?
- **Limitações:** mudanças de modalidade e regras de oferta exigem leitura institucional complementar.

#### 17. EJA integrada à educação profissional

- **Analysis IDs:** `D1_EJA_EDUCACAO_PROFISSIONAL`.
- **Título de trabalho:** A integração entre EJA e formação profissional ganhou escala?
- **Pergunta respondida:** a oferta integrada é substantiva e territorialmente distribuída?
- **Fatos que apareceriam:** Vale 171→157 matrículas integradas e participação 1,94%→1,37%; Nova Santa Rita registrou zero observado em 2014, 2022 e 2025.
- **Visual sugerido:** série regional com distribuição municipal e distinção explícita entre zero e ausência.
- **Bloco municipal:** zero observado local e alternativas regionais a investigar.
- **Ligação PNE/PME:** EJA integrada, EPT e inclusão produtiva.
- **Questão de planejamento:** há escala e articulação suficientes para combinar escolarização e qualificação?
- **Limitações:** matrícula não mede conclusão, demanda, qualidade ou deslocamento.

#### 18. Mudança da escolaridade adulta e vulnerabilidade

- **Analysis IDs:** `D1_ESCOLARIDADE_ADULTA_2010_2022_EJA`, `D1_VULNERABILIDADE_EJA_TRAJETORIA`.
- **Título de trabalho:** Quem ainda precisa ser alcançado pela política educacional adulta?
- **Pergunta respondida:** como a mudança 2010→2022 e a vulnerabilidade territorial reconfiguram a agenda da EJA?
- **Fatos que apareceriam:** mudança dos níveis de escolaridade adulta, distribuição CadÚnico e alinhamento com EJA, após processamento.
- **Visual sugerido:** matriz de mudança de escolaridade × oferta EJA × vulnerabilidade.
- **Bloco municipal:** perfil de Nova Santa Rita em 2010/2022 e localização do público vulnerável, sem microvinculação.
- **Ligação PNE/PME:** equidade, escolaridade adulta e busca ativa.
- **Questão de planejamento:** que público e território devem receber estratégia de alcance específica?
- **Limitações:** teste não executado; lentes e anos precisam permanecer separados.

#### 19. EPT dentro da rede escolar total

- **Analysis IDs:** `D1_MATRICULA_EPT_REDE`.
- **Título de trabalho:** Onde a formação técnica aparece — e onde não aparece — na rede regional?
- **Pergunta respondida:** como o volume de EPT se distribui em relação à rede e às matrículas gerais?
- **Fatos que apareceriam:** Vale 12.774→13.945 matrículas técnicas; Nova Santa Rita 0→0; oferta observada em sete municípios em 2025.
- **Visual sugerido:** mapa de presença, volume e participação da EPT na rede.
- **Bloco municipal:** zero observado local e oferta regional acessível apenas como hipótese, pois não há destino de mobilidade.
- **Ligação PNE/PME:** expansão da EPT e articulação territorial.
- **Questão de planejamento:** quando cooperação regional é mais plausível que duplicação local?
- **Limitações:** ausência local não prova falta de acesso; a fonte não observa origem dos estudantes da EPT.

#### 20. Diagnósticos PNE, educação especial e ruralidade

- **Analysis IDs:** `D1_PNE_DIAGNOSTICOS_COMPARADORES`, `D1_EDUCACAO_ESPECIAL_TERRITORIO`, `D1_EDUCACAO_RURAL_DEMOGRAFIA`.
- **Título de trabalho:** Que agendas transversais o diagnóstico municipal ainda precisa tornar visíveis?
- **Pergunta respondida:** quais metas e públicos específicos acrescentam contexto que as séries centrais não capturam?
- **Fatos que apareceriam:** comparadores PNE, AEE/educação especial e oferta rural, após processamento focado dos contratos já existentes.
- **Visual sugerido:** painel de alertas por meta/público com links metodológicos.
- **Bloco municipal:** diagnóstico completo de Nova Santa Rita, sem percorrer ou republicar os 499 detalhes.
- **Ligação PNE/PME:** metas e estratégias específicas correspondentes.
- **Questão de planejamento:** que agenda transversal deve entrar no monitoramento municipal?
- **Limitações:** relações ainda não testadas no 5F e comparabilidade deve ser validada por indicador.

### Direção 2 — O que as transformações do território colocam na agenda da educação?

#### 21. Trabalho juvenil e ensino médio

- **Analysis IDs:** `D2_TRABALHO_JUVENIL_ENSINO_MEDIO`, `D2_CAGED_JUVENIL_TRAJETORIA`.
- **Título de trabalho:** A expansão do trabalho juvenil muda a agenda de permanência?
- **Pergunta respondida:** o crescimento do emprego formal de jovens coincide com novas pressões de horário, permanência ou articulação?
- **Fatos que apareceriam:** vínculos RAIS 15–17 no Vale 2.483→4.225 e em Nova Santa Rita 104→172; sinais anteriores de RAIS/Caged×trajetória foram instáveis.
- **Visual sugerido:** linhas independentes de trabalho e trajetória, com anotação explícita das lentes.
- **Bloco municipal:** evolução local 15–17 e 18–24 versus Vale.
- **Ligação PNE/PME:** permanência no médio, EPT, busca ativa e articulação escola–trabalho.
- **Questão de planejamento:** como horários, apoio e orientação podem responder ao novo contexto juvenil?
- **Limitações:** emprego é no estabelecimento, educação na escola e população na residência; não são as mesmas pessoas.

#### 22. Aprendizagem profissional

- **Analysis IDs:** `D2_APRENDIZES_JOVENS_EDUCACAO`, `D2_APRENDIZ_OCUPACOES_EIXOS`.
- **Título de trabalho:** A aprendizagem profissional ganhou escala e em quais atividades?
- **Pergunta respondida:** o crescimento de admissões de aprendizes cria oportunidades de articulação educacional?
- **Fatos que apareceriam:** admissões ajustadas 15–17 no Vale 1.235 em 2020 e 3.157 em 2025; Nova Santa Rita 55→174; ocupações/eixos ainda precisam ser consolidados.
- **Visual sugerido:** fluxo de admissões/desligamentos e composição ocupacional.
- **Bloco municipal:** evolução local por idade e, após teste, por ocupação/setor.
- **Ligação PNE/PME:** aprendizagem, EPT, permanência e transição protegida.
- **Questão de planejamento:** quais arranjos podem ampliar aprendizagem compatível com a escolarização?
- **Limitações:** Caged é fluxo de eventos, não pessoas nem estoque; estabelecimento não é residência.

#### 23. Escolaridade dos jovens no trabalho formal

- **Analysis IDs:** `D2_ESCOLARIDADE_JOVENS_TRABALHADORES`, `D2_COORTES_JOVENS_TRABALHO`.
- **Título de trabalho:** Quem são os jovens presentes no emprego formal do território?
- **Pergunta respondida:** como idade e escolaridade dos vínculos jovens mudaram?
- **Fatos que apareceriam:** vínculos 18–24 no Vale 36.742→37.885 e em Nova Santa Rita 1.117→1.638; composição preservada em 11 códigos até validação do dicionário oficial.
- **Visual sugerido:** composição por idade/escolaridade e variação absoluta.
- **Bloco municipal:** perfil local completo, comparado ao Vale.
- **Ligação PNE/PME:** conclusão, EJA, EPT e educação ao longo da vida.
- **Questão de planejamento:** que combinação de conclusão e qualificação dialoga com o perfil jovem empregado?
- **Limitações:** rótulos editoriais dependem de dicionário oficial versionado; vínculos não são pessoas únicas.

#### 24. Escolaridade adulta, EJA e trabalho

- **Analysis IDs:** `D2_ESCOLARIDADE_ADULTA_TRABALHO`, `D2_PUBLICO_ADULTO_EJA_TRABALHO`.
- **Título de trabalho:** A escolaridade adulta dialoga com a estrutura de trabalho do território?
- **Pergunta respondida:** que mudanças na escolaridade residente e no perfil dos vínculos adultos colocam novas questões para EJA e qualificação?
- **Fatos que apareceriam:** composição adulta 2010/2022, RAIS adulta e EJA em painéis de lentes separadas, após processamento.
- **Visual sugerido:** composição comparada de escolaridade residente, vínculos formais e oferta EJA.
- **Bloco municipal:** Nova Santa Rita versus Vale, sem pressupor que residentes, trabalhadores e matriculados sejam as mesmas pessoas.
- **Ligação PNE/PME:** elevação da escolaridade adulta, EJA, EPT e educação ao longo da vida.
- **Questão de planejamento:** que público adulto deve ser priorizado por escolarização, qualificação ou busca ativa?
- **Limitações:** teste não executado no 5F; RAIS adulta precisa ser integrada e os universos não podem ser vinculados individualmente.

#### 25. Ocupações em crescimento e retração × formação

- **Analysis IDs:** `D2_OCUPACOES_CRESCIMENTO_FORMACAO`, `D2_CAGED_OCUPACOES_EMERGENTES`, `D2_CBO_CNCT_PONTE`.
- **Título de trabalho:** Que mudanças ocupacionais merecem investigação formativa?
- **Pergunta respondida:** quais ocupações crescem ou recuam e que cursos possuem correspondência normativa possível?
- **Fatos que apareceriam:** no Vale, telemarketing 2.052→7.984 e auxiliar de logística 606→4.248; em Nova Santa Rita, auxiliar de logística 17→722; listas Caged seriam apenas contexto de fluxo; ponte cobre 39 cursos e 12.664 matrículas, 90,81% das matrículas técnicas.
- **Visual sugerido:** divergência de ocupações com ponte auditável para cursos, sem somar correspondências.
- **Bloco municipal:** logística, transporte e demais mudanças locais versus região.
- **Ligação PNE/PME:** EPT, orientação e articulação com desenvolvimento territorial.
- **Questão de planejamento:** quais movimentos justificam escuta de empregadores, estudantes e provedores de formação?
- **Limitações:** ponte CBO–CNCT é normativa, parcial, muitos-para-muitos e não prova adequação, demanda ou suficiência.

#### 26. Setores, eixos tecnológicos e shift-share

- **Analysis IDs:** `D2_SETORES_CURSOS_EIXOS`, `D2_SHIFT_SHARE_ECONOMIA_EDUCACAO`, `D2_EPT_TENDENCIA_TRABALHO`.
- **Título de trabalho:** A estrutura formativa acompanha a transformação setorial?
- **Pergunta respondida:** mudanças CNAE e ocupacionais são acompanhadas por mudança nos eixos técnicos?
- **Fatos que apareceriam:** matrículas técnicas 13.474→13.945; HHI de eixos 0,181→0,193; painel setorial e shift-share aguardam consolidação.
- **Visual sugerido:** shift-share setorial, variação por eixo e matriz setor–eixo com regras explícitas.
- **Bloco municipal:** mudança setorial de Nova Santa Rita e oferta local/regional.
- **Ligação PNE/PME:** EPT alinhada ao desenvolvimento sustentável, sem subordinação automática ao emprego corrente.
- **Questão de planejamento:** quais competências transversais e eixos merecem expansão, atualização ou investigação?
- **Limitações:** não existe correspondência causal ou exclusiva entre setor e curso; teste consolidado pendente.

#### 27. Concentração territorial da formação e do trabalho

- **Analysis IDs:** `D2_CONCENTRACAO_TRABALHO_FORMACAO`.
- **Título de trabalho:** A oferta técnica está concentrada onde as transformações ocorrem?
- **Pergunta respondida:** a distribuição territorial da EPT cria dependências de cooperação regional?
- **Fatos que apareceriam:** HHI municipal da EPT 0,258 em 2023 e 0,258 em 2025; municípios com oferta observada caíram de oito para sete.
- **Visual sugerido:** Lorenz/mapa de concentração com municípios contribuintes.
- **Bloco municipal:** Nova Santa Rita com zero observado e posição frente aos polos regionais.
- **Ligação PNE/PME:** expansão territorial da EPT e regime de colaboração.
- **Questão de planejamento:** onde a concentração é eficiente e onde cria barreira de acesso?
- **Limitações:** sem origem/destino dos estudantes não se mede acesso efetivo.

#### 28. Mobilidade, transporte, EPT, finanças e agenda futura

- **Analysis IDs:** `D2_MOBILIDADE_EPT`, `D2_TRANSPORTE_MOBILIDADE`, `D2_FINANCAS_CONDICOES_OFERTA`, `D2_COORTES_INDICADORES_PNE`.
- **Título de trabalho:** Que capacidade de coordenação será necessária para responder às pressões futuras?
- **Pergunta respondida:** como coortes, deslocamentos, transporte, concentração de EPT e capacidade financeira podem orientar governança?
- **Fatos que apareceriam:** pressão mecânica do médio em 2030 = 131,47% da base regional e 164,17% em Nova Santa Rita; demais relações aguardam integração de PNATE e finanças.
- **Visual sugerido:** painel prospectivo de pressões e capacidades, com cada lente separada.
- **Bloco municipal:** cenário mecânico e indicadores de capacidade de Nova Santa Rita.
- **Ligação PNE/PME:** monitoramento de metas, transporte, financiamento e colaboração regional.
- **Questão de planejamento:** quais indicadores devem disparar revisão de capacidade e pactuação intermunicipal?
- **Limitações:** não é previsão; não há destino da mobilidade nem causalidade entre gasto, oferta e resultado.

## Fechamento do mapa

Os 28 núcleos são um inventário máximo agrupado, não uma recomendação de publicar 28 módulos. Alguns possuem evidência pronta; outros são espaços analíticos condicionados a processamento adicional. `INSUFFICIENT_DATA`, `REDUNDANT` e `REJECTED` não foram usados para compor histórias. A próxima decisão é externa e deve indicar testes adicionais antes de qualquer protótipo visual.
