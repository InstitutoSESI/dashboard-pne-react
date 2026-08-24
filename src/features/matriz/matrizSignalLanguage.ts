import type { MatrizSignal } from './matrizTypes.js'

/*
 * Linguagem pública dos sinais da matriz de prioridades.
 *
 * Os identificadores e recortes técnicos permanecem no artefato. Esta camada
 * mantém somente rótulos autorados e qualificadores que um gestor reconhece.
 * Medidas sem rótulo não recebem fallback visível.
 */

export interface MatrizSignalReading {
  readonly caution: string
  readonly display: string
  readonly label: string
  readonly period: string
}

export const MEASURE_LABEL: Readonly<Record<string, string>> = Object.freeze({
  'ibge.cempre.employed_persons_total': 'Pessoas ocupadas nas empresas e organizações locais',
  'ibge.cempre.local_units': 'Unidades locais de empresas e organizações',
  'ibge.cempre.salaried_persons': 'Pessoas assalariadas nas empresas e organizações locais',
  'ibge.cempre.wages_thousand_brl': 'Salários e outras remunerações pagos por empresas e organizações',
  'ibge.gdp_current_prices_thousand_brl': 'Produto interno bruto municipal a preços correntes',
  'ibge.gdp_share_of_state_percent': 'Participação do município no PIB estadual',
  'ibge.munic.direct_administration_staff_total': 'Servidores da administração direta',
  'ibge.munic.direct_administration_without_permanent_bond': 'Servidores sem vínculo permanente',
  'ibge.munic.early_childhood_committee_meetings_last_12_months': 'Reuniões do comitê da primeira infância nos últimos 12 meses',
  'ibge.munic.early_childhood_intersectoral_committee_exists': 'Comitê intersetorial da primeira infância',
  'ibge.munic.early_childhood_plan_status': 'Situação do plano municipal pela primeira infância',
  'ibge.munic.public_transport_accessibility_action': 'Ação de acessibilidade no transporte público',
  'ibge.munic.social_assistance_council_status': 'Conselho municipal de assistência social em funcionamento',
  'ibge.munic.social_assistance_council_transport_support': 'Apoio de transporte ao conselho de assistência social',
  'ibge.munic.social_assistance_plan_evaluated_annually': 'Avaliação anual do plano de assistência social',
  'ibge.munic.social_assistance_plan_exists': 'Plano municipal de assistência social',
  'ibge.munic.social_assistance_receives_state_technical_support': 'Apoio técnico estadual à assistência social',

  'inep.atu.creche': 'Média de alunos por turma — creche',
  'inep.atu.ed_inf_total': 'Média de alunos por turma — educação infantil',
  'inep.atu.fun_af': 'Média de alunos por turma — anos finais',
  'inep.atu.fun_ai': 'Média de alunos por turma — anos iniciais',
  'inep.atu.fun_total': 'Média de alunos por turma — ensino fundamental',
  'inep.atu.med_total': 'Média de alunos por turma — ensino médio',
  'inep.atu.multietapa': 'Média de alunos por turma — turmas multietapa',
  'inep.atu.pre_escola': 'Média de alunos por turma — pré-escola',
  'inep.afd.grupo1.ed_inf': 'Professores com formação adequada — educação infantil',
  'inep.afd.grupo1.eja_fun': 'Professores com formação adequada — EJA do ensino fundamental',
  'inep.afd.grupo1.eja_med': 'Professores com formação adequada — EJA do ensino médio',
  'inep.afd.grupo1.fun_af': 'Professores com formação adequada — anos finais',
  'inep.afd.grupo1.fun_ai': 'Professores com formação adequada — anos iniciais',
  'inep.afd.grupo1.fun_total': 'Professores com formação adequada — ensino fundamental',
  'inep.afd.grupo1.med': 'Professores com formação adequada — ensino médio',
  'inep.afd.grupo3.ed_inf': 'Professores formados em outra área — educação infantil',
  'inep.afd.grupo3.eja_fun': 'Professores formados em outra área — EJA do ensino fundamental',
  'inep.afd.grupo3.eja_med': 'Professores formados em outra área — EJA do ensino médio',
  'inep.afd.grupo3.fun_af': 'Professores formados em outra área — anos finais',
  'inep.afd.grupo3.fun_ai': 'Professores formados em outra área — anos iniciais',
  'inep.afd.grupo3.fun_total': 'Professores formados em outra área — ensino fundamental',
  'inep.afd.grupo3.med': 'Professores formados em outra área — ensino médio',
  'inep.afd.grupo5.ed_inf': 'Professores sem formação superior — educação infantil',
  'inep.afd.grupo5.eja_fun': 'Professores sem formação superior — EJA do ensino fundamental',
  'inep.afd.grupo5.eja_med': 'Professores sem formação superior — EJA do ensino médio',
  'inep.afd.grupo5.fun_af': 'Professores sem formação superior — anos finais',
  'inep.afd.grupo5.fun_ai': 'Professores sem formação superior — anos iniciais',
  'inep.afd.grupo5.fun_total': 'Professores sem formação superior — ensino fundamental',
  'inep.afd.grupo5.med': 'Professores sem formação superior — ensino médio',
  'inep.alfabetizacao.media_lp': 'Desempenho médio em alfabetização',
  'inep.alfabetizacao.pc_alfabetizado': 'Estudantes alfabetizados ao final do 2º ano',
  'inep.censo_escolar.microdados.esc_agua_potavel': 'Escolas com água potável',
  'inep.censo_escolar.microdados.esc_alimentacao_escolar': 'Escolas com alimentação escolar',
  'inep.censo_escolar.microdados.esc_banda_larga': 'Escolas com internet de banda larga',
  'inep.censo_escolar.microdados.esc_banheiro': 'Escolas com banheiro',
  'inep.censo_escolar.microdados.esc_banheiro_acessivel': 'Escolas com banheiro acessível',
  'inep.censo_escolar.microdados.esc_biblioteca_sala_leitura': 'Escolas com biblioteca ou sala de leitura',
  'inep.censo_escolar.microdados.esc_coleta_lixo': 'Escolas com coleta de lixo',
  'inep.censo_escolar.microdados.esc_cozinha': 'Escolas com cozinha',
  'inep.censo_escolar.microdados.esc_internet': 'Escolas com acesso à internet',
  'inep.censo_escolar.microdados.esc_internet_alunos': 'Escolas com internet para uso dos alunos',
  'inep.censo_escolar.microdados.esc_lab_informatica': 'Escolas com laboratório de informática',
  'inep.censo_escolar.microdados.esc_localizacao_diferenciada': 'Escolas em área de localização diferenciada',
  'inep.censo_escolar.microdados.esc_oferta_aee': 'Escolas que oferecem atendimento educacional especializado',
  'inep.censo_escolar.microdados.esc_refeitorio': 'Escolas com refeitório',
  'inep.censo_escolar.microdados.esc_sala_recursos_aee': 'Escolas com sala de recursos para atendimento especializado',
  'inep.censo_escolar.microdados.esc_sem_abastecimento_agua': 'Escolas sem abastecimento de água',
  'inep.censo_escolar.microdados.esc_sem_energia': 'Escolas sem energia elétrica',
  'inep.censo_escolar.microdados.esc_sem_esgoto': 'Escolas sem esgotamento sanitário',
  'inep.censo_escolar.microdados.esc_sem_recursos_acessibilidade': 'Escolas sem recursos de acessibilidade',
  'inep.censo_escolar.microdados.mat_transporte_publico': 'Matrículas de estudantes que usam transporte escolar público',
  'inep.censo_escolar.microdados.mat_transporte_resp_estadual': 'Matrículas com transporte escolar oferecido pelo estado',
  'inep.censo_escolar.microdados.mat_transporte_resp_municipal': 'Matrículas com transporte escolar oferecido pelo município',
  'inep.censo_escolar.sinopse.est_rural_total': 'Escolas em área rural',
  'inep.censo_escolar.sinopse.mat_eja_fund': 'Matrículas na EJA do ensino fundamental',
  'inep.censo_escolar.sinopse.mat_eja_medio': 'Matrículas na EJA do ensino médio',
  'inep.censo_escolar.sinopse.mat_eja_total': 'Matrículas na EJA',
  'inep.censo_escolar.sinopse.mat_especial_classes_comuns': 'Matrículas da educação especial em classes comuns',
  'inep.censo_escolar.sinopse.mat_especial_classes_exclusivas': 'Matrículas da educação especial em classes exclusivas',
  'inep.censo_escolar.sinopse.mat_rural_total': 'Matrículas em escolas rurais',
  'inep.censo_escolar.sinopse.mat_tempo_integral_creche': 'Matrículas em tempo integral — creche',
  'inep.censo_escolar.sinopse.mat_tempo_integral_fund_af': 'Matrículas em tempo integral — anos finais',
  'inep.censo_escolar.sinopse.mat_tempo_integral_fund_ai': 'Matrículas em tempo integral — anos iniciais',
  'inep.censo_escolar.sinopse.mat_tempo_integral_medio': 'Matrículas em tempo integral — ensino médio',
  'inep.censo_escolar.sinopse.mat_tempo_integral_pre': 'Matrículas em tempo integral — pré-escola',
  'inep.censo_escolar.sinopse.mat_tempo_integral_rede_publica': 'Matrículas em tempo integral — rede pública',
  'inep.censo_escolar.sinopse.mat_tempo_integral_total': 'Matrículas em tempo integral — total',
  'inep.had.creche': 'Jornada média diária — creche',
  'inep.had.ed_inf_total': 'Jornada média diária — educação infantil',
  'inep.had.fun_af': 'Jornada média diária — anos finais',
  'inep.had.fun_ai': 'Jornada média diária — anos iniciais',
  'inep.had.fun_total': 'Jornada média diária — ensino fundamental',
  'inep.had.med_total': 'Jornada média diária — ensino médio',
  'inep.had.pre_escola': 'Jornada média diária — pré-escola',
  'inep.ideb.af.ideb_observado': 'Ideb — anos finais',
  'inep.ideb.af.indicador_rendimento': 'Indicador de rendimento do Ideb — anos finais',
  'inep.ideb.af.nota_media_padronizada': 'Desempenho médio padronizado — anos finais',
  'inep.ideb.af.nota_saeb_lp': 'Desempenho no Saeb em língua portuguesa — anos finais',
  'inep.ideb.af.nota_saeb_matematica': 'Desempenho no Saeb em matemática — anos finais',
  'inep.ideb.ai.ideb_observado': 'Ideb — anos iniciais',
  'inep.ideb.ai.indicador_rendimento': 'Indicador de rendimento do Ideb — anos iniciais',
  'inep.ideb.ai.nota_media_padronizada': 'Desempenho médio padronizado — anos iniciais',
  'inep.ideb.ai.nota_saeb_lp': 'Desempenho no Saeb em língua portuguesa — anos iniciais',
  'inep.ideb.ai.nota_saeb_matematica': 'Desempenho no Saeb em matemática — anos iniciais',
  'inep.ideb.em.ideb_observado': 'Ideb — ensino médio',
  'inep.ideb.em.indicador_rendimento': 'Indicador de rendimento do Ideb — ensino médio',
  'inep.ideb.em.nota_media_padronizada': 'Desempenho médio padronizado — ensino médio',
  'inep.ideb.em.nota_saeb_lp': 'Desempenho no Saeb em língua portuguesa — ensino médio',
  'inep.ideb.em.nota_saeb_matematica': 'Desempenho no Saeb em matemática — ensino médio',
  'inep.ied.nivel_1.fun_af': 'Professores com jornada de trabalho mais concentrada — anos finais',
  'inep.ied.nivel_1.fun_ai': 'Professores com jornada de trabalho mais concentrada — anos iniciais',
  'inep.ied.nivel_1.fun_total': 'Professores com jornada de trabalho mais concentrada — ensino fundamental',
  'inep.ied.nivel_1.med_total': 'Professores com jornada de trabalho mais concentrada — ensino médio',
  'inep.ied.nivel_5.fun_af': 'Professores com jornada de trabalho intensa — anos finais',
  'inep.ied.nivel_5.fun_ai': 'Professores com jornada de trabalho intensa — anos iniciais',
  'inep.ied.nivel_5.fun_total': 'Professores com jornada de trabalho intensa — ensino fundamental',
  'inep.ied.nivel_5.med_total': 'Professores com jornada de trabalho intensa — ensino médio',
  'inep.ied.nivel_6.fun_af': 'Professores com jornada de trabalho mais intensa — anos finais',
  'inep.ied.nivel_6.fun_ai': 'Professores com jornada de trabalho mais intensa — anos iniciais',
  'inep.ied.nivel_6.fun_total': 'Professores com jornada de trabalho mais intensa — ensino fundamental',
  'inep.ied.nivel_6.med_total': 'Professores com jornada de trabalho mais intensa — ensino médio',
  'inep.inse.media_inse': 'Nível socioeconômico médio dos alunos',
  'inep.ird.faixa_2_a_3': 'Professores com vínculo de baixa estabilidade na escola',
  'inep.ird.faixa_3_a_4': 'Professores com vínculo de estabilidade intermediária na escola',
  'inep.ird.faixa_4_a_5': 'Professores com vínculo mais estável na escola',
  'inep.ird.faixa_ate_2': 'Professores com vínculo menos estável na escola',
  'inep.rendimento.abandono.fun_af': 'Abandono escolar — anos finais',
  'inep.rendimento.abandono.fun_ai': 'Abandono escolar — anos iniciais',
  'inep.rendimento.abandono.fun_total': 'Abandono escolar — ensino fundamental',
  'inep.rendimento.abandono.med_total': 'Abandono escolar — ensino médio',
  'inep.rendimento.aprovacao.fun_af': 'Aprovação escolar — anos finais',
  'inep.rendimento.aprovacao.fun_ai': 'Aprovação escolar — anos iniciais',
  'inep.rendimento.aprovacao.fun_total': 'Aprovação escolar — ensino fundamental',
  'inep.rendimento.aprovacao.med_total': 'Aprovação escolar — ensino médio',
  'inep.rendimento.reprovacao.fun_af': 'Reprovação escolar — anos finais',
  'inep.rendimento.reprovacao.fun_ai': 'Reprovação escolar — anos iniciais',
  'inep.rendimento.reprovacao.fun_total': 'Reprovação escolar — ensino fundamental',
  'inep.rendimento.reprovacao.med_total': 'Reprovação escolar — ensino médio',
  'inep.tdi.fun_af': 'Distorção idade-série — anos finais',
  'inep.tdi.fun_ai': 'Distorção idade-série — anos iniciais',
  'inep.tdi.fun_total': 'Distorção idade-série — ensino fundamental',
  'inep.tdi.med_total': 'Distorção idade-série — ensino médio',
  'inep.transicao.evasao.fun_af': 'Evasão escolar — anos finais',
  'inep.transicao.evasao.fun_ai': 'Evasão escolar — anos iniciais',
  'inep.transicao.evasao.fun_total': 'Evasão escolar — ensino fundamental',
  'inep.transicao.evasao.med_total': 'Evasão escolar — ensino médio',
  'inep.transicao.migracao_eja.fun_af': 'Migração para a EJA — anos finais',
  'inep.transicao.migracao_eja.fun_ai': 'Migração para a EJA — anos iniciais',
  'inep.transicao.migracao_eja.fun_total': 'Migração para a EJA — ensino fundamental',
  'inep.transicao.migracao_eja.med_total': 'Migração para a EJA — ensino médio',
  'inep.transicao.promocao.fun_af': 'Progressão para a etapa seguinte — anos finais',
  'inep.transicao.promocao.fun_ai': 'Progressão para a etapa seguinte — anos iniciais',
  'inep.transicao.promocao.fun_total': 'Progressão para a etapa seguinte — ensino fundamental',
  'inep.transicao.promocao.med_total': 'Progressão para a etapa seguinte — ensino médio',
  'inep.transicao.repetencia.fun_af': 'Repetência — anos finais',
  'inep.transicao.repetencia.fun_ai': 'Repetência — anos iniciais',
  'inep.transicao.repetencia.fun_total': 'Repetência — ensino fundamental',
  'inep.transicao.repetencia.med_total': 'Repetência — ensino médio',
  'inep.censo_escolar.sinopse.mat_educacao_profissional_total': 'Matrículas na educação profissional',

  'mds.censo_suas.council.audit_scope.does_not_audit': 'Conselho de assistência social não realiza fiscalização',
  'mds.censo_suas.council.audit_scope.entities_only': 'Fiscalização do conselho restrita às entidades socioassistenciais',
  'mds.censo_suas.council.audit_scope.full_network': 'Fiscalização do conselho em toda a rede socioassistencial',
  'mds.censo_suas.council.audit_scope.public_units_only': 'Fiscalização do conselho restrita às unidades públicas',
  'mds.censo_suas.council.audits_pbf_execution': 'Conselho fiscaliza a execução do Bolsa Família',
  'mds.censo_suas.council.deliberated_annual_budget': 'Conselho deliberou sobre o orçamento anual',
  'mds.censo_suas.council.fund_report_review_frequency.annual': 'Prestação de contas do fundo analisada anualmente',
  'mds.censo_suas.council.fund_report_review_frequency.bimonthly': 'Prestação de contas do fundo analisada a cada dois meses',
  'mds.censo_suas.council.fund_report_review_frequency.four_monthly': 'Prestação de contas do fundo analisada a cada quatro meses',
  'mds.censo_suas.council.fund_report_review_frequency.monthly': 'Prestação de contas do fundo analisada mensalmente',
  'mds.censo_suas.council.fund_report_review_frequency.quarterly': 'Prestação de contas do fundo analisada a cada três meses',
  'mds.censo_suas.council.fund_report_review_frequency.semiannual': 'Prestação de contas do fundo analisada semestralmente',
  'mds.censo_suas.council.fund_report_review_frequency.undefined': 'Prestação de contas do fundo sem frequência definida',
  'mds.censo_suas.council.invites_users_to_plenary': 'Usuários convidados para as reuniões do conselho',
  'mds.censo_suas.council.specific_budget_foreseen': 'Orçamento específico previsto para o conselho',
  'mds.censo_suas.council.weekly_operating_hours.30_39': 'Funcionamento semanal do conselho — de 30 a 39 horas',
  'mds.censo_suas.council.weekly_operating_hours.40_49': 'Funcionamento semanal do conselho — de 40 a 49 horas',
  'mds.censo_suas.council.weekly_operating_hours.over_49': 'Funcionamento semanal do conselho — mais de 49 horas',
  'mds.censo_suas.council.weekly_operating_hours.under_30': 'Funcionamento semanal do conselho — menos de 30 horas',
  'mds.censo_suas.cras.child_labor_prevention_collective_topic': 'CRAS trabalha a prevenção do trabalho infantil em atividades coletivas',
  'mds.censo_suas.cras.paif_active_search': 'CRAS realiza busca ativa para acompanhamento familiar',
  'mds.censo_suas.cras.pbf_conditionality_followup': 'CRAS acompanha famílias em descumprimento de condições do Bolsa Família',
  'mds.censo_suas.cras.scfv_age_0_6': 'Serviço de convivência atende crianças de 0 a 6 anos',
  'mds.censo_suas.cras.scfv_age_15_17': 'Serviço de convivência atende adolescentes de 15 a 17 anos',
  'mds.censo_suas.cras.scfv_age_7_14': 'Serviço de convivência atende crianças e adolescentes de 7 a 14 anos',
  'mds.censo_suas.cras.scfv_directly_offered': 'CRAS oferece diretamente o serviço de convivência',
  'mds.censo_suas.cras.scfv_school_reinforcement': 'Serviço de convivência oferece apoio às atividades escolares',
  'mds.censo_suas.creas.adolescent_school_attendance_monitoring': 'CREAS acompanha a frequência escolar de adolescentes',
  'mds.censo_suas.creas.identifies_child_labor_or_sexual_exploitation': 'CREAS identifica situações de trabalho infantil ou exploração sexual',
  'mds.censo_suas.creas.pbf_rights_violation_followup': 'CREAS acompanha violações de direitos de famílias do Bolsa Família',
  'mds.censo_suas.creas.referral_education_policy': 'CREAS encaminha famílias para a política de educação',
  'mds.censo_suas.creas.referral_other_public_policies': 'CREAS encaminha famílias para outras políticas públicas',
  'mds.censo_suas.fund.own_municipal_expenditure': 'Recursos municipais usados pelo fundo de assistência social',
  'mds.censo_suas.fund.state_resources_received': 'Recursos estaduais recebidos pelo fundo de assistência social',
  'mds.censo_suas.fund.state_transfer_expenditure': 'Recursos estaduais usados pelo fundo de assistência social',
  'mds.censo_suas.management.bpc_school_inclusion_articulation': 'Assistência social articula a inclusão escolar de beneficiários do BPC',
  'mds.censo_suas.management.child_labor_active_search_cadunico': 'Busca ativa de trabalho infantil com apoio do Cadastro Único',
  'mds.censo_suas.management.child_labor_referral_scfv': 'Encaminhamento de situações de trabalho infantil ao serviço de convivência',
  'mds.censo_suas.management.identifies_child_labor_locations': 'Gestão identifica locais com ocorrência de trabalho infantil',
  'mds.censo_suas.management.pbf_integrated_spending_health_education': 'Uso integrado de recursos do Bolsa Família com saúde e educação',
  'mds.censo_suas.management.socioterritorial_diagnosis_exists': 'Diagnóstico socioterritorial da assistência social',
  'mds.censo_suas.management.surveillance_structure.formal': 'Vigilância socioassistencial em estrutura formal',
  'mds.censo_suas.management.surveillance_structure.informal': 'Vigilância socioassistencial em estrutura informal',
  'mds.censo_suas.management.surveillance_structure.not_constituted': 'Vigilância socioassistencial não constituída',
  'mds.censo_suas.management.users_child_labor': 'Pessoas acompanhadas por situação de trabalho infantil',
  'mds.censo_suas.management.users_out_of_school_or_age_distortion': 'Pessoas acompanhadas fora da escola ou com atraso escolar',

  'midr.atlas.deaths': 'Mortes registradas em desastres',
  'midr.atlas.direct_human_damage_total': 'Pessoas diretamente afetadas por desastres',
  'midr.atlas.disaster_event': 'Evento de desastre registrado',
  'midr.atlas.displaced': 'Pessoas desalojadas por desastres',
  'midr.atlas.drought_affected': 'Pessoas afetadas por estiagem ou seca',
  'midr.atlas.education_facilities_damage_value': 'Valor dos danos em unidades de educação',
  'midr.atlas.education_facilities_damaged': 'Unidades de educação danificadas',
  'midr.atlas.education_facilities_destroyed': 'Unidades de educação destruídas',
  'midr.atlas.homeless': 'Pessoas desabrigadas por desastres',
  'midr.atlas.infrastructure_works_damage_value': 'Valor dos danos em obras de infraestrutura',
  'midr.atlas.infrastructure_works_damaged': 'Obras de infraestrutura danificadas',
  'midr.atlas.infrastructure_works_destroyed': 'Obras de infraestrutura destruídas',
  'midr.atlas.injured': 'Pessoas feridas em desastres',
  'midr.atlas.material_damage_total': 'Valor total dos danos materiais',
  'midr.atlas.missing': 'Pessoas desaparecidas em desastres',
  'midr.atlas.other_affected': 'Outras pessoas afetadas por desastres',
  'midr.atlas.private_loss_total': 'Valor total dos prejuízos privados',
  'midr.atlas.public_education_loss': 'Prejuízos públicos na educação',
  'midr.atlas.public_energy_loss': 'Prejuízos públicos no fornecimento de energia',
  'midr.atlas.public_loss_total': 'Valor total dos prejuízos públicos',
  'midr.atlas.public_private_loss_total': 'Valor total dos prejuízos públicos e privados',
  'midr.atlas.public_telecommunications_loss': 'Prejuízos públicos em telecomunicações',
  'midr.atlas.public_transport_loss': 'Prejuízos públicos em transporte',
  'midr.atlas.sick': 'Pessoas enfermas em desastres',

  'sinisa.governance.municipal_sanitation_policy_law_exists': 'Política municipal de saneamento instituída por lei',
  'sinisa.governance.sanitation_plan_exists': 'Plano municipal de saneamento',
  'sinisa.sewerage.public_collection_service_exists': 'Serviço público de coleta de esgoto',
  'sinisa.solid_waste.public_service_exists': 'Serviço público de manejo de resíduos sólidos',
  'sinisa.urban_drainage.public_service_exists': 'Serviço público de drenagem urbana',
  'sinisa.water.public_network_service_exists': 'Serviço público de abastecimento de água',

  'stn.siconfi.dca.early_childhood_education.committed': 'Despesas empenhadas em educação infantil',
  'stn.siconfi.dca.early_childhood_education.liquidated': 'Despesas liquidadas em educação infantil',
  'stn.siconfi.dca.early_childhood_education.outstanding_non_processed': 'Restos a pagar não processados em educação infantil',
  'stn.siconfi.dca.early_childhood_education.outstanding_processed': 'Restos a pagar processados em educação infantil',
  'stn.siconfi.dca.early_childhood_education.paid': 'Despesas pagas em educação infantil',
  'stn.siconfi.dca.education_total.committed': 'Despesas empenhadas em educação',
  'stn.siconfi.dca.education_total.liquidated': 'Despesas liquidadas em educação',
  'stn.siconfi.dca.education_total.outstanding_non_processed': 'Restos a pagar não processados em educação',
  'stn.siconfi.dca.education_total.outstanding_processed': 'Restos a pagar processados em educação',
  'stn.siconfi.dca.education_total.paid': 'Despesas pagas em educação',
  'stn.siconfi.dca.elementary_education.committed': 'Despesas empenhadas no ensino fundamental',
  'stn.siconfi.dca.elementary_education.liquidated': 'Despesas liquidadas no ensino fundamental',
  'stn.siconfi.dca.elementary_education.outstanding_non_processed': 'Restos a pagar não processados no ensino fundamental',
  'stn.siconfi.dca.elementary_education.outstanding_processed': 'Restos a pagar processados no ensino fundamental',
  'stn.siconfi.dca.elementary_education.paid': 'Despesas pagas no ensino fundamental',
  'stn.siconfi.dca.municipal_total.committed': 'Despesas municipais totais empenhadas',
  'stn.siconfi.dca.municipal_total.liquidated': 'Despesas municipais totais liquidadas',
  'stn.siconfi.dca.municipal_total.outstanding_non_processed': 'Restos a pagar municipais não processados',
  'stn.siconfi.dca.municipal_total.outstanding_processed': 'Restos a pagar municipais processados',
  'stn.siconfi.dca.municipal_total.paid': 'Despesas municipais totais pagas',
  'stn.siconfi.dca.special_education.committed': 'Despesas empenhadas em educação especial',
  'stn.siconfi.dca.special_education.liquidated': 'Despesas liquidadas em educação especial',
  'stn.siconfi.dca.special_education.outstanding_non_processed': 'Restos a pagar não processados em educação especial',
  'stn.siconfi.dca.special_education.outstanding_processed': 'Restos a pagar processados em educação especial',
  'stn.siconfi.dca.special_education.paid': 'Despesas pagas em educação especial',
})

const COUNT_UNITS: Readonly<Record<string, readonly [string, string]>> = Object.freeze({
  enrollments: Object.freeze(['matrícula', 'matrículas'] as const),
  event: Object.freeze(['evento', 'eventos'] as const),
  facilities: Object.freeze(['unidade', 'unidades'] as const),
  meetings: Object.freeze(['reunião', 'reuniões'] as const),
  persons: Object.freeze(['pessoa', 'pessoas'] as const),
  persons_as_reported: Object.freeze(['pessoa', 'pessoas'] as const),
  schools: Object.freeze(['escola', 'escolas'] as const),
  works: Object.freeze(['obra', 'obras'] as const),
})

const DEPENDENCY_LABEL: Readonly<Record<string, string>> = Object.freeze({
  estadual: 'rede estadual',
  municipal: 'rede municipal',
  privada: 'rede privada',
  publica: 'rede pública',
  total: 'todas as redes',
})

const NETWORK_LABEL: Readonly<Record<string, string>> = Object.freeze({
  estadual: 'rede estadual',
  municipal: 'rede municipal',
  publica: 'rede pública',
  publica_estadual_municipal: 'redes estadual e municipal',
})

const LOCATION_LABEL: Readonly<Record<string, string>> = Object.freeze({
  rural: 'área rural',
  urbana: 'área urbana',
})

const SERIES_LABEL: Readonly<Record<string, string>> = Object.freeze({
  '2_ano_fundamental': '2º ano do ensino fundamental',
})

function formatNumber(valueRaw: string, options: Intl.NumberFormatOptions): string | null {
  const numericValue = Number(valueRaw)
  if (!Number.isFinite(numericValue)) return null
  return new Intl.NumberFormat('pt-BR', options).format(numericValue)
}

function formatCount(unit: string, valueRaw: string): string {
  const numericValue = Number(valueRaw)
  if (!Number.isFinite(numericValue)) return valueRaw
  const words = COUNT_UNITS[unit]
  const word = Math.abs(numericValue) === 1 ? words[0] : words[1]
  return `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 }).format(numericValue)} ${word}`
}

/** Formata somente para exibição; não classifica nem compara sinais. */
export function formatSignalValue(unit: string, valueRaw: string, direction: string): string | null {
  if (valueRaw.trim() === '') return null

  if (unit === 'boolean_indicator' || unit === 'category_code') {
    void direction
    if (valueRaw === '1') return 'Sim — declarado pelo município'
    if (valueRaw === '0') return 'Não declarado pelo município'
    return null
  }

  if (unit === 'percent') {
    const formatted = formatNumber(valueRaw, { maximumFractionDigits: 1 })
    return formatted === null ? valueRaw : `${formatted}%`
  }
  if (unit === 'BRL_as_reported') {
    const formatted = formatNumber(valueRaw, { maximumFractionDigits: 0 })
    return formatted === null ? valueRaw : `R$ ${formatted}`
  }
  if (unit === 'thousand_brl_current_prices') {
    const formatted = formatNumber(valueRaw, { maximumFractionDigits: 0 })
    return formatted === null ? valueRaw : `R$ ${formatted} mil`
  }
  if (COUNT_UNITS[unit]) return formatCount(unit, valueRaw)
  if (unit === 'students_per_class') {
    const formatted = formatNumber(valueRaw, { maximumFractionDigits: 1 })
    return formatted === null ? valueRaw : `${formatted} alunos por turma`
  }
  if (unit === 'inse_scale_points') {
    const formatted = formatNumber(valueRaw, { maximumFractionDigits: 2 })
    return formatted === null ? valueRaw : `${formatted} pontos`
  }
  if (unit === 'saeb_scale_points') {
    const formatted = formatNumber(valueRaw, { maximumFractionDigits: 1 })
    return formatted === null ? valueRaw : `${formatted} pontos Saeb`
  }
  if (unit === 'ideb_index' || unit === 'standardized_score') {
    return formatNumber(valueRaw, { maximumFractionDigits: 1 }) ?? valueRaw
  }
  if (unit === 'hours_per_day') {
    const formatted = formatNumber(valueRaw, { maximumFractionDigits: 1 })
    return formatted === null ? valueRaw : `${formatted} horas por dia`
  }
  if (unit === 'ratio') return formatNumber(valueRaw, { maximumFractionDigits: 3 }) ?? valueRaw

  return valueRaw
}

function parseDimensions(dimensions: string): Readonly<Record<string, string>> {
  const entries: Record<string, string> = {}
  for (const part of dimensions.split(';')) {
    const separator = part.indexOf('=')
    if (separator <= 0) continue
    entries[part.slice(0, separator)] = part.slice(separator + 1)
  }
  return entries
}

function disasterDate(protocol: string | undefined): string | null {
  const match = protocol?.match(/(\d{4})(\d{2})(\d{2})$/)
  if (!match) return null
  return `${match[3]}/${match[2]}/${match[1]}`
}

function dimensionQualifier(dimensions: string): string | null {
  if (!dimensions) return null
  const values = parseDimensions(dimensions)

  if (values.disasterType) {
    const date = disasterDate(values.protocolS2id)
    return date ? `${values.disasterType} (${date})` : values.disasterType
  }

  const qualifiers: string[] = []
  const dependency = DEPENDENCY_LABEL[values.dependencia]
  const network = NETWORK_LABEL[values.rede]
  const location = LOCATION_LABEL[values.localizacao]
  const series = SERIES_LABEL[values.serie]
  if (dependency) qualifiers.push(dependency)
  else if (network) qualifiers.push(network)
  if (location) qualifiers.push(location)
  if (series) qualifiers.push(series)
  return qualifiers.length > 0 ? qualifiers.join(', ') : null
}

/** Resolve um sinal para linguagem pública ou o omite silenciosamente. */
export function resolveSignalReading(
  signal: MatrizSignal,
): MatrizSignalReading | null {
  const label = MEASURE_LABEL[signal.measureId]
  if (!label) return null
  const value = formatSignalValue(signal.unit, signal.valueRaw, signal.direction)
  if (value === null) return null
  const qualifier = dimensionQualifier(signal.dimensions)
  return {
    caution: 'caution' in signal ? signal.caution : '',
    display: qualifier ? `${qualifier}: ${value}` : value,
    label,
    period: signal.period,
  }
}
