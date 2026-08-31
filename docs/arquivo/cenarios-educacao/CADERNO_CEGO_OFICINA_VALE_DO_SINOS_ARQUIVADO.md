<!-- artefato-arquivado-nao-operacional -->
# ARQUIVADO — caderno não operacional

> Este material foi retirado do fluxo ativo em 31/08/2026 e permanece somente como
> registro histórico. Não representa etapa, requisito ou gate da publicação atual.

# Caderno cego da oficina — Cenários da Educação

> **RASCUNHO DE FACILITAÇÃO. NÃO É RECIBO DE VALIDAÇÃO.** Nenhuma caixa vem marcada e nenhuma decisão está predefinida.

## Vinculação ao conteúdo revisado

- Região: Vale do Sinos — RS
- Município focal: Nova Santa Rita — código IBGE textual 4313375
- Versão do conteúdo a revisar: `948934d8d5b5dcd8cb843982a19839a57429f24e2675ac13b639a2e42fdb25f7`
- SHA-256 do bundle: `b4235c4026199f44bc4e7f50c7ab7870e508df5f97d1e256c2d069b1347fdbdd`
- Tamanho do bundle: `140202` bytes
- SHA-256 do contrato de autoria: `866a08045bf84b42ab17befbc6237a359090eb246c1f620b3592f2953d384fef`
- Estado institucional atual: `pending`

Se qualquer hash ou versão mudar, descarte este caderno e gere outro. Este arquivo não registra presença, concordância ou validação.

## Regras da oficina

- Os quatro futuros são exploratórios, não probabilísticos e têm o mesmo estatuto.
- O PNE é camada normativa separada; não é um quinto cenário.
- Novo Hamburgo é caso contrastante para testar transferibilidade; não é benchmark, ranking ou quinto cenário.
- Fato observado, derivação, hipótese e escolha normativa não são intercambiáveis.
- Não registrar nomes, contatos, documentos, assinaturas ou qualquer dado pessoal neste caderno.
- Futuro A, B, C e D seguem a ordem técnica do modelo vinculado; títulos e IDs ficam ocultos durante a revisão cega.

## Módulo 1 — Forças, evidências e sinais

### Fontes congeladas do bundle

| Fonte | Caminho | SHA-256 | Bytes |
| --- | --- | --- | --- |
| authoringContract | data_pipeline/contracts/vocacoes-pne-foresight-v1.json | 866a08045bf84b42ab17befbc6237a359090eb246c1f620b3592f2953d384fef | 99660 |
| advancedBundle | src/features/vocacoes-regiao/generated/vocacoesPneAdvancedInsightsValeDoSinos.json | 824fb1c726d7cce0c87de97bc577b46246a3023eef95c385d8405d01e2f66017 | 99576 |
| advancedRegistry | src/features/vocacoes-regiao/generated/vocacoesPneAdvancedInsightsRegistry.json | ebb35b5d451ad34719891cef707d21055d92e8a5b77be96e517c7bb9318d786d | 1120 |
| regionConfig | config/regions/rs.json | 9892fc8fca0b1fc349c4cd49edf455760121adfd5c1113e5e224f547c1e90542 | 11177 |
| municipalityRegistry | config/municipalities/rs.json | 06b5c0eb6f025cf618549fc10fd004c6de628488d59dd35b239207b1ca42e9dd | 52978 |
| pneMunicipalMatrix | public/data/pne2026-matriz/municipios/4313375.json | 7afbb731c506605b2fa98fd3405f263358ef592ef8542e5c74ccfa58315f7267 | 513354 |
| contrastPneMunicipalMatrix | public/data/pne2026-matriz/municipios/4313409.json | f314638c9725ac398b09e55c77a749deb7c5c3564de3f42109f1665d97e842f2 | 261252 |
| vocacoesNarrative | src/features/vocacoes-regiao/generated/vocacoesPneValeDoSinos.json | 8f9515bf35283bb2622f823830dc1c5ff5cad4aa711158ce120edc07eab64f2c | 25963 |
| vocacoesOfficialPromotion | src/features/vocacoes-regiao/generated/vocacoesPneOfficialPromotion.json | 7ec8061bfa8ec1de5b68bfe16a78691d3df441e600226f0b92454390616360f7 | 1575 |
| vocacoesJob5iCore | src/features/vocacoes-pne-internal/generated/vocacoesPneJob5iCore.json | e32f524ff629e546a94b2db4af2d6bc3a15f4d63a189b209a127297cfb2d65a9 | 1308901 |
| vocacoesJob5iSeries | src/features/vocacoes-pne-internal/generated/vocacoesPneJob5iSeries.json | 09c0f13c1143663b29f2f11040af0a098ef332f480d969da905588783d9eb152 | 3225682 |

### Baseline regional observada

| Evidência | Valor/estado | Período | Lente territorial | Classe | Referência técnica | Teto de afirmação |
| --- | --- | --- | --- | --- | --- | --- |
| Mudança nas matrículas de ensino médio | -2339 matrículas; início 29250 matrículas, fim 26911 matrículas | 2018–2025 | SCHOOL_LOCATION_ENROLLMENT | fato observado | advanced:region:readings:demografia-matriculas-rede:0 | Mudança observada em matrículas localizadas; não descreve a população residente. |
| Parte ligada à mudança no número de jovens | -5544.375734534104 matrículas | período declarado na análise | REGIONAL_AGGREGATE | derivação contábil | advanced:region:readings:demografia-matriculas-rede:1 | Componente aritmético da identidade; não é projeção demográfica. |
| Abandono no ensino médio | 2.8 % | período declarado na análise | SCHOOL_LOCATION_ENROLLMENT | fato observado | advanced:region:readings:trajetoria-contexto:0 | Mediana municipal regional; não autoriza causalidade. |
| Mudança nas matrículas técnicas | 471 matrículas; início 13474 matrículas, fim 13945 matrículas | 2023–2025 | EDUCATION_OFFER_LOCATION | fato observado | advanced:region:readings:transformacao-economica-ept:0 | Matrículas localizadas não medem vagas, conclusão, demanda ou emprego. |
| Faixa ao considerar cursos em outros municípios do Vale | 19.91003665173448–50.06034578505054 % | período declarado na análise | REGIONAL_AGGREGATE | faixa validada | advanced:region:readings:transformacao-economica-ept:2 | Faixa nomenclatural validada; não é estimativa de demanda ou empregabilidade. |
| EJA fundamental | -2332 matrículas; início 6510 matrículas, fim 4178 matrículas | 2014–2025 | SCHOOL_LOCATION_ENROLLMENT | fato observado | advanced:region:readings:escolaridade-adulta-eja:0 | Mudança de matrícula por etapa; não equivale a procura. |
| EJA ensino médio | 4944 matrículas; início 2325 matrículas, fim 7269 matrículas | 2014–2025 | SCHOOL_LOCATION_ENROLLMENT | fato observado | advanced:region:readings:escolaridade-adulta-eja:1 | Mudança de matrícula por etapa; não equivale a procura. |
| Empregos formais de 15 a 17 anos | 1742 empregos formais; início 2483 empregos formais, fim 4225 empregos formais | 2019–2025 | ESTABLISHMENT_LOCATION_EMPLOYMENT | fato observado | advanced:region:readings:trabalho-juvenil-permanencia:0 | Vínculos por estabelecimento não identificam os mesmos jovens matriculados. |

### Baseline observada de Nova Santa Rita

| Evidência | Valor/estado | Período | Lente territorial | Classe | Referência técnica | Teto de afirmação |
| --- | --- | --- | --- | --- | --- | --- |
| Mudança nas matrículas de ensino médio | 17 matrículas; início 823 matrículas, fim 840 matrículas | 2018–2025 | SCHOOL_LOCATION_ENROLLMENT | fato observado | advanced:municipality:readings:demografia-matriculas-rede:0 | Mudança observada em matrículas localizadas; não descreve a coorte residente. |
| Diferença que ainda precisa ser investigada | 58.44947676070974 matrículas | período declarado na análise | REGIONAL_AGGREGATE | derivação contábil | advanced:municipality:readings:demografia-matriculas-rede:2 | Componente residual contábil; não mede migração, cobertura ou resposta institucional. |
| Abandono no ensino médio | 3.2 % | período declarado na análise | SCHOOL_LOCATION_ENROLLMENT | fato observado | advanced:municipality:readings:trajetoria-contexto:0 | Ponto observado; diferenças contextuais não demonstram causa. |
| Matrículas técnicas locais | 0 matrículas; início 0 matrículas, fim 0 matrículas — zero observado | 2023–2025 | EDUCATION_OFFER_LOCATION | fato observado | advanced:municipality:readings:transformacao-economica-ept:0 | Zero local observado; não significa ausência de acesso regional ou demanda. |
| EJA fundamental | -157 matrículas; início 309 matrículas, fim 152 matrículas | 2014–2025 | SCHOOL_LOCATION_ENROLLMENT | fato observado | advanced:municipality:readings:escolaridade-adulta-eja:0 | Mudança municipal pequena; não equivale a procura ou efeito. |
| EJA ensino médio | 56 matrículas; início 0 matrículas, fim 56 matrículas | 2014–2025 | SCHOOL_LOCATION_ENROLLMENT | fato observado | advanced:municipality:readings:escolaridade-adulta-eja:1 | Mudança municipal pequena; não equivale a procura ou efeito. |
| Empregos formais de 15 a 17 anos | 68 empregos formais; início 104 empregos formais, fim 172 empregos formais | 2019–2025 | ESTABLISHMENT_LOCATION_EMPLOYMENT | fato observado | advanced:municipality:readings:trabalho-juvenil-permanencia:0 | Vínculos por estabelecimento não identificam os mesmos jovens matriculados. |
| Mudança nas matrículas rurais | 55 matrículas; início 718 matrículas, fim 773 matrículas | 2014–2025 | SCHOOL_LOCATION_ENROLLMENT | fato observado | advanced:municipality:transversal:ruralidade-organizacao-rede:0 | Matrícula rural não mede rota, tempo, regularidade ou segurança do transporte. |
| Mudança nas matrículas da educação especial | 352 matrículas; início 104 matrículas, fim 456 matrículas | 2014–2025 | SCHOOL_LOCATION_ENROLLMENT | fato observado | advanced:municipality:transversal:inclusao-aee:0 | Matrícula não mede necessidade individual, qualidade ou suficiência do AEE. |
| Pessoas de baixa renda registradas | 2362 pessoas | 2024-12 | ADMINISTRATIVE_REGISTER | fato observado | advanced:municipality:transversal:contexto-social-registrado:0 | Contagem cadastrada; não é prevalência de baixa renda. |

> **Pequena base municipal:** Variações municipais pequenas podem refletir poucos registros e oscilar entre safras. Elas funcionam como sinais para investigação, nunca como tendência estável, efeito causal ou projeção.

### Incertezas morfológicas

### Dinâmica demográfica e espacial das matrículas

**Incerteza:** Se coortes residentes e matrículas localizadas voltarão a convergir ou continuarão redistribuídas pelo território.

- **Divergência territorial persistente:** Coortes e matrículas localizadas continuam mudando em ritmos ou direções diferentes, exigindo investigar fluxos e oferta.
- **Volatilidade por choques:** Interrupções e mudanças de residência, acesso ou calendário tornam a demanda localizada menos estável.
- **Redistribuição planejada:** A rede usa informação de coortes e fluxos para ajustar capacidade e pactos de acesso sem presumir fechamento automático.

### Transição econômica e conexão formativa

**Incerteza:** Se a formação conseguirá acompanhar recomposições do trabalho sem converter correspondência nomenclatural em demanda presumida.

- **Descompasso gradual:** Mudanças econômicas avançam lentamente, enquanto oferta e acesso formativo permanecem pouco coordenados.
- **Transição acelerada e fragmentada:** O trabalho se recompõe mais rápido que a capacidade de mapear acesso, conclusão e trajetórias formativas.
- **Pressão de renda e descontinuidade:** Oscilações econômicas e de renda ampliam conciliação estudo-trabalho e instabilidade de oferta.
- **Ecossistema regional de formação:** Municípios e ofertantes pactuam rotas, informação e capacidade regional, ainda sujeitos a centralização e dependência.

### Pressões sociais e trajetórias

**Incerteza:** Como trabalho, renda, cuidado, inclusão e barreiras territoriais se combinarão na permanência, aprendizagem e retorno à escola.

- **Lacunas persistentes e localizadas:** Barreiras permanecem concentradas em públicos e lugares, sem resposta coordenada suficiente.
- **Tensão entre trabalho e estudo:** A recomposição do trabalho aumenta conflitos de horário, deslocamento e continuidade para jovens e adultos.
- **Vulnerabilidades combinadas:** Renda, interrupções, cuidado, inclusão e mobilidade se acumulam e pressionam trajetórias.
- **Proteção antecipada, porém desigual:** Busca ativa e apoios chegam antes, mas cobertura e qualidade variam entre municípios e públicos.

### Mobilidade e coordenação da rede

**Incerteza:** Se residência, escola, formação e trabalho serão conectados por arranjos locais, corredores seletivos ou pactos regionais.

- **Fragmentação local:** Cada rede reage com pouca informação de fluxos e capacidade dos municípios vizinhos.
- **Corredores seletivos:** Alguns eixos de formação e trabalho ganham conexão, enquanto outros públicos e territórios ficam à margem.
- **Acesso interrompido:** Falhas de transporte, calendário ou infraestrutura reduzem a confiabilidade das rotas educacionais.
- **Coordenação regional:** A rede compartilha informação, critérios e serviços, assumindo custos de governança e riscos de centralização.

### Capacidade institucional e fiscal de adaptação

**Incerteza:** Se governos e redes conseguirão financiar, aprender e rever decisões antes de consolidar estruturas rígidas.

- **Resposta reativa e restrita:** Ajustes ocorrem depois dos problemas, com baixa margem para coordenação e experimentação.
- **Projetos seletivos:** Iniciativas avançam em temas visíveis, mas sem escala, integração ou sustentabilidade homogênea.
- **Capacidade defensiva de emergência:** Recursos são deslocados para continuidade imediata, adiando transformação estrutural.
- **Capacidade compartilhada e dependente:** A coordenação amplia repertório e escala, mas depende de acordos, financiamento e equilíbrio de voz.

### Forças transversais ainda sem observação madura

- **Eventos climáticos e continuidade** — EXPLICIT_GAP; Usar apenas como condição de interrupção a testar com registros locais de rota, calendário e infraestrutura.
- **Tecnologia e organização do ensino** — EXPLICIT_GAP; Não presumir acesso, eficácia ou substituição do presencial; monitorar infraestrutura, uso e exclusão.
- **Restrição fiscal e custo de coordenação** — EXPLICIT_GAP; Não atribuir valor futuro; testar margem de continuidade, cofinanciamento e custos recorrentes.
- **Regulação e regime de colaboração** — EXPLICIT_GAP; Tratar como condição institucional, separada da norma vigente e de qualquer compromisso já formalizado.

### Registro do módulo

- [ ] Fontes e lentes territoriais foram compreendidas.
- [ ] Zero observado, ausência e indisponibilidade foram distinguidos.
- [ ] Forças confirmadas: ___________________________________________________
- [ ] Forças contestadas: ___________________________________________________
- [ ] Lacunas adicionais: ___________________________________________________

## Módulo 2 — Coerência, distribuição e vieses

### Futuro A — cartão cego

> Título, rótulo curto e identificador técnico foram retirados deliberadamente.

**Configuração morfológica**

| Fator | Estado neste futuro |
| --- | --- |
| Dinâmica demográfica e espacial das matrículas | Divergência territorial persistente |
| Transição econômica e conexão formativa | Descompasso gradual |
| Pressões sociais e trajetórias | Lacunas persistentes e localizadas |
| Mobilidade e coordenação da rede | Fragmentação local |
| Capacidade institucional e fiscal de adaptação | Resposta reativa e restrita |

**Narrativa sintética:** Até 2036, coortes, matrículas e oferta seguem ritmos diferentes entre os municípios. A rede preserva autonomia local, mas reage tardiamente a fluxos regionais e a barreiras que permanecem concentradas.

**Encadeamento hipotético**

1. Sinais demográficos e matrículas localizadas continuam sem convergir de forma simples.
2. Cada rede ajusta capacidade com informação incompleta sobre residência, escola e deslocamento.
3. Lacunas de permanência, EJA, inclusão e acesso técnico ficam concentradas em públicos pouco visíveis.
4. Decisões incrementais evitam ruptura imediata, porém acumulam descompassos territoriais.

**Oportunidades**

- Preservar flexibilidade local e corrigir problemas pontuais com baixo custo de coordenação.
- Usar o checkpoint de 2030–2031 para transformar divergências repetidas em investigação dirigida.

**Riscos**

- Confundir redução de coorte com queda automática de demanda localizada.
- Manter vazios de acesso regional à EPT, EJA e apoio especializado fora da visão municipal.

**Trade-offs**

- Autonomia e resposta rápida local versus perda de escala e de informação regional.
- Preservação de estruturas existentes versus adaptação tardia a novos fluxos.

#### Seis dimensões integradas

#### Dimensão — Demografia e demanda educacional

- **Estado:** Demanda localizada permanece desigual e não acompanha mecanicamente a coorte residente.
- **Mecanismo:** Fluxos residência–escola e organização da oferta continuam pouco medidos.
- **No Vale:** Municípios alternam ociosidade aparente e pressão localizada sem uma leitura comum.
- **Em Nova Santa Rita:** A divergência já observada entre coorte e matrículas exige confirmar origem dos estudantes antes de redimensionar capacidade.

#### Dimensão — Rede, acesso e mobilidade

- **Estado:** Acesso continua resolvido principalmente por arranjos locais e informais.
- **Mecanismo:** Rotas, tempos, vagas e fluxos entre municípios não formam um mapa operacional compartilhado.
- **No Vale:** A cobertura real depende do município de residência e de conexões não documentadas.
- **Em Nova Santa Rita:** Ruralidade e dependência potencial de oferta externa tornam transporte e continuidade variáveis críticas.

#### Dimensão — Trajetórias educacionais

- **Estado:** Permanência e aprendizagem melhoram ou pioram de modo localizado.
- **Mecanismo:** Barreiras de turno, trabalho, cuidado e deslocamento são tratadas caso a caso.
- **No Vale:** Medianas regionais escondem públicos e escolas que se afastam da trajetória esperada.
- **Em Nova Santa Rita:** Abandono, EJA por etapa e trabalho juvenil precisam ser monitorados juntos, sem assumir associação causal.

#### Dimensão — Capacidade educacional

- **Estado:** Equipes, AEE e infraestrutura são ajustados depois que a pressão aparece.
- **Mecanismo:** Planejamento usa estoques locais e reage lentamente a mudanças de composição.
- **No Vale:** Capacidade especializada permanece desigual e difícil de compartilhar.
- **Em Nova Santa Rita:** O crescimento observado da educação especial exige medir atendimento, profissionais e acessibilidade, não apenas matrículas.

#### Dimensão — Economia, trabalho e formação

- **Estado:** Recomposição econômica avança gradualmente, sem uma ponte operacional entre oferta, conclusão e trabalho.
- **Mecanismo:** Correspondências de nomenclatura orientam perguntas, mas não viram pactos de acesso.
- **No Vale:** A região conserva oferta, porém com informação insuficiente sobre quem alcança e conclui.
- **Em Nova Santa Rita:** O zero local de matrícula técnica aumenta dependência de um acesso regional ainda não mapeado.

#### Dimensão — Financiamento e governança

- **Estado:** Orçamentos e decisões permanecem compartimentados por rede e programa.
- **Mecanismo:** Custos de coordenação são evitados no curto prazo e reaparecem como duplicidade ou vazio de serviço.
- **No Vale:** Ajustes preservam continuidade, mas reduzem capacidade de antecipação.
- **Em Nova Santa Rita:** O município precisa distinguir o que controla, o que pactua e o que depende de oferta estadual ou regional.

#### Efeitos distributivos a validar

#### Estudantes rurais ou dependentes de deslocamento

- **Exposição:** A oferta fragmentada pode tornar rota, tempo e continuidade mais determinantes que a vaga nominal.
- **O que pode abrir:** A flexibilidade local pode corrigir barreiras específicas quando elas são observadas cedo.
- **O que pode agravar:** Fluxos invisíveis podem deixar estudantes sem alternativa estável entre municípios.
- **Pergunta de equidade:** Quem deixa de alcançar escola, apoio ou formação quando a resposta permanece apenas local?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `NSR_RURAL_ENROLLMENT_CHANGE`, `NSR_HS_ENROLLMENT_CHANGE`

#### Públicos da EJA e jovens que conciliam estudo e trabalho

- **Exposição:** Mudanças distintas por etapa, turno e trabalho podem permanecer escondidas na leitura agregada.
- **O que pode abrir:** Ajustes municipais podem responder rapidamente a uma barreira localizada.
- **O que pode agravar:** Sem leitura regional, horário, deslocamento e continuidade podem ficar sem responsável claro.
- **Pergunta de equidade:** A rede identifica separadamente quem precisa retornar, permanecer ou mudar de turno?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `REG_EJA_FUNDAMENTAL_CHANGE`, `NSR_EJA_FUNDAMENTAL_CHANGE`, `NSR_YOUTH_FORMAL_WORK_CHANGE`

#### Estudantes que demandam AEE, acessibilidade ou apoio especializado

- **Exposição:** Capacidade especializada pode variar entre redes e responder somente depois que a pressão aparece.
- **O que pode abrir:** A proximidade local pode preservar vínculo e adaptação ao contexto do estudante.
- **O que pode agravar:** Vazios de equipe, infraestrutura ou transporte podem persistir sem compartilhamento regional.
- **Pergunta de equidade:** Matrícula, atendimento, qualidade e continuidade estão sendo distinguidos?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `NSR_SPECIAL_EDUCATION_CHANGE`

#### Equipes escolares e gestão educacional municipal

- **Exposição:** Decisões reativas podem concentrar diagnóstico, coordenação e execução nas mesmas equipes locais.
- **O que pode abrir:** Autonomia preserva capacidade de ajuste e conhecimento do território.
- **O que pode agravar:** Duplicidade, sobrecarga e informação incompleta podem reduzir antecipação e continuidade.
- **Pergunta de equidade:** Quais responsabilidades exigem capacidade municipal e quais precisam de suporte compartilhado?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `REG_HS_ENROLLMENT_CHANGE`, `NSR_ACCOUNTING_RESIDUAL`

#### Dependências regionais

- **Informação residência–escola e capacidade** (compartilhada): Uma leitura comum de origem, destino, etapa e vaga é necessária para distinguir redistribuição de demanda local.
  Estatuto: hipótese de cenário (`SCENARIO_ASSUMPTION`); referências: `REG_HS_ENROLLMENT_CHANGE`, `NSR_ACCOUNTING_RESIDUAL`.
- **Mapa regional de EPT, EJA e apoio especializado** (compartilhada): Oferta localizada só vira acesso quando vaga, horário, transporte e continuidade são conhecidos.
  Estatuto: hipótese de cenário (`SCENARIO_ASSUMPTION`); referências: `REG_EPT_ACCESSIBLE_BOUND`, `NSR_LOCAL_TECHNICAL_ENROLLMENTS`.
- **Capacidade compartilhada de atendimento especializado** (compartilhada): Equipes e infraestrutura não disponíveis localmente exigem pactos de acesso e continuidade.
  Estatuto: hipótese de cenário (`SCENARIO_ASSUMPTION`); referências: `NSR_SPECIAL_EDUCATION_CHANGE`.

#### Premissas

- A divergência territorial reaparece em atualizações comparáveis.
- Não se consolida um regime regional de informação e coordenação.
- Restrições de capacidade favorecem respostas incrementais.

#### O que enfraquece este futuro

- Dados de residência–escola mostrarem convergência estável entre coorte e demanda localizada.
- Pactos regionais passarem a governar rotas, vagas e capacidade com cobertura demonstrada.

#### Limitações específicas

- Não existe matriz validada de origem e destino entre residência, escola e formação.
- A projeção municipal por idade e sexo permanece indisponível para estimar demanda futura.
- Não há evidência direta suficiente para classificar a capacidade de coordenação institucional.

#### Ficha de revisão — Futuro A

- [ ] Coerência causal revisada.
- [ ] Equilíbrio entre oportunidades, riscos e trade-offs revisado.
- [ ] Efeitos distributivos e risco de estigma revisados.
- [ ] Implicações para Nova Santa Rita revisadas.
- Decisão: [ ] aceitar como instrumento exploratório  [ ] exigir revisão  [ ] rejeitar.
- Concordâncias: ____________________________________________________________
- Dissensos: ________________________________________________________________
- Evidência ou ponto cego a acrescentar: _____________________________________

---

### Futuro B — cartão cego

> Título, rótulo curto e identificador técnico foram retirados deliberadamente.

**Configuração morfológica**

| Fator | Estado neste futuro |
| --- | --- |
| Dinâmica demográfica e espacial das matrículas | Divergência territorial persistente |
| Transição econômica e conexão formativa | Transição acelerada e fragmentada |
| Pressões sociais e trajetórias | Tensão entre trabalho e estudo |
| Mobilidade e coordenação da rede | Corredores seletivos |
| Capacidade institucional e fiscal de adaptação | Projetos seletivos |

**Narrativa sintética:** Até 2036, setores e ocupações se recompõem mais rápido que a capacidade de conectar estudantes a formação, conclusão e trabalho. Corredores seletivos criam oportunidades, mas deixam trajetórias e territórios fora do alcance.

**Encadeamento hipotético**

1. O trabalho formal muda e amplia a pressão por renda e qualificação.
2. Projetos formativos respondem a setores visíveis antes de mapear vagas, egressos e deslocamentos.
3. Alguns corredores de acesso ganham oferta e parceria, enquanto outros públicos enfrentam incompatibilidade de horário e distância.
4. A educação corre atrás de sinais econômicos sem conseguir provar aderência, permanência ou equidade.

**Oportunidades**

- Experimentar rotas formativas e apoio à transição com avaliação explícita.
- Transformar acesso regional à EPT em objeto de governança, não apenas abertura local de curso.

**Riscos**

- Converter crescimento ocupacional em recomendação automática de curso ou promessa de emprego.
- Aumentar desigualdade entre estudantes que alcançam corredores regionais e os que não conseguem conciliar deslocamento, trabalho e estudo.

**Trade-offs**

- Rapidez de resposta econômica versus tempo necessário para validar demanda, qualidade e conclusão.
- Especialização regional versus dependência de transporte e de poucas instituições.

#### Seis dimensões integradas

#### Dimensão — Demografia e demanda educacional

- **Estado:** A demanda se redistribui segundo residência, trabalho e acesso a corredores formativos.
- **Mecanismo:** Mudanças econômicas e de deslocamento alteram onde estudantes procuram escola e formação.
- **No Vale:** Capacidade localizada pode não coincidir com residência ou oportunidade de trabalho.
- **Em Nova Santa Rita:** A leitura de matrículas locais precisa ser combinada com destinos de estudo e trabalho fora do município.

#### Dimensão — Rede, acesso e mobilidade

- **Estado:** Corredores de acesso conectam alguns municípios, turnos e públicos.
- **Mecanismo:** Parcerias e transporte priorizam rotas com oferta e atores já organizados.
- **No Vale:** Acesso melhora seletivamente e pode aprofundar vazios territoriais.
- **Em Nova Santa Rita:** Sem oferta técnica local observada, qualidade do acesso depende de vagas, horários, custo e continuidade das rotas regionais.

#### Dimensão — Trajetórias educacionais

- **Estado:** Conciliação entre estudo, trabalho e deslocamento vira ponto crítico.
- **Mecanismo:** Horários e renda pressionam permanência, embora a relação causal local permaneça não demonstrada.
- **No Vale:** Trajetórias podem se fragmentar entre escola regular, qualificação e trabalho.
- **Em Nova Santa Rita:** O crescimento observado de vínculos juvenis funciona como sentinela para turno, busca ativa e apoio, não como explicação do abandono.

#### Dimensão — Capacidade educacional

- **Estado:** Equipes e infraestrutura são atraídas por projetos de alta visibilidade.
- **Mecanismo:** Recursos se concentram em novas ofertas antes de integrar orientação, inclusão e permanência.
- **No Vale:** Capacidade cresce em ilhas e depende de coordenação entre redes e ofertantes.
- **Em Nova Santa Rita:** O município precisa apoiar acesso e trajetória mesmo quando curso, docente e laboratório estão fora de seu território.

#### Dimensão — Economia, trabalho e formação

- **Estado:** A formação responde rapidamente, mas a aderência entre curso, conclusão e trabalho segue incerta.
- **Mecanismo:** Correspondências ocupacionais orientam pilotos sem base individual de egressos.
- **No Vale:** A região pode ampliar oportunidades e também consolidar ofertas pouco acessíveis ou voláteis.
- **Em Nova Santa Rita:** Mudanças no comércio e no trabalho local não autorizam escolher cursos sem mapear demanda, oferta regional e egressos.

#### Dimensão — Financiamento e governança

- **Estado:** Projetos seletivos atraem recursos temporários e acordos específicos.
- **Mecanismo:** A inovação avança por oportunidade de financiamento, com custeio recorrente e equidade ainda incertos.
- **No Vale:** Ganhos rápidos convivem com fragmentação de responsabilidades.
- **Em Nova Santa Rita:** Contratos e parcerias precisam explicitar custo total, acesso municipal, duração e saída reversível.

#### Efeitos distributivos a validar

#### Jovens que conciliam estudo, trabalho e deslocamento

- **Exposição:** Horários e corredores seletivos podem definir quem consegue acessar e concluir a formação.
- **O que pode abrir:** Novas rotas formativas podem ampliar repertório e transição quando incluem apoio à permanência.
- **O que pode agravar:** A pressão por renda pode selecionar estudantes e fragmentar trajetórias.
- **Pergunta de equidade:** A oportunidade mede somente matrícula ou também acesso, permanência e conclusão?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `REG_YOUTH_FORMAL_WORK_CHANGE`, `NSR_YOUTH_FORMAL_WORK_CHANGE`, `NSR_HS_ABANDONMENT`

#### Adultos e jovens da EJA

- **Exposição:** Ofertas articuladas ao trabalho podem abrir retorno e também impor horários ou deslocamentos incompatíveis.
- **O que pode abrir:** Integração reversível entre EJA e formação profissional pode ampliar opções.
- **O que pode agravar:** Resposta centrada na oferta pode ignorar cuidado, renda e tempo de viagem.
- **Pergunta de equidade:** Quais barreiras impedem matrícula, frequência e conclusão em cada etapa?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `REG_EJA_FUNDAMENTAL_CHANGE`, `REG_EJA_HIGH_SCHOOL_CHANGE`, `NSR_EJA_FUNDAMENTAL_CHANGE`

#### Estudantes de baixa renda, rurais ou sem rota direta

- **Exposição:** Custo, distância e previsibilidade da rota podem limitar o acesso a corredores regionais.
- **O que pode abrir:** Pactos de transporte e apoio podem conectar territórios hoje sem oferta local.
- **O que pode agravar:** Especialização regional pode transferir custo e risco para famílias com menor margem.
- **Pergunta de equidade:** Quem recebe vaga nominal, mas não dispõe de tempo, transporte ou apoio para usá-la?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `NSR_RURAL_ENROLLMENT_CHANGE`, `NSR_LOW_INCOME_REGISTERED`, `NSR_LOCAL_TECHNICAL_ENROLLMENTS`

#### Docentes, orientadores e instituições formadoras

- **Exposição:** Projetos de resposta rápida podem disputar equipes, laboratórios e tempo de formação continuada.
- **O que pode abrir:** Pilotos avaliados podem aproximar escola, formação e trajetórias de trabalho.
- **O que pode agravar:** Ofertas temporárias podem gerar sobrecarga e capacidade pouco sustentável.
- **Pergunta de equidade:** O custeio, a equipe e a qualidade permanecem depois do projeto inicial?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `REG_TECHNICAL_ENROLLMENT_CHANGE`, `REG_EPT_ACCESSIBLE_BOUND`

#### Dependências regionais

- **Vagas, acesso e conclusão na EPT** (compartilhada): A região precisa distinguir oferta nominal, matrícula, frequência, conclusão e destino dos egressos.
  Estatuto: hipótese de cenário (`SCENARIO_ASSUMPTION`); referências: `REG_TECHNICAL_ENROLLMENT_CHANGE`, `REG_EPT_ACCESSIBLE_BOUND`.
- **Rotas, horários e apoio à permanência** (compartilhada): Acesso intermunicipal depende de compatibilidade entre calendário, turno, trabalho e transporte.
  Estatuto: hipótese de cenário (`SCENARIO_ASSUMPTION`); referências: `NSR_LOCAL_TECHNICAL_ENROLLMENTS`, `NSR_YOUTH_FORMAL_WORK_CHANGE`.
- **Dados protegidos de egressos e trabalho** (compartilhada): Avaliar aderência exige acompanhamento sem converter vínculo no estabelecimento em trajetória individual.
  Estatuto: hipótese de cenário (`SCENARIO_ASSUMPTION`); referências: `REG_YOUTH_FORMAL_WORK_CHANGE`, `NSR_YOUTH_FORMAL_WORK_CHANGE`.

#### Premissas

- A recomposição do trabalho mantém ritmo superior ao da coordenação formativa.
- Corredores de oferta surgem antes de um mapa completo de acesso e conclusão.
- Projetos seletivos recebem prioridade institucional.

#### O que enfraquece este futuro

- Dados de egressos e deslocamento mostrarem acesso equitativo e aderência estável.
- A recomposição econômica observada se revelar temporária ou concentrada em poucos estabelecimentos.

#### Limitações específicas

- Vínculos por estabelecimento não identificam trabalho de residentes nem causalidade com permanência escolar.
- Zero observado de matrícula técnica local não demonstra ausência de acesso regional ou demanda.
- Correspondência entre ocupação e formação não autoriza recomendar curso ou prometer emprego.

#### Ficha de revisão — Futuro B

- [ ] Coerência causal revisada.
- [ ] Equilíbrio entre oportunidades, riscos e trade-offs revisado.
- [ ] Efeitos distributivos e risco de estigma revisados.
- [ ] Implicações para Nova Santa Rita revisadas.
- Decisão: [ ] aceitar como instrumento exploratório  [ ] exigir revisão  [ ] rejeitar.
- Concordâncias: ____________________________________________________________
- Dissensos: ________________________________________________________________
- Evidência ou ponto cego a acrescentar: _____________________________________

---

### Futuro C — cartão cego

> Título, rótulo curto e identificador técnico foram retirados deliberadamente.

**Configuração morfológica**

| Fator | Estado neste futuro |
| --- | --- |
| Dinâmica demográfica e espacial das matrículas | Volatilidade por choques |
| Transição econômica e conexão formativa | Pressão de renda e descontinuidade |
| Pressões sociais e trajetórias | Vulnerabilidades combinadas |
| Mobilidade e coordenação da rede | Acesso interrompido |
| Capacidade institucional e fiscal de adaptação | Capacidade defensiva de emergência |

**Narrativa sintética:** Até 2036, interrupções de acesso, pressão de renda e restrição fiscal se combinam. A rede aprende a preservar continuidade em crises, mas adia transformações e amplia o risco de trajetórias quebradas.

**Encadeamento hipotético**

1. Choques afetam transporte, calendário, renda ou infraestrutura de forma desigual.
2. Famílias, estudantes e redes acumulam custos de deslocamento, cuidado e recuperação.
3. Recursos migram para continuidade imediata e reduzem margem de prevenção e coordenação.
4. Permanência, aprendizagem, EJA e inclusão ficam mais sensíveis a interrupções repetidas.

**Oportunidades**

- Instituir protocolos de continuidade que protejam públicos antes invisíveis.
- Usar registros operacionais de interrupção para integrar transporte, infraestrutura, assistência e educação.

**Riscos**

- Naturalizar perda de aprendizagem e abandono como efeito inevitável de crises.
- Concentrar recursos na emergência e tornar permanentes soluções temporárias desiguais.

**Trade-offs**

- Continuidade imediata versus investimento preventivo e transformação estrutural.
- Soluções remotas ou centralizadas versus acesso real, inclusão e vínculo territorial.

#### Seis dimensões integradas

#### Dimensão — Demografia e demanda educacional

- **Estado:** Demanda localizada oscila com interrupções, mudanças de residência e recuperação desigual.
- **Mecanismo:** Choques alteram presença e localização sem que a coorte explique sozinha a mudança.
- **No Vale:** Planejamento baseado em uma única safra torna-se frágil.
- **Em Nova Santa Rita:** A divergência já observada exige séries estáveis e registro de interrupções antes de atribuir mudança à demografia.

#### Dimensão — Rede, acesso e mobilidade

- **Estado:** Rotas, calendários e infraestrutura perdem confiabilidade.
- **Mecanismo:** Interrupções climáticas, fiscais ou operacionais exigem alternativas cuja efetividade ainda precisa ser medida.
- **No Vale:** Municípios com maior dispersão ou dependência externa enfrentam recuperação mais lenta.
- **Em Nova Santa Rita:** Matrículas rurais e acesso a ofertas externas tornam dias sem serviço, tempo e segurança sinais centrais.

#### Dimensão — Trajetórias educacionais

- **Estado:** Ausências e descontinuidades se acumulam sobre barreiras sociais preexistentes.
- **Mecanismo:** Renda, trabalho, cuidado, deslocamento e recuperação da aprendizagem competem entre si.
- **No Vale:** Permanência e aprendizagem podem divergir fortemente entre públicos.
- **Em Nova Santa Rita:** Abandono, EJA e trabalho juvenil precisam ser lidos junto de registros de interrupção e busca ativa.

#### Dimensão — Capacidade educacional

- **Estado:** Equipes e infraestrutura operam em modo de contingência.
- **Mecanismo:** Recursos especializados são redirecionados e filas de apoio podem crescer.
- **No Vale:** AEE, cuidado, recomposição e infraestrutura competem por capacidade escassa.
- **Em Nova Santa Rita:** A expansão observada de matrículas da educação especial exige continuidade acessível nos planos de contingência.

#### Dimensão — Economia, trabalho e formação

- **Estado:** Renda e trabalho ficam mais voláteis, pressionando retorno, turno e conclusão.
- **Mecanismo:** Famílias priorizam necessidades imediatas e ofertas formativas podem ser suspensas ou deslocadas.
- **No Vale:** EPT e EJA perdem previsibilidade justamente quando requalificação ganha importância.
- **Em Nova Santa Rita:** Dependência de acesso regional amplia risco de interrupção de trajetórias técnicas e adultas.

#### Dimensão — Financiamento e governança

- **Estado:** Governança e orçamento priorizam emergência e restauração.
- **Mecanismo:** Custeio inesperado reduz margem para prevenção, pactos e avaliação.
- **No Vale:** A solidariedade regional pode crescer, mas sem regras prévias distribui custo e voz de modo desigual.
- **Em Nova Santa Rita:** Protocolos precisam definir responsabilidades, continuidade e recuperação antes do próximo choque.

#### Efeitos distributivos a validar

#### Estudantes rurais ou dependentes de transporte

- **Exposição:** Falhas de rota, calendário ou infraestrutura podem interromper presença e acesso a ofertas externas.
- **O que pode abrir:** Protocolos prévios podem priorizar continuidade e alternativas acessíveis.
- **O que pode agravar:** Soluções emergenciais podem chegar tarde ou transferir custo e risco às famílias.
- **Pergunta de equidade:** Quais estudantes perdem mais dias de serviço e quanto tempo levam para recuperar acesso?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `NSR_RURAL_ENROLLMENT_CHANGE`, `NSR_HS_ABANDONMENT`

#### Estudantes que demandam AEE, acessibilidade ou apoio contínuo

- **Exposição:** Contingência pode interromper apoio, transporte acessível, comunicação e vínculo especializado.
- **O que pode abrir:** Planos inclusivos de continuidade podem tornar necessidades antes invisíveis parte da resposta regular.
- **O que pode agravar:** Alternativas remotas ou centralizadas podem excluir quem depende de apoio presencial e acessível.
- **Pergunta de equidade:** A continuidade preserva atendimento, acessibilidade e qualidade, além da matrícula?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `NSR_SPECIAL_EDUCATION_CHANGE`

#### Famílias de baixa renda e responsáveis com carga de cuidado

- **Exposição:** Renda, alimentação, cuidado e deslocamento podem competir com presença e recuperação escolar.
- **O que pode abrir:** Resposta intersetorial pode reduzir barreiras acumuladas antes que a trajetória se rompa.
- **O que pode agravar:** Cadastro ou busca ativa sem oferta concreta pode ampliar cobrança sem proteção suficiente.
- **Pergunta de equidade:** A resposta distingue registro administrativo, necessidade observada e acesso efetivo ao apoio?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `NSR_LOW_INCOME_REGISTERED`, `NSR_HS_ABANDONMENT`

#### Públicos da EJA e estudantes que trabalham

- **Exposição:** Pressão de renda e interrupções podem tornar retorno, frequência e conclusão mais instáveis.
- **O que pode abrir:** Horários flexíveis e recuperação pactuada podem preservar trajetórias.
- **O que pode agravar:** Ofertas temporariamente suspensas ou deslocadas podem afastar quem já enfrenta barreiras de tempo.
- **Pergunta de equidade:** Quais trajetórias não retornam depois da interrupção e quais apoios foram acessíveis?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `REG_EJA_HIGH_SCHOOL_CHANGE`, `NSR_YOUTH_FORMAL_WORK_CHANGE`, `NSR_HS_ABANDONMENT`

#### Dependências regionais

- **Protocolos regionais de continuidade e recuperação** (compartilhada): Responsabilidades, alternativas e critérios de retorno precisam existir antes da interrupção.
  Estatuto: hipótese de cenário (`SCENARIO_ASSUMPTION`); referências: `REG_HS_ABANDONMENT`, `NSR_HS_ABANDONMENT`.
- **Transporte, infraestrutura e acessibilidade** (compartilhada): Rotas e instalações exigem monitoramento operacional e alternativas proporcionais a cada público.
  Estatuto: hipótese de cenário (`SCENARIO_ASSUMPTION`); referências: `NSR_RURAL_ENROLLMENT_CHANGE`, `NSR_SPECIAL_EDUCATION_CHANGE`.
- **Proteção social, busca ativa e apoio intersetorial** (compartilhada): Educação não controla isoladamente renda, cuidado, transporte ou recuperação de serviços.
  Estatuto: hipótese de cenário (`SCENARIO_ASSUMPTION`); referências: `NSR_LOW_INCOME_REGISTERED`, `NSR_HS_ABANDONMENT`.

#### Premissas

- Interrupções de acesso ou renda reaparecem de forma relevante para a educação.
- A capacidade fiscal permanece insuficiente para prevenção e resposta simultâneas.
- Barreiras sociais se acumulam em públicos já expostos.

#### O que enfraquece este futuro

- Registros operacionais mostrarem continuidade estável e recuperação equitativa mesmo diante de eventos.
- Financiamento preventivo e protocolos regionais reduzirem interrupção recorrente.

#### Limitações específicas

- Eventos climáticos e outros choques permanecem hipóteses sem série territorial validada neste pacote.
- Cadastro de baixa renda não representa prevalência populacional nem identifica estudantes individualmente.
- Os dados observados não demonstram efeito causal de interrupções sobre abandono ou aprendizagem.

#### Ficha de revisão — Futuro C

- [ ] Coerência causal revisada.
- [ ] Equilíbrio entre oportunidades, riscos e trade-offs revisado.
- [ ] Efeitos distributivos e risco de estigma revisados.
- [ ] Implicações para Nova Santa Rita revisadas.
- Decisão: [ ] aceitar como instrumento exploratório  [ ] exigir revisão  [ ] rejeitar.
- Concordâncias: ____________________________________________________________
- Dissensos: ________________________________________________________________
- Evidência ou ponto cego a acrescentar: _____________________________________

---

### Futuro D — cartão cego

> Título, rótulo curto e identificador técnico foram retirados deliberadamente.

**Configuração morfológica**

| Fator | Estado neste futuro |
| --- | --- |
| Dinâmica demográfica e espacial das matrículas | Redistribuição planejada |
| Transição econômica e conexão formativa | Ecossistema regional de formação |
| Pressões sociais e trajetórias | Proteção antecipada, porém desigual |
| Mobilidade e coordenação da rede | Coordenação regional |
| Capacidade institucional e fiscal de adaptação | Capacidade compartilhada e dependente |

**Narrativa sintética:** Até 2036, municípios compartilham dados, rotas e capacidade para responder a trajetórias regionais. A coordenação amplia acesso, mas cria dependência, disputa por voz e risco de centralizar serviços longe de quem mais precisa.

**Encadeamento hipotético**

1. Coortes, matrículas e capacidade passam a ser lidas com fluxos entre municípios.
2. Redes e ofertantes pactuam acesso à EPT, EJA, apoio especializado e continuidade.
3. Busca ativa e proteção antecipada reduzem algumas barreiras, com cobertura ainda desigual.
4. A região ganha escala e informação, mas depende de financiamento, governança e controle de centralização.

**Oportunidades**

- Ampliar acesso sem exigir que cada município replique toda a oferta.
- Construir aprendizagem institucional com dados comuns e revisão periódica.

**Riscos**

- Centralizar serviços e transferir tempo, custo e risco de deslocamento para estudantes.
- Criar dependência de pactos frágeis, financiamento temporário ou atores com voz desigual.

**Trade-offs**

- Escala e especialização regional versus proximidade e autonomia municipal.
- Padronização de critérios versus adaptação a públicos e territórios distintos.

#### Seis dimensões integradas

#### Dimensão — Demografia e demanda educacional

- **Estado:** Coortes e fluxos orientam redistribuição planejada de capacidade.
- **Mecanismo:** Dados de residência–escola reduzem decisões baseadas apenas na matrícula localizada.
- **No Vale:** A rede pode ajustar oferta sem tratar todo movimento como fechamento ou expansão local.
- **Em Nova Santa Rita:** A divergência observada vira pergunta mensurável sobre origem, destino e capacidade, não justificativa automática de redimensionamento.

#### Dimensão — Rede, acesso e mobilidade

- **Estado:** Rotas e serviços são pactuados regionalmente com critérios de acesso.
- **Mecanismo:** Informação comum permite coordenar vagas, horários, transporte e alternativas.
- **No Vale:** Acesso pode ampliar, mas concentração física aumenta viagens e dependência.
- **Em Nova Santa Rita:** O município ganha opções externas se houver garantia de vaga, tempo, acessibilidade e continuidade.

#### Dimensão — Trajetórias educacionais

- **Estado:** Busca ativa e apoio são acionados antes da ruptura, com cobertura desigual.
- **Mecanismo:** Redes compartilham sinais de ausência, transição, EJA e trabalho sem presumir causa única.
- **No Vale:** Trajetórias ficam mais visíveis entre municípios, mas exigem proteção de dados e responsabilidade definida.
- **Em Nova Santa Rita:** EJA, permanência e trabalho juvenil podem receber rotas integradas desde que a resposta preserve escolha e proximidade.

#### Dimensão — Capacidade educacional

- **Estado:** Especialistas, AEE, formação e infraestrutura são compartilhados ou articulados.
- **Mecanismo:** A região usa escala para ampliar repertório e reduzir vazios locais.
- **No Vale:** Capacidade cresce, mas serviços centralizados podem gerar espera e deslocamento.
- **Em Nova Santa Rita:** A expansão observada da educação especial torna indispensáveis critérios de acesso, continuidade e qualidade no compartilhamento.

#### Dimensão — Economia, trabalho e formação

- **Estado:** EPT e transição escola-trabalho são planejadas como ecossistema regional.
- **Mecanismo:** Vagas, conclusão, egressos e deslocamento substituem correspondência nomenclatural isolada.
- **No Vale:** A região pode testar aderência e equidade, sem prometer emprego.
- **Em Nova Santa Rita:** O zero local deixa de ser vazio automático se o acesso regional for comprovado e sustentável.

#### Dimensão — Financiamento e governança

- **Estado:** Capacidade e custos são compartilhados por pactos revisáveis.
- **Mecanismo:** Cofinanciamento e critérios comuns sustentam serviços que um município não manteria sozinho.
- **No Vale:** Escala aumenta, junto com custo de governança e risco de assimetria de voz.
- **Em Nova Santa Rita:** A participação municipal precisa garantir assento, transparência de custo, nível de serviço e saída sem perda abrupta de atendimento.

#### Efeitos distributivos a validar

#### Estudantes que dependem de oferta técnica ou apoio especializado

- **Exposição:** Serviços compartilhados podem ampliar opções e também concentrar atendimento longe da residência.
- **O que pode abrir:** Escala regional pode reduzir vazios que um município não consegue suprir sozinho.
- **O que pode agravar:** Centralização pode elevar espera, deslocamento e dependência de poucos ofertantes.
- **Pergunta de equidade:** O nível de serviço garante vaga, acessibilidade, continuidade e apoio à conclusão?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `REG_EPT_ACCESSIBLE_BOUND`, `NSR_LOCAL_TECHNICAL_ENROLLMENTS`, `NSR_SPECIAL_EDUCATION_CHANGE`

#### Estudantes rurais ou dependentes de serviços compartilhados

- **Exposição:** A coordenação só amplia acesso se tempo, rota, custo e confiabilidade fizerem parte do pacto.
- **O que pode abrir:** Rotas e horários comuns podem conectar oferta antes inacessível.
- **O que pode agravar:** A concentração física pode transferir a eficiência institucional para o tempo de viagem do estudante.
- **Pergunta de equidade:** Quem ganha acesso e quem passa a viajar mais, faltar mais ou depender de uma única rota?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `NSR_RURAL_ENROLLMENT_CHANGE`, `NSR_HS_ENROLLMENT_CHANGE`

#### Gestões municipais com menor escala ou menor poder de negociação

- **Exposição:** Pactos compartilhados podem ampliar capacidade e também produzir assimetria de voz e dependência.
- **O que pode abrir:** Cofinanciamento e informação comum podem reduzir duplicidade e vazios locais.
- **O que pode agravar:** Critérios definidos pelos maiores atores podem deslocar prioridades e reduzir autonomia.
- **Pergunta de equidade:** Representação, custo, nível de serviço e saída são verificáveis para cada município?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `REG_HS_ENROLLMENT_CHANGE`, `NSR_ACCOUNTING_RESIDUAL`

#### Profissionais da educação em serviços e formações compartilhadas

- **Exposição:** Equipes podem ganhar apoio e repertório, mas enfrentar deslocamento, padronização e responsabilidades difusas.
- **O que pode abrir:** Redes de formação e especialistas podem ampliar suporte profissional.
- **O que pode agravar:** Coordenação sem governança clara pode aumentar burocracia e fragilizar continuidade local.
- **Pergunta de equidade:** A cooperação adiciona capacidade real ou apenas novas obrigações de coordenação?
- **Estatuto:** hipótese de cenário (`SCENARIO_ASSUMPTION`)
- **Referências:** `NSR_SPECIAL_EDUCATION_CHANGE`, `REG_EPT_ACCESSIBLE_BOUND`

#### Dependências regionais

- **Cofinanciamento e custeio recorrente** (compartilhada): Serviços compartilhados exigem continuidade financeira além do projeto ou adesão inicial.
  Estatuto: hipótese de cenário (`SCENARIO_ASSUMPTION`); referências: `REG_EPT_ACCESSIBLE_BOUND`, `NSR_SPECIAL_EDUCATION_CHANGE`.
- **Representação, decisão e revisão do pacto** (compartilhada): Municípios e públicos expostos precisam de voz, transparência e rota de saída sem ruptura de atendimento.
  Estatuto: hipótese de cenário (`SCENARIO_ASSUMPTION`); referências: `NSR_ACCOUNTING_RESIDUAL`, `NSR_HS_ENROLLMENT_CHANGE`.
- **Níveis de serviço e dados comuns** (compartilhada): Vaga, rota, tempo, acessibilidade, continuidade e conclusão precisam ser monitorados por município e público.
  Estatuto: hipótese de cenário (`SCENARIO_ASSUMPTION`); referências: `REG_HS_ENROLLMENT_CHANGE`, `REG_EPT_ACCESSIBLE_BOUND`, `NSR_RURAL_ENROLLMENT_CHANGE`.

#### Premissas

- Atores regionais conseguem manter pactos, dados e financiamento compartilhados.
- Critérios de equidade limitam centralização e exclusão por deslocamento.
- A coordenação preserva revisão e saída quando resultados não aparecem.

#### O que enfraquece este futuro

- Pactos não sustentarem vagas, rotas e serviços ao longo das revisões.
- Tempos, custos ou exclusões mostrarem que a coordenação ampliou desigualdades de acesso.

#### Limitações específicas

- Não há evidência direta suficiente de coordenação institucional regional neste pacote.
- Os efeitos de centralização sobre tempo, custo e exclusão ainda não foram medidos.
- A capacidade fiscal comparável para sustentar serviços compartilhados permanece uma lacuna explícita.

#### Ficha de revisão — Futuro D

- [ ] Coerência causal revisada.
- [ ] Equilíbrio entre oportunidades, riscos e trade-offs revisado.
- [ ] Efeitos distributivos e risco de estigma revisados.
- [ ] Implicações para Nova Santa Rita revisadas.
- Decisão: [ ] aceitar como instrumento exploratório  [ ] exigir revisão  [ ] rejeitar.
- Concordâncias: ____________________________________________________________
- Dissensos: ________________________________________________________________
- Evidência ou ponto cego a acrescentar: _____________________________________

---

## Módulo 3 — Contraste municipal dirigido

**Estado:** TECHNICAL_EVIDENCE_READY_HUMAN_REVIEW_PENDING. Revisão humana pendente: a prontidão técnica não substitui a participação de atores dos dois municípios.

Testar se a lente municipal muda quando aplicada a um município de escala, trajetória demográfica e concentração de oferta distintas, sem transformar o contraste em ranking ou cenário próprio.

Novo Hamburgo foi escolhido porque combina queda observada das coortes e matrículas localizadas, concentração regional de EJA e EPT e menor participação de saída para estudo do que Nova Santa Rita. O contraste testa direção, escala e papel regional; não define município melhor, pior ou representativo.

Cobertura comparável: 78 séries por município, com o mesmo grão; este número mede cobertura do artefato, não equivalência substantiva dos municípios.

### Evidências pareadas para selecionar e testar o caso contrastante

| Evidência | Nova Santa Rita | Novo Hamburgo | Período | Lente | Teto de afirmação |
| --- | --- | --- | --- | --- | --- |
| Coortes escolares menores colocam a distribuição de vagas, turmas e escolas na agenda | 340 pessoas | -7544 pessoas | 2015–2025 | RESIDENT_POPULATION | Mudança observada da população de 0 a 14 anos; não é projeção, matrícula ou capacidade da rede. |
| A queda das matrículas do ensino médio acompanha principalmente a redução da população de 15 a 17 anos | 83 matrículas | -1754 matrículas | 2015–2025 | SCHOOL_LOCATION_ENROLLMENT | Mudança observada em matrículas localizadas; não descreve residência, fluxo ou demanda individual. |
| O deslocamento para estudo coloca a oferta do ensino médio em escala regional | 19.113814074717638% | 9.799976328559593% | 2022 | RESIDENT_STUDENT_MOBILITY | Participação de residentes que estudavam em outro município em 2022; não mede destino, tempo, vaga, motivo ou fluxo de entrada. |
| Participação municipal nas matrículas EPT localizadas no Vale | 0% — zero observado | 39.7346719254213% | 2025 | EDUCATION_OFFER_LOCATION | Participação municipal nas matrículas EPT localizadas no Vale; não mede acesso dos residentes, vagas, conclusão ou empregabilidade. |
| Participação municipal nas matrículas EJA localizadas no Vale | 0.88639066046913% | 76.92141390119987% | 2022 | SCHOOL_LOCATION_ENROLLMENT | Participação municipal nas matrículas EJA de ensino médio localizadas no Vale; não equivale à distribuição do público residente. |
| Parcela dos eventos de admissão classificados como aprendizagem profissional | 79.45205479452055% | 47.37127371273713% | 2025 | ESTABLISHMENT_LOCATION_EMPLOYMENT | Parcela de eventos de admissão no estabelecimento classificados como aprendizagem; não identifica residência, matrícula ou trajetória individual. |

### Cobertura PNE da matriz municipal contrastante

A cobertura descreve somente a presença das metas nas categorias curadas do artefato municipal. Meta ausente da seleção não é zero observado, não comprova falta de dado na fonte primária e não autoriza comparação simétrica de desempenho.

| Meta | Situação na seleção curada | Valor/estado |
| --- | --- | --- |
| 4.a · Acesso escolar 6 a 17 anos | fora das categorias curadas — não equivale a zero nem ausência na fonte primária | indisponível |
| 4.d · Conclusão do ensino médio na idade regular | fora das categorias curadas — não equivale a zero nem ausência na fonte primária | indisponível |
| 5.d · Aprendizagem no ensino médio | presente nas categorias curadas | 3.33 |
| 11.d · Matrículas na EJA | fora das categorias curadas — não equivale a zero nem ausência na fonte primária | indisponível |
| 12.c · EJA articulada à educação profissional | presente nas categorias curadas | 0 — zero observado |
| 17.a · Formação específica dos docentes | fora das categorias curadas — não equivale a zero nem ausência na fonte primária | indisponível |
| 19.c · Infraestrutura mínima nas escolas | presente nas categorias curadas | 43.523316062176164 |

### Futuro A — teste contrastante

**Hipótese localizada em Novo Hamburgo:** Queda de coortes e matrículas pode pressionar reorganização local sem revelar quem depende da oferta de Novo Hamburgo.

- **Demografia:** A direção observada é oposta à de Nova Santa Rita e amplia o risco de tratar queda agregada como ociosidade uniforme.
- **Educação:** A redução de matrículas localizadas convive com concentração regional de EJA e EPT, exigindo separar etapa, público e origem.
- **Economia e trabalho:** A escala da oferta formativa pode sustentar acesso regional, mas não demonstra correspondência com trabalho ou demanda futura.
- **Condições sociais:** Grandes contagens absolutas podem ocultar grupos e bairros com barreiras distintas; participação regional não mede equidade.
- **Território e acesso:** Menor saída de residentes não prova autossuficiência, e a matriz de entradas por origem continua ausente.

**Dependências regionais a verificar**

- Fluxos de entrada e saída por etapa
- Capacidade e qualidade da oferta regional
- Coordenação de EJA e EPT entre municípios

**Alavancas relacionadas, sem decisão automática**

- Observar fluxos residência–escola e capacidade
- Mapear acesso regional à EPT
- Revisar capacidade com opções reversíveis

Referências técnicas: `F5_COHORT_0_14_CHANGE`, `F5_HS_ENROLLMENT_CHANGE`, `F5_HS_OUTBOUND_SHARE`, `F5_EPT_SHARE_2025`, `F5_EJA_HS_SHARE_2022`.

#### Ficha dirigida — Futuro A em Novo Hamburgo

- [ ] A direção do mecanismo continua plausível no caso contrastante.
- [ ] A escala ou o papel regional muda a interpretação.
- [ ] As lentes de residência, oferta e estabelecimento foram mantidas separadas.
- [ ] Alguma afirmação deve ser reduzida por falta de fluxo origem–destino.
- Evidência local que confirma: ______________________________________________
- Evidência local que contradiz: _____________________________________________
- Revisão necessária na lente municipal: ____________________________________

---

### Futuro B — teste contrastante

**Hipótese localizada em Novo Hamburgo:** A concentração de oferta pode crescer como função regional sem garantir acesso, permanência ou conclusão para públicos de outros municípios.

- **Demografia:** Coortes menores alteram o público local enquanto fluxos regionais podem sustentar parte da procura por formação.
- **Educação:** EPT e EJA localizadas dão centralidade potencial ao município, mas acesso e conclusão dos residentes do Vale não estão medidos.
- **Economia e trabalho:** Eventos de aprendizagem e oferta técnica são sinais de articulação possível, não prova de aderência curricular ou emprego futuro.
- **Condições sociais:** Custo, horário, cuidado e deslocamento podem selecionar quem alcança uma oferta fisicamente concentrada.
- **Território e acesso:** A centralidade da oferta aumenta a necessidade de rotas, calendários e informação compartilhados.

**Dependências regionais a verificar**

- Vagas, ingressantes e concluintes por origem
- Rotas e horários compatíveis
- Acompanhamento de egressos sem inferência causal

**Alavancas relacionadas, sem decisão automática**

- Mapear acesso regional à EPT
- Monitorar conciliação entre trabalho e estudo
- Testar corredor regional de EPT

Referências técnicas: `F5_EPT_SHARE_2025`, `F5_EJA_HS_SHARE_2022`, `F5_APPRENTICESHIP_15_17_SHARE_2025`, `F5_HS_OUTBOUND_SHARE`.

#### Ficha dirigida — Futuro B em Novo Hamburgo

- [ ] A direção do mecanismo continua plausível no caso contrastante.
- [ ] A escala ou o papel regional muda a interpretação.
- [ ] As lentes de residência, oferta e estabelecimento foram mantidas separadas.
- [ ] Alguma afirmação deve ser reduzida por falta de fluxo origem–destino.
- Evidência local que confirma: ______________________________________________
- Evidência local que contradiz: _____________________________________________
- Revisão necessária na lente municipal: ____________________________________

---

### Futuro C — teste contrastante

**Hipótese localizada em Novo Hamburgo:** A concentração de oferta transforma continuidade local em dependência regional potencial, ainda sem matriz de origem e destino.

- **Demografia:** Choques podem alterar presença e fluxos sobre uma base local que já perdeu coortes e matrículas.
- **Educação:** Interrupção em EJA, EPT ou ensino médio localizado pode repercutir além do município se a centralidade for confirmada.
- **Economia e trabalho:** Descontinuidade de formação e aprendizagem pode afetar trajetórias, mas vínculos por estabelecimento não identificam estudantes.
- **Condições sociais:** Públicos que dependem de turno flexível ou deslocamento podem acumular barreiras em uma oferta concentrada.
- **Território e acesso:** Sem fluxos de entrada, não é possível quantificar quais municípios ou públicos sofreriam primeiro.

**Dependências regionais a verificar**

- Protocolos regionais de continuidade
- Informação de origem e destino
- Alternativas de atendimento acessíveis

**Alavancas relacionadas, sem decisão automática**

- Pactuar continuidade educacional em interrupções
- Observar fluxos residência–escola e capacidade
- Diagnosticar EJA por etapa, turno e barreira

Referências técnicas: `F5_COHORT_0_14_CHANGE`, `F5_HS_ENROLLMENT_CHANGE`, `F5_EPT_SHARE_2025`, `F5_EJA_HS_SHARE_2022`.

#### Ficha dirigida — Futuro C em Novo Hamburgo

- [ ] A direção do mecanismo continua plausível no caso contrastante.
- [ ] A escala ou o papel regional muda a interpretação.
- [ ] As lentes de residência, oferta e estabelecimento foram mantidas separadas.
- [ ] Alguma afirmação deve ser reduzida por falta de fluxo origem–destino.
- Evidência local que confirma: ______________________________________________
- Evidência local que contradiz: _____________________________________________
- Revisão necessária na lente municipal: ____________________________________

---

### Futuro D — teste contrastante

**Hipótese localizada em Novo Hamburgo:** Novo Hamburgo pode apoiar uma rede regional coordenada, desde que concentração de oferta não substitua equidade, proximidade e voz municipal.

- **Demografia:** Fluxos observados permitem diferenciar demanda local, regional e capacidade compartilhada antes de reorganizar a rede.
- **Educação:** EJA e EPT concentradas podem compor pactos regionais com critérios verificáveis de acesso e qualidade.
- **Economia e trabalho:** Informação sobre formação e trajetórias pode orientar experimentos reversíveis sem prometer aderência ocupacional.
- **Condições sociais:** Critérios de equidade precisam evitar que escala e centralidade concentrem recursos ou ampliem distância para públicos vulneráveis.
- **Território e acesso:** O município pode funcionar como nó regional somente com nível de serviço, cofinanciamento e saída pactuados.

**Dependências regionais a verificar**

- Governança sem dominância do município-polo
- Cofinanciamento e nível de serviço
- Critérios de equidade por origem e público

**Alavancas relacionadas, sem decisão automática**

- Observar fluxos residência–escola e capacidade
- Mapear acesso regional à EPT
- Pactuar nível regional de serviço e representação
- Realizar revisão 2030–2031

Referências técnicas: `F5_HS_OUTBOUND_SHARE`, `F5_EPT_SHARE_2025`, `F5_EJA_HS_SHARE_2022`, `F5_APPRENTICESHIP_15_17_SHARE_2025`.

#### Ficha dirigida — Futuro D em Novo Hamburgo

- [ ] A direção do mecanismo continua plausível no caso contrastante.
- [ ] A escala ou o papel regional muda a interpretação.
- [ ] As lentes de residência, oferta e estabelecimento foram mantidas separadas.
- [ ] Alguma afirmação deve ser reduzida por falta de fluxo origem–destino.
- Evidência local que confirma: ______________________________________________
- Evidência local que contradiz: _____________________________________________
- Revisão necessária na lente municipal: ____________________________________

---

### Registro do módulo de contraste

- [ ] O contraste mudou, confirmou ou delimitou a lente municipal.
- [ ] O caso não foi tratado como ranking, benchmark ou cenário próprio.
- [ ] Ausência na seleção curada do PNE não foi tratada como zero observado.
- Síntese da transferibilidade: ______________________________________________
- Condições para revisão da metodologia: ____________________________________
- Dissensos entre os casos: __________________________________________________

## Módulo 4 — Ações, PNE e gatilhos

O PNE 2026–2036 define compromissos; os cenários testam condições de execução. Nenhum cenário é meta, previsão ou preferência institucional.

### Futuro A — stress-test do PNE

| Bloco normativo | Estado | Mecanismo | Resposta a deliberar |
| --- | --- | --- | --- |
| Acesso e conclusão na idade regular | PRESSURED | Fluxos pouco medidos e respostas locais podem manter barreiras de acesso e conclusão invisíveis. | Observar fluxos residência–escola e capacidade |
| Aprendizagem e formação docente | AMBIGUOUS | Autonomia local permite ajustes, mas capacidade e apoio permanecem desiguais. | Auditar capacidade de AEE, acessibilidade e rotas rurais |
| EJA e retomada de trajetórias | PRESSURED | Planejamento agregado pode esconder barreiras e mudanças distintas por etapa. | Diagnosticar EJA por etapa, turno e barreira |
| EJA articulada à educação profissional | PRESSURED | Ausência de mapa regional dificulta articular trajetórias adultas à oferta profissional. | Mapear acesso regional à EPT |
| Infraestrutura mínima e continuidade | PRESSURED | Resposta reativa pode adiar adequações e compartilhamento de capacidade. | Revisar capacidade com opções reversíveis |

### Futuro B — stress-test do PNE

| Bloco normativo | Estado | Mecanismo | Resposta a deliberar |
| --- | --- | --- | --- |
| Acesso e conclusão na idade regular | PRESSURED | Trabalho, horário e corredores seletivos podem fragmentar acesso e conclusão. | Monitorar conciliação entre trabalho e estudo |
| Aprendizagem e formação docente | PRESSURED | Projetos seletivos disputam equipes e tempo com aprendizagem e formação continuada. | Realizar revisão 2030–2031 |
| EJA e retomada de trajetórias | AMBIGUOUS | Novas rotas podem abrir oportunidades e também tornar horários e deslocamento mais difíceis. | Diagnosticar EJA por etapa, turno e barreira |
| EJA articulada à educação profissional | PRESSURED | Resposta rápida pode confundir oferta nominal com acesso e conclusão efetivos. | Testar corredor regional de EPT |
| Infraestrutura mínima e continuidade | AMBIGUOUS | Investimento cresce em polos, mas pode deixar infraestrutura básica desigual. | Realizar revisão 2030–2031 |

### Futuro C — stress-test do PNE

| Bloco normativo | Estado | Mecanismo | Resposta a deliberar |
| --- | --- | --- | --- |
| Acesso e conclusão na idade regular | PRESSURED | Interrupções e barreiras acumuladas ameaçam presença e conclusão. | Pactuar continuidade educacional em interrupções |
| Aprendizagem e formação docente | PRESSURED | Recuperação e contingência reduzem tempo e capacidade de aprendizagem e formação. | Pactuar continuidade educacional em interrupções |
| EJA e retomada de trajetórias | PRESSURED | Renda, cuidado e acesso instável dificultam retorno e continuidade. | Diagnosticar EJA por etapa, turno e barreira |
| EJA articulada à educação profissional | PRESSURED | Ofertas articuladas dependentes de rota e parceiro ficam vulneráveis a interrupções. | Pactuar continuidade educacional em interrupções |
| Infraestrutura mínima e continuidade | PRESSURED | Emergência compete com prevenção, manutenção e acessibilidade. | Auditar capacidade de AEE, acessibilidade e rotas rurais |

### Futuro D — stress-test do PNE

| Bloco normativo | Estado | Mecanismo | Resposta a deliberar |
| --- | --- | --- | --- |
| Acesso e conclusão na idade regular | SUPPORTED | Fluxos e níveis de serviço compartilhados podem ampliar acesso se distância e equidade forem controladas. | Pactuar nível regional de serviço e representação |
| Aprendizagem e formação docente | AMBIGUOUS | Escala pode ampliar apoio e formação, mas centralização pode reduzir proximidade e continuidade. | Realizar revisão 2030–2031 |
| EJA e retomada de trajetórias | SUPPORTED | Oferta e busca ativa coordenadas podem ampliar opções se horários e deslocamento forem acessíveis. | Diagnosticar EJA por etapa, turno e barreira |
| EJA articulada à educação profissional | SUPPORTED | Pactos regionais podem conectar etapas e formação sem exigir oferta completa em cada município. | Mapear acesso regional à EPT |
| Infraestrutura mínima e continuidade | AMBIGUOUS | Compartilhamento reduz alguns vazios, mas pode concentrar serviços e deslocamentos. | Pactuar nível regional de serviço e representação |

### Carteira de ações

#### Observar fluxos residência–escola e capacidade

- Tipo: robusta nos quatro futuros
- Autoridade: compartilhada
- Descrição: Registrar origem, destino, etapa, rede, vaga e motivo de deslocamento antes de expandir, reduzir ou transferir oferta.
- Gatilho: Divergência reaparece em atualização comparável.
- Risco de lock-in: Baixo, desde que a coleta seja proporcional e preserve privacidade.

#### Mapear acesso regional à EPT

- Tipo: robusta nos quatro futuros
- Autoridade: compartilhada
- Descrição: Combinar oferta, vagas, turnos, deslocamento, conclusão e egressos sem transformar correspondência nomenclatural em demanda.
- Gatilho: Decisão sobre curso, parceria, transporte ou expansão.
- Risco de lock-in: Baixo; o risco cresce se o mapa for usado como recomendação automática.

#### Diagnosticar EJA por etapa, turno e barreira

- Tipo: robusta nos quatro futuros
- Autoridade: compartilhada
- Descrição: Registrar procura, retorno, cuidado, trabalho, deslocamento e continuidade separadamente no fundamental e no médio.
- Gatilho: Mudança de composição ou baixa procura observada.
- Risco de lock-in: Baixo, desde que matrícula não seja tratada como demanda total.

#### Auditar capacidade de AEE, acessibilidade e rotas rurais

- Tipo: robusta nos quatro futuros
- Autoridade: municipal
- Descrição: Medir profissionais, atendimento, acessibilidade, tempo, regularidade e continuidade, além das contagens de matrícula e escola.
- Gatilho: Mudança de matrícula, fila, rota ou interrupção de serviço.
- Risco de lock-in: Baixo; evitar usar matrícula como necessidade individual ou suficiência.

#### Monitorar conciliação entre trabalho e estudo

- Tipo: robusta nos quatro futuros
- Autoridade: municipal
- Descrição: Acompanhar horário, turno, ausência e busca ativa sem atribuir causalidade aos vínculos formais agregados.
- Gatilho: Mudança simultânea em trabalho juvenil e trajetória escolar.
- Risco de lock-in: Baixo; exige proteção contra estigmatização.

#### Realizar revisão 2030–2031

- Tipo: robusta nos quatro futuros
- Autoridade: compartilhada
- Descrição: Revisar premissas, sinais, distribuição de efeitos e PNE sem eleger um cenário vencedor.
- Gatilho: Checkpoint programado ou quebra antecipada de premissa crítica.
- Risco de lock-in: Baixo se mudanças e divergências forem registradas.

#### Revisar capacidade com opções reversíveis

- Tipo: contingente a gatilho
- Autoridade: compartilhada
- Descrição: Testar compartilhamento, turno e uso de espaço antes de mudança estrutural de oferta.
- Gatilho: Divergência persistente acompanhada de fluxo e capacidade confirmados.
- Risco de lock-in: Médio se uma oscilação for tratada como tendência permanente.

#### Testar corredor regional de EPT

- Tipo: experimento reversível
- Autoridade: compartilhada
- Descrição: Piloto com prazo, vaga, transporte, apoio, conclusão, equidade e critério de encerramento definidos.
- Gatilho: Mapa demonstra lacuna de acesso e parceiro com capacidade.
- Risco de lock-in: Alto se infraestrutura ou contrato permanente anteceder evidência de acesso e conclusão.

#### Pactuar continuidade educacional em interrupções

- Tipo: contingente a gatilho
- Autoridade: compartilhada
- Descrição: Definir rotas alternativas, comunicação, AEE, alimentação, recuperação e responsabilidades com teste periódico.
- Gatilho: Interrupção operacional ou alerta com impacto educacional confirmado.
- Risco de lock-in: Médio se solução emergencial desigual substituir prevenção e ensino regular.

#### Pactuar nível regional de serviço e representação

- Tipo: contingente a gatilho
- Autoridade: compartilhada
- Descrição: Formalizar vaga, tempo, acessibilidade, custo, responsabilidade, voz municipal, revisão e saída para serviços compartilhados.
- Gatilho: Serviço regional passa a sustentar trajetória municipal relevante.
- Risco de lock-in: Alto sem cofinanciamento, representação e plano de continuidade.

### Indicadores sentinela

- **Coorte residente e matrículas localizadas** — derivação calculada; ANNUAL; Abrir investigação de fluxo; nunca medir migração pelo residual.
- **Fluxos residência–escola** — indisponível; ANNUAL; Confirmar origem, destino e dependência regional antes de ajustar oferta.
- **Abandono no ensino médio** — observado; ANNUAL; Monitorar trajetória com contexto, sem causa presumida.
- **EJA por etapa e turno** — observado; ANNUAL; Separar composição de matrícula de procura e barreira.
- **Oferta, vagas e acesso regional à EPT** — indisponível; SEMESTER; Testar acesso real; zero local não significa ausência regional.
- **Conclusão e continuidade na EPT** — indisponível; ANNUAL; Distinguir matrícula, conclusão e trajetória.
- **Conciliação trabalho–estudo** — indisponível; SEMESTER; Registrar horário e barreira sem inferir efeito de vínculos agregados.
- **Confiabilidade das rotas educacionais** — indisponível; MONTHLY; Medir tempo, dias sem serviço, segurança e alternativa.
- **Dias de atividade educacional interrompida** — indisponível; EVENT_BASED; Acionar continuidade e registrar recuperação.
- **Capacidade e continuidade do AEE** — indisponível; SEMESTER; Medir atendimento, profissional, acessibilidade e fila além da matrícula.
- **Nível de serviço regional** — não aplicável; QUARTERLY; Aplicar somente quando existir pacto regional ativo.
- **Equidade de acesso por público e território** — indisponível; ANNUAL; Verificar quem não alcança oferta, apoio ou rota compartilhada.

### Registro do módulo

- [ ] Ações robustas foram separadas das contingentes e dos experimentos.
- [ ] Autoridade, dependência e risco de lock-in foram revisados.
- [ ] Gatilhos observáveis foram revisados.
- Ações mantidas: ___________________________________________________________
- Ações a revisar: _________________________________________________________
- Dissensos: _______________________________________________________________

## Fechamento sem decisão predefinida

- Resultado: [ ] validar para uso piloto  [ ] exigir revisões  [ ] rejeitar.
- Autoridade e escopo da decisão, sem nomes: _________________________________
- Condições: ________________________________________________________________
- Dissensos não resolvidos: _________________________________________________
- Referência institucional da ata: __________________________________________

O registro canônico deve ser produzido separadamente pelo protocolo, validado contra os hashes acima e permanecer sem dados pessoais.
