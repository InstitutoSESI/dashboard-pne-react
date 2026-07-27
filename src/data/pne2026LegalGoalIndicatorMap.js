import { PNE_2026_GOAL_TEXTS } from './pne2026GoalTexts.js'

const NO_MUNICIPAL_INDICATOR_REASON =
  'Sem indicador municipal disponível atualmente na plataforma.'

const OFFICIAL_LAW_URL =
  'https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2026/lei/l15388.htm'

export const PNE_2026_LEGAL_GOAL_MAPPING_METADATA = {
  law: 'Lei nº 15.388/2026',
  officialLawUrl: OFFICIAL_LAW_URL,
  totalLegalGoals: 73,
  validatedAgainstOfficialLaw: false,
  validationNote:
    'A estrutura local possui 73 metas com originalText, mas a comparacao linha a linha com a fonte oficial ainda precisa de revisao humana.',
}

const indicator = (
  indicatorId,
  coverage,
  relationNote,
  {
    hasMunicipalResult = true,
    hasDistance = true,
    hasProjection2036 = false,
  } = {},
) => ({
  indicatorId,
  coverage,
  relationNote,
  hasMunicipalResult,
  hasDistance,
  hasProjection2036,
})

const LEGAL_GOAL_RELATIONS = {
  '1.a': {
    relatedIndicators: [
      indicator(
        'creche',
        'parcial',
        'Acompanha a cobertura da população de 0 a 3 anos que frequenta escola/creche; não mede demanda manifesta por vaga em creche.',
        { hasProjection2036: true },
      ),
    ],
  },
  '1.c': {
    relatedIndicators: [
      indicator(
        'pre_escola',
        'direta',
        'Acompanha a população de 4 a 5 anos que frequenta escola/creche, alinhada à universalização da pré-escola.',
        { hasProjection2036: true },
      ),
    ],
  },
  '3.a': {
    relatedIndicators: [
      indicator(
        'alfabetizacao',
        'direta',
        'Acompanha estudantes alfabetizados na rede pública, usado como referência municipal para alfabetização.',
      ),
    ],
  },
  '4.a': {
    relatedIndicators: [
      indicator(
        'basico_6_17',
        'direta',
        'Acompanha a frequência à educação básica da população de 6 a 17 anos.',
        { hasProjection2036: true },
      ),
      indicator(
        'basico_15_17',
        'parcial',
        'Acompanha matrículas da educação básica associadas à faixa de 15 a 17 anos em relação à população residente da faixa.',
        { hasProjection2036: true },
      ),
    ],
  },
  '4.b': {
    relatedIndicators: [
      indicator(
        'idade_regular_quinto',
        'direta',
        'Acompanha a conclusão dos anos iniciais do ensino fundamental na idade regular.',
      ),
    ],
  },
  '4.c': {
    relatedIndicators: [
      indicator(
        'idade_regular_nono',
        'direta',
        'Acompanha a conclusão dos anos finais do ensino fundamental na idade regular.',
      ),
    ],
  },
  '4.d': {
    relatedIndicators: [
      indicator(
        'idade_regular_medio',
        'direta',
        'Acompanha a conclusão do ensino médio na idade regular.',
      ),
    ],
  },
  '5.a': {
    relatedIndicators: [
      indicator(
        'saeb_matematica_anos_iniciais',
        'parcial',
        'Acompanha aprendizagem em Matemática nos anos iniciais; não cobre sozinho todas as dimensões da meta.',
      ),
      indicator(
        'saeb_portugues_anos_iniciais',
        'parcial',
        'Acompanha aprendizagem em Português nos anos iniciais; não cobre sozinho todas as dimensões da meta.',
      ),
    ],
  },
  '5.b': {
    relatedIndicators: [
      indicator(
        'saeb_matematica_anos_finais',
        'parcial',
        'Acompanha aprendizagem em Matemática nos anos finais; não cobre sozinho todas as dimensões da meta.',
      ),
      indicator(
        'saeb_portugues_anos_finais',
        'parcial',
        'Acompanha aprendizagem em Português nos anos finais; não cobre sozinho todas as dimensões da meta.',
      ),
    ],
  },
  '5.d': {
    relatedIndicators: [
      indicator(
        'saeb_matematica_ensino_medio',
        'parcial',
        'Acompanha aprendizagem em Matemática no ensino médio; não cobre sozinho todas as dimensões da meta.',
      ),
      indicator(
        'saeb_portugues_ensino_medio',
        'parcial',
        'Acompanha aprendizagem em Português no ensino médio; não cobre sozinho todas as dimensões da meta.',
      ),
    ],
  },
  '6.a': {
    relatedIndicators: [
      indicator(
        'basico_integral',
        'parcial',
        'Acompanha a parcela de estudantes da educação básica pública em jornada integral.',
      ),
      indicator(
        'escolas_integral',
        'parcial',
        'Acompanha a parcela de escolas públicas com alunos em jornada de tempo integral.',
      ),
    ],
  },
  '7.a': {
    relatedIndicators: [
      indicator(
        'internet',
        'aproximada',
        'Indica acesso à internet nas escolas, mas não mede alta velocidade, uso pedagógico ou redes internas wi-fi.',
        { hasDistance: false },
      ),
      indicator(
        'internet_alunos',
        'aproximada',
        'Indica disponibilidade de internet para alunos, mas não mede alta velocidade ou adequação pedagógica.',
        { hasDistance: false },
      ),
      indicator(
        'internet_aprendizagem',
        'parcial',
        'Acompanha uso da internet em processos de ensino e aprendizagem, uma parte da meta de conectividade pedagógica.',
        { hasDistance: false },
      ),
      indicator(
        'rede_local',
        'aproximada',
        'Indica existência de rede local de computadores, mas não mede rede interna wi-fi nem qualidade da conectividade.',
        { hasDistance: false },
      ),
      indicator(
        'rede_wireless',
        'aproximada',
        'Proxy parcial de rede local sem fio; não mede qualidade, cobertura efetiva ou suficiência da conectividade interna.',
        { hasDistance: false },
      ),
      indicator(
        'banda_larga',
        'aproximada',
        'Proxy parcial de conectividade; não mede velocidade efetiva, estabilidade ou qualidade de uso pedagógico.',
        { hasDistance: false },
      ),
    ],
  },
  '8.b': {
    relatedIndicators: [
      indicator(
        'salas_climatizadas',
        'parcial',
        'Proxy parcial de conforto térmico; não mede integralmente as condições mínimas de infraestrutura escolar, mas permanece com distância operacional de referência.',
      ),
    ],
  },
  '8.c': {
    relatedIndicators: [
      indicator(
        'educacao_ambiental',
        'direta',
        'Acompanha escolas que promovem educação ambiental.',
      ),
    ],
  },
  '10.b': {
    relatedIndicators: [],
  },
  '11.a': {
    relatedIndicators: [
      indicator(
        'alfabetizacao_pop_15_mais',
        'direta',
        'Acompanha a taxa de alfabetização da população de 15 anos ou mais.',
      ),
    ],
  },
  '11.b': {
    relatedIndicators: [
      indicator(
        'fundamental_concluido_18_mais',
        'parcial',
        'Acompanha população de 18 anos ou mais com ensino fundamental concluído; a meta legal usa população de 15 anos ou mais.',
      ),
      indicator(
        'fundamental_concluido_15_29',
        'direta',
        'Acompanha a conclusão do ensino fundamental na população de 15 a 29 anos.',
      ),
    ],
  },
  '11.c': {
    relatedIndicators: [
      indicator(
        'medio_concluido_18_mais',
        'direta',
        'Acompanha a população de 18 anos ou mais com ensino médio concluído.',
      ),
      indicator(
        'medio_concluido_18_29',
        'direta',
        'Acompanha a conclusão do ensino médio na população de 18 a 29 anos.',
      ),
    ],
  },
  '12.a': {
    relatedIndicators: [
      indicator(
        'medio_tecnico_articulado_percentual',
        'direta',
        'Acompanha as matrículas em cursos técnicos integrados sobre o total de matrículas do ensino médio. Matrículas concomitantes permanecem disponíveis apenas como informação complementar.',
      ),
      indicator(
        'medio_tecnico_participacao_publica',
        'parcial',
        'Acompanha a participação pública na expansão da EPT de nível médio, uma parte da meta legal.',
      ),
    ],
  },
  '12.b': {
    relatedIndicators: [
      indicator(
        'subsequente_expansao',
        'parcial',
        'Acompanha expansão acumulada dos cursos técnicos subsequentes; não mede qualidade nem permanência.',
      ),
    ],
  },
  '12.c': {
    relatedIndicators: [
      indicator(
        'eja_integrada_educacao_profissional_percentual',
        'direta',
        'Calcula a proporção das matrículas da EJA articuladas à educação profissional a partir dos componentes brutos da Sinopse Estatística.',
      ),
    ],
  },
  '17.a': {
    relatedIndicators: [
      indicator(
        'adequacao_ai',
        'parcial',
        'Acompanha formação adequada nos anos iniciais; cobre apenas um recorte da meta de formação docente.',
      ),
      indicator(
        'adequacao_af',
        'parcial',
        'Acompanha formação adequada nos anos finais; cobre apenas um recorte da meta de formação docente.',
      ),
      indicator(
        'adequacao_em',
        'parcial',
        'Acompanha formação adequada no ensino médio; cobre apenas um recorte da meta de formação docente.',
      ),
    ],
  },
  '17.b': {
    relatedIndicators: [
      indicator(
        'rendimento_magisterio',
        'parcial',
        'Acompanha a relação remuneratória do magistério frente a outros profissionais com nível superior, sem detalhar cada etapa da educação básica.',
      ),
    ],
  },
  '17.d': {
    relatedIndicators: [
      indicator(
        'temporarios',
        'direta',
        'Acompanha o percentual de docentes da rede publica com vinculo temporario, com meta maxima de 30%.',
      ),
    ],
  },
  '17.f': {
    relatedIndicators: [
      indicator(
        'pos_graduacao',
        'direta',
        'Acompanha docentes da educação básica com pós-graduação.',
      ),
    ],
  },
  '18.b': {
    relatedIndicators: [
      indicator(
        'conselho_escolar',
        'direta',
        'Acompanha escolas públicas da educação básica com conselho escolar instituído e em funcionamento.',
      ),
    ],
  },
  '19.c': {
    relatedIndicators: [
      indicator(
        'salas_acessiveis',
        'parcial',
        'Proxy parcial de acessibilidade física; não mede todas as condições de inclusão e permanência previstas na meta, mas permanece com distância operacional de referência.',
      ),
    ],
  },
}

export const PNE_2026_LEGAL_GOAL_INDICATOR_MAP = Object.entries(PNE_2026_GOAL_TEXTS).map(
  ([legalGoalId, goal]) => {
    const relation = LEGAL_GOAL_RELATIONS[legalGoalId] ?? {}

    return {
      legalGoalId,
      objectiveId: extractObjectiveId(goal.objective),
      legalText: goal.originalText,
      relatedIndicators: relation.relatedIndicators ?? [],
      noMunicipalIndicatorReason:
        relation.relatedIndicators?.length > 0
          ? null
          : relation.noMunicipalIndicatorReason ?? NO_MUNICIPAL_INDICATOR_REASON,
    }
  },
)

function extractObjectiveId(objective) {
  const match = String(objective ?? '').match(/\d+/)
  return match ? match[0] : ''
}
