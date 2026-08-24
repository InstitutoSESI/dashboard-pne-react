import type { CadernoHypothesis, CadernoMonitoringContext } from './cadernoTypes'

/*
 * Linguagem acessível das causas — camada editorial da plataforma.
 *
 * O artefato de pesquisa guarda o texto técnico original (mechanism,
 * expectedRelationship, howToConfirmLocally) verbatim e intocado. Aqui vive uma
 * reescrita em português claro, para o gestor e o público, fiel ao sentido e à
 * cautela do original ("pode", "tende a", "costuma"). Cada fator é reescrito à
 * mão; fator sem entrada cai de volta no texto de pesquisa (sem os fragmentos
 * crípticos de verificação).
 *
 * `title` — nome da causa em linguagem do dia a dia (o nome de pesquisa fica no
 *           artefato: "custo de oportunidade", "distorção", "AEE" viram termos
 *           que o gestor reconhece).
 * `why`   — por que a causa pode pesar na meta.
 * `help`  — o que costuma ajudar.
 * `look`  — o que olhar no município para confirmar ou descartar.
 */

export interface CadernoPlainCause {
  readonly title: string
  readonly why: string
  readonly help: string
  readonly look: readonly string[]
}

/** Nome acessível por fator; sem entrada, usa o nome de pesquisa do artefato. */
export const FACTOR_TITLE: Readonly<Record<string, string>> = Object.freeze({
  F_DISTANCE: 'Distância e transporte até a escola',
  F_POV_CCT: 'Pobreza e apoio de renda às famílias',
  F_DEMAND_DISCOVERY: 'Encontrar quem precisa de vaga',
  F_EC_QUALITY: 'Qualidade da creche e da pré-escola',
  F_ATTEND: 'Frequência e busca ativa',
  F_MGMT: 'Gestão e organização da escola',
  F_FOUNDATION: 'Bases de leitura e matemática',
  F_TIME_QUALITY: 'Tempo de aula efetivo',
  F_HOME_LEARNING: 'Apoio à aprendizagem em casa',
  F_TEACH_COACH: 'Acompanhamento dos professores',
  F_TEACH_MATCH: 'Professores dando aula fora da sua área de formação',
  F_STRUCT_PED: 'Currículo, material e avaliação em sala',
  F_FOOD: 'Alimentação escolar',
  F_INTERGOV: 'Parceria com o estado e a União',
  F_DISASTER: 'Desastres e eventos climáticos',
  F_REPETITION: 'Reprovação e atraso escolar',
  F_HEALTH: 'Saúde física e mental dos alunos',
  F_WORK: 'Trabalho que concorre com o estudo',
  F_PREG_CARE: 'Gravidez e cuidado de dependentes',
  F_BULLY: 'Violência, bullying e clima escolar',
  F_HEAT: 'Calor e conforto nas salas',
  F_BASIC_INFRA: 'Infraestrutura básica da escola',
  F_FULLTIME_DESIGN: 'Organização do tempo integral',
  F_DIG_PHYS: 'Internet e equipamentos na escola',
  F_DIG_PED: 'Uso da tecnologia em sala',
  F_ENV_CURR: 'Educação ambiental na prática',
  F_INDIG_RELEV: 'Adequação da escola indígena',
  F_INCLUSION_SUPPORT: 'Apoio à inclusão e atendimento especializado',
  F_EJA_FIT: 'Oferta de EJA para jovens e adultos',
  F_CASH_AID_HE: 'Ajuda de custo no ensino superior e técnico',
  F_EPT_BUNDLE: 'Oferta e qualidade da educação profissional',
  F_HE_FACULTY: 'Professores e condições no ensino superior',
  F_HE_OFFER: 'Oferta de ensino superior na região',
  F_CAREER_PAY: 'Carreira e salário dos professores',
  F_POSTGRAD_CAP: 'Capacidade de pós-graduação e pesquisa',
  F_GOV_AUDIT: 'Transparência e fiscalização',
  F_PARTICIPATION: 'Participação e conselhos',
})

/** Títulos específicos por objetivo; têm precedência sobre o título geral do fator. */
export const FACTOR_TITLE_BY_GOAL: Readonly<Record<string, string>> = Object.freeze({
  '1:F_POV_CCT': 'Custo para a família manter a criança na creche',
  '6:F_BASIC_INFRA': 'Espaço e estrutura para ampliar a jornada',
  '8:F_BASIC_INFRA': 'Estrutura e recursos para climatizar as salas',
  '19:F_BASIC_INFRA': 'Obras e adaptações de acessibilidade que não saem do papel',
  '17:F_CAREER_PAY': 'Plano de carreira e salário na prática',
})

export const CONTEXT_TITLE: Readonly<Record<string, string>> = Object.freeze({
  F_SES: 'Condições sociais do território',
  F_EC_OFFER: 'Vagas e matrículas na rede',
  F_HEALTH: 'Saúde dos alunos no território',
  F_TEACH_STABILITY: 'Rotatividade e vínculos dos professores',
  F_FINANCING_EXECUTION: 'Recursos da educação e sua execução',
  F_EPT_DEMAND: 'Conexão dos cursos técnicos com o trabalho local',
})

type PlainBody = Omit<CadernoPlainCause, 'title'>

const FACTOR_PLAIN: Readonly<Record<string, PlainBody>> = Object.freeze({
  F_DISTANCE: {
    why: 'Quando a escola fica longe e o transporte é caro, demorado ou falha, ir e continuar estudando fica mais difícil.',
    help: 'Transporte confiável e trajetos mais curtos costumam melhorar a frequência e a permanência.',
    look: ['Rotas, tempo de viagem e dias sem transporte', 'Segurança no caminho até a escola'],
  },
  F_POV_CCT: {
    why: 'Famílias com pouca renda enfrentam custos e, às vezes, a necessidade de trabalhar ou cuidar de alguém, o que concorre com o estudo.',
    help: 'Apoio de renda e benefícios com condições, como o Bolsa Família, podem ajudar a manter crianças e jovens na escola.',
    look: ['Alunos em situação de pobreza e alertas de risco', 'O que a busca ativa conseguiu ao longo do ano'],
  },
  F_DEMAND_DISCOVERY: {
    why: 'Quando o município não sabe quem precisa de vaga, algumas famílias ficam invisíveis e não chegam a se matricular.',
    help: 'Cadastro atualizado, busca ativa e boa comunicação ajudam a transformar quem tem direito em matrícula.',
    look: ['Famílias que procuraram vaga e ainda esperam', 'Quanto da busca ativa virou matrícula'],
  },
  F_EC_QUALITY: {
    why: 'Na creche e na pré-escola, o cuidado e as atividades do dia a dia moldam o desenvolvimento da criança — não basta ter a vaga.',
    help: 'Rotinas, materiais e interações de qualidade favorecem o desenvolvimento e a aprendizagem.',
    look: ['Qualidade observada nas turmas', 'Planos de melhoria em andamento'],
  },
  F_ATTEND: {
    why: 'Faltas que se acumulam tiram tempo de aprendizagem e costumam vir antes do abandono.',
    help: 'Acompanhar a presença de perto e agir rápido já na primeira falta ajuda a manter o aluno na escola.',
    look: ['Frequência diária de todos os alunos', 'Tempo até o primeiro contato com a família'],
  },
  F_MGMT: {
    why: 'Sem rotinas de acompanhamento e resposta a problemas, boas intenções não chegam à sala de aula.',
    help: 'Gestão organizada, com metas e acompanhamento, ajuda a executar; o efeito direto na aprendizagem costuma ser gradual.',
    look: ['Rotinas de acompanhamento e execução dos planos', 'Tempo de resposta aos alertas'],
  },
  F_FOUNDATION: {
    why: 'Quando faltam bases de leitura e de matemática, fica mais difícil acompanhar os conteúdos seguintes.',
    help: 'Identificar e recuperar cedo essas lacunas tende a melhorar a aprendizagem adiante.',
    look: ['Lacunas em avaliações diagnósticas locais', 'Recuperação dos alunos após o apoio'],
  },
  F_TIME_QUALITY: {
    why: 'Aulas efetivamente dadas, presença de professores e tempo bem usado aumentam as oportunidades de aprender.',
    help: 'Cumprir o calendário e repor aulas ajuda; só aumentar horas, sem planejamento, pode não surtir efeito.',
    look: ['Dias e aulas efetivamente dados', 'Aulas perdidas por falta, clima ou infraestrutura'],
  },
  F_HOME_LEARNING: {
    why: 'Leitura, conversa e estímulo em casa complementam o que a escola faz.',
    help: 'Livros, conversa e atividades em família tendem a favorecer o desenvolvimento e a alfabetização.',
    look: ['Materiais de leitura no domicílio', 'Participação das famílias em ações de apoio'],
  },
  F_TEACH_COACH: {
    why: 'A formação de professores só muda a aula quando vem com observação e devolutiva na prática.',
    help: 'Apoio pedagógico próximo, com observação e feedback, pode melhorar o ensino.',
    look: ['Professores acompanhados e ciclos de feedback', 'Mudança de prática observada em sala'],
  },
  F_TEACH_MATCH: {
    why: 'Quando o professor dá aula de uma matéria ou etapa fora da sua formação, explicar o conteúdo e corrigir as dúvidas fica mais difícil.',
    help: 'Alocar cada professor na área em que se formou e oferecer formação na disciplina tende a melhorar a qualidade das aulas.',
    look: ['Turmas com professor atuando fora da área de formação', 'Necessidades de formação por disciplina e etapa'],
  },
  F_STRUCT_PED: {
    why: 'Currículo claro, bons materiais e avaliação que orienta o professor ajudam a organizar o trabalho em sala.',
    help: 'Ensinar no nível do aluno, com material alinhado e reforço, tende a elevar a aprendizagem.',
    look: ['Uso de material e currículo alinhados', 'Alunos em reforço ou tutoria'],
  },
  F_FOOD: {
    why: 'Fome e refeições irregulares afetam a saúde, a atenção e até o custo de ir à escola.',
    help: 'Alimentação regular e de qualidade pode proteger a presença e a aprendizagem.',
    look: ['Refeições realmente servidas e interrupções', 'Qualidade e aceitação da comida'],
  },
  F_INTERGOV: {
    why: 'Matrícula, transporte, ensino médio, educação profissional e financiamento dependem de mais de um ente — o município não resolve tudo sozinho.',
    help: 'Acordos e continuidade entre município, estado e União ajudam nos serviços de responsabilidade compartilhada.',
    look: ['Combinados e pendências entre os entes', 'Funcionamento das instâncias de pactuação'],
  },
  F_DISASTER: {
    why: 'Enchentes, secas e outros desastres fecham escolas, deslocam famílias e interrompem o ano letivo.',
    help: 'Planos de continuidade e recuperação rápida reduzem o tempo de aula perdido.',
    look: ['Escolas fechadas e dias de aula perdidos', 'Alunos deslocados por eventos climáticos'],
  },
  F_REPETITION: {
    why: 'Reprovar e ficar atrasado em relação à idade da turma aumenta a frustração e o risco de abandono.',
    help: 'Recuperação efetiva e correção do atraso idade-série ajudam a segurar o aluno até concluir.',
    look: ['Trajetória dos alunos ao longo dos anos', 'Resultado das ações de recuperação'],
  },
  F_HEALTH: {
    why: 'Doença, sofrimento emocional ou deficiência sem apoio reduzem a disponibilidade do aluno para estudar.',
    help: 'Encaminhamento e cuidado em saúde, inclusive mental, tendem a proteger a presença e a aprendizagem.',
    look: ['Faltas por motivo de saúde', 'Encaminhamentos e necessidades não atendidas'],
  },
  F_WORK: {
    why: 'Precisar trabalhar, ou ter horários incompatíveis, concorre com o estudo, o descanso e o cuidado.',
    help: 'Reduzir esse conflito de horário e apoiar a renda tende a melhorar a frequência e a conclusão.',
    look: ['Motivos declarados de saída da escola', 'Compatibilidade entre trabalho e horário escolar'],
  },
  F_PREG_CARE: {
    why: 'Cuidar de filhos ou dependentes, sem apoio e sem creche, aumenta o custo de continuar estudando.',
    help: 'Creche para mães e pais estudantes e horários flexíveis ajudam na permanência.',
    look: ['Estudantes com filhos ou dependentes', 'Acesso a creche para mães e pais estudantes'],
  },
  F_BULLY: {
    why: 'Medo, conflito e discriminação afetam o pertencimento, a presença e a concentração dos alunos.',
    help: 'Escolas com bom acolhimento e resposta rápida a incidentes podem reduzir o bullying.',
    look: ['Incidentes por escola e tempo de resposta', 'Percepção de segurança dos alunos'],
  },
  F_HEAT: {
    why: 'Calor excessivo e ambientes mal ventilados prejudicam a concentração e as condições de aula.',
    help: 'Ventilação, sombra e climatização podem amenizar o efeito do calor sobre a aprendizagem.',
    look: ['Equipamentos de climatização funcionando', 'Aulas afetadas por calor'],
  },
  F_BASIC_INFRA: {
    why: 'Água, banheiro, energia, acessibilidade e manutenção são o mínimo para a escola funcionar bem.',
    help: 'Boas condições e manutenção em dia favorecem o funcionamento e a presença; cada item pesa de um jeito.',
    look: ['O que está quebrado e há quanto tempo', 'Acessibilidade efetiva do prédio'],
  },
  F_FULLTIME_DESIGN: {
    why: 'Ampliar o tempo na escola só melhora a experiência quando vêm junto equipe, atividades, alimentação e espaço.',
    help: 'Uma jornada integral bem desenhada pode trazer ganhos; só aumentar horas pode não mudar nada.',
    look: ['Frequência e permanência na jornada ampliada', 'Qualidade do que é oferecido no tempo a mais'],
  },
  F_DIG_PHYS: {
    why: 'Sem internet estável, rede interna e equipamentos, o acesso digital na escola não funciona de fato.',
    help: 'Conexão disponível, estável e rápida habilita o uso; ter internet no papel pode não bastar.',
    look: ['Velocidade e estabilidade medidas na escola', 'Chamados e tempo de reparo'],
  },
  F_DIG_PED: {
    why: 'A tecnologia só ajuda a aprender quando tem conteúdo, mediação do professor e uso com propósito.',
    help: 'Uso planejado e acompanhado pode ajudar; dispositivo solto, sem orientação, pode não ajudar.',
    look: ['Plataformas e conteúdos usados', 'Formação dos professores aplicada em sala'],
  },
  F_ENV_CURR: {
    why: 'Educação ambiental vira prática quando entra no currículo e ganha experiências no território.',
    help: 'Formação, currículo e projetos contínuos ampliam a educação ambiental de verdade.',
    look: ['Projetos ambientais e sua continuidade', 'Intensidade e qualidade da prática'],
  },
  F_INDIG_RELEV: {
    why: 'Sem língua, professores, currículo e calendário adequados, a escola cria barreiras para estudantes indígenas.',
    help: 'Oferta no território e com adequação cultural tende a favorecer o acesso e a qualidade.',
    look: ['Consulta à comunidade indígena', 'Adequação cultural e transporte no território'],
  },
  F_INCLUSION_SUPPORT: {
    why: 'Matricular não basta: sem apoio individual, acessibilidade e recursos, a inclusão não se realiza.',
    help: 'Apoio adequado — atendimento especializado, acessibilidade e recursos de apoio — pode ampliar a participação e a aprendizagem.',
    look: ['Intensidade e qualidade do apoio individual', 'Barreiras removidas e progresso após o apoio'],
  },
  F_EJA_FIT: {
    why: 'Jovens e adultos conciliam trabalho, cuidado e transporte — se a EJA não cabe na vida deles, evadem.',
    help: 'Horário, currículo e acolhimento compatíveis ajudam a matricular e a manter na EJA.',
    look: ['Procura por EJA que não encontrou oferta', 'Motivos de saída e apoios oferecidos'],
  },
  F_CASH_AID_HE: {
    why: 'Mensalidade, transporte, moradia e renda perdida pesam na permanência no ensino superior e técnico.',
    help: 'Bolsa, crédito e apoios locais podem ampliar acesso e conclusão quando o custo é a barreira.',
    look: ['Apoios locais de transporte, moradia ou alimentação', 'Conclusão dos estudantes que recebem apoio'],
  },
  F_EPT_BUNDLE: {
    why: 'Na educação profissional, currículo, estágio e apoio à permanência funcionam juntos.',
    help: 'Oferta bem articulada, com estágio e apoio, pode reduzir o abandono e elevar a aprendizagem.',
    look: ['Apoio à permanência oferecido', 'Estágios realizados e sua qualidade'],
  },
  F_HE_FACULTY: {
    why: 'A disponibilidade e a formação dos professores sustentam o ensino e a orientação no ensino superior.',
    help: 'Titulação, estabilidade e tempo para pesquisa são condições plausíveis de qualidade.',
    look: [],
  },
  F_HE_OFFER: {
    why: 'Distância, vagas, cursos e horários definem a chance real de ingressar no ensino superior.',
    help: 'Mais oferta acessível tende a ampliar o acesso, dependendo de modalidade, custo e qualidade.',
    look: [],
  },
  F_CAREER_PAY: {
    why: 'Concurso, salário, progressão e condições influenciam quem entra e permanece na carreira docente.',
    help: 'Carreira e remuneração melhores podem ajudar a atrair e reter profissionais; o efeito direto na aprendizagem é incerto.',
    look: ['Implementação do plano de carreira', 'Retenção de profissionais e seus motivos'],
  },
  F_POSTGRAD_CAP: {
    why: 'A oferta e o financiamento definem a capacidade local de formar mestres e doutores.',
    help: 'Programas, bolsas, docentes e infraestrutura sustentam a formação de mestres e doutores.',
    look: [],
  },
  F_GOV_AUDIT: {
    why: 'Fiscalização, transparência e correção reduzem desvios e falhas na execução das políticas.',
    help: 'Controle e capacidade de execução podem melhorar a entrega; o efeito depende do que é fiscalizado.',
    look: ['Achados de auditoria e correções feitas', 'Funcionamento do controle social'],
  },
  F_PARTICIPATION: {
    why: 'Conselhos e fóruns ativos trazem informação, controle e legitimidade às decisões da educação.',
    help: 'Participação pode ampliar a prestação de contas e a adequação das políticas; o efeito nos resultados finais é incerto.',
    look: ['Reuniões, quórum e representação dos segmentos', 'Deliberações respondidas e atas publicadas'],
  },
})

const FACTOR_PLAIN_BY_GOAL: Readonly<Record<string, PlainBody>> = Object.freeze({
  '1:F_POV_CCT': {
    why: 'Transporte, material, roupa e horários pesam no orçamento; quando o custo aperta, a família adia ou desiste da vaga.',
    help: 'Apoio de renda, transporte e prioridade de vaga para famílias do Bolsa Família costumam facilitar a matrícula.',
    look: ['Famílias do Bolsa Família com crianças fora da creche', 'Custos que as famílias citam para não matricular'],
  },
  '6:F_BASIC_INFRA': {
    why: 'Sem salas, refeitório e espaço adequados, a escola não consegue oferecer o dia inteiro.',
    help: 'Adequar espaços existentes e planejar obras destrava a ampliação da jornada.',
    look: ['Escolas sem espaço para o dia inteiro', 'Obras previstas e seu andamento'],
  },
  '8:F_BASIC_INFRA': {
    why: 'Climatizar exige rede elétrica que aguente, equipamento instalado e manutenção em dia.',
    help: 'Adequar a rede elétrica e manter os equipamentos funcionando amplia as salas com conforto térmico.',
    look: ['Salas ainda sem climatização e o motivo', 'Equipamentos parados por falta de manutenção ou energia'],
  },
  '19:F_BASIC_INFRA': {
    why: 'A adaptação das escolas depende de obra e recurso executados; o que fica no papel não muda o prédio.',
    help: 'Plano de acessibilidade por escola, com obra e prazo, tende a destravar as adaptações.',
    look: ['Escolas sem salas acessíveis e o que falta em cada uma', 'Obras e recursos de acessibilidade parados'],
  },
  '17:F_CAREER_PAY': {
    why: 'Ter lei de plano de carreira não basta: progressão e salário praticados definem quem entra e quem fica.',
    help: 'Cumprir a progressão prevista e comparar o salário com redes vizinhas ajuda a atrair e reter professores.',
    look: ['Progressões previstas e efetivadas', 'Salário praticado comparado ao piso e a redes próximas'],
  },
})

/**
 * Reescrita acessível do fator; se não houver entrada, cai no texto de pesquisa
 * (mecanismo e relação esperada), sem os fragmentos crípticos de verificação.
 * Cartões protetivos não recebem a reescrita específica por meta porque ela é formulada como causa.
 */
export function resolvePlainCause(
  hypothesis: CadernoHypothesis,
  goalId?: string,
  variant: 'cause' | 'protective' = 'cause',
): CadernoPlainCause {
  const goalFactorKey = goalId ? `${goalId}:${hypothesis.factorId}` : ''
  const titleByGoal = variant === 'cause' ? FACTOR_TITLE_BY_GOAL[goalFactorKey] : undefined
  const plainByGoal = variant === 'cause' ? FACTOR_PLAIN_BY_GOAL[goalFactorKey] : undefined
  const title = titleByGoal ?? FACTOR_TITLE[hypothesis.factorId] ?? hypothesis.name
  const plain = plainByGoal ?? FACTOR_PLAIN[hypothesis.factorId]
  if (plain) return { title, ...plain }
  return {
    title,
    why: hypothesis.mechanism ? `${hypothesis.mechanism}.` : '',
    help: hypothesis.expectedRelationship ? `${hypothesis.expectedRelationship}.` : '',
    look: [],
  }
}

export function resolveContextTitle(context: CadernoMonitoringContext): string {
  return CONTEXT_TITLE[context.factorId] ?? FACTOR_TITLE[context.factorId] ?? context.name
}
