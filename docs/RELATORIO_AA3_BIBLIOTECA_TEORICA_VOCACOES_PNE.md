# Relatório AA3 — Biblioteca teórica, mecanismos e tetos de afirmação

## Resposta executiva

O AA3 transforma a literatura local congelada em um contrato verificável de interpretação para as oito perguntas do AA2. A principal conclusão é que a teoria disponível **não sustenta ampliar indistintamente as afirmações da página**: quatro perguntas possuem apoio oficial ou acadêmico direto para mecanismos gerais, uma pergunta é uma identidade contábil que dispensa referência de mecanismo e três perguntas permanecem com lacuna primária direta e teto reduzido.

O ganho para o produto não é acrescentar causalidade onde ela não foi identificada. É permitir que a página explique, para cada relação:

1. qual mecanismo geral torna a leitura plausível;
2. qual padrão seria esperado nos dados;
3. quais variáveis locais foram efetivamente confrontadas;
4. quais explicações alternativas permanecem abertas;
5. qual evidência enfraqueceria a hipótese;
6. o que a plataforma pode e não pode afirmar para Nova Santa Rita e para o Vale do Sinos.

O primeiro parecer Opus foi `AT_RISK` (confiança 0,72). As seis recomendações válidas foram aceitas e aplicadas. A reauditoria do checkpoint corrigido retornou `ON_TRACK` (confiança 0,78), sem lacuna material alta ou média. A recomendação residual de acrescentar evidência vinculada ao manifesto foi aplicada; o pacote final está em `AA3_COMPLETE_OPUS_REAUDIT_ON_TRACK` e autoriza a abertura controlada do AA4.

## Escopo e classificação

- classificação: `DATA_LOGIC`;
- estado: Rio Grande do Sul;
- região: Vale do Sinos;
- município selecionado: Nova Santa Rita, código IBGE textual `4313375`;
- escopo educacional: `total_all_dependencies`;
- pesquisa externa nova: não autorizada e não realizada;
- literatura utilizada: somente referências locais previamente congeladas;
- efeito local criado pela literatura: não;
- número externo promovido como estimativa municipal: não;
- alteração de fórmula, indicador ou resultado AA2: não.

## Decisão por pergunta

| Pergunta | Estado AA2 preservado | Cobertura teórica AA3 | Teto efetivo para AA4 | Papel editorial |
|---|---|---|---|---|
| P1 — contexto e trajetória | `CONTEXT_COMPARISON_COMPLETE` | apoio oficial com transferência estrita | comparação contextual, sem afirmar tipicidade | núcleo do dossiê 1 |
| P2 — demografia e matrículas | `ACCOUNTING_DECOMPOSITION_COMPLETE` | identidade contábil; referência de mecanismo não exigida | decomposição contábil apenas | núcleo do dossiê 2 |
| P3 — condições escolares e trajetória | `NO_ROBUST_ASSOCIATION` | lacuna primária direta | fronteira interpretativa, sem associação robusta | limite do dossiê 1 |
| P4 — trabalho juvenil e ensino médio | `NO_ROBUST_ASSOCIATION` | duas referências gerais com transferência estrita | sem associação robusta; literatura sustenta somente a pergunta de monitoramento | limite e agenda do dossiê 3 |
| P5 — ocupações e EPT | `DISTRIBUTIONAL_PATTERN_COMPLETE` | uma referência geral e ponte normativa local | correspondência nomenclatural descritiva, somente CBO de dois dígitos | núcleo do dossiê 4 |
| P6 — escolaridade adulta, trabalho e EJA | `NO_ROBUST_ASSOCIATION` | uma referência geral com transferência estrita | sem associação robusta; somente distribuições descritivas | núcleo com limite do dossiê 5 |
| P7 — ruralidade, inclusão e acesso | `NO_ROBUST_ASSOCIATION` | lacuna primária direta | fronteira interpretativa, sem associação robusta | camada transversal opcional |
| P8 — financiamento, oferta e capacidade | `INSUFFICIENT_DATA` | lacuna primária direta | não sustentado ou indisponível | somente técnico; bloqueado da página gerencial |

## Relações com apoio teórico limitado

### P1 — contexto mensurável e trajetória

A Nota Técnica do INEP sobre o INSE sustenta que nível socioeconômico é uma dimensão oficial de contexto educacional observável. Ela não valida o modelo AA2, não mede contribuição isolada da família ou da escola e não torna Nova Santa Rita um caso típico.

O AA2 permanece soberano: o modelo completo não melhorou o RMSE do baseline e o resíduo municipal ficou dentro de banda ampla. A leitura permitida é uma comparação qualificada pela incerteza; “não sinalizado” não equivale a “típico”.

### P4 — estudo e trabalho juvenil

O artigo nacional sobre juventude, educação e trabalho sustenta que estudo e trabalho coexistem de forma heterogênea. A nota do Ipea sustenta que aprendizagem profissional é vínculo regulado e diferente de emprego jovem genérico.

Essas referências justificam formular uma pergunta de monitoramento intersetorial, mas não ligam as mesmas pessoas entre RAIS e registros educacionais, não medem informalidade e não criam efeito municipal. O AA2 terminou em `NO_ROBUST_ASSOCIATION` (`P4_MAIN_L0`, efeito 0,0211; BH 0,8887; regra não satisfeita). Esse continua sendo o resultado empírico primário: não existe “sinal local” resgatado pela literatura.

### P5 — EPT e famílias ocupacionais

A referência sobre permanência e abandono na EPT sustenta que condições escolares e de trabalho podem integrar o mecanismo geral. A relação local, porém, deriva da ponte normativa CNCT–CBO congelada, no subgrupo CBO de dois dígitos.

A afirmação permitida é nomenclatural e descritiva: como matrículas técnicas observadas e famílias ocupacionais se organizam numa correspondência normativa reproduzível no CBO de dois dígitos. Estão proibidas inferências de demanda futura, empregabilidade, suficiência, qualidade, ingresso, conclusão, validação da ponte ou trajetória de egressos.

### P6 — EJA, escolaridade adulta e trabalho

A referência de EJA sustenta mecanismos gerais ligados a trabalho, retorno à escolarização e motivações sociais. Ela não estima demanda, cobertura ou barreira municipal.

Como o AA2 não encontrou associação robusta e trabalha com apenas dez municípios nas comparações principais, a página poderá mostrar apenas distribuições e estimativas descritivas já registradas em `P6_EJA_SPEARMAN` e `P6_WORK_SPEARMAN`. `stablePrimaryFit` permanece nulo. A literatura não cria padrão local; população residente, localização da escola e estabelecimento de trabalho continuam universos distintos.

## Relação que dispensa referência de mecanismo

### P2 — decomposição de matrículas

P2 é uma identidade matemática: a mudança total de matrículas fecha como soma do componente populacional e do componente residual da relação territorial matrícula/população. Sua validade depende da fórmula e das séries locais, não da transferência de um efeito acadêmico externo.

O componente residual não é comportamento. Ele pode absorver mobilidade, organização da oferta, cobertura, mudança de registro e revisão ou rebase populacional. A razão entre matrícula por local da escola e população residente não é taxa de cobertura nem frequência; a decomposição também não é previsão.

## Reconciliação dos sete mecanismos com oito perguntas

Os sete mecanismos Job5L não são convertidos um a um em oito “mecanismos novos”. O AA3 publica quatro registros do tipo `THEORY_MECHANISM`, uma `ACCOUNTING_IDENTITY` e três `INTERPRETATION_BOUNDARY`.

- `M1_CONTEXT_AND_TRAJECTORY` → P1;
- `M2_STUDY_AND_WORK` + `M3_APPRENTICESHIP` → P4;
- `M4_EPT_AND_WORK` → P5;
- `M6_EJA_PARTICIPATION` → P6;
- `M5_MIGRATION_AND_SCHOOL_FLOW` e `M7_EDUCATIONAL_COMMUTING` permanecem preservados sem uso;
- P2 não recebe mecanismo teórico porque é identidade contábil;
- P3, P7 e P8 são registros de fronteira, não mecanismos teóricos adicionados por prosa.

## Lacunas que reduzem o teto

### P3 — condições escolares

Não há, na biblioteca local congelada, referência primária diretamente adequada ao mecanismo específico testado. O resultado AA2 é `NO_ROBUST_ASSOCIATION`. O AA4 poderá informar o limite e as hipóteses não testadas, mas não construir explicação positiva por analogia.

### P7 — ruralidade, AEE e acesso

As referências locais sobre deslocamento foram mantidas, mas não reaproveitadas: elas não sustentam diretamente o mecanismo agregado de contagem de escolas/serviços e matrículas testado em P7. O p rural bruto foi 0,039 e o BH familiar conservador foi 0,117; isso deve ser apresentado como instabilidade após o ajuste, não como presença ou ausência definitiva de relação.

Contagem de escola ou serviço não mede distância, capacidade, transporte, suficiência ou qualidade. Esses são dados adicionais necessários para avançar.

### P8 — financiamento e oferta

P8 continua `INSUFFICIENT_DATA`. Valores nominais não permitem comparação entre anos; financiamento e oferta são determinados conjuntamente; a alternativa por matrícula compartilha o denominador com o desfecho e não é evidência independente. Sem referência direta congelada e sem resultado empírico válido, toda promoção gerencial fica bloqueada.

## Referências congeladas e uso

Foram preservadas oito referências. Cinco sustentam atribuições limitadas nas perguntas atuais:

- `LIT_INEP_INSE_2023` — P1, medição oficial de contexto;
- `LIT_JUVENTUDE_EDUCACAO_TRABALHO_2012_2022` — P4, coexistência geral entre estudo e trabalho;
- `LIT_APRENDIZAGEM_IPEA` — P4, distinção institucional da aprendizagem;
- `LIT_EPT_PERMANENCIA_ABANDONO` — P5, mecanismo geral de permanência na EPT;
- `LIT_EJA_REPRESENTACOES_PRATICAS` — P6, mecanismos gerais de participação em EJA.

Três foram mantidas explicitamente como não usadas nas oito perguntas atuais:

- `LIT_MIGRACAO_FLUXO_ESCOLAR`;
- `LIT_DESLOCAMENTO_ESCOLA_ADOLESCENTES`;
- `LIT_IBGE_CENSO_DESLOCAMENTOS_2022`.

A não utilização é deliberada: referência adjacente não foi tratada como apoio direto para preencher lacuna.
No artefato, as três recebem `NOT_USABLE_FOR_P3_P7_P8`; o AA4 deve falhar se tentar vinculá-las a essas lacunas.

## Regras globais para a narrativa

1. Literatura nunca altera estado terminal, significância, robustez ou disponibilidade do AA2.
2. Número de estudo externo nunca vira estimativa para Nova Santa Rita ou Vale do Sinos.
3. Lacuna de referência reduz o teto; prosa genérica não a preenche.
4. Compatibilidade teórica ou associação territorial não identifica causalidade.
5. Residência, localização da escola e estabelecimento de trabalho permanecem lentes distintas.
6. Resultados negativos precisam mostrar potência, multiplicidade e alternativas; não são “prova de ausência”.
7. P8 permanece bloqueado para leitura gerencial.
8. P4 e P6 permanecem `NO_ROBUST_ASSOCIATION`; teoria sustenta a pergunta, não um sinal local.
9. A ponte P5 é nomenclatural, descritiva e limitada ao CBO de dois dígitos.

## Sentinela de `public/data` e publicações paralelas

Durante o primeiro gate AA3, uma materialização regional paralela e pertencente ao trabalho já existente alterou onze arquivos em `public/data/regioes`. O AA3 falhou fechado e não produziu pacote.

Após duas verificações consecutivas idênticas, o contrato AA3 registrou o primeiro evento:

- digest histórico do AA2, preservado: `4a52e3891163cb3427c5c01f2ef5414c5fe7855dd491a9a125b509899dcc23e1`;
- primeiro digest estável observado: `aa8927c11efccf220b66e3770f35bd449931b96ace8dbc8e999707818a5b9d35`;
- impacto sobre insumos analíticos AA3: nenhum; AA3 lê os artefatos AA2 e a literatura local congelada;
- arquivos públicos editados ou regenerados pelo AA3: nenhum.

Depois do primeiro parecer Opus, uma segunda publicação externa materializou `public/data/pne2026-matriz`: 497 arquivos municipais, manifesto `pne2026-matriz-manifest-v3`, gerador v5, último horário de escrita `2026-08-30T21:35:50Z`. O AA3 não executou esse gerador nem editou a coleção.

Por isso, o gate corrigido não trata um digest global volátil como insumo analítico. Ele exige `PUBLIC_DATA_NOT_WRITTEN_BY_AA3_INVARIANT_WITHIN_AND_EQUAL_ACROSS_TWO_CANDIDATE_MATERIALIZATIONS`. Os processos 303 e 404 observaram, antes e depois, o mesmo digest `7efdf16f57a8e8da0c26fd27daa8e1331a427fa4376d8929c568ff471a0dafdd`. O AA4 deverá capturar um novo baseline de entrada explícito quando as publicações concorrentes tiverem cessado; rebaseline automático está proibido.

## Artefatos materializados

Raiz temporária: `.tmp/vocacoes-pne/advanced-analytics-v1/aa3`.

| Artefato | Bytes | SHA-256 |
|---|---:|---|
| `BIBLIOTECA_MECANISMOS_AA3.json` | 36.460 | `99e0177a71cc146c56331f79d1c72c82475524f8d87fc22cb0d889766fdf68b4` |
| `MATRIZ_COBERTURA_TEORICA_AA3.csv.gz` | 2.165 | `6adc2ed6b896e52f26b5b43762d840191235d6d658fed2a30cb4261d3482a2be` |
| `FRONTEIRAS_INTERPRETACAO_AA3.json` | 16.788 | `d8215995707c02e7e7324a2104819dc2142f5cf632eff5ef9b0806d09f3c1480` |
| `EVIDENCIAS_COMPLEMENTARES_AA3.json` | 18.287 | `03e8c0536b6f35a86daa3bd6c786d233c7e8381cf58969aa2a5d60ed48016f42` |
| `QA_SUMMARY_AA3.json` | 12.779 | `943424155b2773f6188c4c7520568e09c68a05c41f2f42626aabb1cd828140d1` |
| `MANIFEST_AA3.json` | 9.072 | `121eb0e0878f49dcde1c2c56e422fce27f4c96eaac889ad4c2a172282dba77ac` |

- digest do conjunto analítico não manifesto: `8fa9ed8d365873b2074b84ca49ca8fa0b6be9615b2d85771760fb3fb7ec5d464`;
- digest da árvore final de ambos os candidatos: `f7cc79e7bf4d7d85c175653e0032fda17018ea3d3bfab2aa2637511c536121e5`;
- implementação usada nos dois processos: `e00561393bb30b457246138d9d85e931ae7a066e5cce640f89bee2ecf1263a5a`;
- seeds: `303` e `404`;
- igualdade: `VERIFIED_IDENTICAL`.

O apêndice complementar é um artefato ordinário do conjunto não manifesto e, portanto, seu hash está vinculado pelo manifesto. Ele registra 11 vínculos de entrada, 8 pares de teto AA2–AA3 com papel no AA4, 9 decisões de reconciliação cruzadas com as revisões A–G, 4 amostras técnicas de explicações alternativas/refutação, escopo dos digests públicos e o caminho de staging, validação, promoção atômica e rollback.

Antes da normalização, os dois candidatos tiveram o mesmo conjunto não manifesto (`a0c124111ee3c03168ff020b177adf278fecd4708ff1d4c228aec578664433ce`), mas manifestos e árvores distintos porque cada um registrava seu seed. O apêndice preserva os dois pares de digests. Depois de normalizar `artifacts`, `artifactSetDigestSha256`, seeds e evidência dos processos, a árvore completa foi comparada e ficou idêntica. O digest final aparece no recibo externo do processo pai para evitar autorreferência dentro da própria árvore hasheada.

## Contagens e QA

- perguntas: 8;
- referências: 8;
- referências usadas: 5;
- referências não usadas e preservadas: 3;
- linhas da matriz pergunta–referência/lacuna: 9;
- perguntas com apoio e transferência limitada: 4;
- identidades que dispensam referência de mecanismo: 1;
- lacunas primárias diretas: 3;
- autorizações para teoria substituir estado AA2: 0;
- relações bloqueadas da leitura gerencial: 1;
- mecanismos congelados de origem: 7;
- registros de mecanismo teórico: 4;
- identidades contábeis: 1;
- fronteiras interpretativas: 3;
- controles de QA: 33;
- falhas de QA: 0.

## Fontes e proveniência

- resultados e estados terminais: `.tmp/vocacoes-pne/advanced-analytics-v1/aa2/CLAIMS_AA2.json`, SHA-256 `065f4f96d15591b4d239eebb5f18f0f6af0144daec47844dfae00d919fb09419`;
- manifesto AA2: SHA-256 `e626762e37843673956c0aa27bcf0bbc099ffba2661cd413859f7ce433b75b2f`;
- conjunto AA2: `b166cd6742cedb279a7c16316245e1ae08589b41c6e73b8cd3849c44fdd22879`;
- literatura congelada Job5L: SHA-256 `efa00b16995fe3be90b6d23c0a9a983c7c4c42ef6d8692a4947cd5c3706b4b18`;
- biblioteca local de mecanismos: SHA-256 `5b0edb5ad0a6cb61d4a3d6b7d6f66a801e9f8179be6ed84412c2d1e17c1a5a91`;
- diretriz analítica: SHA-256 `0cf88d3f405e5274072327b5560a34db58bfbdf0d4a88569654f52e3fe385b25`;
- ponte curso–CBO: SHA-256 `bb3d437efda4f067e1ebb4a3bb05927aaf751ce14294f4fc4800efd321ee97e0`;
- plano do programa: SHA-256 `063e44ab88c763f8563b28a826c96a10585de8b92d9dc04b0b0cc04f1c465b71`;
- reconciliação inicial Opus: SHA-256 `a61b1a0d824dcf215f927f8a37d9e1890c4208cf04f26f25ac9085d007cc7119`;
- contrato AA3: SHA-256 `cd5a468ba8889c311e13aaad4b2e9ed737016d5d9053fc7180baa4152ac2fc81`;
- reauditoria Opus: `.tmp/codex-analytics-program/aa3-opus-results-r2/opus-result.json`, SHA-256 `fea8c9d55711dcdc9326248259b6c997c370b4dead7f26a8f1408bbe247f5f67`.

## Validações executadas e encerramento

- compilação Python dos três arquivos AA3: passou;
- testes puros antes da materialização final: `12 passed, 1 deselected`;
- verificação de onze hashes/entradas congeladas: passou;
- materialização transacional em dois processos: passou;
- validação do pacote materializado: passou;
- teste do cabeçalho GZIP determinístico (`mtime=0`): passou;
- testes focados finais após o apêndice: `13 passed in 43.20s`;
- primeiro parecer Opus: `AT_RISK`, confiança 0,72;
- correções aceitas: 6; rejeições: 0; esclarecimentos: 3;
- reauditoria Opus: `ON_TRACK`, confiança 0,78, sem lacuna material alta ou média;
- recomendações residuais de apresentação: 6, todas materializadas no apêndice vinculado;
- o Opus avaliou o checkpoint anterior (`7298bb5b…`) e recomendou o apêndice; os bytes finais do apêndice foram validados localmente e não são descritos como uma terceira reauditoria;
- acesso a banco: não;
- aquisição de dados ou pesquisa na rede: não;
- chamada de rede prevista: somente a auditoria Opus autorizada pelo usuário;
- build completo: não;
- alteração manual de `public/data`: não.

## Gate para AA4

O gate AA3 passou: reauditoria registrada, recomendações reconciliadas, apêndice vinculado, 33/33 controles e pacote final validado. O AA4 está autorizado. Sua primeira ação obrigatória é capturar um baseline explícito de `public/data` após estabilização do worktree; rebaseline automático permanece proibido. P4/P6 só podem entrar com `NO_ROBUST_ASSOCIATION` e limites adjacentes, e a limitação de literatura congelada deve ser transportada integralmente.
