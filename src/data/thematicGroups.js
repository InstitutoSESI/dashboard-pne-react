const EDUCACAO_INFANTIL_KEYS = ['creche', 'pre_escola']

const ENSINO_FUNDAMENTAL_KEYS = [
  'basico_6_17',
  'idade_regular_quinto',
  'idade_regular_nono',
  'ensino_fundamental_ou_completo_pop_6_14',
  'fundamental_concluido_18_mais',
  'fundamental_concluido_15_29',
]

const ENSINO_MEDIO_KEYS = [
  'basico_15_17',
  'ensino_medio_ou_basica_completa_pop_15_17',
  'idade_regular_medio',
  'medio_concluido_18_mais',
  'medio_concluido_18_29',
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
    indicatorKeys: ['salas_acessiveis'],
  },
  {
    key: 'ideb_saeb_fluxo',
    label: 'IDEB / SAEB e Fluxo Escolar',
    shortLabel: 'IDEB / SAEB',
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
    indicatorKeys: ['conselho_escolar', 'proposta_pedagogica', 'educacao_ambiental'],
  },
  {
    key: 'escolaridade_populacao',
    label: 'Escolaridade e Alfabetização',
    shortLabel: 'Escolaridade e Alfabetização',
    icon: 'EP',
    accent: '#0f766e',
    indicatorKeys: [
      'alfabetizacao_pop_15_mais',
      'ensino_medio_ou_basica_completa_pop_15_17',
      'ensino_fundamental_ou_completo_pop_6_14',
      'escolaridade_media_18_29',
      'razao_escolaridade_racial_18_29',
      'fundamental_concluido_18_mais',
      'fundamental_concluido_15_29',
      'medio_concluido_18_mais',
      'medio_concluido_18_29',
    ],
  },
]

export function buildThematicGroups(categories) {
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
