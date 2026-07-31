# Contrato PNE 2026–2036

> Arquivo gerado por `scripts/generate-diagnostic-catalog.mjs`. Não edite manualmente.

- Fonte canônica: `contracts/pne2026-goal-indicator-contract.json`
- Versão do contrato: `1.9.0`
- Hash normalizado SHA-256: `c9f4baaee43a7f105863a07bcac69d2f56a90095b75d0c7bcde25ca533fedab5`
- Metas legais: 73
- Indicadores e fórmulas: 59
- Relações: 59 (27 progresso, 15 acompanhamento, 15 complementares e 2 ocultas)

## Metas, prazos e fórmulas

| Meta | Indicador | Modo | Tipo de referência | Valor de referência | Prazo | Fórmula |
| --- | --- | --- | --- | --- | --- | --- |
| 1.a | creche | progress | legal | 60 percent (2036) | 2036 | 100 * sum(mat_basico_0_3) / denominator_aggregate(pop_0_3) |
| 1.c | pre_escola | progress | legal | 100 percent (2028) | 2028 | 100 * sum(mat_infantil_pre) / denominator_aggregate(pop_4_5) |
| 3.a | alfabetizacao | progress | legal | 80 percent (2031); 100 percent (2036) | 2031, 2036 | PC_ALUNO_ALFABETIZADO oficial |
| 4.a | basico_15_17 | tracking | monitoring | 100 percent | sem prazo legal | 100 * sum(mat_basico_15_17) / denominator_aggregate(pop_15_17) |
| 4.a | basico_6_17 | progress | legal | 100 percent (2029) | 2029 | 100 * sum(mat_basico_6_17) / denominator_aggregate(pop_6_17) |
| 4.b | idade_regular_quinto | tracking | monitoring | 100 percent | sem prazo legal | pne2026.idade_regular_quinto |
| 4.c | idade_regular_nono | tracking | monitoring | 100 percent | sem prazo legal | pne2026.idade_regular_nono |
| 4.d | idade_regular_medio | tracking | monitoring | 100 percent | sem prazo legal | pne2026.idade_regular_medio |
| 5.a | saeb_matematica_anos_iniciais | progress | legal | 70 percent (2031); 90 percent (2036) | 2031, 2036 | pne2026.saeb_matematica_anos_iniciais |
| 5.a | saeb_portugues_anos_iniciais | progress | legal | 70 percent (2031); 90 percent (2036) | 2031, 2036 | pne2026.saeb_portugues_anos_iniciais |
| 5.b | saeb_matematica_anos_finais | progress | legal | 60 percent (2031); 85 percent (2036) | 2031, 2036 | pne2026.saeb_matematica_anos_finais |
| 5.b | saeb_portugues_anos_finais | progress | legal | 60 percent (2031); 85 percent (2036) | 2031, 2036 | pne2026.saeb_portugues_anos_finais |
| 5.d | saeb_matematica_ensino_medio | progress | legal | 50 percent (2031); 80 percent (2036) | 2031, 2036 | pne2026.saeb_matematica_ensino_medio |
| 5.d | saeb_portugues_ensino_medio | progress | legal | 50 percent (2031); 80 percent (2036) | 2031, 2036 | pne2026.saeb_portugues_ensino_medio |
| 6.a | basico_integral | progress | legal | 35 percent (2031); 50 percent (2036) | 2031, 2036 | 100 * mat_basico_integral / mat_basico |
| 6.a | escolas_integral | progress | legal | 50 percent (2031); 65 percent (2036) | 2031, 2036 | pne2026.escolas_integral |
| 7.a | banda_larga | complementary | — | — | não se aplica | pne2026.banda_larga |
| 7.a | internet | complementary | — | — | não se aplica | pne2026.internet |
| 7.a | internet_alunos | complementary | — | — | não se aplica | pne2026.internet_alunos |
| 7.a | internet_aprendizagem | complementary | — | — | não se aplica | pne2026.internet_aprendizagem |
| 7.a | rede_local | complementary | — | — | não se aplica | pne2026.rede_local |
| 7.a | rede_wireless | complementary | — | — | não se aplica | pne2026.rede_wireless |
| 8.b | salas_climatizadas | tracking | monitoring | 100 percent | sem prazo legal | pne2026.salas_climatizadas |
| 8.c | educacao_ambiental | progress | legal | 100 percent (2036) | 2036 | pne2026.educacao_ambiental |
| 9.d | educacao_indigena_cobertura_estimada_4_17 | complementary | — | — | não se aplica | 100 * matriculas_indigenas_localizadas_4_17 / populacao_indigena_residente_4_17_2022 |
| 10.b | aee_oferta_escolas_elegiveis | complementary | — | — | não se aplica | 100 * escolas_elegiveis_com_oferta_aee / escolas_com_matriculas_educacao_especial |
| 11.a | alfabetizacao_pop_15_mais | progress | legal | 97 percent (2031); 100 percent (2036) | 2031, 2036 | pne2026.alfabetizacao_pop_15_mais |
| 11.b | fundamental_concluido_15_29 | progress | legal | 100 percent (2036) | 2036 | 100 * (concluintes_15_17 + concluintes_18_24 + concluintes_25_29) / (total_15_17 + total_18_24 + total_25_29) |
| 11.b | fundamental_concluido_15_mais | progress | legal | 85 percent (2036) | 2036 | 100 * (concluintes_15_17 + concluintes_18_mais) / (total_15_17 + total_18_mais) |
| 11.b | fundamental_concluido_18_mais | hidden | — | — | não se aplica | pne2026.fundamental_concluido_18_mais |
| 11.c | medio_concluido_18_29 | progress | legal | 100 percent (2036) | 2036 | pne2026.medio_concluido_18_29 |
| 11.c | medio_concluido_18_mais | progress | legal | 75 percent (2036) | 2036 | pne2026.medio_concluido_18_mais |
| 11.d | eja_atendimento_18_mais | progress | legal | 10 percent (2031); 20 percent (2036) | 2031, 2036 | 100 × matrículas_EJA_18_mais / população_18_mais_sem_básica_concluída |
| 12.a | medio_tecnico_articulado_percentual | tracking | monitoring | 50 percent | sem prazo legal | 100 * sum(mat_integrado_total + mat_concomitante_total) / sum(mat_medio) |
| 12.a | medio_tecnico_participacao_publica | progress | legal | 50 percent (2036) | 2036 | 100 * (publica_atual - publica_2025) / (total_atual - total_2025) |
| 12.b | subsequente_expansao | progress | legal | 60 percent (2036) | 2036 | 100 * (mat_subsequente_atual - mat_subsequente_2025) / mat_subsequente_2025 |
| 12.c | eja_integrada_educacao_profissional_percentual | progress | legal | 25 percent (2031); 50 percent (2036) | 2031, 2036 | pne2026.eja_integrada_educacao_profissional_percentual |
| 14.a | graduacao_frequencia_18_24 | tracking | monitoring | 40 percent | sem prazo legal | 100 × residentes_18_24_frequentando_graduação / residentes_18_24 |
| 14.b | superior_completo_25_34 | tracking | monitoring | 40 percent | sem prazo legal | 100 × Σ superior_completo_25_29,30_34 / Σ população_25_29,30_34 |
| 14.c | superior_concluintes_oferta_local | complementary | — | — | não se aplica | concluintes_graduacao_oferta_local |
| 14.d | taxa_bruta_graduacao | progress | legal | 60 percent (2036) | 2036 | 100 × residentes_de_todas_as_idades_frequentando_graduação / residentes_18_24 |
| 15.a | cpc_cursos_oferta_local | complementary | — | — | não se aplica | 100 * cursos_CPC_3a5 / cursos_CPC_validos |
| 15.b | docentes_tempo_integral_centros_universitarios | tracking | monitoring | 40 percent | sem prazo legal | 100 × Σ docentes_TI_por_categoria / Σ docentes_totais_por_categoria |
| 15.b | docentes_tempo_integral_faculdades | tracking | monitoring | 30 percent | sem prazo legal | 100 × Σ docentes_TI_por_categoria / Σ docentes_totais_por_categoria |
| 15.b | docentes_tempo_integral_ies | progress | legal | 70 percent (2036) | 2036 | 100 × docentes_tempo_integral / docentes_em_exercício |
| 15.b | docentes_tempo_integral_universidades | tracking | monitoring | 50 percent | sem prazo legal | 100 × Σ docentes_TI_por_categoria / Σ docentes_totais_por_categoria |
| 15.c | superior_docentes_mestres_doutores_sede | complementary | — | — | não se aplica | 100 * (docentes_mestrado + docentes_doutorado) / docentes_total_titulacao_exaustiva |
| 16.a | capes_titulados_oferta_local | complementary | — | — | não se aplica | mestres_titulados_oferta_local + doutores_titulados_oferta_local |
| 17.a | adequacao_af | progress | legal | 100 percent (2031) | 2031 | pne2026.adequacao_af |
| 17.a | adequacao_ai | progress | legal | 100 percent (2031) | 2031 | pne2026.adequacao_ai |
| 17.a | adequacao_em | progress | legal | 100 percent (2031) | 2031 | pne2026.adequacao_em |
| 17.b | rendimento_magisterio | hidden | — | — | não se aplica | pne2026.rendimento_magisterio |
| 17.c | munic_planos_carreira_declarados | tracking | monitoring | 2 count | sem prazo legal | I(MEDU16=Sim) + I(MEDU21=Sim) |
| 17.d | temporarios | complementary | — | — | não se aplica | pne2026.temporarios |
| 17.e | enade_licenciaturas_oferta_local | complementary | — | — | não se aplica | 100 * concluintes_padrao_1 / concluintes_participantes_validos |
| 17.f | pos_graduacao | complementary | — | — | não se aplica | pne2026.pos_graduacao |
| 18.b | conselho_escolar | tracking | monitoring | 100 percent | sem prazo legal | pne2026.conselho_escolar |
| 18.c | munic_forum_educacao_declarado | tracking | monitoring | 1 count | sem prazo legal | I(MEDU15=Sim) |
| 19.c | salas_acessiveis | tracking | monitoring | 100 percent | sem prazo legal | pne2026.salas_acessiveis |

## Linhagem populacional

| Fonte | Conjunto de origem | Artefato versionado | SHA-256 | Configuração reproduzível |
| --- | --- | --- | --- | --- | --- |
| municipal_age_population_panel | Estudo de Estimativas Populacionais por Município, Idade e Sexo | POP25.dbf | `ffa3a2c91a8fc33b8b606137b50cf3b0d52b879eb3b92a96a6453661ccb9a38d` | `SESI_DB_DIR` |
| ibge_population_projection_2024 | Projeções das Populações, revisão 2024 — população por sexo e idade simples, 2000–2070 | projecao_pop.xlsx | `6e5c3d21a2e8ff50badd7be2785e1664b41a43277543be541641b0cd802c3205` | `POPULATION_PROJECTION_SOURCE_PATH` |

## Fontes declaradas

| Identificador | Organização | Período | URL |
| --- | --- | --- | --- |
| capes_sucupira_2024 | Coordenação de Aperfeiçoamento de Pessoal de Nível Superior (CAPES) | — | [link oficial](https://dadosabertos.capes.gov.br/) |
| ibge_censo_demografico_2010_2022 | Instituto Brasileiro de Geografia e Estatística (IBGE) | — | [link oficial](https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-censo-demografico-2022.html) |
| ibge_censo_demografico_2022_educacao_10061 | Instituto Brasileiro de Geografia e Estatística (IBGE) | — | [link oficial](https://sidra.ibge.gov.br/tabela/10061) |
| ibge_censo_demografico_2022_educacao_superior | Instituto Brasileiro de Geografia e Estatística (IBGE) | — | [link oficial](https://sidra.ibge.gov.br/pesquisa/censo-demografico/demografico-2022/resultados-do-universo-educacao) |
| ibge_censo_demografico_2022_indigena_9970 | Instituto Brasileiro de Geografia e Estatística (IBGE) | — | [link oficial](https://sidra.ibge.gov.br/tabela/9970) |
| ibge_munic_2021 | Instituto Brasileiro de Geografia e Estatística (IBGE) | — | [link oficial](https://ftp.ibge.gov.br/Perfil_Municipios/2021/Base_de_Dados/Base_MUNIC_2021_20240425.xlsx) |
| ibge_population_projection_2024 | Instituto Brasileiro de Geografia e Estatística (IBGE) | 2000–2070 | [link oficial](https://www.ibge.gov.br/estatisticas/sociais/populacao/9109-projecao-da-populacao.html) |
| inep_avaliacao_alfabetizacao | Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP) | — | [link oficial](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/avaliacoes-da-educacao-basica) |
| inep_censo_educacao_superior | Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP) | — | [link oficial](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior) |
| inep_censo_escolar | Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP) | — | [link oficial](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar) |
| inep_cpc_2023 | Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP) | — | [link oficial](https://download.inep.gov.br/educacao_superior/indicadores/resultados/2023/CPC_2023.xlsx) |
| inep_enade_licenciaturas_2025 | Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP) | — | [link oficial](https://download.inep.gov.br/educacao_superior/indicadores/resultados/2025/conceito_enade_licenciaturas.xlsx) |
| inep_saeb | Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP) | — | [link oficial](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/saeb) |
| inep_sinopse_educacao_basica | Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP) | — | [link oficial](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/sinopses-estatisticas/educacao-basica) |
| lei_15388_2026 | Presidência da República | — | [link oficial](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2026/lei/l15388.htm) |
| municipal_age_population_panel | Ministério da Saúde (MS) / DATASUS | 2000–2025 | [link oficial](https://datasus.saude.gov.br/populacao-residente) |
| pipeline_rendimento_professores_provenance_pending | — | — | — |

