# Plano de implementação — Integração Vocações × PNE

**Versão:** 1.0  
**Piloto:** Vale do Sinos  
**Objetivo de execução:** orientar o Fable a orquestrar a reconstrução da página para que ela entregue, de forma rastreável e útil ao gestor, as duas saídas solicitadas pela gestão:

1. **O que o território ajuda a compreender sobre a educação?**
2. **O que o futuro do território coloca na agenda da educação?**

A comparação temporal deve estar incorporada às duas saídas, e não aparecer como uma terceira seção isolada.

---

## 0. Estado de execução, protocolo e adaptações ao repositório (Fable, 2026-08-27)

Este bloco foi adicionado pelo Fable na revisão do plano. Ele adapta o texto do
GPT Pro (íntegro abaixo) à realidade do repositório e fixa o protocolo de
execução. Em conflito entre este bloco e o restante do documento, **este bloco
prevalece**.

### 0.1 Identidade e sucessão

Este é o **plano V6** da linha Vocações da Região (sucede o V5,
`docs/PLANO_VOCACOES_REGIAO_V5.md`). Não é uma rodada de adição: é a
reconstrução do produto em torno das duas perguntas da gestão.

- O **V5 encerra na R0 daqui**: a R3 do V5 (contrato 2.9.0, página nova) está
  verificada até C10, com C11 (GA humano), C12 (commits) e C13 (relatório)
  pendentes — é o conteúdo atual do working tree. As R4–R5 do V5 são
  **absorvidas**: cenários das 8 regiões restantes → Etapas 7/13 daqui;
  entrega/governança → Etapa 13.
- Aproveitamento declarado do que o V1–V5 já construiu (nada é descartado sem
  a matriz da Etapa 0): curadoria por força (2.7.0), decomposições E2 (2.8.0),
  layout leve (2.9.0, 6.965px no piloto), guardas byte a byte, corpus
  adversarial, ponte PNE 2.3.0, cenários publicados em VRP e Noroeste.

### 0.2 Protocolo de execução (herda o v4 do V3, §4)

| Papel | Quem | Regras |
|---|---|---|
| Gate/orquestrador | **Fable 5**, sessão Claude Code com **contexto limpo por rodada** | Escreve a especificação fechada de cada job antes do despacho; verifica com instrumentos próprios (testes, greps, hashes, DOM, screenshots, recomputação em amostra); redige toda a linguagem pública; emite o veredito da rodada. Nunca aceita relato do executor como prova. |
| Executor | **GPT 5.6 sol xhigh** — sempre `gpt-5.6-sol`, reasoning xhigh, plugin Codex/`codex-rescue`, `--write`, **um job por chamada**, saída declarada em `.tmp/` (`gpt-5.6` retorna 400; `gpt-5.6-codex` trava em starting) | Todo código de produção e de teste, sob especificação fechada do Fable. Nunca define critérios, nunca redige linguagem pública, nunca verifica o próprio trabalho. |
| Árbitro | **Mantenedor** | GA humano, empates, mudanças de plano. A "validação com usuários" (Etapa 11.5) executa-se como GA humano do mantenedor — e da gestora quando possível. |

Vivacidade (V3 §4.3): segunda morte de um job = o Fable executa e registra.
Diretórios da execução: `.tmp/vocacoes-pne/rodada-<NN>/` (gitignored), com
`ESPEC`, `TAREFA_*`, relatos, `CHECKLIST`, `RELATORIO` e `VIVACIDADE` por
rodada, no padrão do V5.

**Sessão nova por rodada**: cada rodada começa em sessão limpa do Fable, aberta
com o prompt fechado da §9. Tudo o que a rodada seguinte precisa saber deve
estar no plano, no `RELATORIO_RODADA_<NN>.md` da rodada anterior e nos
artefatos versionados — nunca só na conversa.

### 0.3 Decisões desta revisão

| # | Decisão | Registro |
|---|---|---|
| V6-D1 | Protocolo da §0.2; piloto **Vale do Sinos** (com Nova Santa Rita como referência municipal na matriz, herdado do V3-D7). | 2026-08-27 |
| V6-D2 | **Escada E1–E5 sai da página pública** (supersede a parte pública de V5-D5): graus, força e classificação viram camada interna do pacote. A decomposição E2 permanece publicada, mas traduzida ("parte da mudança ligada ao tamanho da população"), nunca como grau ou sigla. | 2026-08-27 |
| V6-D3 | **Cenários**: só VRP e Noroeste têm cenários publicados (2.1.0). O Vale do Sinos **não tem** — a segunda saída do piloto apoia-se em mudanças observadas e tendências sustentadas (Etapa 7.1, classes 1–2), sem mensagem de ausência. Cenários das demais regiões são trabalho posterior ou paralelo, não pré-requisito do piloto. | 2026-08-27 |
| V6-D4 | **Dois repositórios**: aquisição, materialização e estatística vivem na camada de pesquisa (`C:\Users\rnbirck\PROJETOS\SESI\PNE`); a plataforma (este repo) só recebe artefatos publicados, com handshake fail-closed (herdado). As Etapas 4–5 executam majoritariamente na pesquisa. | 2026-08-27 |
| V6-D5 | **Invariantes herdadas** (V3-D3, V5-D7) mantidas: fail-closed pesquisa→gerador→plataforma, prévia rotulada, taxa nunca somada, classe `calculated`, corpus bilateral, portar antes de deletar, sem número futuro fora de cenário, sem p-valor. A **ausência silenciosa** (§3.6) substitui a "ausência declarada" apenas na camada pública; internamente cada não-publicação mantém `reasonCode`. | 2026-08-27 |
| V6-D6 | Os números do estado atual citados na §1 e na Etapa 0 (18 leituras, 8 retidas, 4 decomposições, 15 conclusões, 71 séries) referem-se ao contrato 2.8.0/2.9.0 e **devem ser reauditados na Rodada 0** contra o pacote publicado — o plano não é a fonte da verdade, o manifesto é. | 2026-08-27 |
| V6-D7 | A ordem de rodadas da §9 (reescrita pelo Fable) substitui a sugestão original do GPT; os gates e etapas do corpo do plano permanecem válidos como conteúdo. | 2026-08-27 |

---

## 1. Ponto de partida e mudança central

A página atual tem boa base de dados, rastreabilidade e proteção contra afirmações causais, mas ainda está organizada principalmente como uma coleção de pares de séries. No piloto do Vale do Sinos, o contrato atual reúne 18 leituras publicadas, 8 leituras mantidas fora da página, 4 decomposições e 15 conclusões, apoiadas por 71 séries territoriais e por um conjunto amplo de indicadores educacionais ainda pouco utilizado na leitura integrada.

O novo produto não deve ampliar a quantidade de pares expostos. Deve transformar os dados em **poucas leituras integradas, orientadas por questões educacionais e por transformações do território**.

A sequência central será:

```text
Resultado educacional
→ separação dos componentes que formam esse resultado
→ fatores territoriais realmente pertinentes
→ diferenças entre municípios e ao longo do tempo
→ questão concreta para o planejamento educacional
```

No sentido inverso:

```text
Transformação do território
→ grupos, municípios e atividades mais expostos
→ situação educacional atual relacionada
→ implicação para os próximos anos
→ temas e metas do PNE/PME que entram na agenda
```

A página pública deve deixar de ser um catálogo de relações e passar a ser uma **leitura editorialmente curada do território, da educação e do futuro**.

---

## 2. Resultado final esperado

### 2.1 Estrutura pública da página

A página deverá ter duas áreas principais.

#### Área A — O território e a educação hoje

Deve partir de resultados educacionais relevantes e apresentar, para cada um:

- o que mudou;
- qual parte dessa mudança acompanha a transformação demográfica, a trajetória escolar, a oferta ou outra dimensão diretamente pertinente;
- quais características do território ajudam a interpretar o resultado;
- como a situação varia entre os municípios da região;
- qual questão concreta entra no planejamento.

A página deverá publicar **de três a cinco leituras principais**, e não dezenas de pares.

#### Área B — O futuro do território e a agenda da educação

Deve partir de transformações territoriais já observadas, tendências sustentadas por fontes adequadas ou cenários publicados e apresentar:

- qual transformação está em curso;
- quais municípios, faixas etárias, setores ou ocupações são mais afetados;
- qual é o ponto de partida educacional da região;
- o que essa transformação coloca na agenda da educação;
- quais temas e metas do PNE/PME se relacionam à questão;
- quais indicadores devem ser acompanhados nos próximos anos.

A página deverá publicar **de duas a cinco questões de agenda**, sempre ancoradas em dados.

### 2.2 Camada de consulta

Os gráficos completos, séries, fontes e detalhes de cálculo poderão permanecer disponíveis em uma camada de consulta, mas não devem competir com a leitura principal.

A camada de consulta deve ser acessada por ações como:

- **Ver evolução**
- **Ver municípios**
- **Ver dados e fontes**

Ela não deve exibir ao usuário listas de relações descartadas, classificações estatísticas, graus internos de evidência ou mensagens de insuficiência.

### 2.3 Regra de publicação

Uma informação só entra na página principal quando produzir um insight que:

1. combine educação e território;
2. responda a uma das duas perguntas da gestão;
3. seja sustentado por dados rastreáveis;
4. altere ou qualifique uma questão de planejamento;
5. possa ser explicado em linguagem pública, sem depender de jargão metodológico;
6. não repita outra leitura já publicada.

Quando uma relação não alcançar esse padrão, ela fica apenas nos artefatos internos. A página não deverá dizer ao usuário que “não foi possível medir”, que “a relação é fraca” ou que “há evidência insuficiente”. Nesses casos, o conteúdo simplesmente não é publicado.

---

## 3. Princípios não negociáveis

### 3.1 Curadoria antes de quantidade

A plataforma não deve publicar uma relação apenas porque ela foi calculada ou porque apresentou um coeficiente elevado. A triagem automática pode gerar candidatos internamente, mas nunca deve decidir sozinha o que o usuário vê.

### 3.2 Mecanismo antes da associação

Todo cruzamento deve partir de uma pergunta substantiva previamente definida. Não será permitido procurar pares entre todas as séries e depois tentar criar uma explicação para os resultados encontrados.

### 3.3 Separar os componentes antes de relacionar

Quando um resultado educacional puder ser separado em componentes, essa separação deve ocorrer antes de buscar fatores territoriais.

Exemplos:

- matrículas por etapa: tamanho da população na idade, participação escolar, fluxo e oferta;
- EJA: população potencial, oferta disponível e participação;
- educação profissional: população jovem, oferta formativa, composição dos cursos e demanda ocupacional;
- rede rural: população rural, distribuição territorial e organização da oferta.

### 3.4 Universo compatível

As variáveis precisam representar populações e territórios comparáveis.

Exemplos de incompatibilidades que devem ser bloqueadas:

- população de 0 a 14 anos para interpretar diretamente matrícula de 15 a 17 anos;
- total de vínculos formais para interpretar trabalho juvenil sem recorte de idade;
- matrícula localizada na região comparada diretamente à população residente sem observar deslocamentos;
- CadÚnico total usado como medida direta da demanda por EJA.

### 3.5 Linguagem pública e linguagem interna são camadas diferentes

A análise interna pode utilizar correlações, testes de sensibilidade, decomposições, graus de evidência e relatórios de insuficiência. A página pública não deve reproduzir esse vocabulário.

A camada interna existe para proteger a qualidade da informação. A camada pública existe para comunicar o que é útil.

### 3.6 Ausência silenciosa, não mensagem negativa

Se não houver uma leitura útil, o cartão não aparece. A plataforma não deverá preencher espaços com:

- “não foi possível medir”;
- “relação fraca”;
- “dados insuficientes”;
- “cenário ausente”;
- “hipótese a verificar”;
- “não se pode concluir”.

A proteção contra conclusões indevidas deverá ser alcançada pela própria redação, e não por sucessivos avisos ao usuário.

### 3.7 Nenhuma recomendação genérica

Não publicar frases como:

- “é necessário aprofundar a análise”;
- “o município deve acompanhar os dados”;
- “é importante realizar ações”;
- “a gestão deve investigar as causas”.

Toda questão de planejamento deverá nomear:

- o público ou etapa;
- o fenômeno;
- o indicador;
- e, quando cabível, o recorte territorial ou temporal.

Exemplo aceitável:

> O planejamento do ensino médio precisa considerar, ao mesmo tempo, a redução da população de 15 a 17 anos e os níveis de reprovação e abandono, especialmente no início da etapa.

### 3.8 Tudo o que aparece deve ser reconstruível

Cada frase pública deve apontar para fatos estruturados, séries, períodos, fontes e regras de cálculo. Nenhum texto manual pode introduzir uma interpretação sem rastreabilidade.

---

## 4. Modelo de orquestração para o Fable

O Fable deverá atuar como coordenador do processo, separando descoberta, implementação, revisão e validação.

### 4.1 Regras de execução

1. Antes de alterar a aplicação, mapear os caminhos reais do repositório e adaptar os nomes lógicos deste plano à estrutura existente.
2. Congelar a versão atual como baseline reproduzível.
3. Não permitir duas implementações paralelas nos mesmos arquivos.
4. Paralelizar apenas trabalhos independentes, como:
   - auditoria de dados;
   - definição editorial;
   - catálogo de mecanismos;
   - pesquisa de novas fontes.
5. Toda etapa deve terminar com:
   - arquivos alterados;
   - comandos executados;
   - testes realizados;
   - artefatos gerados;
   - pendências;
   - veredito do gate.
6. Usar revisão independente nas etapas que criam interpretações públicas.
7. Não promover para todas as regiões antes de validar o piloto e a transferência para regiões contrastantes.
8. Preservar uma rota de rollback para o contrato público atual.

### 4.2 Vereditos permitidos em cada etapa

- **Aprovada:** todos os critérios do gate foram cumpridos.
- **Aprovada com pendências não bloqueantes:** a entrega pode seguir, mas as pendências ficam registradas.
- **Revisão necessária:** há falhas corrigíveis antes da próxima etapa.
- **Bloqueada:** falta dado, contrato ou decisão essencial.
- **Interrompida:** a solução proposta não produz valor suficiente e deve ser substituída.

### 4.3 Artefatos transversais obrigatórios

Os nomes abaixo são lógicos; o Fable deverá escolher os caminhos canônicos do repositório.

- inventário da implementação atual;
- contrato público da nova página;
- catálogo de mecanismos;
- registro de compatibilidade das séries;
- catálogo de fatos derivados;
- registro de candidatos a insight;
- registro de decisões de publicação;
- dossiê do piloto;
- relatório de transferência;
- manifesto de publicação;
- conjunto de testes de linguagem;
- conjunto de testes numéricos;
- conjunto de testes visuais e E2E.

---

# ETAPAS DE IMPLEMENTAÇÃO

## Etapa 0 — Congelar, reproduzir e auditar o estado atual

### Objetivo

Criar uma referência segura da versão atual e identificar exatamente o que deve ser preservado, removido, substituído ou reaproveitado.

### Tarefas

1. Identificar os contratos, geradores, dados, componentes, rotas, testes e documentos que formam a página atual.
2. Reproduzir o Vale do Sinos a partir da cadeia completa:
   - fontes;
   - materialização;
   - JSON público;
   - renderização.
3. Registrar:
   - os 18 cartões atuais;
   - as 8 leituras não exibidas;
   - as 4 decomposições;
   - as 15 conclusões;
   - as 71 séries territoriais;
   - os indicadores educacionais disponíveis fora da página.
4. Capturar screenshots desktop, tablet, mobile e impressão.
5. Criar uma matriz de decisão para cada elemento atual:
   - preservar;
   - reaproveitar internamente;
   - reescrever;
   - mover para consulta;
   - remover da experiência pública.
6. Confirmar e registrar os problemas já conhecidos:
   - duplicação do par EJA × escolaridade do emprego;
   - hipótese herdada do fator errado;
   - uso de população de 0 a 14 anos com ensino médio;
   - títulos que descrevem as pontas da série enquanto a métrica interna descreve variações anuais;
   - cartões de triagem sem mecanismo;
   - excesso de mensagens de limitação;
   - área de futuro sem conteúdo efetivo para o Vale do Sinos.
7. Criar fixtures imutáveis para os números e textos da versão atual, permitindo comparação e rollback.

### Entregáveis

- relatório de auditoria do estado atual;
- mapa de arquivos e dependências;
- baseline reproduzível;
- screenshots de referência;
- matriz preservar/reaproveitar/remover;
- lista priorizada de problemas;
- branch ou tag de rollback.

### Gate 0

A etapa só passa quando:

- a versão atual for reproduzida sem divergências;
- todos os componentes públicos tiverem origem identificada;
- os problemas conhecidos estiverem reproduzidos;
- existir rollback testado.

---

## Etapa 1 — Definir o contrato de produto e de conteúdo público

### Objetivo

Transformar o pedido da gestora em regras explícitas de produto, para impedir que a implementação volte a ser guiada pela disponibilidade de pares estatísticos.

### Tarefas

1. Criar um contrato funcional com as duas direções:
   - `educacao_para_territorio`;
   - `territorio_para_educacao`.
2. Definir o número máximo de leituras:
   - três a cinco na primeira saída;
   - duas a cinco na segunda saída.
3. Definir o mínimo para publicar a página:
   - pelo menos três leituras válidas na primeira saída;
   - pelo menos duas questões válidas na segunda saída.
4. Definir a anatomia obrigatória de cada leitura.
5. Definir a diferença entre:
   - fato observado;
   - leitura integrada;
   - questão de planejamento;
   - tendência futura;
   - cenário.
6. Definir o que não será mais conteúdo público:
   - coeficientes;
   - classificações de força;
   - escada E1–E5;
   - lista de relações descartadas;
   - mensagens de ausência;
   - frases de “não conclusão”;
   - triagem automática;
   - detalhes do método estatístico.
7. Criar exemplos aprovados e reprovados de cartões públicos.
8. Definir o texto curto de enquadramento da página, por exemplo:

> Esta página reúne mudanças da educação e do território ao longo do tempo. Os dados são apresentados em conjunto quando ajudam a interpretar uma mesma questão de planejamento. A leitura não atribui automaticamente uma mudança à outra.

9. Submeter o contrato a uma revisão editorial independente.

### Entregáveis

- contrato funcional da página;
- schema lógico dos dois tipos de cartão;
- guia editorial;
- vocabulário público permitido;
- vocabulário interno;
- exemplos aprovados/reprovados;
- critérios mínimos de publicação.

### Gate 1

A etapa só passa quando:

- cada requisito da gestora estiver ligado a um campo ou bloco da nova página;
- estiver definido o que aparece e o que nunca aparece ao usuário;
- os exemplos de linguagem forem compreensíveis sem explicação técnica;
- a página puder ser descrita sem mencionar correlação, força ou grau de evidência.

---

## Etapa 2 — Construir o catálogo de mecanismos

### Objetivo

Substituir a busca livre de pares por um conjunto controlado de relações que façam sentido para a educação e o território.

### Tarefas

Criar um catálogo versionado. Cada mecanismo deverá registrar:

- pergunta educacional;
- transformação territorial relacionada;
- justificativa substantiva;
- variável educacional principal;
- variáveis territoriais aceitas;
- população e faixa etária corretas;
- escala geográfica;
- janela temporal mínima;
- eventual distância temporal entre os fenômenos;
- decomposição que deve ocorrer antes do cruzamento;
- leitura pública máxima permitida;
- afirmações proibidas;
- temas do PNE/PME relacionados;
- fontes atuais;
- fontes desejáveis;
- status de disponibilidade.

### Famílias iniciais do catálogo

#### M1 — Demografia e tamanho da oferta

Aplicações:

- nascimentos e educação infantil;
- coortes de 6 a 14 anos e ensino fundamental;
- coortes de 15 a 17 anos e ensino médio;
- envelhecimento e reorganização da rede;
- migração de crianças e jovens.

#### M2 — Trajetória escolar e permanência

Aplicações:

- transição entre etapas;
- aprovação;
- reprovação;
- abandono;
- distorção idade-série;
- conclusão na idade adequada.

Fatores territoriais possíveis:

- trabalho juvenil;
- deslocamento;
- renda;
- vulnerabilidade;
- migração;
- organização da oferta.

#### M3 — EJA e população que ainda não concluiu a educação básica

Aplicações:

- adultos sem fundamental completo;
- adultos sem médio completo;
- matrícula da EJA em relação ao público potencial;
- escolas, turmas, turnos e localização;
- EJA integrada à educação profissional;
- perfil de escolaridade do trabalho.

O CadÚnico entra apenas como contexto de vulnerabilidade, nunca como denominador principal da demanda por EJA.

#### M4 — Educação profissional e transformação do trabalho

Aplicações:

- matrículas, ingressantes e concluintes por modalidade ou eixo;
- ocupações em crescimento, reposição ou transformação;
- setores predominantes;
- aprendizagem profissional;
- escolaridade e qualificação requeridas;
- localização da oferta.

O total de emprego industrial não será aceito como substituto da demanda por cursos.

#### M5 — Mobilidade territorial e organização regional da educação

Aplicações:

- município de residência;
- município de estudo;
- município de trabalho;
- fluxos intermunicipais;
- transporte escolar;
- rede que recebe estudantes de outros municípios;
- oferta compartilhada de ensino médio, EJA e educação profissional.

#### M6 — Condições escolares e resultados educacionais

Aplicações:

- infraestrutura;
- conectividade;
- horas-aula;
- regularidade docente;
- adequação da formação;
- tamanho das turmas;
- nível socioeconômico;
- aprendizagem e trajetória.

Essas variáveis devem ser tratadas como condições que ajudam a compor o contexto, sem afirmar efeito automático.

#### M7 — Transformações setoriais, tecnológicas e agenda formativa

Aplicações:

- mudança da composição econômica;
- novas ocupações;
- digitalização;
- transição energética;
- novas competências;
- requalificação de adultos;
- atualização da oferta técnica.

Só serão publicadas quando houver ligação rastreável entre a transformação territorial e uma questão educacional concreta.

### Bloqueio da triagem irrestrita

O sistema pode continuar calculando associações para controle interno, mas:

- nenhum par fora do catálogo pode virar cartão;
- nenhum par entra no catálogo apenas por ter resultado estatístico alto;
- novos mecanismos exigem justificativa, fonte e revisão.

### Entregáveis

- catálogo de mecanismos versionado;
- mapa mecanismo × série;
- lista de pares permitidos;
- lista de pares bloqueados;
- regras de temporalidade;
- regras de universo;
- regras de leitura pública.

### Gate 2

A etapa só passa quando:

- cada candidato público estiver ligado a um mecanismo;
- todas as faixas etárias e populações estiverem coerentes;
- a triagem irrestrita estiver impedida de alimentar a interface;
- cada mecanismo tiver uma utilidade de planejamento claramente definida.

---

## Etapa 3 — Organizar as séries por universo, território e finalidade

### Objetivo

Evitar interpretações erradas causadas por diferenças de população, localização, rede, unidade ou período.

### Tarefas

1. Criar um registro canônico para todas as séries relevantes.
2. Para cada série, registrar:
   - nome público;
   - nome técnico;
   - fonte;
   - periodicidade;
   - período;
   - unidade;
   - faixa etária;
   - população de referência;
   - residência ou local de ocorrência;
   - município, região ou estado;
   - rede responsável, quando aplicável;
   - observado, calculado ou projetado;
   - comparabilidade ao longo do tempo;
   - uso permitido.
3. Classificar as lentes territoriais:
   - **residentes da região**;
   - **escolas localizadas na região**;
   - **rede municipal ou estadual responsável**.
4. Criar alertas internos para combinações incompatíveis.
5. Definir denominadores adequados:
   - matrícula por população da idade;
   - EJA por adultos que ainda não concluíram a etapa;
   - aprendizagem por população jovem;
   - oferta técnica por população ou público potencial;
   - escolas rurais por população rural e distribuição territorial.
6. Definir como tratar taxas acima de 100 sem expor uma explicação técnica no cartão principal.
7. Registrar quebras de série, mudanças de fonte e anos preliminares.
8. Criar testes automáticos de compatibilidade.

### Entregáveis

- registro canônico das séries;
- matriz de compatibilidade;
- dicionário de denominadores;
- validações automáticas;
- relatório de quebras e limitações;
- mapa das três lentes territoriais.

### Gate 3

A etapa só passa quando:

- nenhum par público usar universos incompatíveis;
- toda medida derivada tiver numerador e denominador explícitos;
- residência, localização da escola e responsabilidade da rede estiverem separadas;
- os testes bloquearem os erros já encontrados no piloto.

---

## Etapa 4 — Enriquecer primeiro com dados já disponíveis

### Objetivo

Aproveitar o que já existe no PNE e na camada de pesquisa antes de iniciar uma expansão ampla de fontes.

### Prioridade 1 — Demografia por idade correta

Incorporar ou consolidar:

- 0 a 3 anos;
- 4 e 5 anos;
- 6 a 10 anos;
- 11 a 14 anos;
- 15 a 17 anos;
- 18 a 24 anos;
- nascimentos;
- migração por coorte;
- envelhecimento;
- população rural, quando disponível.

### Prioridade 2 — Trajetória escolar

Incorporar regionalmente e por município:

- aprovação;
- reprovação;
- abandono;
- distorção idade-série;
- transição entre etapas;
- idade regular no 5º, 9º e ensino médio;
- conclusão do fundamental;
- conclusão do médio.

### Prioridade 3 — Oferta educacional

Incorporar:

- escolas;
- turmas;
- turnos;
- localização urbana/rural;
- rede;
- etapa;
- transporte escolar, quando disponível;
- educação integral;
- EJA;
- educação profissional;
- educação especial.

### Prioridade 4 — Público potencial da EJA

Construir, com base já disponível ou já adquirida:

- adultos sem fundamental completo;
- adultos sem médio completo;
- distribuição por idade;
- distribuição municipal;
- matrícula da EJA por mil adultos do público potencial;
- oferta de EJA por município, etapa e turno.

### Prioridade 5 — Educação profissional

Separar:

- educação profissional total;
- técnica;
- integrada;
- concomitante;
- subsequente;
- qualificação;
- EJA integrada;
- rede;
- município;
- eixo tecnológico ou curso, quando disponível.

### Prioridade 6 — Trabalho por idade, escolaridade e ocupação

A partir das bases já adquiridas, materializar:

- vínculos de 15 a 17 anos;
- vínculos de 18 a 24 anos;
- vínculos de 25 anos ou mais;
- escolaridade;
- setor;
- ocupação;
- salário;
- admissões e desligamentos, quando disponíveis;
- participação da aprendizagem.

### Medidas derivadas prioritárias

- matrícula em relação à população da idade;
- mudança da matrícula separada entre população e participação;
- EJA em relação ao público potencial;
- contribuição de cada município para a mudança regional;
- composição da matrícula por rede;
- composição da oferta por turno;
- participação da formação técnica por modalidade;
- transição e permanência por etapa;
- trabalho juvenil por faixa etária;
- concentração das ocupações por escolaridade;
- diferença entre região e estado;
- diferença entre municípios semelhantes.

### Entregáveis

- pacote de séries enriquecidas;
- medidas derivadas;
- documentação de cálculo;
- testes de fechamento;
- relatório de cobertura municipal e temporal.

### Gate 4

A etapa só passa quando:

- o Vale do Sinos tiver dados suficientes para reconstruir ao menos três leituras da primeira saída;
- o ensino médio puder ser lido com demografia e trajetória;
- a EJA puder ser relacionada ao público potencial, ou for explicitamente retida da publicação;
- a educação profissional estiver separada por modalidade;
- os dados regionais puderem ser decompostos por município.

---

## Etapa 5 — Incorporar novas fontes apenas onde houver ganho claro

### Objetivo

Adicionar fontes externas de forma seletiva, vinculadas a lacunas específicas das duas saídas.

### Regra de entrada de uma nova fonte

Uma fonte só entra no pipeline se:

1. for pública ou tiver permissão clara de publicação;
2. puder ser reproduzida;
3. tiver recorte municipal ou regional adequado;
4. tiver periodicidade e comparabilidade conhecidas;
5. preencher uma lacuna de um mecanismo;
6. possibilitar ao menos uma leitura ou questão de agenda que ainda não existe;
7. não puder ser substituída por dado já disponível.

### Ordem sugerida

#### Lote A — Maior ganho imediato

- microdados do Censo Escolar para oferta, turno, transporte e composição da rede;
- fluxo e distorção do Inep, já disponíveis na camada de pesquisa;
- RAIS por idade e CBO;
- dados de deslocamento para estudo e trabalho;
- dados de aprendizagem profissional;
- correspondência entre cursos técnicos, eixos e ocupações.

#### Lote B — Atualização do mercado de trabalho

- Novo Caged mensal por idade, setor e ocupação;
- admissões, desligamentos e saldo;
- primeiro emprego;
- mudanças ocupacionais recentes.

#### Lote C — Futuro do território

- cenários regionais já produzidos pela metodologia da plataforma;
- estudos setoriais com recorte aplicável à região;
- mapas de demanda ocupacional;
- transformações tecnológicas e energéticas com exposição local demonstrável;
- projeções demográficas defensáveis para o horizonte da página.

### Pesquisa obrigatória para cada fonte

O job responsável deverá entregar:

- o que a fonte mede;
- qual pergunta ela responde;
- escala territorial;
- periodicidade;
- riscos;
- forma de download;
- regra de atualização;
- uso público permitido;
- custo de manutenção;
- decisão de incorporar ou rejeitar.

### Entregáveis

- dossiê de fontes candidatas;
- decisão por fonte;
- adaptadores apenas para fontes aprovadas;
- testes;
- registro de atualização.

### Gate 5

A etapa só passa quando:

- nenhuma fonte tiver sido adicionada apenas por disponibilidade;
- cada fonte aprovada estiver ligada a um mecanismo e a uma saída;
- o custo de manutenção for compatível com o valor público;
- os dados futuros tiverem origem e horizonte declarados internamente.

---

## Etapa 6 — Construir a primeira saída: o território ajuda a compreender a educação

### Objetivo

Gerar leituras integradas a partir de resultados educacionais prioritários.

### 6.1 Seleção dos resultados educacionais

A seleção deve ocorrer nesta ordem:

1. indicador ligado a tema prioritário do PNE/PME;
2. mudança relevante ao longo do tempo ou posição relevante frente ao estado;
3. mecanismo territorial disponível;
4. dados compatíveis;
5. capacidade de produzir questão concreta de planejamento;
6. ausência de redundância com outra leitura.

Não usar um score opaco. Aplicar gates e, entre os aprovados, ordenar por:

1. prioridade educacional;
2. alcance da população afetada;
3. atualidade;
4. diferença frente ao estado;
5. diversidade temática.

### 6.2 Sequência analítica obrigatória

Para cada resultado selecionado, executar:

#### Passo A — Descrever o resultado educacional

Registrar:

- valor inicial;
- valor final;
- variação;
- posição frente ao estado;
- municípios que mais contribuíram;
- diferenças internas.

#### Passo B — Separar seus componentes

Exemplos:

- matrícula = população da idade + participação escolar;
- conclusão = acesso + fluxo + permanência;
- EJA = público potencial + disponibilidade da oferta + participação;
- formação técnica = população + oferta + composição dos cursos;
- escolas rurais = população rural + distribuição territorial + organização da rede.

#### Passo C — Incorporar trajetória e oferta

Antes de recorrer a renda, emprego ou setor, verificar:

- transição;
- reprovação;
- abandono;
- distorção;
- conclusão;
- rede;
- turno;
- localização;
- oferta disponível.

#### Passo D — Acrescentar fatores territoriais

Selecionar no máximo dois ou três fatores que:

- tenham mecanismo catalogado;
- sejam compatíveis;
- acrescentem algo que a educação sozinha não mostra;
- permaneçam estáveis nas validações internas.

#### Passo E — Verificar o tempo

Definir se a leitura é:

- simultânea;
- anterior;
- posterior;
- acumulada;
- ligada a uma coorte.

Não apresentar ao público o termo técnico. Traduzir em expressões como:

- “no mesmo período”;
- “seis anos depois”;
- “desde o início da série”;
- “a mudança começou antes”;
- “a diferença se concentrou nos anos...”.

#### Passo F — Verificar a heterogeneidade municipal

Calcular:

- contribuição de cada município para a mudança regional;
- resultado sem cada município;
- concentração da tendência;
- comparação com municípios de perfil semelhante.

Uma leitura regional não pode ser publicada como característica do território inteiro quando depender quase exclusivamente de um município.

#### Passo G — Produzir a questão de planejamento

A questão deve resultar dos dados anteriores e indicar:

- etapa;
- público;
- fenômeno;
- recorte;
- indicador a acompanhar.

### 6.3 Estrutura pública do cartão

Cada cartão deverá conter:

1. **Título com a principal leitura**
2. **O que mudou na educação**
3. **O que o território ajuda a compreender**
4. **Como isso aparece entre os municípios**
5. **O que entra no planejamento**
6. **Indicadores e fontes**, em detalhe recolhido

### 6.4 Exemplo esperado para o Vale do Sinos

#### Título

**A queda das matrículas no ensino médio acompanha principalmente a redução da população jovem**

#### O que mudou

Entre 2014 e 2025, as matrículas no ensino médio passaram de 31.789 para 26.911.

#### Leitura integrada

No mesmo período, a população correspondente às idades de 15 a 17 anos caiu de 46.217 para 34.238. A redução da população jovem foi maior do que a queda das matrículas, enquanto a relação entre matrículas e população da idade aumentou.

#### Complemento educacional

Mesmo com essa melhora relativa, a mediana regional de reprovação e abandono no ensino médio permanece acima da mediana estadual.

#### Questão para o planejamento

O ajuste do tamanho e da distribuição da oferta precisa ocorrer junto com ações voltadas à transição, à permanência e à conclusão, sobretudo nos anos e municípios em que reprovação e abandono se concentram.

Este exemplo deve ser recalculado e refinado com os dados municipais antes da publicação.

### 6.5 Validações internas permitidas

A camada técnica poderá usar:

- correlação das variações;
- comparação das pontas;
- distância temporal;
- sensibilidade a janelas;
- retirada de um município por vez;
- comparação com pares;
- medidas de trajetória;
- decomposições contábeis.

Nenhum desses nomes deverá aparecer no cartão público.

### Entregáveis

- motor de candidatos da primeira saída;
- registro de decisão por candidato;
- três a cinco leituras aprovadas no Vale do Sinos;
- fatos estruturados;
- textos reconstruíveis;
- visualizações;
- testes.

### Gate 6

Cada leitura deverá passar por oito gates:

1. relevância para o PNE/PME;
2. mecanismo válido;
3. universo compatível;
4. tempo coerente;
5. estabilidade territorial;
6. valor para o planejamento;
7. não redundância;
8. clareza pública.

Se qualquer gate falhar, a leitura não aparece.

---

## Etapa 7 — Construir a segunda saída: o futuro do território coloca temas na agenda da educação

### Objetivo

Partir das transformações do território e traduzi-las em questões educacionais concretas para os próximos anos.

### 7.1 Tipos de transformação

O motor deverá distinguir internamente:

1. mudança já observada;
2. tendência sustentada por série ou projeção adequada;
3. transformação apontada por estudo setorial;
4. caminho possível presente nos cenários.

Na interface, os rótulos poderão ser simples:

- **Mudança já em curso**
- **Tendência para os próximos anos**
- **Tema presente nos cenários**

### 7.2 Famílias prioritárias

#### Demografia

- redução de nascimentos;
- diminuição das coortes escolares;
- envelhecimento;
- migração de jovens;
- redistribuição da população.

#### Trabalho e renda

- mudanças no emprego juvenil;
- escolaridade dos vínculos;
- ocupações em crescimento ou retração;
- primeiro emprego;
- aprendizagem;
- remuneração e estabilidade.

#### Estrutura econômica

- setores que ganham ou perdem participação;
- exposição dos municípios;
- substituição ou transformação de ocupações;
- especializações regionais.

#### Tecnologia e transições

- digitalização;
- automação;
- transição energética;
- novas exigências de qualificação;
- requalificação de trabalhadores adultos.

#### Mobilidade regional

- deslocamentos para estudo;
- deslocamentos para trabalho;
- concentração regional da oferta;
- municípios que atraem ou perdem jovens.

### 7.3 Regra para criar uma questão de agenda

Uma transformação só gera cartão quando houver:

1. dado territorial que mostre a mudança;
2. indicador educacional que descreva o ponto de partida;
3. grupo, etapa ou território afetado;
4. implicação concreta para o planejamento;
5. tema do PNE/PME relacionado;
6. indicador que possa ser acompanhado.

### 7.4 Estrutura pública do cartão

1. **Transformação do território**
2. **O que já está mudando**
3. **Ponto de partida da educação**
4. **O que essa mudança coloca na agenda**
5. **Municípios ou públicos mais expostos**
6. **Indicadores para acompanhar**
7. **Metas e temas relacionados**

### 7.5 Exemplo demográfico

#### Título

**Menos crianças e jovens exigirão uma rede mais ajustada à distribuição da população**

#### Transformação

Os nascimentos diminuíram de forma prolongada e as coortes das etapas escolares já são menores.

#### Ponto de partida educacional

A educação infantil ampliou o atendimento mesmo com a redução das novas gerações, enquanto o ensino fundamental e o médio registraram queda de matrículas.

#### Agenda

O planejamento precisa antecipar onde a demanda continuará elevada, onde a oferta poderá ficar dispersa e como preservar acesso e qualidade sem reduzir a presença da rede em áreas vulneráveis ou distantes.

#### Indicadores

- nascimentos;
- população por idade;
- matrículas por etapa;
- escolas e turmas;
- deslocamento;
- rede;
- localização urbana/rural.

### 7.6 Exemplo de formação profissional

O cartão só deverá ser publicado após existir ligação entre:

- ocupações ou famílias ocupacionais;
- nível de qualificação;
- setores e municípios;
- cursos ou eixos ofertados;
- matrículas, ingressantes ou concluintes.

Não será suficiente dizer que a indústria caiu e a matrícula técnica cresceu.

### 7.7 Relação com os cenários

Os cenários deverão enriquecer a segunda saída, mas não substituir a leitura dos dados observados.

Quando houver cenários publicados:

- identificar questões que aparecem em mais de um cenário;
- registrar incertezas que mudam a resposta educacional;
- evitar números futuros não autorizados;
- mostrar quais decisões são robustas em diferentes futuros.

Quando ainda não houver cenários, a página não exibirá uma mensagem de ausência. A saída só será publicada quando houver conteúdo mínimo sustentado por tendências observadas e fontes aprovadas.

### Entregáveis

- registro de transformações territoriais;
- mapa transformação × educação;
- duas a cinco questões de agenda para o Vale do Sinos;
- ligação com PNE/PME;
- indicadores de acompanhamento;
- integração com cenários quando disponíveis.

### Gate 7

A etapa só passa quando:

- cada cartão partir do território e chegar à educação;
- nenhuma questão for genérica;
- houver dado atual e implicação concreta;
- a seção não depender de mensagens de ausência;
- o futuro estiver claramente separado do observado nos artefatos internos.

---

## Etapa 8 — Incorporar a comparação temporal e territorial às duas saídas

### Objetivo

Mostrar quando e onde as mudanças ocorreram, sem transformar a página em relatório estatístico.

### Tarefas

1. Padronizar janelas comparáveis.
2. Identificar períodos de mudança relevantes.
3. Aplicar distâncias temporais apenas quando previstas no mecanismo.
4. Construir minigráficos alinhados por período.
5. Destacar no texto:
   - início e fim;
   - aceleração ou desaceleração;
   - mudança de direção;
   - concentração em determinados anos.
6. Decompor a mudança regional por município.
7. Mostrar:
   - municípios que mais contribuíram;
   - municípios que seguiram direção diferente;
   - distribuição interna.
8. Criar comparação com o RS e, quando útil, com regiões semelhantes.
9. Evitar rankings sem interpretação.
10. Bloquear leituras em que a região seja apresentada como homogênea sem ser.

### Visualizações recomendadas

- dois minigráficos alinhados;
- gráfico de componentes da mudança;
- barras de contribuição municipal;
- mapa apenas quando a geografia agregar interpretação;
- linha regional com faixa de municípios;
- comparação simples com RS.

### Entregáveis

- componentes temporais;
- componentes municipais;
- visualizações;
- regras de comparação;
- testes de consistência.

### Gate 8

A etapa só passa quando:

- cada leitura mostrar um período coerente;
- a contribuição dos municípios estiver disponível;
- nenhuma conclusão regional depender apenas de um município sem que isso seja explicitado;
- os gráficos acrescentarem informação ao texto.

---

## Etapa 9 — Construir o compilador de narrativas e o contrato de linguagem

### Objetivo

Gerar textos úteis, consistentes e protegidos contra jargão, causalidade indevida e mensagens sem valor.

### 9.1 Arquitetura

Separar três camadas:

#### Camada 1 — Fatos

Exemplos:

- matrícula inicial e final;
- população inicial e final;
- variação;
- municípios que mais contribuíram;
- posição frente ao RS;
- indicador de fluxo;
- fonte.

#### Camada 2 — Leitura aprovada

Registra internamente:

- mecanismo;
- combinação de fatos;
- alcance permitido;
- questão de planejamento;
- decisão de publicação.

#### Camada 3 — Texto público

É gerado apenas a partir da leitura aprovada e de templates editoriais fechados.

### 9.2 Termos que não devem aparecer na página pública

- correlação;
- Pearson;
- Spearman;
- significância;
- p-valor;
- relação fraca;
- relação moderada;
- relação forte;
- evidência E1, E2, E3, E4 ou E5;
- triagem automática;
- lead;
- note;
- ausência declarada;
- evidência insuficiente;
- não foi possível medir;
- hipótese a verificar;
- não se pode concluir;
- decomposição Bennett;
- shift-share;
- efeito demográfico;
- efeito taxa;
- taxa de atendimento aparente;
- universo incompatível;
- fail-closed.

### 9.3 Traduções públicas recomendadas

| Interno | Público |
|---|---|
| efeito demográfico | parte da mudança ligada ao tamanho da população |
| taxa de atendimento aparente | matrículas em relação à população da idade |
| defasagem de seis anos | seis anos depois |
| correlação das variações | mudanças ocorridas no mesmo período |
| contribuição municipal | participação de cada município na mudança regional |
| público elegível da EJA | adultos que ainda não concluíram essa etapa |
| shift-share | componentes da mudança do emprego |
| cenário invariante | questão que permanece importante em diferentes futuros |

### 9.4 Frases que devem ser bloqueadas

- “A relação é fraca.”
- “Não foi possível estabelecer relação.”
- “Os dados são insuficientes.”
- “Não se pode afirmar que uma variável causou a outra.”
- “A análise sugere uma correlação.”
- “A hipótese precisa ser verificada localmente.”
- “É necessário aprofundar a análise.”
- “O município deve investigar.”
- “A plataforma não possui dados.”
- “Não há cenários publicados.”

### 9.5 Estratégia correta

Em vez de mostrar um aviso sobre o que não pode ser dito, redigir apenas o que os dados permitem.

#### Evitar

> A relação entre emprego formal e matrícula do ensino médio é moderada e não permite concluir causalidade.

#### Preferir

> Enquanto o emprego formal cresceu, a matrícula do ensino médio diminuiu. A queda da população de 15 a 17 anos foi ainda maior, indicando que a mudança demográfica é central para interpretar esse resultado.

#### Evitar

> Não foi possível medir a demanda por EJA.

#### Preferir

Não publicar o cartão até existir um denominador adequado de adultos que ainda não concluíram a educação básica.

### 9.6 Teste de valor do insight

Antes de publicar, responder:

1. O usuário aprende algo que não obteria olhando apenas um indicador?
2. A leitura combina ao menos um fato educacional e um territorial?
3. A leitura produz uma questão de planejamento específica?
4. O texto pode ser compreendido sem método estatístico?
5. Há números e fontes que sustentam a frase?
6. O conteúdo é diferente dos demais cartões?

Qualquer resposta negativa bloqueia a publicação.

### Entregáveis

- compilador de narrativas;
- templates;
- linter de linguagem;
- testes adversariais;
- registro de fatos;
- registro de textos;
- revisão editorial.

### Gate 9

A etapa só passa quando:

- nenhum termo bloqueado aparecer na página;
- nenhum cartão depender de aviso negativo;
- toda frase pública puder ser reconstruída;
- os textos forem compreensíveis para gestores municipais;
- nenhum texto for genérico.

---

## Etapa 10 — Redesenhar a experiência da página

### Objetivo

Fazer a interface refletir a nova lógica editorial.

### 10.1 Cabeçalho

Manter:

- região selecionada;
- período de referência;
- explicação curta da proposta.

Substituir os quatro números soltos por **três achados integrados**, por exemplo:

- redução das coortes escolares;
- mudança da participação nas etapas;
- transformação do perfil do trabalho.

Cada destaque deve levar a uma leitura completa.

### 10.2 Navegação principal

Usar duas entradas claras:

1. **O território e a educação hoje**
2. **O futuro do território e a agenda da educação**

Evitar títulos em formato de “Pergunta 1”, “Pergunta 2” ou nomes metodológicos.

### 10.3 Cartões principais

Cada cartão deve ser maior e mais completo, reunindo:

- título;
- síntese;
- números;
- visual temporal;
- diferenças municipais;
- questão de planejamento;
- ligação ao PNE.

Não dividir uma mesma história em vários cartões de pares.

### 10.4 Detalhes recolhidos

Ações possíveis:

- Ver evolução
- Ver municípios
- Ver metas relacionadas
- Ver dados e fontes

A metodologia técnica não deve aparecer como conteúdo de primeiro nível.

### 10.5 Destino do conteúdo atual

- cartões de triagem: remover da página principal;
- relações redundantes: eliminar;
- “o que não se conclui”: remover;
- escada E1–E5: manter apenas na documentação interna;
- lista de relações: mover para artefato interno ou área separada de dados;
- decomposições: reaproveitar, mas traduzidas em linguagem pública;
- conclusões automáticas: substituir por sínteses integradas;
- ausência de cenários: não renderizar;
- explorador de séries: mover para uma rota ou aba de dados, fora do núcleo narrativo.

### 10.6 Requisitos visuais

- altura significativamente menor;
- leitura em blocos;
- hierarquia tipográfica clara;
- poucos elementos simultâneos;
- números destacados;
- gráficos legíveis;
- responsividade;
- impressão limpa;
- fontes sempre acessíveis;
- sem rolagem horizontal em mobile.

### Entregáveis

- nova arquitetura de informação;
- componentes;
- protótipo;
- implementação;
- screenshots;
- testes E2E;
- testes de impressão e mobile.

### Gate 10

A etapa só passa quando:

- um usuário consegue identificar as duas saídas sem explicação;
- os cartões respondem à pergunta da seção;
- não há listas de métricas técnicas;
- o percurso principal é curto;
- a página funciona em desktop, mobile e impressão.

---

## Etapa 11 — Validar o piloto do Vale do Sinos

### Objetivo

Comprovar que a nova arquitetura produz valor real antes de escalar.

### 11.1 Leituras mínimas esperadas para avaliação

As seguintes frentes devem ser testadas, mas só publicadas se passarem os gates:

1. educação infantil e redução das novas gerações;
2. ensino fundamental: população, participação e trajetória;
3. ensino médio: demografia, permanência e conclusão;
4. EJA: público potencial, oferta e perfil do trabalho;
5. educação profissional: cursos, ocupações e transformação econômica;
6. reorganização territorial da oferta;
7. agenda futura ligada à demografia;
8. agenda futura ligada ao trabalho e à qualificação.

### 11.2 Validação numérica

- reconstrução de todos os valores;
- fechamento das contas;
- comparação com fontes;
- arredondamento tardio;
- consistência região × municípios;
- consistência região × RS;
- repetição da geração.

### 11.3 Validação metodológica interna

- mecanismo;
- universo;
- tempo;
- sensibilidade;
- município dominante;
- redundância;
- alcance da leitura;
- futuro observado versus projetado.

### 11.4 Validação editorial

Perguntas para cada cartão:

- Qual é o principal insight?
- Ele aparece no título?
- Os dados sustentam a leitura?
- A questão de planejamento decorre dos dados?
- Há jargão?
- Há aviso defensivo desnecessário?
- O texto seria compreendido sem abrir a metodologia?
- O cartão repete outro?

### 11.5 Validação com usuários

Executar testes com tarefas, por exemplo:

1. identificar por que a matrícula do ensino médio caiu;
2. identificar o que ainda preocupa além da demografia;
3. explicar o que a redução dos nascimentos coloca na agenda;
4. identificar a relação entre trabalho e formação profissional;
5. localizar os municípios que mais contribuíram para uma mudança.

Registrar:

- tempo;
- resposta;
- dúvidas;
- termos mal compreendidos;
- informações consideradas úteis;
- informações ignoradas.

### 11.6 Comparação da versão antiga e nova

Avaliar:

- número de cartões;
- altura;
- tempo para encontrar o insight;
- quantidade de termos técnicos;
- número de mensagens negativas;
- redundância;
- cobertura das duas saídas;
- capacidade de explicar uma decisão de planejamento.

### Entregáveis

- dossiê do piloto;
- versão integrada;
- relatório numérico;
- revisão independente;
- teste com usuários;
- comparação antes/depois;
- lista final de ajustes.

### Gate 11

O piloto só é aprovado quando:

- a primeira saída tiver ao menos três leituras;
- a segunda tiver ao menos duas questões;
- nenhum termo bloqueado aparecer;
- nenhuma leitura for genérica;
- todas as frases forem rastreáveis;
- os usuários entenderem as duas direções;
- a página não depender de mensagens de ausência.

---

## Etapa 12 — Testar a transferência para regiões contrastantes

### Objetivo

Evitar que o método funcione apenas no Vale do Sinos.

### Seleção

Escolher duas regiões com perfis contrastantes, preferencialmente entre as regiões que já possuem cenários publicados e boa cobertura de dados. A seleção deve incluir:

- uma região com maior peso rural ou baixa densidade;
- uma região com estrutura econômica e demográfica diferente do Vale do Sinos.

Vale do Rio Pardo e Noroeste podem ser avaliadas como candidatas, mas a decisão deve considerar a cobertura real e o contraste.

### Tarefas

1. Rodar a mesma cadeia sem ajustes manuais específicos.
2. Verificar quais mecanismos aparecem.
3. Confirmar que o sistema aceita publicar menos cartões quando os dados não sustentam mais.
4. Impedir preenchimento com textos genéricos.
5. Verificar estabilidade dos templates.
6. Avaliar se os cenários enriquecem a segunda saída.
7. Registrar diferenças regionais reais.
8. Ajustar o catálogo apenas quando houver justificativa geral, nunca para acomodar um único caso.

### Regra de publicação regional

- uma região pode ter menos cartões;
- uma região não pode receber cartões genéricos para completar quantidade;
- se não atingir o mínimo das duas saídas, a nova página permanece não publicada para aquela região;
- a ausência é registrada internamente, não transformada em conteúdo público.

### Entregáveis

- relatório de transferência;
- comparação entre três regiões;
- ajustes gerais;
- testes;
- decisão de escalabilidade.

### Gate 12

A etapa só passa quando:

- a cadeia funcionar em três perfis regionais;
- não houver texto manual por região;
- o catálogo continuar coerente;
- a interface acomodar quantidades diferentes;
- as duas saídas permanecerem reconhecíveis.

---

## Etapa 13 — Escalar para as demais regiões

### Objetivo

Publicar de forma progressiva, sem reduzir a qualidade editorial.

### Tarefas

1. Rodar a cadeia para todas as regiões.
2. Gerar relatório de cobertura por mecanismo.
3. Produzir fila de regiões:
   - prontas;
   - quase prontas;
   - bloqueadas internamente.
4. Publicar em lotes.
5. Reexecutar testes numéricos, editoriais e visuais.
6. Criar manifesto de publicação.
7. Monitorar regressões.
8. Versionar contratos e dados.
9. Registrar diferenças de atualização das fontes.
10. Planejar manutenção periódica.

### Critério de lote

Uma região entra no lote quando:

- alcança o mínimo das duas saídas;
- tem fontes atualizadas;
- passa pelos gates;
- não contém texto genérico;
- tem revisão independente.

### Entregáveis

- lote de publicação;
- manifesto;
- relatório de cobertura;
- rollback;
- documentação de atualização.

### Gate 13

A expansão é concluída quando:

- todas as regiões publicadas cumprem o contrato;
- regiões ainda não prontas permanecem fora da nova rota;
- nenhuma ausência técnica aparece para o usuário;
- o processo é repetível.

---

# 5. Catálogo inicial de leituras para o Vale do Sinos

Este catálogo é um roteiro de investigação, não uma autorização automática de publicação.

## 5.1 Educação infantil

### Pergunta

Como a redução das novas gerações conviveu com o crescimento das matrículas?

### Dados

- nascimentos;
- população de 0 a 3 e 4 a 5 anos;
- matrículas;
- rede;
- municípios;
- escolas e turmas.

### Insight esperado

Separar a redução da população da ampliação da participação e mostrar onde a oferta cresceu.

### Agenda possível

Distribuição territorial da oferta e sustentabilidade do atendimento, com atenção a creche e pré-escola separadamente.

---

## 5.2 Ensino fundamental

### Pergunta

A queda das matrículas acompanha apenas a redução da população de 6 a 14 anos?

### Dados

- população de 6 a 10 e 11 a 14 anos;
- matrículas;
- participação;
- aprovação;
- reprovação;
- abandono;
- distorção;
- transição;
- rede;
- migração;
- municípios.

### Insight esperado

Distinguir mudança demográfica de mudança de fluxo, atendimento ou deslocamento.

### Agenda possível

Acesso, transição, permanência e distribuição da rede nos municípios que se afastam do padrão regional.

---

## 5.3 Ensino médio

### Pergunta

Quanto da queda das matrículas acompanha a redução da população de 15 a 17 anos e o que permanece como desafio de trajetória?

### Dados

- coorte de 15 a 17 anos;
- matrículas;
- participação;
- transição do 9º ano;
- reprovação;
- abandono;
- distorção;
- conclusão;
- trabalho juvenil;
- migração;
- deslocamento;
- rede.

### Insight esperado

Mostrar que a demografia pesa na redução, mas não elimina a agenda de permanência e conclusão.

### Agenda possível

Ajuste da oferta com foco em transição, primeiro ano, abandono e conclusão.

---

## 5.4 EJA

### Pergunta

A oferta alcança os adultos que ainda não concluíram a educação básica?

### Dados

- adultos sem fundamental;
- adultos sem médio;
- matrícula;
- escolas;
- turmas;
- turnos;
- rede;
- trabalho;
- escolaridade exigida;
- vulnerabilidade;
- municípios.

### Insight esperado

Comparar o tamanho do público potencial com a oferta e a participação, sem usar CadÚnico como substituto da demanda.

### Agenda possível

Localização, turnos, integração profissional e públicos com menor alcance.

---

## 5.5 Educação profissional

### Pergunta

A formação ofertada acompanha as ocupações e transformações econômicas da região?

### Dados

- cursos e eixos;
- matrículas, ingressantes e concluintes;
- rede;
- CBO;
- setor;
- idade;
- aprendizagem;
- escolaridade requerida;
- municípios;
- cenários.

### Insight esperado

Mostrar alinhamentos e lacunas entre oferta formativa e transformação ocupacional.

### Agenda possível

Expansão, atualização ou redistribuição de cursos por eixo, público e território.

---

## 5.6 Mobilidade e rede regional

### Pergunta

A oferta educacional acompanha os fluxos de residência, estudo e trabalho?

### Dados

- deslocamento;
- migração;
- transporte;
- escolas;
- matrículas;
- rede;
- cursos;
- municípios.

### Insight esperado

Identificar municípios que atendem além de seus residentes e públicos que dependem de deslocamento.

### Agenda possível

Coordenação regional da oferta, transporte e distribuição de etapas ou modalidades de menor escala.

---

# 6. Schema lógico dos cartões

## 6.1 Cartão da primeira saída

```yaml
id:
direction: educacao_para_territorio
title:
education_question:
education_facts:
territorial_facts:
integrated_reading:
municipal_pattern:
planning_question:
pne_topics:
monitoring_indicators:
period:
sources:
internal:
  mechanism_id:
  universe_check:
  temporal_check:
  sensitivity_check:
  territorial_check:
  publication_decision:
```

## 6.2 Cartão da segunda saída

```yaml
id:
direction: territorio_para_educacao
title:
territorial_transformation:
territorial_facts:
education_starting_point:
exposed_groups_or_municipalities:
education_agenda:
pne_topics:
monitoring_indicators:
horizon:
sources:
internal:
  transformation_class:
  mechanism_id:
  future_basis:
  sensitivity_check:
  publication_decision:
```

Os campos internos não deverão chegar ao documento público.

---

# 7. Gates de publicação de um insight

## G1 — Relevância

O conteúdo responde a uma questão do PNE, PME ou planejamento educacional?

## G2 — Mecanismo

Existe ligação substantiva catalogada entre as variáveis?

## G3 — Universo

Faixa etária, população, território e rede são compatíveis?

## G4 — Tempo

A janela e a sequência temporal fazem sentido?

## G5 — Estabilidade

A leitura permanece ao mudar moderadamente a janela ou retirar um município dominante?

## G6 — Valor

A leitura acrescenta algo além dos indicadores isolados?

## G7 — Planejamento

A questão final é concreta e derivada dos dados?

## G8 — Clareza

O conteúdo pode ser comunicado sem jargão?

## G9 — Não redundância

Outro cartão já transmite a mesma leitura?

## G10 — Rastreabilidade

Todos os números e frases podem ser reconstruídos?

A falha em qualquer gate bloqueia a publicação, sem gerar mensagem pública.

---

# 8. Testes obrigatórios

## 8.1 Numéricos

- fechamento das decomposições;
- soma municipal igual à região;
- comparação regional consistente;
- denominador zero gera ausência interna;
- arredondamento somente na exibição;
- nenhum percentual impossível sem tratamento;
- períodos coerentes;
- fontes corretas;
- dados preliminares identificados.

## 8.2 De contrato

- todo cartão tem direção;
- todo cartão tem mecanismo;
- todo cartão tem questão de planejamento;
- todo cartão tem fonte;
- nenhum campo interno chega ao frontend;
- nenhuma relação fora do catálogo é publicada.

## 8.3 De linguagem

Bloquear:

- termos técnicos listados;
- causalidade;
- avisos negativos;
- recomendações genéricas;
- frases sem sujeito ou indicador;
- “conclui-se” em sequência automática;
- duplicações;
- textos herdados de outro fator.

## 8.4 De conteúdo

- insight diferente de mera repetição de dois números;
- combinação real de educação e território;
- questão de planejamento específica;
- coerência entre título, dados e leitura;
- nenhum cartão sem valor agregado.

## 8.5 Territoriais

- retirada de um município por vez;
- concentração da mudança;
- municípios em direção oposta;
- coerência entre região e municípios;
- comparação com pares.

## 8.6 Temporais

- janelas idênticas;
- distância temporal válida;
- sensibilidade;
- quebras de série;
- anos preliminares;
- estabilidade da leitura.

## 8.7 Visuais

- desktop;
- tablet;
- mobile;
- impressão;
- altura;
- legibilidade;
- ausência de rolagem horizontal;
- fontes acessíveis;
- estados com números diferentes.

## 8.8 E2E

- seleção de região;
- navegação entre as duas saídas;
- expansão de detalhes;
- fontes;
- municípios;
- retorno;
- URL;
- persistência de filtros;
- comportamento quando uma região tem menos cartões;
- bloqueio de região ainda não pronta.

---

# 9. Rodadas (reescritas pelo Fable, V6-D7)

Sequência: `R0 → R1 → R2 → R3 → R4 → R5 → R6 → R7 → R8 → R9`. **Cada rodada em
sessão nova do Fable**, aberta com o prompt fechado abaixo. Diretórios:
`.tmp/vocacoes-pne/rodada-<NN>/`. Cada rodada termina com checklist, relatório,
vivacidade e veredito (§4.2); nenhuma inicia a seguinte.

## Rodada 0 — Encerrar o V5 e auditar o estado atual (Etapa 0)

Fecha a R3 do V5 que está no working tree: **GA humano do layout 2.9.0 (C11)**,
commits temáticos (C12), relatório (C13), push de `main` (que já carrega 4
commits não pushados). Nota de encerramento no `PLANO_VOCACOES_REGIAO_V5.md`
(R4–R5 absorvidas aqui). Em seguida a auditoria da Etapa 0 sobre o estado
commitado: inventário, reprodução ponta a ponta do Vale do Sinos, matriz
preservar/reaproveitar/remover, confirmação dos problemas conhecidos,
screenshots, fixtures imutáveis, tag de rollback. Executor só entra se o GA
gerar correção de código.

Saída: V5 encerrado; Gate 0 aprovado.

```text
Leia docs/PLANO_IMPLEMENTACAO_VOCACOES_PNE.md (§0 e Etapa 0),
.tmp/vocacoes-v5/rodada-03/CHECKLIST_RODADA_03.md e o
GA_HUMANO_RODADA_03.md parcial. Execute a Rodada 0 conforme o protocolo
(§0.2): feche C11–C13 da R3 do V5 (GA humano comigo), commits e push, nota de
encerramento no plano V5, depois a auditoria completa da Etapa 0 com baseline
e rollback. Relate em .tmp/vocacoes-pne/rodada-00/. Não inicie a rodada
seguinte.
```

## Rodada 1 — Contrato de produto e de linguagem (Etapas 1 e 9-contrato)

O contrato funcional das duas saídas, a anatomia dos cartões (§6), o guia
editorial, vocabulário público × interno (§9.2–9.4), exemplos
aprovados/reprovados e critérios mínimos de publicação. **Trabalho editorial do
Fable** (linguagem pública nunca é delegada); o executor implementa o linter de
linguagem e os testes de contrato como código. Revisão independente: leitura
adversarial + GA humano do mantenedor sobre os exemplos.

Saída: Gate 1 aprovado; linter e testes de contrato verdes contra os exemplos.

```text
Leia docs/PLANO_IMPLEMENTACAO_VOCACOES_PNE.md (§0, Etapa 1, §6, §7, Etapa 9) e
.tmp/vocacoes-pne/rodada-00/RELATORIO_RODADA_00.md. Execute a Rodada 1
conforme o protocolo (§0.2): você redige o contrato, os exemplos e o
vocabulário; o GPT 5.6 sol xhigh implementa o linter e os testes de contrato
sob sua especificação; GA humano comigo sobre os exemplos de cartão. Relate em
.tmp/vocacoes-pne/rodada-01/. Não inicie a rodada seguinte.
```

## Rodada 2 — Catálogo de mecanismos e registro de séries (Etapas 2 e 3)

Catálogo versionado M1–M7 com pares permitidos/bloqueados; registro canônico
das séries com universo, lente territorial e denominadores; validações
automáticas de compatibilidade que reproduzem (e bloqueiam) os erros já
conhecidos do piloto. O executor constrói os registros e testes; o Fable define
cada mecanismo (a substância é critério, não código) e verifica em amostra.

Saída: Gates 2 e 3 aprovados; triagem irrestrita impedida de alimentar a
interface.

```text
Leia docs/PLANO_IMPLEMENTACAO_VOCACOES_PNE.md (§0, Etapas 2 e 3) e o relatório
da rodada anterior. Execute a Rodada 2 conforme o protocolo (§0.2): você
define os mecanismos e as regras de universo, o GPT 5.6 sol xhigh implementa
catálogo, registro e validações; você verifica em amostra. Relate em
.tmp/vocacoes-pne/rodada-02/. Não inicie a rodada seguinte.
```

## Rodada 3 — Dados já disponíveis (Etapa 4, na camada de pesquisa)

Prioridades 1–6 e medidas derivadas, executadas majoritariamente em
`SESI\PNE` (V6-D4), com handshake fail-closed para cá. O Gate 4 mede-se no
piloto: ensino médio legível com demografia+trajetória, EJA com público
potencial ou retida, educação profissional por modalidade, decomposição
municipal disponível.

Saída: Gate 4 aprovado; relatório de cobertura municipal e temporal.

```text
Leia docs/PLANO_IMPLEMENTACAO_VOCACOES_PNE.md (§0, Etapa 4) e o relatório da
rodada anterior. Execute a Rodada 3 conforme o protocolo (§0.2): jobs de
materialização na camada de pesquisa (C:\Users\rnbirck\PROJETOS\SESI\PNE),
um job por chamada, você recomputa amostras e verifica fechamentos. Relate em
.tmp/vocacoes-pne/rodada-03/. Não inicie a rodada seguinte.
```

## Rodada 4 — Fontes novas dirigidas (Etapa 5)

Apenas lacunas nomeadas pelos mecanismos; regra de entrada da Etapa 5;
aprovação parcial permitida — o que já puder ser construído não fica bloqueado.
Lotes A/B/C conforme ganho.

Saída: Gate 5 aprovado ou parcialmente aprovado, com decisão registrada por
fonte.

```text
Leia docs/PLANO_IMPLEMENTACAO_VOCACOES_PNE.md (§0, Etapa 5) e o relatório da
rodada anterior. Execute a Rodada 4 conforme o protocolo (§0.2): um job de
pesquisa por fonte candidata com o dossiê obrigatório; adaptadores só para
aprovadas; você decide incorporar ou rejeitar. Relate em
.tmp/vocacoes-pne/rodada-04/. Não inicie a rodada seguinte.
```

## Rodada 5 — Primeira saída no piloto (Etapas 6 e 8)

Motor de candidatos, sequência analítica A–G, heterogeneidade municipal,
comparação temporal incorporada, fatos estruturados e três a cinco leituras do
Vale do Sinos. O executor constrói motor e fatos; **o Fable redige os textos
públicos a partir dos fatos aprovados** e recomputa cada número citado.

Saída: Gates 6 e 8 aprovados para a primeira direção no piloto.

```text
Leia docs/PLANO_IMPLEMENTACAO_VOCACOES_PNE.md (§0, Etapas 6 e 8, §7) e o
relatório da rodada anterior. Execute a Rodada 5 conforme o protocolo (§0.2):
o GPT 5.6 sol xhigh constrói motor, decomposições e fatos; você seleciona,
redige as leituras e recomputa todos os números citados; os oito gates por
leitura. Relate em .tmp/vocacoes-pne/rodada-05/. Não inicie a rodada seguinte.
```

## Rodada 6 — Segunda saída no piloto (Etapas 7 e 8)

Registro de transformações, mapa transformação×educação, duas a cinco questões
de agenda do Vale do Sinos ancoradas em dados observados e tendências
sustentadas (V6-D3: sem cenários no piloto), ligação PNE/PME, indicadores de
acompanhamento.

Saída: Gate 7 (e 8 para a segunda direção) aprovado no piloto.

```text
Leia docs/PLANO_IMPLEMENTACAO_VOCACOES_PNE.md (§0, Etapas 7 e 8, §7) e o
relatório da rodada anterior. Execute a Rodada 6 conforme o protocolo (§0.2):
o GPT 5.6 sol xhigh constrói o registro de transformações e os fatos; você
redige as questões de agenda e verifica cada regra da Etapa 7.3; lembre a
V6-D3 (Vale do Sinos sem cenários). Relate em .tmp/vocacoes-pne/rodada-06/.
Não inicie a rodada seguinte.
```

## Rodada 7 — Compilador de narrativas e página nova (Etapas 9 e 10)

Compilador em três camadas (fatos → leitura aprovada → texto público),
templates fechados, linter ativo em CI, nova arquitetura da página sobre a base
2.9.0 (portar antes de deletar), camada de consulta, destino do conteúdo atual
(§10.5). QA visual do Fable no navegador com instrumentos de altura/largura;
testes visuais e E2E.

Saída: Gates 9 e 10 aprovados; GA humano do mantenedor sobre o piloto renderizado.

```text
Leia docs/PLANO_IMPLEMENTACAO_VOCACOES_PNE.md (§0, Etapas 9 e 10) e o
relatório da rodada anterior. Execute a Rodada 7 conforme o protocolo (§0.2):
o GPT 5.6 sol xhigh implementa compilador, componentes e testes sob sua
especificação; você faz o QA visual no navegador e o byte a byte das guardas
internas; GA humano comigo contra o piloto renderizado. Relate em
.tmp/vocacoes-pne/rodada-07/. Não inicie a rodada seguinte.
```

## Rodada 8 — Validação do piloto (Etapa 11)

Dossiê do piloto, validação numérica/metodológica/editorial, comparação
antes/depois, **GA humano como teste de usuário** (mantenedor; gestora quando
possível) com as tarefas da Etapa 11.5.

Saída: Gate 11 aprovado.

```text
Leia docs/PLANO_IMPLEMENTACAO_VOCACOES_PNE.md (§0, Etapa 11) e o relatório da
rodada anterior. Execute a Rodada 8 conforme o protocolo (§0.2): auditoria
numérica e editorial suas, correções pelo GPT 5.6 sol xhigh, GA humano comigo
com as tarefas da Etapa 11.5. Relate em .tmp/vocacoes-pne/rodada-08/. Não
inicie a rodada seguinte.
```

## Rodada 9 — Transferência e escala (Etapas 12 e 13)

Transferência para duas regiões contrastantes (candidatas: VRP e Noroeste, que
têm cenários publicados — confirmar contraste e cobertura), sem ajuste manual
por região; depois a fila de publicação, lotes, manifesto, rollback e push
final. Uma região sem mínimo permanece na rota antiga, sem mensagem pública.

Saída: Gates 12 e 13 aprovados; documento de entrega à gestão (redigido pelo
Fable) mapeando as duas perguntas ao que está no ar.

```text
Leia docs/PLANO_IMPLEMENTACAO_VOCACOES_PNE.md (§0, Etapas 12 e 13, §10) e o
relatório da rodada anterior. Execute a Rodada 9 conforme o protocolo (§0.2):
transferência nas duas regiões contrastantes primeiro, GA humano comigo por
lote de publicação, manifesto e rollback, documento de entrega à gestão
redigido por você, push final. Relate em .tmp/vocacoes-pne/rodada-09/. Este é
o encerramento do plano.
```

---

# 10. Definição de pronto

A frente Vocações × PNE estará pronta para expansão quando:

- as duas saídas solicitadas pela gestora estiverem claramente visíveis;
- o Vale do Sinos tiver ao menos três leituras da primeira saída e duas da segunda;
- as leituras combinarem educação, território e tempo;
- cada cartão produzir um insight e uma questão concreta de planejamento;
- não houver correlação, força, grau de evidência ou mensagens de insuficiência na interface;
- não houver cartões automáticos sem mecanismo;
- não houver duplicações;
- não houver textos genéricos;
- a demografia estiver separada da trajetória antes de outros cruzamentos;
- EJA utilizar público potencial adequado;
- educação profissional utilizar ocupações e composição da oferta, e não apenas total setorial;
- as diferenças municipais estiverem incorporadas;
- todas as frases forem reconstruíveis;
- a metodologia funcionar em regiões contrastantes;
- a publicação possuir rollback, manifesto e testes.

---

# 11. Instrução final ao Fable

O Fable deverá tratar este plano como um **programa de reconstrução de produto**, e não como uma rodada de adição de novos gráficos.

A prioridade é:

1. corrigir a lógica de seleção;
2. enriquecer os dados que realmente mudam a interpretação;
3. reconstruir as duas saídas;
4. traduzir a análise para linguagem pública;
5. validar no Vale do Sinos;
6. testar a transferência;
7. escalar.

O Fable não deverá:

- preservar a atual quantidade de cartões como requisito;
- procurar correlações mais altas para preencher a página;
- publicar mensagens sobre relações fracas ou não mensuradas;
- expor graus internos;
- transformar indisponibilidade em conteúdo;
- criar recomendações genéricas;
- avançar para todas as regiões antes do piloto;
- incluir uma nova fonte sem demonstrar o ganho;
- escrever manualmente conclusões sem fatos estruturados.

O Fable deverá buscar uma página menor, mais clara e mais útil, em que cada bloco responda diretamente a uma das perguntas da gestão e ajude o usuário a compreender uma decisão real de planejamento educacional.
