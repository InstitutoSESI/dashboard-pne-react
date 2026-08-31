export interface PlainFactorCopy {
  readonly title: string
  readonly question: string
}

export interface PlainDriverCopy {
  readonly dataStatus: string
  readonly title: string
  readonly introduction: string
  readonly shows: string
  readonly doesNotShow: string
  readonly missing: string
}

export interface PlainScenarioCopy {
  readonly summary: string
  readonly steps: readonly string[]
  readonly opportunities: readonly string[]
  readonly risks: readonly string[]
  readonly difficultChoices: readonly string[]
}

export interface PlainMunicipalCopy {
  readonly headline: string
  readonly exposures: Readonly<Record<string, string>>
  readonly regionalNeeds: readonly string[]
}

export const FACTOR_PLAIN_LANGUAGE: Readonly<Record<string, PlainFactorCopy>> = Object.freeze({
  F_DEMOGRAPHIC_SPATIAL: {
    title: 'Onde estarão os estudantes?',
    question: 'O número de crianças e jovens e o local onde estudam podem mudar de forma diferente em cada município.',
  },
  F_ECONOMY_FORMATION: {
    title: 'A formação vai acompanhar o trabalho?',
    question: 'As oportunidades de formação podem avançar no mesmo ritmo do trabalho ou ficar distantes das necessidades dos estudantes.',
  },
  F_SOCIAL_TRAJECTORIES: {
    title: 'Os estudantes conseguirão permanecer e aprender?',
    question: 'Renda, trabalho, cuidado, inclusão e deslocamento podem facilitar ou dificultar a continuidade dos estudos.',
  },
  F_MOBILITY_NETWORK: {
    title: 'Será fácil chegar à escola e aos cursos?',
    question: 'Transporte, horários, vagas e acordos entre municípios podem ampliar ou limitar o acesso.',
  },
  F_ADAPTIVE_CAPACITY: {
    title: 'As redes conseguirão se adaptar?',
    question: 'Recursos, equipes e organização podem permitir respostas rápidas ou manter decisões rígidas por mais tempo.',
  },
})

export const DRIVER_PLAIN_LANGUAGE: Readonly<Record<string, PlainDriverCopy>> = Object.freeze({
  X_CLIMATE: {
    dataStatus: 'Há registros oficiais disponíveis',
    title: 'Eventos climáticos e continuidade das aulas',
    introduction: 'Interrupções podem afetar transporte, calendário, prédios escolares e recuperação das aprendizagens.',
    shows: 'Quantos eventos foram registrados oficialmente e em quais municípios.',
    doesNotShow: 'Não informa quantos dias de aula, escolas ou estudantes foram afetados.',
    missing: 'Dias de interrupção, rotas afetadas e resultados dos planos de continuidade.',
  },
  X_TECHNOLOGY: {
    dataStatus: 'Há dados sobre a infraestrutura das escolas',
    title: 'Internet e tecnologia nas escolas',
    introduction: 'A estrutura disponível pode ajudar na continuidade das atividades, mas acesso não significa uso de qualidade.',
    shows: 'Quantas escolas declararam internet para aprendizagem e acesso à internet por computador.',
    doesNotShow: 'Não mede qualidade da conexão, uso pedagógico, acesso em casa ou efeito na aprendizagem.',
    missing: 'Qualidade, frequência de uso, competências digitais e acesso dos estudantes fora da escola.',
  },
  X_FISCAL: {
    dataStatus: 'Há dados financeiros conferidos',
    title: 'Recursos municipais para a educação',
    introduction: 'A margem acima do mínimo obrigatório ajuda a entender o ponto de partida financeiro de cada município.',
    shows: 'Quanto cada município aplicou acima do mínimo constitucional em 2025.',
    doesNotShow: 'Não representa dinheiro livre, orçamento regional nem capacidade futura de financiar novas ações.',
    missing: 'Custos das opções, compromissos futuros e possibilidade real de dividir despesas entre municípios.',
  },
  X_REGULATION: {
    dataStatus: 'Ainda não há uma medida pública adequada',
    title: 'Acordos educacionais entre municípios',
    introduction: 'Serviços compartilhados dependem de responsabilidades, custos e regras bem definidos.',
    shows: 'O dado público encontrado não responde se existem acordos educacionais regionais em funcionamento.',
    doesNotShow: 'A informação sobre acessibilidade no transporte não comprova cooperação educacional entre municípios.',
    missing: 'Acordos, responsabilidades, padrões de atendimento, divisão de custos, revisão e possibilidade de saída.',
  },
})

export const SCENARIO_PLAIN_LANGUAGE: Readonly<Record<string, PlainScenarioCopy>> = Object.freeze({
  S1_UNEVEN_NETWORK_TEMPO: {
    summary: 'Cada município ajusta sua rede no próprio ritmo. Isso preserva autonomia local, mas pode deixar problemas regionais sem resposta conjunta.',
    steps: [
      'O número de estudantes e o local onde estudam mudam de forma diferente entre os municípios.',
      'Cada rede decide com uma visão incompleta dos deslocamentos e das vagas da região.',
      'Alguns grupos continuam encontrando mais barreiras para permanecer, voltar à escola ou acessar formação.',
      'Pequenos ajustes evitam mudanças bruscas, mas podem acumular diferenças entre os territórios.',
    ],
    opportunities: [
      'Resolver problemas locais com rapidez.',
      'Testar mudanças pequenas antes de alterar a rede de forma permanente.',
    ],
    risks: [
      'Reduzir vagas apenas porque há menos crianças e jovens residentes.',
      'Deixar demandas regionais de formação, educação de jovens e adultos e apoio especializado sem resposta.',
    ],
    difficultChoices: [
      'Autonomia de cada município ou maior coordenação regional.',
      'Manter a estrutura atual ou adaptar a oferta antes que o problema cresça.',
    ],
  },
  S2_WORK_OUTRUNS_TRAJECTORIES: {
    summary: 'O trabalho muda mais rápido que a formação. Novas oportunidades aparecem, mas nem todos os estudantes conseguem chegar aos cursos ou conciliar estudo, trabalho e deslocamento.',
    steps: [
      'Mudanças no trabalho aumentam a procura por renda e qualificação.',
      'Cursos e projetos surgem antes de uma visão completa sobre vagas, conclusão e deslocamento.',
      'Alguns estudantes acessam as novas oportunidades; outros ficam limitados por horário, distância ou renda.',
      'A educação tenta acompanhar a economia, mas ainda precisa verificar acesso, permanência e resultados.',
    ],
    opportunities: [
      'Testar novas formas de conectar formação e trabalho.',
      'Ampliar o acesso regional à educação profissional e tecnológica.',
    ],
    risks: [
      'Criar cursos apenas porque uma ocupação cresceu.',
      'Aumentar a diferença entre quem consegue se deslocar e quem não consegue.',
    ],
    difficultChoices: [
      'Responder rapidamente ou estudar melhor a demanda antes de expandir.',
      'Concentrar cursos regionais ou manter ofertas mais próximas dos estudantes.',
    ],
  },
  S3_INTERRUPTED_ROUTES: {
    summary: 'Crises climáticas, dificuldades de transporte e pressão sobre a renda interrompem trajetórias. A rede prioriza manter as aulas, mas pode adiar prevenção e mudanças mais profundas.',
    steps: [
      'Eventos e crises afetam transporte, calendário, renda ou prédios escolares de forma desigual.',
      'Famílias, estudantes e redes acumulam custos de deslocamento, cuidado e recuperação.',
      'Recursos são direcionados para manter o atendimento imediato.',
      'Ausências, aprendizagem, educação de jovens e adultos e inclusão ficam mais vulneráveis a novas interrupções.',
    ],
    opportunities: [
      'Criar planos de continuidade que protejam os grupos mais expostos.',
      'Integrar educação, transporte, infraestrutura e assistência nas respostas a crises.',
    ],
    risks: [
      'Tratar perdas de aprendizagem e abandono como inevitáveis.',
      'Transformar soluções temporárias e desiguais em práticas permanentes.',
    ],
    difficultChoices: [
      'Atender a emergência ou reservar recursos para prevenção.',
      'Usar soluções remotas e centralizadas ou preservar acesso e vínculo local.',
    ],
  },
  S4_REGIONAL_COORDINATION_UNDER_TENSION: {
    summary: 'Os municípios compartilham informações, serviços e rotas. A cooperação amplia possibilidades, mas exige regras claras para não afastar serviços nem concentrar decisões.',
    steps: [
      'Os municípios passam a observar juntos onde os estudantes moram, estudam e se deslocam.',
      'Redes e instituições combinam acesso a cursos, educação de jovens e adultos, apoio especializado e continuidade das aulas.',
      'Apoios podem chegar antes da interrupção da trajetória escolar.',
      'A região ganha escala, mas passa a depender de acordos, recursos e representação equilibrada.',
    ],
    opportunities: [
      'Ampliar serviços sem que cada município precise oferecer tudo sozinho.',
      'Aprender com dados comuns e revisar os acordos periodicamente.',
    ],
    risks: [
      'Concentrar serviços longe de quem mais precisa.',
      'Depender de acordos frágeis ou de recursos temporários.',
    ],
    difficultChoices: [
      'Ganhar escala regional ou manter serviços próximos e autonomia local.',
      'Usar regras comuns ou adaptar o atendimento a cada território.',
    ],
  },
})

export const MUNICIPAL_PLAIN_LANGUAGE: Readonly<Record<string, PlainMunicipalCopy>> = Object.freeze({
  S1_UNEVEN_NETWORK_TEMPO: {
    headline: 'Nova Santa Rita pode tomar decisões locais sem enxergar todos os estudantes que chegam, saem ou dependem de serviços de outros municípios.',
    exposures: {
      demographic: 'O número de moradores e o número de matrículas podem apontar direções diferentes.',
      educational: 'EJA, permanência e atendimento especializado podem exigir respostas próprias para cada grupo.',
      economic: 'A falta de cursos técnicos locais aumenta a dependência de vagas e transporte para outros municípios.',
      social: 'Renda, trabalho e cuidado podem dificultar a permanência de alguns estudantes.',
      territorial: 'Áreas rurais e deslocamentos longos tornam uma resposta apenas municipal mais cara e difícil.',
    },
    regionalNeeds: ['Saber onde os estudantes moram e estudam', 'Mapear cursos e vagas na região', 'Compartilhar atendimento educacional especializado'],
  },
  S2_WORK_OUTRUNS_TRAJECTORIES: {
    headline: 'Novas oportunidades podem surgir na região sem que os estudantes de Nova Santa Rita consigam chegar aos cursos e concluí-los.',
    exposures: {
      demographic: 'A procura por formação passa a depender também de onde estão os cursos e os empregos.',
      educational: 'Horários, permanência e conclusão se tornam tão importantes quanto abrir novas vagas.',
      economic: 'Mudanças no trabalho aumentam a procura por qualificação, mas não indicam sozinhas qual curso criar.',
      social: 'Quem não consegue conciliar estudo, trabalho e deslocamento pode ficar de fora.',
      territorial: 'Sem oferta técnica local, o município depende mais de transporte, vagas e calendários externos.',
    },
    regionalNeeds: ['Informações sobre vagas e conclusão nos cursos', 'Rotas e horários compatíveis', 'Acompanhamento de ex-estudantes e trabalho'],
  },
  S3_INTERRUPTED_ROUTES: {
    headline: 'Interrupções podem afetar ao mesmo tempo transporte, frequência, EJA e atendimento especializado em Nova Santa Rita.',
    exposures: {
      demographic: 'Mudanças rápidas de presença e residência dificultam estimar a procura por vagas.',
      educational: 'Ausências, recuperação, EJA e atendimento especializado disputam a mesma capacidade de resposta.',
      economic: 'Pressão sobre a renda pode aumentar a necessidade de horários mais flexíveis.',
      social: 'As dificuldades se acumulam sobre estudantes que já enfrentam mais barreiras.',
      territorial: 'Áreas rurais e serviços fora do município ficam mais expostos a falhas de transporte e calendário.',
    },
    regionalNeeds: ['Planos para manter o atendimento', 'Coordenação de transporte e infraestrutura', 'Apoio conjunto entre educação e assistência'],
  },
  S4_REGIONAL_COORDINATION_UNDER_TENSION: {
    headline: 'A cooperação regional pode ampliar o acesso se Nova Santa Rita participar das decisões e tiver garantias de atendimento e transporte.',
    exposures: {
      demographic: 'Informações sobre deslocamentos ajudam a planejar vagas com menos suposições.',
      educational: 'EJA, formação profissional e apoio especializado ganham novas opções, mas podem ficar mais distantes.',
      economic: 'A formação pode se aproximar das trajetórias dos estudantes sem prometer emprego.',
      social: 'Apoios compartilhados podem proteger mais estudantes, desde que todos os públicos sejam atendidos.',
      territorial: 'O acesso depende de tempo de viagem, acessibilidade, regularidade e alternativas quando o serviço falha.',
    },
    regionalNeeds: ['Participação municipal nas decisões', 'Divisão estável dos custos', 'Regras de atendimento e acesso justo'],
  },
})

export const DOMAIN_PLAIN_LABELS: Readonly<Record<string, string>> = Object.freeze({
  DEMOGRAPHY_DEMAND: 'Número e localização dos estudantes',
  NETWORK_ACCESS_MOBILITY: 'Acesso, transporte e deslocamento',
  EDUCATION_TRAJECTORIES: 'Permanência e aprendizagem',
  EDUCATION_CAPACITY: 'Equipes, serviços e infraestrutura',
  ECONOMY_WORK_FORMATION: 'Formação e trabalho',
  FINANCE_GOVERNANCE: 'Recursos e coordenação',
})

export const DOMAIN_PLAIN_SUMMARIES: Readonly<Record<string, Readonly<Record<string, string>>>> = Object.freeze({
  S1_UNEVEN_NETWORK_TEMPO: {
    DEMOGRAPHY_DEMAND: 'A procura por vagas muda de forma diferente em cada município.',
    NETWORK_ACCESS_MOBILITY: 'Transporte, horários e vagas continuam resolvidos principalmente por cada rede.',
    EDUCATION_TRAJECTORIES: 'As dificuldades de permanência e aprendizagem ficam concentradas em alguns grupos.',
    EDUCATION_CAPACITY: 'Equipes e estruturas são ajustadas depois que a pressão já apareceu.',
    ECONOMY_WORK_FORMATION: 'Cursos e trabalho continuam pouco conectados na prática.',
    FINANCE_GOVERNANCE: 'Recursos e decisões permanecem separados por município e programa.',
  },
  S2_WORK_OUTRUNS_TRAJECTORIES: {
    DEMOGRAPHY_DEMAND: 'A procura por escola e formação acompanha novas rotas de trabalho e deslocamento.',
    NETWORK_ACCESS_MOBILITY: 'Alguns corredores ampliam o acesso, mas não alcançam todos os públicos e horários.',
    EDUCATION_TRAJECTORIES: 'Conciliar estudo, trabalho e deslocamento se torna mais difícil.',
    EDUCATION_CAPACITY: 'Equipes e recursos se concentram nos projetos mais visíveis.',
    ECONOMY_WORK_FORMATION: 'A oferta cresce, mas ainda é preciso verificar conclusão e entrada no trabalho.',
    FINANCE_GOVERNANCE: 'Projetos temporários avançam antes de garantir recursos para sua continuidade.',
  },
  S3_INTERRUPTED_ROUTES: {
    DEMOGRAPHY_DEMAND: 'Crises e mudanças de residência alteram onde as vagas são necessárias.',
    NETWORK_ACCESS_MOBILITY: 'Rotas, calendários e prédios escolares ficam menos confiáveis.',
    EDUCATION_TRAJECTORIES: 'Ausências e dificuldades sociais se acumulam e interrompem estudos.',
    EDUCATION_CAPACITY: 'Equipes e serviços trabalham em situação de emergência por mais tempo.',
    ECONOMY_WORK_FORMATION: 'Pressão sobre renda e trabalho dificulta retorno, frequência e conclusão.',
    FINANCE_GOVERNANCE: 'O orçamento prioriza a emergência e reduz espaço para prevenção.',
  },
  S4_REGIONAL_COORDINATION_UNDER_TENSION: {
    DEMOGRAPHY_DEMAND: 'Informações compartilhadas ajudam a planejar vagas e serviços entre municípios.',
    NETWORK_ACCESS_MOBILITY: 'Rotas, horários e vagas são combinados regionalmente.',
    EDUCATION_TRAJECTORIES: 'Sinais de risco permitem apoiar estudantes antes da ruptura.',
    EDUCATION_CAPACITY: 'Especialistas, formação e estruturas podem ser compartilhados.',
    ECONOMY_WORK_FORMATION: 'Cursos, conclusão e acesso ao trabalho são planejados em conjunto.',
    FINANCE_GOVERNANCE: 'Custos e responsabilidades são divididos por acordos que precisam ser revistos.',
  },
})

export const ACTION_TYPE_PLAIN_LANGUAGE = Object.freeze({
  NO_REGRET: {
    title: 'Úteis em qualquer futuro',
    description: 'Ações que melhoram a informação e a capacidade de resposta sem exigir uma grande decisão antecipada.',
  },
  CONTINGENT: {
    title: 'Para usar quando um sinal aparecer',
    description: 'Ações que só devem avançar quando a situação indicada estiver realmente acontecendo.',
  },
  REVERSIBLE_EXPERIMENT: {
    title: 'Testes pequenos antes de decidir em definitivo',
    description: 'Experiências com prazo e critérios claros para aprender antes de assumir compromissos permanentes.',
  },
})

export const AUTHORITY_PLAIN_LABELS = Object.freeze({
  MUNICIPAL: 'O município pode liderar',
  SHARED: 'Depende de acordo com outros',
  EXTERNAL: 'Depende de decisão externa',
})

export const CADENCE_PLAIN_LABELS: Readonly<Record<string, string>> = Object.freeze({
  ANNUAL: 'Todo ano',
  SEMESTER: 'A cada semestre',
  QUARTERLY: 'A cada trimestre',
  MONTHLY: 'Todo mês',
  EVENT_BASED: 'Sempre que houver uma interrupção',
})

export const SENTINEL_PLAIN_LANGUAGE: Readonly<Record<string, { readonly label: string; readonly use: string }>> = Object.freeze({
  SENT_COHORT_ENROLLMENT_DIVERGENCE: {
    label: 'Crianças e jovens residentes comparados às matrículas',
    use: 'Investigar onde os estudantes estão matriculados antes de mudar a oferta.',
  },
  SENT_RESIDENCE_SCHOOL_FLOWS: {
    label: 'Onde os estudantes moram e onde estudam',
    use: 'Confirmar origem, destino e dependência de outros municípios.',
  },
  SENT_HS_ABANDONMENT: {
    label: 'Abandono no ensino médio',
    use: 'Observar a trajetória completa antes de atribuir uma causa.',
  },
  SENT_EJA_BY_STAGE: {
    label: 'EJA por etapa e turno',
    use: 'Distinguir mudança nas matrículas, procura e barreiras de acesso.',
  },
  SENT_EPT_ACCESS_MAP: {
    label: 'Cursos, vagas e acesso à formação profissional na região',
    use: 'Verificar se os estudantes realmente conseguem chegar à oferta disponível.',
  },
  SENT_EPT_COMPLETION: {
    label: 'Conclusão dos cursos de formação profissional',
    use: 'Acompanhar entrada, permanência e conclusão separadamente.',
  },
  SENT_YOUTH_WORK_STUDY: {
    label: 'Conciliação entre trabalho e estudo',
    use: 'Observar horários e barreiras sem presumir uma causa única.',
  },
  SENT_ROUTE_RELIABILITY: {
    label: 'Regularidade das rotas escolares',
    use: 'Acompanhar tempo de viagem, dias sem serviço, segurança e alternativas.',
  },
  SENT_INTERRUPTED_SCHOOL_DAYS: {
    label: 'Dias com atividades educacionais interrompidas',
    use: 'Acionar o plano de continuidade e registrar a recuperação.',
  },
  SENT_AEE_CAPACITY: {
    label: 'Capacidade do atendimento educacional especializado',
    use: 'Acompanhar profissionais, acessibilidade, atendimento e fila.',
  },
  SENT_SHARED_SERVICE_LEVEL: {
    label: 'Qualidade dos serviços compartilhados na região',
    use: 'Acompanhar somente quando existir um acordo regional em funcionamento.',
  },
  SENT_EQUITY_OF_ACCESS: {
    label: 'Quem ainda não consegue acessar vagas, apoio ou transporte',
    use: 'Identificar públicos e territórios que continuam fora do atendimento.',
  },
})

export const ACRONYM_DEFINITIONS = Object.freeze([
  ['PNE', 'Plano Nacional de Educação'],
  ['MDE', 'manutenção e desenvolvimento do ensino'],
  ['EJA', 'Educação de Jovens e Adultos'],
  ['EPT', 'educação profissional e tecnológica'],
  ['AEE', 'atendimento educacional especializado'],
] as const)

export interface SimpleDecisionPriority {
  readonly id: string
  readonly title: string
  readonly explanation: string
}

export interface SimpleScenarioCopy {
  readonly title: string
  readonly change: string
  readonly preparation: string
}

export interface SimplePublicSignal {
  readonly indicatorId: string
  readonly title: string
  readonly decisionUse: string
}

export const SIMPLE_DECISION_PRIORITIES: readonly SimpleDecisionPriority[] = Object.freeze([
  {
    id: 'network-capacity',
    title: 'Mudar vagas ou escolas',
    explanation: 'Os dados públicos de população e matrículas, sozinhos, não mostram o caminho dos estudantes. Antes de abrir, fechar ou deslocar oferta, confira capacidade, local de moradia, local de estudo e transporte.',
  },
  {
    id: 'courses-access',
    title: 'Criar ou ampliar cursos',
    explanation: 'O crescimento dos empregos e a ausência de oferta local não provam que um novo curso é necessário. Antes de decidir, confira quais cursos existem na região e se os estudantes conseguem acessar e concluir.',
  },
  {
    id: 'adult-education',
    title: 'Reorganizar a educação de jovens e adultos',
    explanation: 'Matrícula não é o mesmo que procura. Antes de mudar turmas, confira separadamente etapa, turno, local de oferta e barreiras de acesso.',
  },
])

export const SIMPLE_SCENARIO_LANGUAGE: Readonly<Record<string, SimpleScenarioCopy>> = Object.freeze({
  S1_UNEVEN_NETWORK_TEMPO: {
    title: 'Cada município por conta própria',
    change: 'As redes se ajustam em ritmos diferentes e alguns estudantes ficam sem resposta regional.',
    preparation: 'Acompanhe deslocamentos e combine apoio quando o atendimento local não bastar.',
  },
  S2_WORK_OUTRUNS_TRAJECTORIES: {
    title: 'Empregos mudam mais rápido que os cursos',
    change: 'Surgem oportunidades, mas distância, horário e renda impedem parte dos estudantes de aproveitá-las.',
    preparation: 'Confirme vagas, acesso e conclusão antes de ampliar a oferta.',
  },
  S3_INTERRUPTED_ROUTES: {
    title: 'Interrupções afastam estudantes',
    change: 'Transporte, clima ou renda interrompem trajetórias, sobretudo de quem já enfrenta barreiras.',
    preparation: 'Defina alternativas de rota, comunicação, atendimento e recuperação.',
  },
  S4_REGIONAL_COORDINATION_UNDER_TENSION: {
    title: 'Municípios trabalham juntos',
    change: 'A cooperação amplia opções, mas pode afastar o atendimento e concentrar decisões.',
    preparation: 'Defina acesso, custos, responsabilidades e formas de encerrar o acordo.',
  },
})

export const SIMPLE_PUBLIC_SIGNALS: readonly SimplePublicSignal[] = Object.freeze([
  {
    indicatorId: 'SENT_COHORT_ENROLLMENT_DIVERGENCE',
    title: 'População de 15 a 17 anos e matrículas locais do ensino médio',
    decisionUse: 'Se mudarem em direções diferentes, investigue antes de alterar vagas, escolas ou transporte.',
  },
  {
    indicatorId: 'SENT_HS_ABANDONMENT',
    title: 'Abandono no ensino médio',
    decisionUse: 'Se houver mudança contínua, revise o contexto dos estudantes e das escolas sem escolher uma causa antes da investigação.',
  },
  {
    indicatorId: 'SENT_EJA_BY_STAGE',
    title: 'Matrículas da educação de jovens e adultos por etapa e turno',
    decisionUse: 'Se o perfil mudar, revise cada etapa separadamente antes de alterar turmas.',
  },
])

export const SIMPLE_PUBLIC_DATA_GAP = 'Ainda não há informação suficiente sobre onde cada estudante mora e estuda, acesso e conclusão em cursos técnicos, regularidade das rotas, dias letivos interrompidos e capacidade efetiva do atendimento especializado. Essas lacunas devem aparecer como desconhecidas, não como estimativas.'
