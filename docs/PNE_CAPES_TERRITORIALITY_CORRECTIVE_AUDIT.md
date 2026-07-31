# Auditoria corretiva CAPES — territorialidade de titulados em rede

## Decisão

O P0 `P0-CAPES-JAGUARI` foi classificado como defeito de reconciliação e
materialização, não como transferência nominal de títulos. O arquivo de
programas registra a sede da instituição principal. O arquivo de discentes
registra a IES à qual cada discente está vinculado no programa e o município
dessa IES. Em programa em rede, esses municípios podem divergir legitimamente.

O código `30004012074P8` é um mestrado profissional em rede:

- a instituição principal é o IFES, com sede do programa em Vitória/ES;
- o IFFarroupilha consta na lista oficial de IES associadas;
- as 79 linhas de Jaguari/RS identificam o IFFarroupilha como IES vinculada;
- 24 dessas linhas têm situação `TITULADO` e data de situação em 2024.

Vitória/ES permanece apenas como metadado de origem da instituição principal.
Não integra o universo municipal, não gera arquivo ou resultado público e não
é usada para completar a lista gaúcha. A saída normalizada contém somente os
497 códigos IBGE do Rio Grande do Sul.

## Evidência oficial e significado dos campos

Foram auditados os quatro snapshots preservados em
`data_pipeline/data/pne_macro_sources/capes_2024/raw`.

| Fonte | SHA-256 | Definição oficial relevante |
| --- | --- | --- |
| Programas 2024 | `9402aec8b2bfbf1d0b4d690511ba86f477f649e6f56f477ff747119a7dc67476` | `NM_MUNICIPIO_PROGRAMA_IES` é o município sede do programa. |
| Metadados de programas | `5ad3d2c23c8d71bb352a4efb122d636ed7a600aebf13b4cc43d5be8af0ca5db5` | Em programa em rede, `NM_ENTIDADE_ENSINO` representa a instituição principal e `SG_ENTIDADE_ENSINO_REDE` informa as IES associadas. |
| Discentes 2024 | `b37737e9e9552f51ab8aaeb4fe53f281a95c1078e4ad295cbeb5c2561c65b566` | Cada linha identifica a IES e o município aos quais o discente está vinculado no programa. |
| Metadados de discentes | `e1c28ec0ac28f65a52917077bdf258af1ebf1d03f59eba8fa78de3a472e522f2` | `NM_MUNICIPIO_PROGRAMA_IES` é o município da IES à qual o discente está vinculado no programa. |

Significados homologados:

- município do programa, no arquivo de programas: sede do programa;
- município no arquivo de discentes: município da IES à qual o discente está
  vinculado no programa;
- programa em rede: programa para o qual `IN_REDE` informa `SIM`;
- instituição coordenadora/principal: `NM_ENTIDADE_ENSINO` no arquivo de
  programas;
- instituição participante: IES de `SG_ENTIDADE_ENSINO_REDE` que coincide com
  `SG_ENTIDADE_ENSINO` no registro do discente;
- oferta associada: vínculo observado entre programa em rede, IES participante
  e discente no município da IES;
- situação do discente: estado de suas atividades, incluindo `MATRICULADO`,
  `TITULADO`, desligamento, abandono e mudança de nível;
- ano de titulação: ano de `DT_SITUACAO_DISCENTE` quando
  `NM_SITUACAO_DISCENTE` é `TITULADO`.

O município não representa residência do titulado.

## Regra territorial final

1. O universo de saída é a lista canônica dos 497 códigos IBGE do RS.
2. Um programa com sede em município do RS confirma oferta local.
3. Um programa confirma oferta em outro município do RS quando há discente
   vinculado a uma IES desse município e, em caso de divergência com a sede, o
   programa é oficialmente em rede e a IES consta como principal ou associada.
4. Divergência sem `IN_REDE=SIM` ou sem vínculo da IES participante invalida a
   carga; não há fallback por nome de município.
5. Os títulos são contados uma única vez no município da IES vinculada ao
   discente. A sede externa da instituição principal permanece só como
   proveniência.

Não existe condição nominal para Jaguari no código.

## Reconciliação dos programas divergentes

Todos os 29 pares divergentes, pertencentes a 15 códigos, passaram pelas mesmas
guardas de rede e associação oficial.

| programCode | Sede no arquivo de programas | Município/IES no arquivo de discentes | Modalidade/grau | Instituição principal | IES participante | Linhas | Matriculados | Mestres | Doutores | Decisão |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `30004012074P8` | VITÓRIA/ES | BENTO GONÇALVES/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | IFES | IFRS | 63 | 36 | 21 | 0 | IES participante vinculada |
| `30004012074P8` | VITÓRIA/ES | JAGUARI/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | IFES | IFFARROUPILHA | 79 | 52 | 24 | 0 | IES participante vinculada |
| `30004012074P8` | VITÓRIA/ES | PELOTAS/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | IFES | IFSUL | 65 | 44 | 20 | 0 | IES participante vinculada |
| `31001017155P1` | RIO DE JANEIRO/RJ | PORTO ALEGRE/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | UFRJ | UFRGS | 59 | 46 | 12 | 0 | IES participante vinculada |
| `31001017155P1` | RIO DE JANEIRO/RJ | SANTA MARIA/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | UFRJ | UFSM | 32 | 23 | 7 | 0 | IES participante vinculada |
| `31001017169P2` | RIO DE JANEIRO/RJ | PORTO ALEGRE/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | UFRJ | UFRGS | 29 | 25 | 0 | 0 | IES participante vinculada |
| `31075010001P2` | RIO DE JANEIRO/RJ | CAÇAPAVA DO SUL/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | SBM | UNIPAMPA-CAÇAPAVA DO SUL | 6 | 2 | 0 | 0 | IES participante vinculada |
| `31075010001P2` | RIO DE JANEIRO/RJ | CANOAS/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | SBM | IFRS-CANOAS | 41 | 24 | 8 | 0 | IES participante vinculada |
| `31075010001P2` | RIO DE JANEIRO/RJ | RIO GRANDE/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | SBM | FURG | 9 | 7 | 0 | 0 | IES participante vinculada |
| `31075010001P2` | RIO DE JANEIRO/RJ | SANTA MARIA/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | SBM | UFSM | 25 | 7 | 7 | 0 | IES participante vinculada |
| `31102000001P6` | MACEIÓ/AL | BENTO GONÇALVES/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | UFAL | IFRS | 42 | 35 | 6 | 0 | IES participante vinculada |
| `33004013069P2` | ILHA SOLTEIRA/SP | PORTO ALEGRE/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | UNESP-ILHA SOLTEIRA | UFRGS | 28 | 19 | 6 | 0 | IES participante vinculada |
| `33004137068P8` | PRESIDENTE PRUDENTE/SP | IJUÍ/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | UNESP-PRESIDENTE PRUDENTE | UNIJUÍ | 9 | 8 | 0 | 0 | IES participante vinculada |
| `33147019001P2` | SÃO PAULO/SP | PELOTAS/RS | ACADÊMICO / MESTRADO/DOUTORADO | SBFIS | UFPEL | 19 | 16 | 2 | 0 | IES participante vinculada |
| `33147019001P2` | SÃO PAULO/SP | URUGUAIANA/RS | ACADÊMICO / MESTRADO/DOUTORADO | SBFIS | UNIPAMPA | 30 | 23 | 4 | 1 | IES participante vinculada |
| `33283010001P5` | SÃO PAULO/SP | RIO GRANDE/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | SBF | FURG | 12 | 7 | 4 | 0 | IES participante vinculada |
| `33283010001P5` | SÃO PAULO/SP | TRAMANDAÍ/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | SBF | UFRGS-LITORAL NORTE | 25 | 17 | 6 | 0 | IES participante vinculada |
| `33303002001P9` | RIO DE JANEIRO/RJ | PELOTAS/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | ABRASCO | UFPEL | 20 | 11 | 9 | 0 | IES participante vinculada |
| `33303002001P9` | RIO DE JANEIRO/RJ | PORTO ALEGRE/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | ABRASCO | UFCSPA; UFRGS | 33 | 22 | 11 | 0 | IES participante vinculada |
| `40001016170P6` | CURITIBA/PR | PORTO ALEGRE/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | UFPR | UFRGS | 19 | 19 | 0 | 0 | IES participante vinculada |
| `42001013098P9` | PORTO ALEGRE/RS | RIO GRANDE/RS | ACADÊMICO / MESTRADO/DOUTORADO | UFRGS | FURG | 1 | 0 | 0 | 0 | IES participante vinculada |
| `42001013098P9` | PORTO ALEGRE/RS | SANTA MARIA/RS | ACADÊMICO / MESTRADO/DOUTORADO | UFRGS | UFSM | 97 | 77 | 6 | 10 | IES participante vinculada |
| `42001013098P9` | PORTO ALEGRE/RS | URUGUAIANA/RS | ACADÊMICO / MESTRADO/DOUTORADO | UFRGS | UNIPAMPA | 114 | 83 | 16 | 15 | IES participante vinculada |
| `42001013102P6` | FLORIANÓPOLIS/SC | PORTO ALEGRE/RS | ACADÊMICO / MESTRADO/DOUTORADO | UFSC | UFRGS | 28 | 21 | 3 | 3 | IES participante vinculada |
| `42037018003P1` | CRUZ ALTA/RS | ERECHIM/RS | ACADÊMICO / MESTRADO/DOUTORADO | UNICRUZ | URI | 8 | 6 | 2 | 0 | IES participante vinculada |
| `42037018003P1` | CRUZ ALTA/RS | IJUÍ/RS | ACADÊMICO / MESTRADO/DOUTORADO | UNICRUZ | UNIJUÍ | 47 | 28 | 16 | 0 | IES participante vinculada |
| `53045009001P3` | BRASÍLIA/DF | BAGÉ/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | ANDIFES | UNIPAMPA | 8 | 7 | 0 | 0 | IES participante vinculada |
| `53045009001P3` | BRASÍLIA/DF | PELOTAS/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | ANDIFES | UFPEL | 45 | 29 | 13 | 0 | IES participante vinculada |
| `53045009001P3` | BRASÍLIA/DF | RIO GRANDE/RS | PROFISSIONAL / MESTRADO PROFISSIONAL | ANDIFES | FURG | 25 | 13 | 9 | 0 | IES participante vinculada |

A tabela completa dos 497 municípios, com programas de sede, programas
vinculados, linhas de discentes, mestres, doutores, estado/valor anterior,
estado/valor corrigido e razão da decisão está em
`data_pipeline/data/pne_macro_sources/capes_2024/manifest.json`, no campo
`audit.municipalReconciliation`.

## Matriz de publicação

| Situação | Resultado |
| --- | --- |
| Mestres + doutores maior que zero, territorialidade homologada | `available`, valor igual à soma; `localProgramCount` não pode anular o resultado. |
| Oferta local confirmada e zero títulos, com cobertura completa | `available`, valor zero. |
| Nenhuma sede/oferta vinculada e nenhuma linha de discente | `not_applicable`, sem card público. |
| Cobertura incompleta ou territorialidade inconclusiva | `unavailable`, nunca zero e nunca `not_applicable` por falta de sede. |
| Supressão indicada pela fonte | `suppressed`, sem reconstrução. |

O normalizador registra cobertura completa e territorialidade homologada para
este snapshot. Não há valor suprimido na fonte de discentes usada.

## Contagens e integridade

- 497 municípios canônicos, todos com código IBGE iniciado por `43`;
- 34 municípios com sede de programa;
- 35 municípios com IES vinculada a discentes;
- 35 municípios com oferta local reconciliada;
- 35 municípios com títulos observados;
- 425 programas-sede municipais e 454 vínculos municipais reconciliados;
- 5.227 títulos de mestrado e 2.456 de doutorado;
- 7.683 chaves únicas de título e zero duplicidade;
- soma municipal igual a 7.683, sem título contado em dois municípios.

A referência estadual é tecnicamente aditiva neste snapshot porque a chave
global pessoa + programa + grau + data é única e cada linha possui um único
município de IES vinculada. A relação continua com
`stateReferencePolicy=none`; nenhum total estadual ou comparação foi
acrescentado à interface.

## Contrato e política

A correção mantém a fórmula já declarada e passa a conciliar corretamente os
dois arquivos usados por ela. Assim:

- contrato: versão `1.6.0`, hash
  `758438f2d1c508800b29a8db991d25ec0a18ec9cf63bab8a5a4df349d80e30a6`;
- política: versão `1.4.0`, hash
  `57a59d6b7284728074812e0555392bccd1169404d0c7f9eb94d345d2b6285fa8`;
- relação: `complementary`, sem meta municipal, distância, status,
  classificação, projeção ou referência estadual.

## Staging e paridade

Os lotes completos são:

- `C:\tmp\pne-diagnostic-v3-staging-capes-fix-final-a`;
- `C:\tmp\pne-diagnostic-v3-staging-capes-fix-final-b`.

Cada lote contém 497 arquivos municipais e um manifesto. A auditoria de diff
contra a release `818635eaa0c9004d1597252589170e529d6d087d17bc1d28a75db1700945838a`
encontrou mudança apenas em
`relation.16.a.capes_titulados_oferta_local`: 34 leituras territoriais
reconciliadas e o novo resultado observado de Jaguari. Somente o resumo de
Jaguari mudou; todas as outras relações permaneceram idênticas.

Os 498 arquivos dos dois lotes são idênticos byte a byte. O SHA-256 do
manifesto de staging é
`92eef3984f7df4638a2e55d7a5bd4a3afabf40d2648d9be8581ce79c12ea7628`;
o `generationHash` é
`cebc9af2f51cfc779598a930e9ead348cd7463cc8d186b156c89bba4e4d88131`
e o hash semântico é
`575bade9388b72b87a85606fe0eb6d4f26d396e2c90c37a0ce8dfb97ac4b1b3b`.

## Reauditoria após promoção

A promoção foi feita exclusivamente por
`data_pipeline/scripts/promote_pne2026_public_diagnostic_v3.py`. A release
ativa é:

- release/`aggregateHash`:
  `cebc9af2f51cfc779598a930e9ead348cd7463cc8d186b156c89bba4e4d88131`;
- hash semântico:
  `575bade9388b72b87a85606fe0eb6d4f26d396e2c90c37a0ce8dfb97ac4b1b3b`;
- SHA-256 do manifesto da release:
  `bab4f13867b69efe2c87c7603143f3a7aa48a7d89b8fb17ce75d29a7275e066a`;
- SHA-256 de `current.json`:
  `ce8198816a3203d04035e427cb028569dc27cff5cd3f21551a84a80135e92d13`;
- SHA-256 do snapshot CAPES normalizado:
  `1211982c91a501ea79fb70b00e192e633ed01f0518fbe9a9eb6dc8e6b5ea80b7`;
- SHA-256 do manifesto do snapshot CAPES:
  `f183c2219d7378480c98bc0fd5b96d98ba76e12d43890b77bcec7461c9adbf24`.

A release contém 497 municípios e 17.273 resultados. São 10.155 resultados
`progress`, 7.118 `complementary`, 4.466 `essential` e 12.807 `standard`;
não há código fora do prefixo IBGE `43`, duplicidade, órfão, `NaN` ou
`Infinity`. Os 497 arquivos municipais publicados são idênticos byte a byte
aos do staging aprovado; o manifesto publicado apenas aplica o envelope da
release.

No painel de Jaguari, a inspeção confirmou o resultado 24 e a leitura
“em programas em rede, a territorialidade é a da IES à qual o discente está
vinculado”. O card permanece complementar e neutro, sem meta municipal,
distância, status, projeção ou referência estadual. Não houve overflow
horizontal em 1280 × 720 ou 390 × 844, não houve erro de console, e a mídia de
impressão A4 passou no teste dedicado.

As suítes Python, unitária, educacional, de contrato/geração, de promoção, de
interface macro, `lint`, `build` e `git diff --check` passaram. O único aviso
do lint já existia em `src/features/education/EducationPage.tsx` e não pertence
ao escopo. O P0 está resolvido; fontes sem territorialidade municipal
homologada permanecem bloqueadas. Não houve commit nem push.
