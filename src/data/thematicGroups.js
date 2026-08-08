import presentationPolicy from '../../contracts/pne2026-diagnostic-presentation-policy.json' with { type: 'json' }
import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  PNE_2026_RELATIONSHIP_MODES,
  canPne2026RelationEnterCycleSummary,
  resolvePne2026Relation,
} from './pne2026GoalIndicatorContract.js'

const PNE_2026_CYCLE = 'pne_2026_2036'
const PNE_2026_COMPARABLE_MODES = new Set([
  PNE_2026_RELATIONSHIP_MODES.PROGRESS,
  PNE_2026_RELATIONSHIP_MODES.TRACKING,
])
const PNE_2026_RELATIONS_BY_ID = new Map(
  PNE_2026_GOAL_INDICATOR_CONTRACT.relations.map((relation) => [
    relation.relationId,
    relation,
  ]),
)
const PNE_2026_POLICY_BY_RELATION_ID = new Map(
  presentationPolicy.relations.map((entry) => [entry.relationId, entry]),
)
const PNE_2026_THEMES_BY_ID = new Map(
  presentationPolicy.themes.map((theme) => [theme.themeId, theme]),
)

/*
 * Perguntas editoriais dos temas do ciclo 2026–2036. O contrato de apresentação
 * (contracts/pne2026-diagnostic-presentation-policy.json) é a fonte dos temas e
 * da ordem; a pergunta é camada de leitura da interface e por isso vive aqui,
 * sem tocar no JSON de contrato. Ciclo em curso: tom presente.
 */
const PNE_2026_THEME_QUESTIONS = {
  atendimento_escolar_v2: 'Quem a rede está atendendo hoje?',
  aprendizagem_trajetoria_escolar_v2: 'Como estão a aprendizagem e o fluxo escolar?',
  profissionais_educacao_v2: 'Quem são e como atuam os profissionais da educação?',
}

const EDUCACAO_INFANTIL_KEYS = ['creche', 'pre_escola']

const ENSINO_FUNDAMENTAL_KEYS = [
  'basico_6_17',
  'ensino_fundamental_ou_completo_pop_6_14',
]

const ENSINO_MEDIO_KEYS = [
  'basico_15_17',
  'ensino_medio_ou_basica_completa_pop_15_17',
]

function uniqueKeys(keys) {
  return [...new Set(keys)]
}

const BASIC_EDUCATION_FILTERS = [
  {
    key: 'todos',
    label: 'Todos',
    indicatorKeys: uniqueKeys([
      ...EDUCACAO_INFANTIL_KEYS,
      ...ENSINO_FUNDAMENTAL_KEYS,
      ...ENSINO_MEDIO_KEYS,
      'educacao_indigena_cobertura_estimada_4_17',
    ]),
  },
  {
    key: 'educacao_infantil',
    label: 'Educação Infantil',
    indicatorKeys: EDUCACAO_INFANTIL_KEYS,
  },
  {
    key: 'ensino_fundamental',
    label: 'Ensino Fundamental',
    indicatorKeys: ENSINO_FUNDAMENTAL_KEYS,
  },
  {
    key: 'ensino_medio',
    label: 'Ensino Médio',
    indicatorKeys: ENSINO_MEDIO_KEYS,
  },
]

const THEMATIC_GROUPS = [
  {
    key: 'educacao_basica',
    label: 'Educação Básica',
    shortLabel: 'Educação Básica',
    question: 'O acesso à educação básica alcançou o previsto?',
    icon: 'EB',
    accent: '#2563eb',
    indicatorKeys: BASIC_EDUCATION_FILTERS[0].indicatorKeys,
    filters: BASIC_EDUCATION_FILTERS,
  },
  {
    key: 'educacao_integral',
    label: 'Educação Integral',
    shortLabel: 'Educação Integral',
    icon: 'IN',
    accent: '#16a34a',
    indicatorKeys: ['basico_integral', 'escolas_integral'],
  },
  {
    key: 'eja_educacao_profissional',
    label: 'EJA e Educação Profissional',
    shortLabel: 'EJA e Educação Profissional',
    icon: 'EP',
    accent: '#0891b2',
    indicatorKeys: [
      'medio_tecnico_total',
      'medio_tecnico_articulado_percentual',
      'medio_tecnico',
      'medio_tecnico_participacao_publica',
      'subsequente_expansao',
      'eja_integrada_educacao_profissional_percentual',
      'eja_integrada_educacao_profissional',
    ],
  },
  {
    key: 'educacao_especial',
    label: 'Educação Especial',
    shortLabel: 'Educação Especial',
    icon: 'EE',
    accent: '#db2777',
    indicatorKeys: ['aee_oferta_escolas_elegiveis'],
  },
  {
    key: 'ideb_saeb_fluxo',
    label: 'IDEB / SAEB e Fluxo Escolar',
    shortLabel: 'IDEB / SAEB',
    question: 'O que IDEB, SAEB e o fluxo escolar mostraram no ciclo?',
    icon: 'IS',
    accent: '#4f46e5',
    indicatorKeys: [
      'alfabetizacao',
      'ideb_anos_iniciais',
      'ideb_anos_finais',
      'ideb_ensino_medio',
      'saeb_matematica_anos_iniciais',
      'saeb_matematica_anos_finais',
      'saeb_matematica_ensino_medio',
      'saeb_portugues_anos_iniciais',
      'saeb_portugues_anos_finais',
      'saeb_portugues_ensino_medio',
      'idade_regular_quinto',
      'idade_regular_nono',
      'idade_regular_medio',
    ],
  },
  {
    key: 'corpo_docente',
    label: 'Corpo Docente',
    shortLabel: 'Corpo Docente',
    icon: 'CD',
    accent: '#ca8a04',
    indicatorKeys: [
      'adequacao_ai',
      'adequacao_af',
      'adequacao_em',
      'pos_graduacao',
      'rendimento_magisterio',
      'temporarios',
      'munic_planos_carreira_declarados',
    ],
  },
  {
    key: 'infraestrutura_tecnologia',
    label: 'Infraestrutura e Tecnologia',
    shortLabel: 'Infraestrutura e Tecnologia',
    icon: 'IT',
    accent: '#059669',
    indicatorKeys: [
      'internet',
      'internet_alunos',
      'internet_aprendizagem',
      'internet_comunidade',
      'acesso_internet_computador',
      'acesso_internet_disp_pessoais',
      'rede_local',
      'rede_wireless',
      'banda_larga',
      'salas_climatizadas',
      'salas_acessiveis',
      'desktop_aluno',
      'comp_portatil_aluno',
      'tablet_aluno',
    ],
  },
  {
    key: 'gestao_ambiental',
    label: 'Gestão Escolar e Educação Ambiental',
    shortLabel: 'Gestão Escolar e Educação Ambiental',
    icon: 'GA',
    accent: '#65a30d',
    indicatorKeys: [
      'conselho_escolar',
      'munic_forum_educacao_declarado',
      'proposta_pedagogica',
      'educacao_ambiental',
    ],
  },
  {
    key: 'escolaridade_populacao',
    label: 'Escolaridade e Alfabetização',
    shortLabel: 'Escolaridade e Alfabetização',
    question: 'A escolaridade da população aumentou?',
    icon: 'EP',
    accent: '#0f766e',
    indicatorKeys: [
      'alfabetizacao_pop_15_mais',
      'escolaridade_media_18_29',
      'razao_escolaridade_racial_18_29',
      'fundamental_concluido_18_mais',
      'fundamental_concluido_15_29',
      'fundamental_concluido_15_mais',
      'medio_concluido_18_mais',
      'medio_concluido_18_29',
    ],
  },
]

export function getPne2026PresentationThemeForRelation(relationId) {
  const editorial = PNE_2026_POLICY_BY_RELATION_ID.get(relationId)
  const theme = editorial
    ? PNE_2026_THEMES_BY_ID.get(editorial.themeId)
    : null
  if (!editorial || !theme) return null

  return {
    key: theme.themeId,
    label: theme.label,
    shortLabel: theme.label,
    order: theme.displayOrder,
    relationOrder: editorial.displayOrder,
  }
}

export function getPne2026PresentationThemeForIndicator(indicatorId, goalId) {
  const relation = resolvePne2026Relation(goalId, indicatorId)
  return relation
    ? getPne2026PresentationThemeForRelation(relation.relationId)
    : null
}

export function buildThematicGroups(categories, cycleId) {
  if (cycleId === PNE_2026_CYCLE) {
    return buildPne2026ThematicGroups(categories)
  }

  const indicatorByKey = new Map()

  categories.forEach((category) => {
    ;(category.items ?? []).forEach((item) => {
      if (!indicatorByKey.has(item.key)) {
        indicatorByKey.set(item.key, item)
      }
    })
  })

  return THEMATIC_GROUPS.map((group) => materializeGroup(group, indicatorByKey))
    .filter((group) => group.items.length > 0)
}

function buildPne2026ThematicGroups(categories) {
  const indicatorByKey = new Map()
  categories.forEach((category) => {
    ;(category.items ?? []).forEach((item) => {
      if (!indicatorByKey.has(item.key)) {
        indicatorByKey.set(item.key, item)
      }
    })
  })

  const editorialByTheme = new Map()
  for (const editorial of presentationPolicy.relations) {
    const relation = PNE_2026_RELATIONS_BY_ID.get(editorial.relationId)
    if (
      !relation
      || !PNE_2026_COMPARABLE_MODES.has(relation.mode)
      || !canPne2026RelationEnterCycleSummary(relation)
    ) {
      continue
    }
    const item = indicatorByKey.get(relation.indicatorId)
    if (!item) continue
    const current = editorialByTheme.get(editorial.themeId) ?? []
    current.push({ editorial, item })
    editorialByTheme.set(editorial.themeId, current)
  }

  return presentationPolicy.themes
    .toSorted((left, right) => left.displayOrder - right.displayOrder)
    .flatMap((theme) => {
      const entries = editorialByTheme.get(theme.themeId)
        ?.toSorted((left, right) => (
          left.editorial.displayOrder - right.editorial.displayOrder
        )) ?? []
      if (!entries.length) return []
      return [{
        key: theme.themeId,
        label: theme.label,
        shortLabel: theme.label,
        question: PNE_2026_THEME_QUESTIONS[theme.themeId] ?? null,
        items: entries.map(({ item }) => item),
      }]
    })
}

function materializeGroup(group, indicatorByKey) {
  const filters = group.filters
    ?.map((filter) => materializeFilter(filter, indicatorByKey))
    .filter((filter) => filter.items.length > 0)

  return {
    ...group,
    items: materializeItems(group.indicatorKeys, indicatorByKey),
    ...(filters ? { filters } : {}),
  }
}

function materializeFilter(filter, indicatorByKey) {
  return {
    ...filter,
    items: materializeItems(filter.indicatorKeys, indicatorByKey),
  }
}

function materializeItems(indicatorKeys, indicatorByKey) {
  return indicatorKeys
    .map((indicatorKey) => indicatorByKey.get(indicatorKey))
    .filter(Boolean)
}
