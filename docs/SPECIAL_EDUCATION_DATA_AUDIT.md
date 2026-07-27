# Auditoria de dados — Educação Especial e Educação Bilíngue de Surdos

## Arquitetura escolhida

Foi escolhida a alternativa B: a tabela dedicada
`censo_educacao_especial_escolas`, no grão `NU_ANO_CENSO × CO_ENTIDADE`.
Ela é produzida pelo parser autoritativo `SESI/DB/censo_escolar.py` e não
altera o contrato de `censo_escolas`. Dependência administrativa,
classificação de rede pública, localização e situação de funcionamento
continuam derivadas no SESI pelas mesmas regras usadas na tabela escolar.

A tabela conserva as chaves escolares, os códigos e rótulos normalizados das
dimensões, as variáveis temáticas, uma marca `disponivel_*` para cada campo e
uma marca `valor_extremo_*` para impedir a publicação de `88888`.

## Aquisição auditada

O diretório compartilhado `SESI/DB/data/censo_escolar` contém os CSVs anuais de
2014 a 2025 e os pacotes oficiais extraídos de 2022, 2023, 2024 e 2025. Os
pacotes de 2022–2024 incluem dicionário, CSV principal e MD5 fornecido pelo
Inep. Não havia rotina de aquisição do Censo Escolar.

Foi criado `sync_censo_escolar_microdata.py`, que usa as URLs oficiais
`https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_{ano}.zip`,
valida ZIP e leiaute, extrai em staging, preserva a fonte anterior, promove por
troca atômica, registra tamanho e SHA-256 e é idempotente.

“Local” e “após aquisição” coincidem para 2022–2024 porque os pacotes completos
oficiais já estavam recuperados; portanto, a ausência dos quantitativos de
Libras nesses três leiautes foi confirmada no CSV e no dicionário, não inferida
de uma cópia parcial.

## Matriz definitiva de disponibilidade

| Variável | Conceito | Tabela do dicionário | Anos declarados | Anos locais | Após aquisição | Decisão | Justificativa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `QT_MAT_ESP` | matrículas da Educação Especial | Cadastro/Tabela de Escola | 2014–2025 | 2014–2025 | 2014–2025 | publicar | série observada |
| `QT_MAT_ESP_CC` | matrículas em classes comuns | Cadastro/Tabela de Escola | 2014–2025 | 2014–2025 | 2014–2025 | publicar | numerador da inclusão |
| `QT_MAT_ESP_CE` | matrículas em classes exclusivas | Cadastro/Tabela de Escola | 2014–2025 | 2014–2025 | 2014–2025 | publicar | componente reconciliável |
| `QT_TUR_ESP` | turmas da Educação Especial | Cadastro/Tabela de Escola | 2014–2025 | 2014–2025 | 2014–2025 | publicar | atuações/turmas, não pessoas |
| `QT_TUR_ESP_CC` | turmas com matrículas em classes comuns | Cadastro/Tabela de Escola | 2014–2025 | 2014–2025 | 2014–2025 | publicar | componente oficial de turmas |
| `QT_TUR_ESP_CE` | turmas com matrículas em classes exclusivas | Cadastro/Tabela de Escola | 2014–2025 | 2014–2025 | 2014–2025 | publicar | componente oficial de turmas |
| `QT_DOC_BAS` | atuações docentes na educação básica | Cadastro/Tabela de Escola | 2014–2025 | 2014–2025 | 2014–2025 | publicar nas escolas elegíveis | não representa pessoas únicas |
| `QT_DOC_ESP` | atuações docentes na Educação Especial | Cadastro/Tabela de Escola | 2014–2025 | 2014–2025 | 2014–2025 | conservar | apoio de auditoria |
| `QT_DOC_ESP_CC` | atuações docentes em classes comuns | Cadastro/Tabela de Escola | 2014–2025 | 2014–2025 | 2014–2025 | publicar | componente oficial de `QT_DOC_ESP` |
| `QT_DOC_ESP_CE` | atuações docentes em classes exclusivas | Cadastro/Tabela de Escola | 2014–2025 | 2014–2025 | 2014–2025 | publicar | componente oficial de `QT_DOC_ESP` |
| `TP_AEE` | tipo de oferta de AEE | Cadastro/Tabela de Escola | 2014–2025 | 2014–2025 | 2014–2025 | publicar | `{1,2}` = oferta; `2` = exclusivo |
| `IN_SALA_ATENDIMENTO_ESPECIAL` | sala de recursos/AEE | Cadastro/Tabela de Escola | 2014–2025 | 2014–2025 | 2014–2025 | publicar | resposta binária escolar |
| `QT_MAT_ESP_INF` | matrículas especiais na educação infantil | Tabela de Escola | 2025 | 2025 | 2025 | publicar só em 2025 | ausente nos leiautes anteriores |
| `QT_MAT_ESP_INF_CRE` | matrículas especiais em creche | Tabela de Escola | 2025 | 2025 | 2025 | publicar só em 2025 | ausente antes de 2025 |
| `QT_MAT_ESP_INF_PRE` | matrículas especiais na pré-escola | Tabela de Escola | 2025 | 2025 | 2025 | publicar só em 2025 | ausente antes de 2025 |
| `QT_MAT_ESP_FUND` | matrículas especiais no fundamental | Tabela de Escola | 2025 | 2025 | 2025 | publicar só em 2025 | ausente antes de 2025 |
| `QT_MAT_ESP_FUND_AI` | matrículas especiais nos anos iniciais | Tabela de Escola | 2025 | 2025 | 2025 | publicar só em 2025 | ausente antes de 2025 |
| `QT_MAT_ESP_FUND_AF` | matrículas especiais nos anos finais | Tabela de Escola | 2025 | 2025 | 2025 | publicar só em 2025 | ausente antes de 2025 |
| `QT_MAT_ESP_MED` | matrículas especiais no ensino médio | Tabela de Escola | 2025 | 2025 | 2025 | publicar só em 2025 | ausente antes de 2025 |
| `QT_MAT_ESP_PROF` | matrículas especiais na educação profissional | Tabela de Escola | 2025 | 2025 | 2025 | publicar só em 2025 | ausente antes de 2025 |
| `QT_MAT_ESP_EJA` | matrículas especiais na EJA | Tabela de Escola | 2025 | 2025 | 2025 | publicar só em 2025 | ausente antes de 2025 |
| `QT_MAT_ESP_INT` | matrículas especiais em tempo integral | Tabela de Escola | 2025 | 2025 | 2025 | publicar só em 2025 | ausente antes de 2025 |
| `QT_TUR_ESP_INT` | turmas especiais em tempo integral | Tabela de Escola | 2025 | 2025 | 2025 | publicar só em 2025 | ausente antes de 2025 |
| `QT_MAT_BAS_LIBRAS` | matrículas em educação bilíngue de surdos | Tabela de Matrícula | 2025 | 2025 | 2025 | publicar só em 2025 | confirmado ausente em 2022–2024 |
| `QT_TUR_BAS_LIBRAS` | turmas em educação bilíngue de surdos | Tabela de Turma | 2025 | 2025 | 2025 | publicar só em 2025 | confirmado ausente em 2022–2024 |
| `QT_DOC_BAS_LIBRAS` | atuações docentes na oferta bilíngue | Tabela de Docente | 2025 | 2025 | 2025 | publicar só em 2025 | confirmado ausente em 2022–2024 |
| `QT_PROF_TRAD_LIBRAS` | atuações de tradutor/intérprete de Libras | Unidade de coleta/Tabela de Escola | 2023–2025 | 2023–2025 | 2023–2025 | publicar | contagem de atuações, não pessoas |
| `IN_MATERIAL_PED_BIL_SURDOS` | materiais para educação bilíngue de surdos | Unidade de coleta/Tabela de Escola | 2023–2025 | 2023–2025 | 2023–2025 | publicar | contagem distinta de escolas |
| `QT_DOC_BAS_GUIA_INTERPRETE` | atuações de guia-intérprete | Tabela de Docente | 2025 | 2025 | 2025 | publicar só em 2025 | campo não existia antes |
| `QT_TUR_BAS_DISC_LIBRAS` | turmas com componente curricular Libras | Tabela de Turma | 2025 | 2025 | 2025 | publicar separadamente | não é sinônimo de classe bilíngue |
| `QT_DOC_BAS_DISC_LIBRAS` | atuações docentes no componente Libras | Tabela de Docente | 2025 | 2025 | 2025 | publicar separadamente | não é sinônimo de classe bilíngue |
| `QT_DOC_BAS_ESPEC_BIL_SURDOS` | atuações docentes com especialização bilíngue | Tabela de Docente | 2025 | 2025 | 2025 | publicar só em 2025 | formação observada |
| `QT_DOC_BAS_ESPEC_GESTAO` | atuações docentes com especialização em gestão | Tabela de Docente | 2025 | 2025 | 2025 | publicar com rótulo literal | não autoriza inferir gestores únicos |

## Causa da classificação `partial`

A classificação incorreta era produzida na agregação municipal. A regra antiga
equivalia a:

1. converter a coluna escolar com `pd.to_numeric(..., errors="coerce")`;
2. somar somente os valores não nulos;
3. se qualquer linha escolar permanecesse nula, retornar
   `state="partial"` e `reason="incomplete_school_aggregation"`;
4. a razão recebia componentes `partial` e retornava valor nulo com
   `reason="unresolved_component"`.

Em São Leopoldo, a escola `43343058` exemplifica a causa em 2025. A linha oficial
está presente e ativa, `TP_AEE=0` e
`IN_SALA_ATENDIMENTO_ESPECIAL=0`, mas os campos `QT_MAT_ESP`,
`QT_MAT_ESP_CC`, `QT_MAT_ESP_CE`, `QT_TUR_ESP`,
`QT_TUR_ESP_CC`, `QT_TUR_ESP_CE` e `QT_DOC_ESP` estão vazios.
Esses vazios representam ausência de ocorrência, não perda da linha escolar.
Em 2022, as escolas `43139140` e `43343058` apresentam o mesmo padrão; a escola
`43226809` tem matrícula e turma observadas, mas `QT_DOC_ESP` vazio.

O parser usa `sep=";"`, `encoding="latin1"` e os `na_values` padrão do pandas.
Não houve mudança local de separador, encoding ou lista de NA. A mudança está no
preenchimento oficial: em São Leopoldo, 2021 contém 50 zeros explícitos em
`QT_MAT_ESP` e nenhum nulo; em 2022 há 29 zeros explícitos e dois vazios; em
2025 há 13 zeros explícitos e um vazio. As somas observadas continuam
reconciliando.

## Regra corrigida

- O parser só converte vazio em zero para campos quantitativos `QT_*` que
  existem no leiaute anual.
- Cada conversão conserva `vazio_estrutural_<campo>=true`; coluna ausente no
  leiaute continua indisponível.
- Valores não numéricos inesperados causam erro, em vez de serem silenciosamente
  transformados em zero.
- `88888` continua nulo, com `valor_extremo_<campo>=true`, e afeta somente a
  métrica correspondente.
- A materialização aceita como zero apenas o vazio com marcador estrutural.
  Nulo sem marcador permanece `partial`.
- Cada ponto quantitativo expõe `observedSchools` e `missingSchools`.
- Para a proporção de AEE, o universo elegível é `QT_MAT_ESP > 0`.
  Em 2022, os 116 nulos estaduais de `TP_AEE` e
  `IN_SALA_ATENDIMENTO_ESPECIAL` ocorrem exclusivamente em escolas sem
  matrícula especial e não tornam a proporção parcial.
- A inclusão em classes comuns usa
  `100 × Σ QT_MAT_ESP_CC / Σ QT_MAT_ESP`; denominador zero é
  `not_applicable`.

Os componentes oficiais `QT_TUR_ESP_CC`, `QT_TUR_ESP_CE`,
`QT_DOC_ESP`, `QT_DOC_ESP_CC` e `QT_DOC_ESP_CE` também passam a integrar o
contrato. Todos existem nos leiautes de 2014 a 2025.

## Evidência de São Leopoldo

| Ano | Escolas ativas | `QT_MAT_ESP` | `QT_MAT_ESP_CC` | `QT_MAT_ESP_CE` | Inclusão |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022 | 167 | 1.675 | 1.520 | 155 | 90,74626865671642% |
| 2023 | 170 | 1.977 | 1.819 | 158 | 92,00809307030855% |
| 2024 | 167 | 2.195 | 2.027 | 168 | 92,34624145785877% |
| 2025 | 159 | 2.692 | 2.520 | 172 | 93,61069836552748% |

Em 2025, `2.520 + 172 = 2.692`, o total coincide com a Visão Geral Municipal,
não há extremo, a chave `ano × escola` é única e nenhuma linha esperada se
perdeu. Os quatro pontos são, portanto, `observed`.

## Auditoria reproduzível

`data_pipeline/scripts/audit_special_education_completeness.py` gera, para
Aceguá, Alegrete, São Leopoldo e todo o Rio Grande do Sul, um perfil por ano
(2014–2025) e variável contendo escolas ativas, linhas, positivos, zeros
explícitos, vazios estruturais, nulos genuínos, extremos, soma observada,
universo elegível, escolas observadas e escolas faltantes.

Na fonte normalizada há 120.548 linhas, 497 municípios em cada ano, nenhuma
duplicidade de `ano × escola` e nenhuma chave/dimensão escolar nula. Os únicos
extremos são quatro ocorrências de `QT_PROF_TRAD_LIBRAS`: duas em 2023
(`4300604`, `4314100`) e duas em 2025 (`4314407`, `4317202`). Elas não se
propagam para matrículas, turmas, escolas, AEE ou inclusão.

## Resultado da rematerialização

Na comparação com o mesmo conjunto de métricas do contrato anterior:

| Estado | Antes | Depois |
| --- | ---: | ---: |
| `observed` | 592.833 | 606.383 |
| `derived_zero` | 131.793 | 131.793 |
| `partial` | 13.655 | 15 |
| `unavailable` | 946.288 | 946.288 |
| `not_applicable` | 33.063 | 33.153 |

Foram reclassificados 13.640 pontos `partial`: 13.550 passaram a `observed` e
90 razões com denominador zero passaram a `not_applicable`. Por ano, a redução
foi:

| Ano | `partial` antes | `partial` depois | Redução |
| --- | ---: | ---: | ---: |
| 2022 | 3.686 | 0 | 3.686 |
| 2023 | 2.211 | 7 | 2.204 |
| 2024 | 2.140 | 0 | 2.140 |
| 2025 | 5.618 | 8 | 5.610 |

No recorte municipal total, matrículas, matrículas em classes comuns,
matrículas em classes exclusivas, turmas, escolas e inclusão deixaram de ser
`partial` em 87 municípios em 2022, 57 em 2023, 55 em 2024 e 48 em 2025.
Os componentes quantitativos de 2025 e da educação bilíngue tiveram a mesma
correção localizada nos 48 municípios afetados.

O contrato final também acrescenta os cinco componentes oficiais de turmas e
docentes que não eram publicados. Com esses pontos aditivos, o conjunto final
tem 795.548 `observed`, 181.188 `derived_zero`, 15 `partial`, 946.288
`unavailable` e 33.153 `not_applicable`.

Os 15 `partial` remanescentes são as projeções legítimas, por recorte, das
quatro ocorrências escolares de `QT_PROF_TRAD_LIBRAS=88888`: sete pontos em
2023 e oito em 2025. O manifesto final possui
`contentHash=e1bf2c016540559d596539b9661c923eaf6dd102a70b68569d4f1e1221011c13`.

## Compatibilidade com o indicador `aee`

- Fórmula antiga: `100 × quantidade_aee / total_turmas_educacao_especial`.
- Fonte antiga: tabela agregada `atendimento_educacional_especializado`.
- Limitação antiga: o denominador é turmas, não escolas com matrículas da
  Educação Especial; por isso o indicador atual é marcado como proxy.
- Fórmula nova complementar:
  `100 × escolas com TP_AEE em {1,2} / escolas com QT_MAT_ESP > 0`.
- Valor principal novo: número absoluto de escolas com `TP_AEE em {1,2}`.
- Fonte nova: `censo_educacao_especial_escolas`, com contagem distinta de
  `CO_ENTIDADE`.

Nenhum consumidor de frontend foi alterado. A migração futura deverá tratar,
em conjunto, `src/data/educationIndicatorCatalog.js`,
`data_pipeline/src/pne/calculations_2014.py`,
`data_pipeline/src/pne/calculations_2026.py`,
`data_pipeline/src/pne/indicator_details.py`,
`data_pipeline/src/municipal_diagnostic.py`,
`scripts/generate-diagnostic-catalog.mjs`, os catálogos de diagnóstico e as
regras/notas de apresentação de `aee`. Até essa migração, o contrato novo fica
isolado e não apresenta a fórmula nova como se fosse o indicador legado.
