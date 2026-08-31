# Inventário de dados PNE × Vocações

**Data da auditoria:** 27 de agosto de 2026
**Modo:** prioritariamente somente leitura
**Unidade de contagem:** 66 conjuntos lógicos relacionados ao produto. Réplicas físicas da mesma fonte não foram contadas como novos conjuntos; são registradas na seção de duplicações.
**Veredito:** **há dados suficientes para parte do piloto, com lacunas dirigidas**.

## Síntese executiva

O acervo já sustenta um piloto factual para trajetória escolar, diferenças municipais, contribuição municipal ao resultado regional, demografia histórica, EJA, condições escolares e trabalho juvenil formal. O principal ganho desta auditoria foi localizar no projeto CEI uma base RAIS municipal por idade e escolaridade, com 701.106 linhas de 2019 a 2025 e cobertura dos 497 municípios do RS, além de 30,58 GB de CAGED local com idade, CBO, CNAE, escolaridade, salário e indicador de aprendiz. Portanto, trabalho juvenil não depende de novo download para o piloto.

O que não está sustentado é igualmente claro: não há matriz residência–escola, residência–trabalho ou residência anterior; não há projeção demográfica municipal canônica; cenários regionais equivalentes existem apenas para 2 das 10 regiões; ingressantes e concluintes da educação profissional não foram encontrados; e os cursos/eixos detalhados cobrem somente 10 municípios do Vale do Rio Pardo em 2025.

A classificação das 73 análises e subanálises solicitadas é:

| Status | Quantidade |
|---|---:|
| PRONTA | 29 |
| DERIVÁVEL | 14 |
| PARCIAL | 20 |
| AUSENTE | 8 |
| INADEQUADA | 2 |
| **Total** | **73** |

As classificações completas, com campos, períodos, cobertura, transformação, limitação, confiança e próximo passo, estão em `MATRIZ_COBERTURA_ANALITICA.csv`. A prontidão das 11 leituras candidatas está em `MATRIZ_PRONTIDAO_INSIGHTS.csv`.

## Escopo efetivamente inspecionado

- `C:\Users\rnbirck\PROJETOS\SESI\PNE`: base de conhecimento, foresight, pacotes municipais/regionais e artefatos da rodada.
- `C:\Users\rnbirck\PROJETOS\DASHBOARDS\PNE-REACT`: aplicação, `public/data`, pipeline, queries, fontes brutas/normalizadas, manifests, testes e área temporária `.tmp\foresight-r5b`.
- `C:\Users\rnbirck\PROJETOS\SESI\VOCACOES`: bases, CSVs de dashboard, app Vocações Regionais, pacotes do Vale do Rio Pardo e Serra, cenários, arquivos históricos, scripts, catálogos e manifests.
- `C:\Users\rnbirck\PROJETOS\SESI\DB`: scripts de download/carga, arquivos brutos e Banco SESI PostgreSQL.
- `C:\Users\rnbirck\PROJETOS\CEI`: arquivos RAIS/CAGED, scripts e banco PostgreSQL `cei`.
- Banco SESI PostgreSQL: 67 objetos acessíveis, sendo 50 tabelas e 17 views; todas as consultas desta auditoria executaram `SET TRANSACTION READ ONLY` e foram encerradas com rollback.
- Banco CEI PostgreSQL: 88 objetos acessíveis; mesma disciplina de transação somente leitura.
- Arquivos locais: JSON, JSONL, CSV, TSV, Parquet, XLSX, ODS, ZIP, 7z, RAR, TXT e DBF. Não foi encontrado banco SQLite/DuckDB materializado utilizável.
- Uso real: imports/adaptadores da aplicação, manifests públicos, geradores regionais, scripts de publicação, testes e contagem dos JSONs efetivamente publicados.

### Volume físico observado

| Área | Evidência física |
|---|---|
| Banco SESI bruto | 246 arquivos de dados, 8,73 GB; Censo Escolar 2007-2025, DBFs populacionais e planilhas oficiais |
| PNE fontes/pipeline | 765 arquivos, 1,298 GB; bundles normalizados com QA aprovado |
| PNE publicado | 1.995 JSONs educacionais, cerca de 872 MB; 1.988 municípios, 499 diagnósticos, 11 regiões e 12 artefatos Vocações |
| CEI RAIS 2025 | 18 arquivos, 30,50 GB; TXT/7z regionais, estabelecimentos e Parquet nacional agregado |
| CEI CAGED | 458 arquivos, 30,58 GB; 229 TXT e 228 7z |
| Vocações | pacote atual com 71 séries por região; no Vale do Rio Pardo: 71 séries, 6 associações, 5 pares temporais, 4 cenários e 15 limites |

## Recursos inacessíveis ou não materializados

| Recurso | Motivo | Acesso/informação necessária | Impacto |
|---|---|---|---|
| Supabase/warehouse remoto opcional mencionado pelo PNE | Não havia conector, variável de ambiente ou conexão ativa disponível nesta tarefa | Conector autorizado ou string de conexão fornecida por canal seguro | Não foi possível confirmar tabelas remotas que não tenham réplica local; os artefatos públicos e bancos locais foram auditados |
| `database/runtime/warehouse/pne_local.duckdb` declarado em documentação/configuração | Arquivo físico não existe; nenhum `.duckdb` foi encontrado | Materialização do warehouse ou caminho real | Impede conferir esse warehouse específico; não impede o inventário dos dados locais e PostgreSQL |
| `PNE-REACT\data_pipeline\export\al-source-snapshots\...` | Acesso negado pelo sistema de arquivos | Permissão de leitura para o diretório | Impacto baixo no RS; bundles equivalentes normalizados e publicados foram acessíveis |
| `.pytest_cache` do PNE | Acesso negado | Permissão de leitura | Nenhum impacto material; cache de teste não é fonte de dados |
| BigQuery, FTPs e APIs oficiais remotas citadas pelos scripts | Não foram consultados porque a tarefa proíbe baixar novas fontes e não havia necessidade para confirmar o material local | Nova rodada autorizada e credenciais/conectores apropriados | Só impede afirmar o estado atual da fonte remota; não foi usado para inferir existência local |
| Bases externas apenas citadas em documentação, como tabelas OD do Censo 2022 | Não há arquivo, tabela ou view correspondente materializado | Caminho local real ou aquisição dirigida em rodada posterior | Bloqueia mobilidade origem-destino |

Foi detectada em alguns scripts uma configuração legada de conexão com valor de fallback embutido. Os valores foram deliberadamente omitidos deste documento. A correção de segurança está fora do escopo; nenhuma credencial, token, senha ou string privada é reproduzida aqui.

## Critérios de auditoria

- **Bruto:** arquivo oficial ou extração presente, ainda não normalizada para consumo.
- **Tratado:** limpeza/normalização presente, mas sem prova de publicação.
- **Materializado:** tabela/arquivo analítico consultável e perfilado.
- **Publicado:** artefato no contrato público e com consumidor/import confirmado.
- **Arquivado:** cópia histórica fora do fluxo atual.
- **Script sem dado:** código presente, porém a saída material correspondente não foi encontrada.
- **Documentação sem implementação:** menção textual sem arquivo/tabela/view verificável.
- **Derivação teórica:** cálculo conceitualmente possível, mas sem todos os insumos ou sem semântica confirmada; nunca foi tratado como dado existente.

O último período completo é 2025 para RAIS e para a maior parte do núcleo educacional. CAGED 2026 existe apenas até junho e deve ser tratado como parcial/preliminar. Dados INEP 2025 podem carregar indisponibilidades/supressões próprias, preservadas nos bundles normalizados.

## Inventário dos 66 conjuntos lógicos

### Referências e demografia

| ID | Conjunto e fonte oficial original | Caminho/tabela | Formato e situação | Período, cobertura e chaves | Lente, uso, publicação e limitações |
|---:|---|---|---|---|---|
| 1 | Cadastro canônico de municípios — IBGE | Banco SESI `public.municipio`; registries PNE | PostgreSQL/JSON, materializado e publicado | 5.570 municípios; chave `id_municipio`/código IBGE | Referência. RS=497; sem nulos/duplicações na chave auditada; consumido pelo PNE |
| 2 | Mapa município × região FIERGS | PNE/Vocações, registries e manifests de regionalização | CSV/JSON/JS, materializado e publicado | 497 municípios, 10 regiões; `id_municipio`, `region_id` | Mapa canônico do produto; Vale do Rio Pardo=23 municípios; soma cobre o RS |
| 3 | Mapa COREDE — fonte declarada no projeto | `SESI\DB` e bases de regionalização | tabela/CSV, materializado | 497 municípios; código IBGE e COREDE | Referência alternativa, não intercambiável com FIERGS; não usar para reproduzir regiões do produto |
| 4 | População anual por idade e sexo — IBGE/DATASUS conforme pipeline | Banco SESI `public.populacao_idade` | PostgreSQL, materializado | 1.164.456 linhas; 2014-2025; 599 municípios RS+AL, incluindo 497 RS em todos os anos; `id_municipio,ano,sexo,idade` | Residentes; estimado; publicável em agregado; ainda subutilizado; script `SESI\DB\populacao_idade.py` |
| 5 | População por idade RS legada | Banco SESI `public.populacao_idade_rs`; CEI `public.populacao_idade_rs` | PostgreSQL, materializado/duplicado | 966.168 linhas no Banco SESI; 2014-2025; 497 municípios | Residentes; versão concorrente sem `sigla_uf`; preferir #4 |
| 6 | População por idade no Censo 2022 — IBGE SIDRA | `PNE-REACT\data_pipeline\data\pne_macro_sources\ibge_censo2022` | JSON normalizado, QA aprovado | 4.970 observações; 497 municípios; idade/faixa, município, 2022 | Residentes; observado; fonte publicada em bundle, adequada para âncora censitária |
| 7 | Estimativa populacional total 2024-2025 — IBGE | `...\pne_macro_sources\ibge_estimativa_pop` | JSON normalizado, QA aprovado | 994 observações; 497 municípios × 2 anos | Residentes; estimado; consumível diretamente |
| 8 | Projeção populacional Revisão 2024 — IBGE | arquivos brutos Banco SESI e `.tmp\foresight-r5b\insumos\fontes\xlsx\projecao_pop.xlsx` | XLSX, bruto/tratado | 2000-2070; Brasil, grandes regiões e UF | Projetado; não contém município; inadequado como projeção municipal |
| 9 | Nascimentos — fonte DATASUS/SINASC declarada no catálogo | séries demográficas Vocações/pacote municipal | CSV/JSON, tratado/materializado | série histórica nos municípios do pacote; `id_municipio,ano,valor` | População/ocorrência conforme metadado de cada série; não confundir com projeção; consumidor no pacote regional |
| 10 | Óbitos — DATASUS/SIM | `...\entidades_municipais\095_saude__obitos_por_causa_mun.csv` e arquivos 097/099 | CSV, tratado/materializado | município, ano, causa/faixa; Vale do Rio Pardo e Serra onde há pacote | Ocorrência/residência deve seguir o catálogo; exemplos são agregados, sem pessoas |
| 11 | Migração e composição etária intercensitária — IBGE Censos | pacotes municipais/cenários Vocações | CSV/JSON, tratado/materializado | 2010 e 2022; 23 municípios no pacote auditado | Residentes; observado/calculado; sem município de origem/destino e sem série anual |
| 12 | CadÚnico e vulnerabilidade — MDS | bases municipais Vocações e pacote regional | CSV/JSON, materializado | cobertura municipal conforme pacote e período do cadastro | Residentes/famílias cadastradas, não população total; pode contextualizar EJA/educação, com cautela de universo |

### Educação

| ID | Conjunto e fonte oficial original | Caminho/tabela | Formato e situação | Período, cobertura e chaves | Lente, uso, publicação e limitações |
|---:|---|---|---|---|---|
| 13 | Censo Escolar agregado — INEP | Banco SESI `public.censo` | PostgreSQL, materializado | 28.284 linhas; 2014-2025; 599 municípios RS+AL; `ano,id_municipio,dependencia,localizacao` | Escolas localizadas/rede responsável; cerca de 100 colunas de matrícula, escola, turma, docente, infraestrutura e integral; script `censo_escolar.py` |
| 14 | Censo Escolar por escola — INEP | Banco SESI `public.censo_escolas` | PostgreSQL, materializado | 183.642 linhas; 2014-2025; chave `ano,id_municipio,cod_escola` | Escola localizada; inclui código/nome da escola, etapa, idade, rede, turmas, docentes e infraestrutura; parcialmente consumido |
| 15 | Censo Escolar bruto | `SESI\DB` e diretórios de dados do pipeline | ZIP/CSV/XLSX, bruto | arquivos anuais 2007-2025 | Fonte física presente; scripts `censo_escolar.py`, `sync_censo_escolar_microdata.py` e `build_censo_escolar_panel.py` |
| 16 | Recorte histórico de escolas dos 3 pilotos | `PNE-REACT\.tmp\foresight-r5b\insumos\fontes\censo_escolar_escola_hist` | 19 CSVs, tratado temporário | 2007-2025; 3 municípios: 4312625, 4313375 e 4318705; 148-213 escolas/ano, 202 em 2025 | Escola localizada; `IN_DIURNO/IN_NOTURNO` até 2024 e `QT_MAT_*_D/N` em 2025; sem duplicação de `ano,CO_ENTIDADE`; não publicado |
| 17 | Tabelas detalhadas Censo Escolar 2025 dos 3 pilotos | `.tmp\...\censo_escolar_2025_detalhe\Tabela_*_2025_V2_pilotos.csv` | 5 CSVs, tratado temporário | Escola 202; Docente 192; Gestor 193; Matrícula agregada 192; Turma 192; 3 municípios | Escola/rede; contém EJA/EPT, turno e integral em agregados; não cobre 497 e não tem consumidor público |
| 18 | Matrículas por faixa etária — INEP Sinopse | Banco SESI `public.matriculas_faixa_etaria` | PostgreSQL, materializado | 258.564 linhas; 2014-2025; 599 municípios; `ano,id_municipio,etapa_ensino,faixa_etaria` | Matrículas em escolas localizadas; script `sinopse_estatistica_censo.py`; não identifica residência |
| 19 | Rendimento escolar — INEP | Banco SESI `public.rendimento_escolar` | PostgreSQL, materializado e consumido | 185.701 linhas; 2018-2025; 599 municípios; dependência, localização, etapa | Aprovação/reprovação/abandono; observado/calculado pelo INEP; script `rendimento_escolar.py` |
| 20 | Distorção idade-série — INEP | Banco SESI `public.distorcao_idade_serie` | PostgreSQL, materializado e consumido | 73.832 linhas; 2019-2025; 599 municípios | `dependencia,categoria,valor`; script `distorcao_idade_serie.py`; taxa exige ponderação regional |
| 21 | Transição — INEP Indicadores Educacionais | bundle PNE `inep_indicadores_eb` | JSON normalizado, materializado | transição somente 2021-2022; parte das 427.677 observações e 85 medidas | Município/rede/etapa; série descontinuada; status PARCIAL |
| 22 | Alunos por turma/ATU — INEP | Banco SESI `public.alunos_turma`; PNE `inep_indicadores_eb` | PostgreSQL/JSON, materializado | 1.567.434 linhas no Banco; anos recentes até 2025 | Escola localizada; `etapa_ensino,serie,alunos_por_turma`; script `alunos_turma.py`; ponderar por turma/matrícula |
| 23 | Horas-aula diária/HAD e jornada integral — INEP | PNE `inep_indicadores_eb`; Banco SESI `public.censo` | JSON/PostgreSQL, materializado | HAD 2023-2025; integral 2014-2025; 497 municípios com indisponibilidades explícitas | Escola localizada; não é sinônimo de turno; publicado via bundle |
| 24 | Adequação da formação docente/AFD — INEP | Banco SESI `public.adequacao_docente`; PNE bundle | PostgreSQL/JSON, materializado | 258.810 linhas; 2014-2025 | Rede/escola localizada; `percentual_adequacao,etapa`; script `adequacao_docente.py` |
| 25 | Esforço docente/IED — INEP | PNE `inep_indicadores_eb` | JSON normalizado, materializado | 2023-2025 no bundle auditado; 497 municípios conforme medida | Escola/rede; observado/calculado; ainda pouco exposto pelos consumidores |
| 26 | Regularidade docente/IRD — INEP | PNE `inep_indicadores_eb`; XLSX `IRD_MUNICIPIOS_2025.xlsx` temporário | JSON/XLSX, materializado/bruto | 2023-2025; 2025 também em planilha | Escola/rede; preservar indisponibilidade; não combinar com IED em escore sintético |
| 27 | Nível socioeconômico/INSE — INEP | Banco SESI `public.inse`; PNE XLSX/escola | PostgreSQL/XLSX, materializado | 49.626 linhas; 2019, 2021, 2023; 495 municípios em 2023 | Alunos avaliados; `media_inse,qtd_alunos_inse,pc_nivel_socio_1..8`; dois municípios sem cobertura em 2023 |
| 28 | Alfabetização — INEP | Banco SESI `public.alfabetizacao`; PNE bundle 2025 | PostgreSQL/JSON, materializado | 1.666 linhas no Banco; 2023-2025; bundle 2025 com 2.961 observações e 487 municípios | Município/rede; cobertura variável; inclui `participacao_avaliacao` e método |
| 29 | IDEB/SAEB — INEP | Banco SESI `public.saeb_ideb`; PNE bundle | PostgreSQL/JSON, materializado e consumido | 170.410 linhas; 2005-2025; RS municipal completo desde 2011 conforme edição; PNE=174.980 obs./15 medidas | Município/rede/etapa; supressões e periodicidade próprias; script `saeb.py` |
| 30 | Proficiência SAEB — INEP | Banco SESI `public.saeb_proficiencia` e `public.saeb` | PostgreSQL, materializado | 2017, 2019, 2021, 2023; cobertura municipal 595, 595, 586 e 597 no conjunto RS+AL | Município, matéria, nível, etapa; script `saeb_proficiencia.py`; não anual |
| 31 | EJA integrada à educação profissional — INEP Sinopse/Censo Escolar | Banco SESI `public.eja_integrada_educacao_profissional` | PostgreSQL, materializado | 7.188 linhas; 2014-2025; 599 municípios | Escola localizada; total, fundamental/médio, FIC/técnico e redes; `sync_eja_integrada_from_sinopse.py` |
| 32 | EPT de nível médio por modalidade e rede — INEP Sinopse | Banco SESI `public.ept_nivel_medio` | PostgreSQL, materializado | 7.787 linhas; 2013-2025; 599 municípios | Escola localizada; integrado, concomitante, subsequente, EJA e rede; `sync_ept_nivel_medio_from_sinopse.py` |
| 33 | Cursos e eixos tecnológicos do piloto | Vocações VRP, bases municipais de cursos técnicos | CSV, tratado/materializado sem consumidor amplo | 56 registros, 2025, 10 municípios, 8 eixos | Oferta localizada; curso/eixo/rede; fotografia incompleta do Vale do Rio Pardo |
| 34 | Conclusão educacional da população adulta — IBGE Censos | Banco SESI `public.censo_populacao_ensino_*_concluido_*` | PostgreSQL, materializado | 2010 e 2022; 497 municípios RS | Residentes; estoque declarado de conclusão, não conclusão escolar anual; queries PNE correspondentes |
| 35 | Educação/população rural — INEP/IBGE | Banco SESI `public.matriculas_rurais_faixa_etaria_municipal`, `public.populacao_rural_estimada_4_17_municipal` | PostgreSQL, materializado/calculado | Censo 2022 e anos educacionais conforme tabela; municipal | Mistura população residente estimada e matrícula escolar rural; método de estimativa está registrado |
| 36 | População e educação indígena — IBGE/INEP | Banco SESI `public.populacao_indigena_*`; PNE bundles | PostgreSQL/JSON, materializado | Censo 2022 e Censo Escolar conforme publicação; municipal | Residentes versus escolas; scripts `sync_indigenous_*`; não é núcleo desta integração, mas está disponível |
| 37 | Educação especial/AEE — INEP | Banco SESI `public.censo_educacao_especial_escolas` e tabelas AEE | PostgreSQL, materializado | 7.188 linhas na tabela AEE agregada; 2014-2025; 599 municípios | Escola/rede; chaves de escola/município/ano; possui flags explícitas de disponibilidade e extremo |
| 38 | PNATE — FNDE | Banco SESI `public.fnde_pnate_municipio_dashboard`; XLSX 2024-2026 temporários | PostgreSQL/XLSX, materializado/bruto | anos conforme planilhas; município e rede estadual/municipal | Beneficiários/repasse, não origem-destino; scripts `pnate.py` e query PNE |
| 39 | VAAR/Fundeb condicionalidades | Banco SESI `public.vaar_*` e views | PostgreSQL, materializado | 54.742 registros de indicadores; município/ano Fundeb | Indicadores e coeficientes; scripts `vaar.py`/views; pode contextualizar, não substitui resultados educacionais |
| 40 | SIOPE/Fundeb/finanças educacionais — FNDE/STN | Banco SESI `public.siope_fundeb_municipio_indicadores`; PNE SICONFI/finance | PostgreSQL/JSON, materializado | 8.978 linhas na tabela SIOPE; períodos anuais; municipal | Finanças do ente/rede responsável; scripts `financeiro_educacao.py`, `generate_siope_publication.py` |
| 41 | Sinopse da educação superior — INEP | PNE data pipeline e scripts `sync_higher_education_from_sinopse.py` | JSON/tabelas de pipeline, tratado/materializado | anos conforme artefatos PNE; municipal/IES onde disponível | Educação superior, não EPT; não usar como substituto para cursos técnicos |
| 42 | Discentes de pós-graduação stricto sensu 2024 — CAPES | `...\pne_macro_sources\capes_2024\raw\students_2024.csv` | CSV bruto, 188 MB; normalização/manifest presente | 432.888 linhas; 37 colunas; 27 UFs; 341 municípios de programa | Local de programa; contém nomes/documentos e outros dados pessoais: **não publicar linhas**. Somente agregações. `ST_INGRESSANTE` e titulação são pós-graduação, não EPT; script `sync_pne_capes_2024.py` |
| 43 | Diagnóstico público PNE 2026 | PNE `public/data/diagnostics` e materializações v3 | JSON, publicado/consumido | 497 arquivos municipais, 51 resultados cada, 25.347 resultados; mais referências regional/RS | Município selecionado e comparadores; contratos/testes aprovados; scripts `materialize_*diagnostic_v3.py` e promoção |

### Trabalho, economia e território

| ID | Conjunto e fonte oficial original | Caminho/tabela | Formato e situação | Período, cobertura e chaves | Lente, uso, publicação e limitações |
|---:|---|---|---|---|---|
| 44 | RAIS por subsetor — Ministério do Trabalho | `SESI\VOCACOES\bases` e app Vocações | Parquet/CSV, materializado e consumido | 166.451 linhas; 2006-2025; 497 municípios | Vínculos localizados; `ano,id_municipio,subsetor`; sem defeitos de chave detectados |
| 45 | RAIS por idade, escolaridade, sexo e raça | CEI `public.rais_vinculos` | PostgreSQL, materializado sem consumidor PNE | 701.106 linhas; 2019-2025; 497 municípios todos os anos; chave natural sem nulos/duplicações | Vínculos localizados; faixas 2=15-17 e 3=18-24; 21.703.443 vínculos somados no período; script `rais_vinculos.py` |
| 46 | RAIS Vínculos 2025 Brasil/Sul | `CEI\db\data\rais\2025\rais_vinculos_2025_br.parquet`; CEI `public.rais_vinculos_2025_sul` | Parquet/PostgreSQL, bruto agregado/materializado | 27.040.053 linhas no Parquet, 103 row groups; tabela Sul estimada em 5.585.125 linhas | Município de trabalho; idade, escolaridade, CNAE, remuneração, natureza jurídica; publicação apenas agregada |
| 47 | RAIS ocupações e renda | CEI `public.rais_ocupacoes_rs_25`, `public.rais_vinculos_ocupacao`, `public.rais_renda`; Vocações ocupações | PostgreSQL/CSV, materializado | arquivo regional 13.984 linhas, 2006-2025; tabela municipal detalhada 2025; 18 CBO nulos no arquivo regional | Vínculo localizado; CBO/CNAE/salário; scripts `rais_ocupacao.py`, `rais_ocupacoes_rs_25.py`, `rais_renda.py` |
| 48 | RAIS estabelecimentos | CEI `public.rais_estabelecimentos`; arquivos RAIS estabelecimento 2025 | PostgreSQL/TXT/7z, materializado/bruto | município, CNAE, tamanho, ano; 2025 bruto presente | Estabelecimentos localizados; script `rais_estabelecimentos.py`; não representa trabalhadores residentes |
| 49 | Novo CAGED bruto | `CEI\db\data\caged` | 458 TXT/7z, bruto presente | CAGEDMOV jan/2020-jun/2026 sem lacunas; CAGEDFOR fev/2020-jun/2026; CAGEDEXC abr/2020-jun/2026 exceto mar/2023 | Movimentos no município de trabalho; idade exata, faixa, CBO, CNAE, escolaridade, salário, movimento e aprendiz; 2026 parcial/preliminar |
| 50 | CAGED municipal por idade e perfil | CEI `public.caged_prefeituras` | PostgreSQL, materializado | 10.966.491 linhas; 2020-jun/2026; 497 municípios por ano agregado | Saldo por município, faixa etária, escolaridade, raça, sexo e CNAE; não separa admissões/desligamentos |
| 51 | CAGED CNAE com tipo de movimento | CEI `public.caged_cnae` | PostgreSQL, materializado | 34.709.661 linhas; 2020-jun/2026; meses completos disponíveis | Município, CNAE, tipo 0/1, massa salarial e saldo; movimentos localizados |
| 52 | CAGED CNAE × ocupação | CEI `public.caged_cnae_ocup` | PostgreSQL, materializado | 3.381.322 linhas; 2023-2024 completos e 2025 com 9 meses | Município, CBO, CNAE, admitido/desligado; histórico parcial |
| 53 | Estoque mensal por faixa etária calculado | CEI `public.estoque_emprego_faixa_etaria` | PostgreSQL, materializado **inadequado** | 600.834 linhas; 2020-jun/2026; 497 municípios | Calculado por RAIS dezembro + CAGED acumulado; 297.492 chaves duplicadas e valores conflitantes, inclusive negativos; não consumir; script `prefeituras\estoque_emprego.py` |
| 54 | CEMPRE — IBGE | PNE `ibge_cempre/2022_2024` | JSON normalizado, QA aprovado | 5.964 observações; 2022-2024; 497 municípios | Empresas/estabelecimentos e pessoal localizado; útil para estrutura econômica |
| 55 | PIB dos municípios — IBGE | PNE `ibge_pib_municipios/2021_2023` | JSON normalizado, QA aprovado | 2.982 observações; 2021-2023; 497 municípios | Economia localizada/contas municipais; 2023 último completo no bundle |
| 56 | Comércio exterior — Comex Stat/MDIC | Vocações `scripts\comex.py` e bases regionais | CSV/JSON, tratado/materializado | histórico conforme pacote; município/região/produto | Fluxo econômico localizado; consumidor Vocações; não é emprego |
| 57 | Oferta Sistema S e formação | bases Vocações/SESI e Censo Escolar `mantenedora_sistema_s` | CSV/PostgreSQL, materializado parcial | escola/curso/município conforme base; anos variados | Oferta localizada; cobertura e conceitos diferentes entre mantenedora escolar e curso ofertado |
| 58 | Desastres — MIDR Atlas Digital | PNE `midr_atlas_desastres/1991_2025_v1.1_2026-08-06` e Vocações | JSON normalizado, QA aprovado | 1991-2025; 497 municípios no bundle | Ocorrência/impacto territorial; série materializada, ainda sem uso educacional sistemático |
| 59 | MUNIC — IBGE | PNE `ibge_munic/2023` | JSON normalizado, QA aprovado | 5.467 observações; 2023; 497 municípios | Gestão/políticas do município; `consorcio_transporte` não mede deslocamento |
| 60 | Censo SUAS — MDS | PNE `mds_censo_suas/2024_corrected_2026-04-29` | JSON normalizado, QA aprovado | 2024; 497 municípios no recorte normalizado | Serviços/equipamentos localizados; contexto social, não matrícula |
| 61 | SINISA — Ministério das Cidades | PNE `mcid_sinisa/2023` | JSON normalizado, QA aprovado | 2023; cobertura municipal do bundle aprovado | Saneamento territorial; pode contextualizar condições, sem relação causal automática |
| 62 | SICONFI/DCA — STN | PNE `stn_siconfi/2024_dca_annex_i_e` | JSON normalizado, QA aprovado | 2024; municipal | Finanças do ente; fonte para capacidade fiscal, não gasto educacional por si só |
| 63 | Cenários regionais Vocações | PNE `public/data/vocacoes`; Vocações `pacote_vocacoes` e manifests | JSON, publicado/consumido | 4 cenários nas regiões Noroeste e Vale do Rio Pardo; base 2026, horizonte 2031; 2 de 10 regiões | Cenário regional, não previsão; metadados/método/limites presentes; oito regiões sem pacote equivalente |
| 64 | Exposição/composição municipal aos cenários | pacote municipal Vale do Rio Pardo | JSON/CSV, materializado | 23 municípios; 5 dimensões decomponíveis, 4 exposições e 3 dimensões não decomponíveis | Município; observado/calculado; **não é cenário municipal** |
| 65 | Projeções experimentais de atendimento/planejamento | PNE `education_attendance_projection_models.py`, `materialize_planning_scenario_snapshots.py` e artefatos da rodada | Python/JSON, script e materialização experimental | horizonte conforme contrato de experimento; municípios-piloto | Estimado/cenário de planejamento; não é projeção demográfica oficial; não expor classificação técnica |
| 66 | Rotas/distâncias de compatibilidade municipal | PNE `config\compatibility\education-municipality-routes\rs.json` e código associado | JSON/Python, materializado de apoio | 497 municípios conforme registry RS | Apoio técnico a seleção/compatibilidade, não dado de deslocamento observado; não usar como mobilidade |

## Evidências mínimas e qualidade

### Perfis de cobertura, chaves, nulos e duplicações

As contagens de banco abaixo são `COUNT(*)` ou perfis exatos feitos em transações somente leitura. Para arquivos muito grandes foram usados metadados Parquet e agregações dirigidas.

| Conjunto | Registros | Período e cobertura municipal | Chave principal auditada | Nulos/duplicações e código municipal |
|---|---:|---|---|---|
| `public.populacao_idade` | 1.164.456; 966.168 RS | 2014-2025; 599 municípios, sendo 497 RS em todos os anos | `id_municipio,ano,sexo,idade` | 0 chave nula/duplicada no perfil; IBGE canônico de 7 dígitos |
| `public.censo` | 28.284 | 2014-2025; 599; RS=497/ano | `ano,id_municipio,dependencia,localizacao` | 0 chave nula/duplicada no perfil; código canônico |
| `public.censo_escolas` | 183.642 | 2014-2025; 599 | `ano,cod_escola` com município | sem anomalia de chave material no perfil; escola localizada |
| `public.matriculas_faixa_etaria` | 258.564 | 2014-2025; 599 | `ano,id_municipio,etapa_ensino,secao_sinopse,faixa_etaria` | sem duplicação de chave natural no perfil; código canônico |
| `public.rendimento_escolar` | 185.701 | 2018-2025; 599 | `ano,id_municipio,dependencia,localizacao,etapa_ensino` | sem duplicação natural; taxas podem ser nulas/suprimidas em cortes pequenos |
| `public.distorcao_idade_serie` | 73.832 | 2019-2025; 599 | `ano,id_municipio,dependencia,categoria` | sem duplicação natural; rótulos de dependência variam em capitalização entre tabelas |
| `public.eja_integrada_educacao_profissional` | 7.188 | 2014-2025; 599 | `ano,id_municipio` | sem duplicação; percentual nulo quando denominador é zero |
| `public.ept_nivel_medio` | 7.787 | 2013-2025; 599 | `ano,id_municipio` | sem duplicação; contagens zero são valores, não ausência |
| `public.adequacao_docente` | 258.810 | 2014-2025; 599 | município/ano/localização/dependência/etapa | sem defeito de chave identificado |
| `public.alunos_turma` | 1.567.434 | série até 2025; 599 | município/ano/localização/dependência/etapa/série | granularidade exige ponderação; não somar médias |
| `public.inse` | 49.626 | 2019, 2021, 2023; 495 municípios RS em 2023 | `ano,id_municipio,rede` | 2 municípios RS sem cobertura 2023; ponderador `qtd_alunos_inse` presente |
| `public.alfabetizacao` | 1.666 | 2023-2025; cobertura variável | `ano,id_municipio,dependencia` | 2025 normalizado cobre 487 municípios; ausência deve permanecer explícita |
| `public.saeb_ideb` | 170.410 | 2005-2025; RS conforme edição desde 2011 | `id_municipio,ano,rede,indicador,categoria` | supressões aparecem como valor nulo; não preencher automaticamente |
| PNE CEMPRE normalizado | 5.964 | 2022-2024; 497 municípios | chave natural do bundle | QA aprovado; 0 duplicação/código fora do registry |
| PNE Censo 2022 idade | 4.970 | 2022; 497 | município × faixa/medida | QA aprovado |
| PNE estimativa populacional | 994 | 2024-2025; 497 | município × ano | QA aprovado |
| PNE MUNIC | 5.467 | 2023; 497 | município × medida | QA aprovado |
| PNE PIB municipal | 2.982 | 2021-2023; 497 | município × ano × medida | QA aprovado |
| PNE alfabetização 2025 | 2.961 | 2025; 487 municípios | município × rede/medida | 10 municípios sem valor no bundle; indisponibilidade não foi tratada como zero |
| PNE Censo Escolar 2025 | 30.814 | 2025; 497; 62 medidas | município × medida/dimensão | QA aprovado |
| PNE IDEB 2025 | 174.980 | edições até 2025; 497; 15 medidas | município × ano × indicador/dimensão | QA aprovado; supressões preservadas |
| PNE Indicadores EB | 427.677 | 2023-2025, salvo transição 2021-2022; 497; 85 medidas | município × ano × medida/dimensões | 336.930 observações e 90.747 estados indisponíveis; 0 duplicação natural no QA |
| Vocações RAIS subsetor | 166.451 | 2006-2025; 497 | município × ano × subsetor | sem nulos/duplicações de chave no perfil |
| Vocações composição etária regional | 1.684 | 2006-2025; 10 regiões FIERGS | região × ano × faixa | inclui faixas 15-17 e 18-24; 25 linhas com faixa vazia; é regional, não municipal |
| Vocações ocupações/CBO | 13.984 | 2006-2025; regional | região × ano × CBO/subgrupo | 18 linhas com CBO nulo; não apagar sem investigar |
| Vocações cursos técnicos VRP | 56 | 2025; 10 municípios; 8 eixos | município × curso/eixo/ofertante | cobertura incompleta: 13 municípios da região sem registro na base |
| CEI `public.rais_vinculos` | 701.106 | 2019-2025; 497 municípios em cada ano | `ano,id_municipio,sexo,raca_cor,faixa_etaria,grau_instrucao` | 0 nulos de município/ano e 0 duplicação natural; IBGE canônico, tipo físico variável |
| RAIS 2025 Parquet | 27.040.053 | 2025; Brasil; tabela Sul derivada | dimensões agregadas do Parquet | 103 row groups; sem linhas pessoais no Parquet agregado; publicar apenas agregados |
| CEI `public.caged_prefeituras` | 10.966.491 | jan/2020-jun/2026; 497 municípios por ano agregado | município × competência × perfil × CNAE | chave agregada utilizável; guarda saldo, não fluxo separado |
| CEI `public.caged_cnae` | 34.709.661 | jan/2020-jun/2026 | município × competência × CNAE × tipo | tipos de movimento separados; 2026 parcial |
| CEI `public.caged_cnae_ocup` | 3.381.322 | 2023-2024 completos; 2025=9 meses | município × competência × CNAE × CBO × tipo | período 2025 incompleto nessa tabela específica |
| CEI `public.estoque_emprego_faixa_etaria` | 600.834 | jan/2020-jun/2026; 497 | deveria ser município × competência × faixa | **297.492 grupos de chave aparecem duas vezes; só 34.076 desses pares têm valor igual; há valores negativos** |
| Recorte Censo Escolar dos pilotos | 3.714 registros-escola somados nos 19 anos | 2007-2025; exatamente 3 municípios | `NU_ANO_CENSO,CO_ENTIDADE` | 0 duplicação de escola/ano; código municipal canônico; não cobre o estado |
| CAPES discentes 2024 | 432.888 | 2024; 27 UFs e 341 municípios de programa | nível de pessoa/programa | contém PII; nenhum registro foi reproduzido; campos territoriais por nome, sem código IBGE canônico |

### Cobertura anual de RAIS e CAGED materializados

| Ano | RAIS: linhas | RAIS: vínculos ativos | CAGED prefeitura: linhas | CAGED prefeitura: saldo | CAGED CNAE: linhas | Meses CAGED |
|---:|---:|---:|---:|---:|---:|---:|
| 2019 | 96.768 | 2.893.240 | — | — | — | — |
| 2020 | 95.926 | 2.820.968 | 1.229.419 | -41.312 | 4.098.280 | 12 |
| 2021 | 99.790 | 2.960.685 | 1.509.201 | 144.563 | 4.806.714 | 12 |
| 2022 | 103.772 | 3.146.981 | 1.623.744 | 100.073 | 5.066.192 | 12 |
| 2023 | 103.366 | 3.227.570 | 1.668.794 | 46.725 | 5.163.851 | 12 |
| 2024 | 100.407 | 3.287.525 | 1.741.706 | 63.457 | 5.411.614 | 12 |
| 2025 | 101.077 | 3.366.474 | 2.122.526 | 41.921 | 6.792.544 | 12 |
| 2026 | — | — | 1.071.101 | 39.465 | 3.370.466 | 6, preliminar |

### Valores distintos de dimensões centrais

- `censo.dependencia`: federal, estadual, municipal e privada; `localizacao`: urbana/rural/total conforme linha.
- `rendimento_escolar.etapa_ensino`: fundamental, anos iniciais, anos finais, médio e demais categorias disponibilizadas pelo INEP; rede e localização permanecem dimensões separadas.
- RAIS `faixa_etaria`: 1=10-14, 2=15-17, 3=18-24, 4=25-29, 5=30-39, 6=40-49, 7=50-64, 8=65+ e 99=não informado.
- No CAGEDMOV RS de junho de 2026, os códigos de movimento observados foram 31, 32, 33, 35, 40, 43, 50, 60, 90, 97 e 98; `indicadoraprendiz` assumiu 0/1. O significado dos códigos deve vir do dicionário oficial, não de inferência.
- CAPES 2024: `NM_MODALIDADE_PROGRAMA` tem ACADÊMICO (356.058) e PROFISSIONAL (76.830); isso significa pós-graduação profissional. `ST_INGRESSANTE`: SIM=120.618, NÃO=312.270. Situação: matriculado=325.278, titulado=91.833, desligado=11.689, abandonou=3.704 e mudança de nível sem defesa=384.
- Vocações regional contém as faixas exatas 15-17 e 18-24, mas os 72 arquivos com dimensão etária inspecionados não trazem município; o município foi encontrado no CEI.

### Registros de exemplo seguros

Até três registros agregados são mostrados por conjunto principal. Não há dado pessoal. Código 4312625 corresponde a um dos municípios-piloto; os exemplos servem para validar schema, não para interpretação substantiva.

| Conjunto | Exemplos reais auditados |
|---|---|
| População por idade | `{id_municipio:4312625, ano:2025, sexo:Feminino, idade:0, pop_estimada:8}`; `{..., sexo:Masculino, idade:0, pop_estimada:7}`; `{..., sexo:Feminino, idade:4, pop_estimada:9}` |
| Censo Escolar agregado | 2025/4312625/estadual/rural: creche 0, pré 12, fundamental 47, médio 0; estadual/urbana: fundamental 121, médio 52; municipal/rural: creche 16, pré 19, fundamental 29 |
| Rendimento | 2025/4312625/estadual/rural/fundamental: aprovação 86,5, reprovação 13,5, abandono 0; estadual/total/fundamental: 95,4/4,6/0 |
| Distorção | 2025/4312625/Estadual: fundamental 10,1; anos finais 11,9; anos iniciais 8,9 |
| INSE | 2023/4312625/estadual: `media_inse=5,5389`, `qtd_alunos_inse=39`; 2021/estadual: 5,49 e 44 |
| IDEB | 2025/4312625/Estadual: anos iniciais nulo por indisponibilidade; anos finais 5,5; ensino médio 4,5 |
| EJA | 2025/4300034: total 14, integrada EPT 0; 4300109: total 13, integrada 0; 4300208: total 43, integrada 0 |
| EPT | 2025/4300109: total 25, concomitante 5, subsequente 20; 4300406: total 1.299, integrado 559, concomitante 6, subsequente 345, EJA integrada 3; 4300604: total 1.582, integrado 325, concomitante 447, subsequente 616, EJA integrada 41 |
| RAIS juvenil | 2025/4312625/faixa 2 (15-17): 5 vínculos; faixa 3 (18-24): 40 vínculos |
| CAGED juvenil agregado | 2025-01/4312625/faixa 18-24: saldo 2; 2025-02/faixa 15-17: saldo 1; 2025-02/faixa 18-24: saldo 1 |
| Defeito no estoque calculado | 2020-01/4300034/15-17 aparece duas vezes com -1 e 6; 18-24 com -2 e 143; 25-29 com 3 e 135 |
| Censo Escolar turno — 3 pilotos | 2025: EJA diurna 72 e noturna 1.045; EPT técnica diurna 1.812 e noturna 1.051, somadas nas escolas dos três municípios |

### Padronização do código municipal

- PNE, Banco SESI e mapas FIERGS usam o código IBGE canônico de 7 dígitos e passaram nos testes de registry para os 497 municípios.
- CEI contém `id_municipio` como texto em algumas tabelas e inteiro em outras. Para o RS todos os códigos auditados preservam o valor canônico, mas a junção deve converter para texto de 7 dígitos.
- CAPES usa nome do município do programa e não fornece código IBGE no CSV de discentes; requer tradutor e não deve ser unido apenas por nome sem QA.
- Nenhum agrupamento regional deve usar nome textual do município como chave.

## Lentes territoriais

| Lente | Conjuntos que a representam | Disponibilidade | Compatibilidade |
|---|---|---|---|
| População residente | população por idade, Censos 2010/2022, CadÚnico, migração | ampla para população; parcial para migração | combina diretamente entre si após compatibilizar universo/período |
| Estudantes residentes | nenhum conjunto com residência individual/OD | ausente | não inferir a partir de matrícula localizada |
| Matrículas em escolas localizadas no município | Censo Escolar, EJA, EPT, matrícula por idade | pronta 2014-2025 | combina diretamente com escola/rede/etapa; com população somente como contraste de lentes |
| Rede municipal responsável | `dependencia=municipal`, matrículas conveniadas e finanças do ente | pronta | não equivale a estudantes residentes no município |
| Rede estadual responsável | `dependencia=estadual`, PNATE e indicadores de rede | pronta | mesma cautela; uma escola estadual está localizada em um município |
| Trabalhadores residentes | nenhum conjunto confirmado | ausente | RAIS/CAGED não substituem esta lente |
| Vínculos localizados no município | RAIS e CAGED | pronta/derivável | combina com estrutura econômica local; com educação é associação ecológica, não seguimento individual |
| Empresas/estabelecimentos localizados | RAIS estabelecimentos, CEMPRE | pronta | soma municipal reproduz regiões para contagens; taxas precisam recomputação |
| Deslocamento residência–estudo–trabalho | nenhum conjunto OD | ausente | transporte escolar/PNATE e caches de distância são inadequados como substitutos |

### Combinações diretas e combinações com cautela

- **Diretas:** escola–matrícula–turma–docente–infraestrutura pelo código da escola/município/ano; rendimento–TDI–IDEB por município/rede/etapa/período compatível; RAIS–CAGED por município de trabalho/CNAE/período, mantendo estoque e fluxo separados; município–região pelo mapa FIERGS.
- **Diretas com recomputação:** resultados regionais de contagem; taxas somente por numerador/denominador ou peso apropriado. O gerador regional do PNE já evita média simples de fluxo, IDEB, SAEB e INSE.
- **Contraste legítimo, não junção de população:** população residente × matrícula localizada; residentes × vínculos localizados; conclusão populacional × matrícula EJA. Essas comparações devem exibir as duas lentes.
- **Incompatíveis:** CAPES profissional × EPT; transporte escolar × deslocamento OD; indicador de aprendiz × oferta de aprendizagem; exposição municipal × cenário municipal; tendência × projeção; saldo CAGED × admissões/desligamentos quando o tipo foi descartado.

## Avaliação regional e municipal

O mapa canônico para o produto é FIERGS: 497 municípios em 10 regiões. Para contagens, a soma municipal reproduz a região quando todos os municípios/anos estão cobertos. Para taxas, médias e índices, a região deve ser recomputada; média simples de municípios não reproduz o resultado regional.

| Família | Leitura regional | Decomposição municipal | Município selecionado | Lente municipal | Soma reproduz a região? | Anos/municípios sem cobertura |
|---|---|---|---|---|---|---|
| Demografia e matrículas | Sim | Sim | Sim | residentes versus escolas localizadas | contagens sim; razões por recomputação | núcleo 2014-2025 completo; migração só 2010/2022 no pacote piloto |
| Trajetória escolar | Sim | Sim | Sim | escola/rede responsável | taxas não somam; usar pesos | rendimento 2018-2025; TDI 2019-2025; transição só 2021/2022 |
| Formação do resultado regional | Sim | Sim, inclusive contribuição e leave-one-out | Sim | depende da métrica | sim para componentes aditivos; índices exigem contrato | cobertura varia por indicador e supressão |
| EJA | Sim | Sim | Sim | escola localizada; potencial=residentes | matrículas sim; razão potencial deve ser recomputada | potencial só 2010/2022; turno somente 3 municípios |
| Educação profissional | Sim para matrícula/modalidade | Sim para matrícula; parcial para curso/eixo | Sim para matrícula | escola/oferta localizada | matrículas sim | curso/eixo somente 10 municípios em 2025; ingressante/concluinte ausente |
| Trabalho juvenil | Sim | Sim | Sim | vínculo/movimento localizado no trabalho | vínculos e fluxos sim | RAIS 2019-2025 completa; CAGED 2026 somente jan-jun |
| Mobilidade | Não para OD | Não | Não | lente OD ausente | não aplicável | ausência estrutural de origem/destino |
| Condições escolares | Sim | Sim | Sim | escolas localizadas/rede | contagens sim; proporções por denominador | INSE 2023 cobre 495; demais variam por medida/ano |
| Futuro demográfico | Sim para tendência; projeção apenas UF | Sim para tendência/coorte, não cenário | Sim para tendência | residentes | contagens históricas sim | sem projeção municipal |
| Futuro do trabalho | Sim para histórico; cenário em 2 regiões | Sim para histórico; cenário municipal não | Sim para emprego observado | vínculos/estabelecimentos localizados | contagens sim | cenários ausentes em 8 regiões; cursos municipais incompletos |
| Finanças e contexto social | Sim | Sim | Sim | ente/equipamento/população cadastrada | valores aditivos conforme rubrica | anos e universos diferem entre SIOPE, SICONFI, SUAS e MUNIC |

## Mapa de dados existentes e subutilizados

### Materializados sem consumidor ou com consumo muito menor que o potencial

1. **RAIS juvenil municipal no CEI:** `public.rais_vinculos`, 2019-2025, 497 municípios, faixas exatas 15-17 e 18-24. Não foi encontrado consumidor PNE/Vocações que exponha esse recorte municipal anual.
2. **CAGED bruto e cubos CEI:** idade exata, aprendiz, CBO, CNAE, escolaridade, salário e tipo de movimento já estão em disco; falta materialização específica do recorte juvenil, não aquisição.
3. **População anual por idade:** 2014-2025, 497 municípios; já permite substituir comparações demográficas genéricas por faixas alinhadas às etapas.
4. **EJA e EPT no Banco SESI:** 2014/2013-2025, modalidade e rede; permitem leituras públicas imediatas sem recorrer somente a narrativa.
5. **Censo Escolar por escola:** 183.642 linhas com matrícula, etapa, rede, turmas, docentes, infraestrutura e conectividade; a interface usa apenas parte desse schema.
6. **Indicadores Educacionais normalizados:** 85 medidas e estado de disponibilidade explícito; HAD, IED, IRD, TDI e transição estão mais ricos que o contrato atualmente exposto.
7. **Turno EJA/EPT dos 3 pilotos:** dados concretos 2007-2025 na área temporária; úteis para validar uma leitura local, mas não devem ser promovidos como cobertura estadual.
8. **CEMPRE, PIB, MUNIC, SUAS, SINISA, SICONFI e desastres:** bundles aprovados, com código municipal canônico e ainda sem uso sistemático na integração educação-território.
9. **CAPES 2024:** ingressantes/titulados de pós-graduação e município do programa estão presentes, mas qualquer uso deve ser agregado e separado de EPT; linhas contêm PII.
10. **Estoque mensal por faixa etária:** materializado, porém subutilização aqui é correta: está em quarentena lógica por defeito grave de chave e não deve ganhar consumidor.

### Variáveis presentes, mas não expostas por adaptadores públicos

- `censo`: `mat_basico_0_3`, `mat_basico_4_5`, `mat_basico_6_10`, `mat_basico_11_14`, `mat_basico_15_17`, `mat_eja_*`, `mat_profissional_tecnico_*`, docentes, turmas, integral, internet, banda larga e salas.
- `censo_escolas`: as mesmas famílias no nível escola, além de `cod_escola`, situação, rede, localização e mantenedora Sistema S.
- `eja_integrada_educacao_profissional`: 39 campos de numeradores por etapa/rede e o percentual calculado.
- `ept_nivel_medio`: 39 campos de modalidade e rede.
- `rais_vinculos`: idade, grau de instrução, sexo e raça por município/ano.
- CAGED bruto: idade exata, `indicadoraprendiz`, CBO, CNAE, salário, escolaridade e tipo de movimento.
- `inse`: distribuição pelos oito níveis, além da média e quantidade de alunos.
- PNE Indicadores EB: estados `observed` e `unavailable`, necessários para não converter ausência em zero.

### Relações genéricas que os dados já permitem substituir

- Matrícula de creche/pré-escola versus população residente 0-3/4-5, por município e contribuição regional.
- Ensino médio, população 15-17, abandono/TDI e vínculos formais 15-17, sem alegação causal.
- Matrícula EJA versus estoque adulto sem conclusão em 2022, explicitando residente versus escola localizada.
- Condições escolares versus trajetória/SAEB em painéis compatíveis de município, rede, etapa e ano.
- Estrutura e mudança setorial/ocupacional observada versus oferta EPT existente, limitada à cobertura real de cursos.

### Scripts que existem, mas cuja saída necessária não está plenamente materializada

| Script | O que pode produzir | Estado factual |
|---|---|---|
| PNE `sync_censo_escolar_microdata.py` / `build_censo_escolar_panel.py` | turno, etapa, escola e outros detalhes | saídas completas de turno para 497 não encontradas; há somente recorte temporário de 3 pilotos |
| PNE `materialize_planning_scenario_snapshots.py` | snapshots de planejamento | materialização experimental existe, não cenário demográfico municipal oficial |
| PNE `rematerialize_education_attendance_projections.py` | projeções de atendimento | código/testes presentes; não substituir projeção de população |
| Vocações `atualizar_ponte_curricular.py` | ponte curso/eixo/ocupação | ponte presente, mas pequena e não exaustiva |
| Vocações `gerar_panorama_escolaridade_baixa_censo_2010_2022.py` | panorama de baixa escolaridade | scripts novos sem consumidor público confirmado |
| CEI `caged.py`, `caged_ocupacoes.py` | cubos CAGED | tabelas amplas existem; recorte juvenil admissão/desligamento/aprendiz ainda precisa materialização própria |
| CEI `prefeituras/estoque_emprego.py` | estoque mensal calculado | foi executado, porém a saída por idade tem duplicações conflitantes; requer correção/QA antes de qualquer uso |

Nenhum desses scripts foi executado nesta auditoria quando implicava download, escrita ou substituição de tabela.

## Duplicações, versões concorrentes e diferenças de conceito

### Duplicações/versões

- **População por idade:** Banco SESI `populacao_idade`, `populacao_idade_rs`, CEI `populacao_idade_rs` e arquivos Vocações. O Banco SESI multestado é a referência técnica mais completa para a integração.
- **Educação:** Banco SESI contém a série atual e granular; CEI possui tabelas `educacao_*`/`censo_escolar` mais antigas ou mais estreitas. Não misturar versões sem comparar período/schema.
- **RAIS:** Vocações guarda séries regionais/subsetor e CEI guarda cubos municipais/2025. São complementares, mas podem duplicar a mesma fonte em granularidades distintas.
- **PNE:** fonte normalizada, artefato materializado e JSON público são estágios do mesmo dado; não contam como observações independentes.
- **Vocações:** o app atual do Vale do Rio Pardo/Serra convive com `arquivo/projeto-anterior` e regionalizações antigas. O consumidor atual deve seguir os manifests do app, não os arquivos arquivados.
- **Regionalização:** FIERGS e COREDE cobrem os 497 municípios, mas definem regiões diferentes. O produto usa FIERGS; trocar o mapa altera o resultado regional.

### Conceitos com nomes semelhantes

| Nome semelhante | Diferença factual |
|---|---|
| população 15-17 × matrícula 15-17 × matrícula do ensino médio | residentes por idade; alunos matriculados por idade; alunos em uma etapa, respectivamente |
| município da matrícula × rede responsável | localização da escola versus mantenedor/ente da rede |
| trabalhador residente × vínculo localizado | o primeiro não foi encontrado; RAIS/CAGED representam o segundo |
| admissão/desligamento × saldo CAGED | fluxos separados versus diferença líquida; `caged_prefeituras` só guarda saldo |
| aprendiz empregado × oferta de aprendizagem | indicador CAGED mede vínculo/movimento; não mede vaga/programa ofertado |
| curso profissional CAPES × educação profissional técnica | pós-graduação profissional versus EPT de nível médio/FIC |
| tendência × projeção × cenário × exposição | mudança observada/estimada; extrapolação futura; futuro plausível; sensibilidade municipal a cenário regional |
| transporte escolar × deslocamento | beneficiário/financiamento/uso de transporte versus par origem-destino |
| conclusão da população × conclusão escolar anual | estoque declarado no Censo versus evento/coorte escolar |

## Inconsistências e quebras conhecidas

1. **Bloqueio de qualidade no estoque mensal por idade:** 297.492 chaves duplicadas com dois registros; a maior parte apresenta valores diferentes. Exemplos incluem valores negativos e diferenças superiores a cem vínculos. Classificação: INADEQUADA.
2. **2026 é parcial:** CAGED vai somente até junho. Nenhuma comparação anual deve tratar 2026 como ano completo.
3. **CAGED ocupação 2025 é parcial em uma tabela:** `caged_cnae_ocup` tem 9 meses em 2025, embora o CAGEDMOV bruto tenha os 12 meses.
4. **Transição interrompida:** medidas de transição existem em 2021-2022 e aparecem como descontinuadas posteriormente.
5. **INSE incompleto:** 495 de 497 municípios em 2023.
6. **Alfabetização variável:** 487 municípios no bundle 2025; participação e indisponibilidade precisam permanecer explícitas.
7. **Códigos/tipos de município:** PNE/Banco usam texto canônico; CEI mistura texto e inteiro. Converter antes de juntar.
8. **CAPES com PII:** o CSV inclui identificador, documento, nome, datas, trabalho acadêmico e orientador. Não deve ser publicado em linha nem usado como exemplo.
9. **Rótulos e encoding:** alguns CSVs legados exibem mojibake em nomes/rótulos; códigos e catálogos devem prevalecer.
10. **Cobertura de curso:** a ausência de curso em 13 municípios do Vale do Rio Pardo não pode ser interpretada automaticamente como ausência de oferta.

## Scripts responsáveis e trilha de publicação

- Banco SESI: `populacao_idade.py`, `populacao.py`, `censo_escolar.py`, `sinopse_estatistica_censo.py`, `rendimento_escolar.py`, `distorcao_idade_serie.py`, `adequacao_docente.py`, `alunos_turma.py`, `inse.py`, `alfabetizacao.py`, `saeb.py`, `saeb_proficiencia.py`, `pnate.py`, `vaar.py`, `financeiro_educacao.py` e SQLs de views.
- PNE: `sync_censo_escolar_microdata.py`, `sync_eja_integrada_from_sinopse.py`, `sync_ept_nivel_medio_from_sinopse.py`, `sync_higher_education_from_sinopse.py`, `sync_pne_capes_2024.py`, `export_education_indicators.py`, `export_static_data.py`, `partition_static_data.py`, `materialize_pne2026_public_diagnostic_v3.py` e `promote_pne2026_public_diagnostic_v3.py`.
- Vocações: `demografia.py`, `educacao.py`, `mercado_trabalho.py`, `regionalizar_csvs_rs.py`, `gerar_base_regional.py`, `gerar_pacote_vocacoes_vale_rio_pardo.py`, `atualizar_referencia_rais_subsetores.py`, `atualizar_demografia_censo_projecoes.py`, `atualizar_ponte_curricular.py` e validadores de pacote/catálogo.
- CEI: `rais_vinculos.py`, `rais_vinculos_25.py`, `rais_ocupacao.py`, `rais_ocupacoes_rs_25.py`, `rais_estabelecimentos.py`, `rais_renda.py`, `download_caged.py`, `caged.py`, `caged_ocupacoes.py` e `prefeituras/estoque_emprego.py`.

A presença de um script não foi usada como prova de dado. Cada conjunto marcado como materializado teve arquivo/tabela real perfilado. Scripts sem saída confirmada permanecem identificados como tal.

## Cobertura das análises solicitadas

| Família | PRONTA | DERIVÁVEL | PARCIAL | AUSENTE | INADEQUADA | Total |
|---|---:|---:|---:|---:|---:|---:|
| A. Demografia e matrículas | 0 | 5 | 1 | 0 | 0 | 6 |
| B. Trajetória escolar | 5 | 1 | 3 | 0 | 0 | 9 |
| C. Formação do resultado regional | 1 | 3 | 1 | 0 | 0 | 5 |
| D. EJA | 2 | 1 | 4 | 0 | 0 | 7 |
| E. Educação profissional | 3 | 0 | 4 | 2 | 1 | 10 |
| F. Trabalho juvenil e ocupações | 8 | 2 | 1 | 0 | 0 | 11 |
| G. Mobilidade territorial | 0 | 0 | 1 | 5 | 1 | 7 |
| H. Condições escolares | 7 | 1 | 1 | 0 | 0 | 9 |
| I. Futuro do território | 3 | 1 | 4 | 1 | 0 | 9 |
| **Total** | **29** | **14** | **20** | **8** | **2** | **73** |

## Matriz de prontidão do produto — resumo

| Leitura candidata | Status | Decisão sugerida |
|---|---|---|
| Educação infantil e mudança demográfica | DERIVÁVEL | construir após pequena materialização |
| Ensino fundamental e trajetória | PRONTA | construir agora |
| Ensino médio, demografia e permanência | DERIVÁVEL | construir após pequena materialização |
| EJA e público potencial | DERIVÁVEL | construir após pequena materialização |
| Educação profissional e ocupações | PARCIAL | construir após pequena materialização, com escopo explícito |
| Trabalho juvenil e permanência | DERIVÁVEL | construir após pequena materialização |
| Mobilidade regional | PARCIAL | pesquisar nova fonte dirigida |
| Reorganização da rede | DERIVÁVEL | construir após pequena materialização |
| Condições escolares e resultados | DERIVÁVEL | construir após pequena materialização |
| Futuro demográfico | PARCIAL | construir apenas coortes/tendências; não projeção municipal |
| Futuro do trabalho e qualificação | PARCIAL | pilotar nas regiões/municípios cobertos |

## Cinco dados existentes de maior valor imediato

1. RAIS municipal 2019-2025 por faixa etária e escolaridade, com 497 municípios.
2. População municipal anual por idade 2014-2025.
3. Censo Escolar por escola e agregado, incluindo matrículas por idade/etapa, EJA, EPT, rede, turmas, docentes e infraestrutura.
4. Rendimento, TDI, IDEB/SAEB, HAD, ATU, AFD, IED, IRD e INSE com chaves municipais e dimensões educacionais.
5. CAGED local 2020-jun/2026 com idade, tipo de movimento, aprendiz, CBO, CNAE, escolaridade e salário.

## Cinco lacunas comprovadas de maior impacto

1. Matriz município de residência × município de estudo/escola.
2. Matriz município de residência × município de trabalho e residência anterior.
3. Projeção demográfica municipal por idade/sexo e cenários municipais com método/horizonte.
4. Ingressantes, concluintes e capacidade/vagas da educação profissional.
5. Curso/eixo/rede EPT com cobertura de todos os municípios, além de transição/conclusão escolar anual recente.

## Conclusão

**Há dados suficientes para parte do piloto, com lacunas dirigidas.** A primeira saída pode ser construída para trajetória, demografia histórica, condições escolares, contribuição municipal e contexto de trabalho formal. A segunda saída pode ser pilotada com coortes já nascidas, tendências demográficas, mudança setorial/ocupacional observada e cenários nas duas regiões cobertas. Mobilidade OD, projeção municipal, cenários municipais e a cadeia completa ingressante–concluinte da EPT permanecem bloqueadas.

Este documento não autoriza implementação nem aquisição. A decisão de quais leituras entram na próxima rodada deve ser tomada fora deste job, usando as duas matrizes e a lista de lacunas comprovadas.
