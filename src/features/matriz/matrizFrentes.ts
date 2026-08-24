import type { AppPageKey } from '../../types/app'

/**
 * Caminhos para avançar — camada editorial da Matriz de Prioridades.
 *
 * Regra central: a orientação oficial (PNE 2026–2036, Novo PAR, programas e
 * instrumentos do MEC/FNDE) define as ações; cada caminho aponta explicitamente
 * para o contexto em `matrizInsights.ts`. A plataforma não declara razão local
 * comprovada.
 *
 * O conteúdo deste arquivo é editorial e revisado manualmente. Os dados do
 * município nunca vivem aqui.
 */

export interface MatrizFrenteProgram {
  readonly name: string
  readonly description: string
  readonly url?: string
}

export interface MatrizFrenteBridge {
  readonly label: string
  readonly page: AppPageKey
  readonly params?: Readonly<Record<string, string>>
}

export interface MatrizFrente {
  readonly id: string
  /** Ponto analítico que sustenta este caminho na leitura unificada. */
  readonly mechanismId: string
  readonly title: string
  /** Sugestão editorial de primeiro movimento para a leitura da meta. */
  readonly startHere?: boolean
  /** Orientações práticas do governo federal sobre como avançar. */
  readonly steps: readonly string[]
  /** Entrega verificável que traduz as orientações em um marco de implementação. */
  readonly implementationMilestone: string
  /** Resultado público e direção esperada na leitura seguinte. */
  readonly monitoringSignal: string
  /** Programas, instrumentos ou formas de apoio relacionados. */
  readonly programs: readonly MatrizFrenteProgram[]
  /** Referência legal discreta, exibida em linha pequena ao pé do cartão. */
  readonly legalRef: string
  /** Aprofundamento já existente no painel (no máximo 1). */
  readonly bridge?: MatrizFrenteBridge
}

const PAR = Object.freeze({
  name: 'Novo PAR (FNDE)',
  description: 'Planejamento com assistência técnica e financeira da União para obras, mobiliário, equipamentos e ações pedagógicas.',
  url: 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/programas/par',
})

const CNCA = Object.freeze({
  name: 'Compromisso Nacional Criança Alfabetizada',
  description: 'Adesão ao pacto federal de alfabetização, com formação de professores, materiais e acompanhamento das crianças.',
  url: 'https://www.gov.br/mec/pt-br/crianca-alfabetizada',
})

function educationBridge(label: string, section: string): MatrizFrenteBridge {
  return Object.freeze({
    label,
    page: 'educacao',
    params: Object.freeze({ secao: section }),
  })
}

const ATTENDANCE_BRIDGE = educationBridge(
  'Atendimento e oferta no município',
  'atendimento',
)
const DEMAND_BRIDGE = educationBridge(
  'Cenários de atendimento no município',
  'demanda',
)
const TRAJECTORY_BRIDGE = educationBridge(
  'Trajetória e aprendizagem no município',
  'trajetoria',
)
const MODALITIES_BRIDGE = educationBridge(
  'Oferta de EJA no município',
  'modalidades',
)
const PROFESSIONALS_BRIDGE = educationBridge(
  'Profissionais da educação no município',
  'profissionais',
)
const INFRASTRUCTURE_BRIDGE = educationBridge(
  'Infraestrutura escolar no município',
  'infraestrutura',
)

function frente(entry: MatrizFrente): MatrizFrente {
  return Object.freeze({
    ...entry,
    steps: Object.freeze([...entry.steps]),
    programs: Object.freeze(entry.programs.map((program) => Object.freeze({ ...program }))),
    bridge: entry.bridge
      ? Object.freeze({
          ...entry.bridge,
          params: entry.bridge.params ? Object.freeze({ ...entry.bridge.params }) : undefined,
        })
      : undefined,
  })
}

/** Frentes por meta prioritária do piloto (chave = goalId do artefato). */
export const MATRIZ_FRENTES: Readonly<Record<string, readonly MatrizFrente[]>> = Object.freeze({
  '1.a': Object.freeze([
    frente({
      id: 'procura-por-vaga',
      mechanismId: 'procura-maior-que-oferta',
      startHere: true,
      title: 'Conhecer a procura por vaga em creche',
      steps: [
        'Reunir, em uma lista municipal, os pedidos das famílias e os dados necessários para ordenar as inscrições.',
        'Localizar crianças de até 3 anos ainda não inscritas com apoio das equipes de saúde e assistência social.',
        'Publicar as regras de prioridade e usar a demanda territorial para planejar novas turmas.',
      ],
      implementationMilestone: 'Fila municipal auditável, com posição de cada pedido, atualização periódica e cobertura dos bairros.',
      monitoringSignal: 'Na próxima leitura, o atendimento em creche deve avançar em direção à referência; estagnação exige rever alcance, atualização e transparência da fila.',
      programs: [
        {
          name: 'Busca Ativa Escolar',
          description: 'Plataforma gratuita que apoia o município a localizar crianças fora da creche e da pré-escola.',
          url: 'https://buscaativaescolar.org.br',
        },
      ],
      bridge: ATTENDANCE_BRIDGE,
      legalRef: 'PNE 2026–2036 — meta 1.a e estratégia 1.3',
    }),
    frente({
      id: 'ampliar-oferta',
      mechanismId: 'distribuicao-territorial-das-vagas',
      title: 'Ampliar a oferta com apoio federal',
      steps: [
        'Estimar o déficit de vagas por bairro a partir das inscrições e da capacidade existente.',
        'Cadastrar no PAR os projetos de construção, ampliação ou equipagem compatíveis com esse déficit.',
        'Ordenar as propostas pelo impacto previsto sobre as áreas menos atendidas.',
      ],
      implementationMilestone: 'Carteira territorial de expansão aprovada, com capacidade adicional, custo, fonte de recurso e prazo para cada intervenção.',
      monitoringSignal: 'Na próxima leitura, o atendimento em creche deve avançar; se recuar, convém rever cobertura territorial, execução física e entrada em operação.',
      programs: [
        PAR,
        {
          name: 'Proinfância / Novo PAC',
          description: 'Construção, ampliação e mobiliário de creches e pré-escolas.',
          url: 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/programas/proinfancia',
        },
      ],
      bridge: DEMAND_BRIDGE,
      legalRef: 'PNE 2026–2036 — meta 1.a e estratégia 1.12',
    }),
  ]),

  '5.a': Object.freeze([
    frente({
      id: 'avaliar-e-recompor',
      mechanismId: 'lacunas-anteriores-de-aprendizagem',
      startHere: true,
      title: 'Avaliar e recompor as aprendizagens',
      steps: [
        'Aplicar instrumentos comuns de leitura e matemática no início e ao longo do período letivo.',
        'Definir intervenções por habilidade ainda não consolidada, turma e estudante.',
        'Reavaliar os alunos atendidos e ajustar a intensidade do apoio conforme a resposta observada.',
      ],
      implementationMilestone: 'Registro pedagógico consolidado, com lacunas priorizadas, responsáveis, prazos e evolução após as intervenções.',
      monitoringSignal: 'Na próxima leitura, a aprendizagem nos anos iniciais deve avançar; estagnação exige rever efetividade e cobertura da resposta pedagógica.',
      programs: [CNCA],
      bridge: TRAJECTORY_BRIDGE,
      legalRef: 'PNE 2026–2036 — estratégias 5.11, 3.10 e 3.15',
    }),
    frente({
      id: 'apoio-pedagogico-da-secretaria',
      mechanismId: 'apoio-pedagogico-descontinuo',
      title: 'Apoiar pedagogicamente as escolas',
      steps: [
        'Designar técnicos da secretaria para visitas regulares e devolutivas às equipes escolares.',
        'Oferecer formação continuada alinhada às dificuldades observadas nas primeiras turmas do ensino fundamental.',
        'Verificar se livros e materiais escolhidos pela rede chegam e são usados em todas as turmas.',
      ],
      implementationMilestone: 'Ciclo de suporte às escolas instituído, com calendário, responsáveis, registros de visita e encaminhamentos concluídos.',
      monitoringSignal: 'Na próxima leitura, a aprendizagem nos anos iniciais deve avançar; estagnação exige rever regularidade, coerência e alcance da assistência pedagógica.',
      programs: [
        CNCA,
        {
          name: 'PNLD',
          description: 'Livros e materiais didáticos distribuídos pelo governo federal, escolhidos pela rede.',
          url: 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/programas/programas-do-livro',
        },
      ],
      bridge: TRAJECTORY_BRIDGE,
      legalRef: 'PNE 2026–2036 — estratégia 3.13',
    }),
  ]),

  '11.c': Object.freeze([
    frente({
      id: 'eja-compativel-com-trabalho',
      mechanismId: 'oferta-eja-pouco-compativel',
      startHere: true,
      title: 'Oferecer EJA compatível com quem trabalha',
      steps: [
        'Estimar o público potencial por território e divulgar matrículas nos canais usados por jovens e adultos.',
        'Definir horários, locais e formatos compatíveis com a jornada de quem trabalha.',
        'Negociar com a rede estadual as vagas de ensino médio necessárias.',
      ],
      implementationMilestone: 'Programação municipal da EJA formalizada para o próximo período, com turmas confirmadas e responsabilidades definidas entre as redes.',
      monitoringSignal: 'Na próxima leitura, as matrículas na EJA integrada devem avançar; estagnação exige rever conveniência da oferta, conversão de interessados e permanência.',
      programs: [
        {
          name: 'Pacto Nacional pela Superação do Analfabetismo e Qualificação da EJA',
          description: 'Adesão federal que organiza apoio técnico e financeiro à oferta de EJA.',
        },
        {
          name: 'Pé-de-Meia',
          description: 'Incentivo financeiro federal à permanência e conclusão, incluindo estudantes da EJA.',
          url: 'https://www.gov.br/mec/pt-br/pe-de-meia',
        },
      ],
      bridge: MODALITIES_BRIDGE,
      legalRef: 'PNE 2026–2036 — metas 11.c e 11.d; estratégias 11.10 e 11.13',
    }),
    frente({
      id: 'eja-integrada-profissional',
      mechanismId: 'eja-sem-formacao-profissional',
      title: 'Integrar a EJA à formação profissional',
      steps: [
        'Levantar cursos, instituições formadoras e vagas que possam ser articulados à escolarização de jovens e adultos.',
        'Selecionar opções formativas e validar sua utilidade com estudantes, instituições formadoras e empregadores.',
        'Definir com a rede estadual quem ofertará cada componente e como serão feitas matrícula e certificação.',
      ],
      implementationMilestone: 'Arranjo interinstitucional pronto para abertura de turma, com capacidade definida, calendário comum e responsabilidades formalizadas.',
      monitoringSignal: 'Na próxima leitura, as matrículas na EJA integrada devem avançar; se recuarem, convém rever atratividade, acesso e continuidade do percurso.',
      programs: [
        {
          name: 'EJA integrada à educação profissional',
          description: 'Modalidade apoiada pelo governo federal no âmbito do pacto da EJA e da expansão da educação técnica.',
        },
      ],
      bridge: MODALITIES_BRIDGE,
      legalRef: 'PNE 2026–2036 — meta 12.c e estratégia 12.4',
    }),
  ]),

  '17.a': Object.freeze([
    frente({
      id: 'formacao-na-area-de-atuacao',
      mechanismId: 'docencias-fora-da-area',
      startHere: true,
      title: 'Formar os professores na área em que atuam',
      steps: [
        'Comparar a habilitação de cada professor com as disciplinas e etapas em que atua.',
        'Encaminhar os profissionais elegíveis para segunda licenciatura ou complementação pedagógica.',
        'Solicitar às universidades públicas turmas compatíveis com as necessidades da rede.',
      ],
      implementationMilestone: 'Plano nominal de qualificação aprovado, com percurso formativo, instituição e prazo definidos para cada docente elegível.',
      monitoringSignal: 'Na próxima leitura, o percentual de docências com formação adequada deve subir; estagnação exige rever adesão, conclusão e uso das novas habilitações.',
      programs: [
        {
          name: 'Parfor',
          description: 'Turmas de licenciatura e segunda licenciatura para professores em exercício.',
          url: 'https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/educacao-basica/parfor',
        },
        {
          name: 'Universidade Aberta do Brasil (UAB)',
          description: 'Licenciaturas públicas a distância com polos de apoio presencial.',
        },
        {
          name: 'Mais Professores para o Brasil',
          description: 'Política federal de atração, formação e valorização de docentes.',
        },
      ],
      bridge: PROFESSIONALS_BRIDGE,
      legalRef: 'PNE 2026–2036 — meta 17.a',
    }),
    frente({
      id: 'carreira-e-vinculos-estaveis',
      mechanismId: 'provimento-e-permanencia-docente',
      title: 'Estruturar carreira que atraia e fixe professores habilitados',
      steps: [
        'Comparar regras, vencimentos e progressões do magistério com o piso nacional e com redes que retêm profissionais habilitados.',
        'Projetar concursos e nomeações conforme as vagas permanentes e a previsão orçamentária.',
      ],
      implementationMilestone: 'Proposta de carreira e calendário de provimento formalizados, com impacto financeiro estimado e critérios objetivos de progressão.',
      monitoringSignal: 'Na próxima leitura, o percentual de docências com formação adequada deve subir; estagnação exige rever atratividade, rotatividade e ocupação das vagas.',
      programs: [
        {
          name: 'Piso nacional do magistério',
          description: 'Referência obrigatória de remuneração para os planos de carreira municipais.',
        },
      ],
      bridge: PROFESSIONALS_BRIDGE,
      legalRef: 'PNE 2026–2036 — metas 17.c e 17.d',
    }),
  ]),

  '4.a': Object.freeze([
    frente({
      id: 'encontrar-quem-esta-fora',
      mechanismId: 'saida-sem-resposta-rapida',
      startHere: true,
      title: 'Encontrar e rematricular quem está fora da escola',
      steps: [
        'Conferir mensalmente matrículas, frequência e cadastros sociais para localizar crianças e jovens fora da escola.',
        'Acionar saúde, assistência social e conselho tutelar para contato com cada família.',
        'Remover barreiras ao retorno e manter contato frequente nos primeiros meses.',
      ],
      implementationMilestone: 'Registro nominal de retorno escolar em funcionamento, com situação, responsável e desfecho de cada caso.',
      monitoringSignal: 'Na próxima leitura, o atendimento escolar deve avançar em direção à referência; recuo exige rever alcance da localização, efetivação da matrícula e nova saída.',
      programs: [
        {
          name: 'Busca Ativa Escolar',
          description: 'Plataforma gratuita (Unicef/Undime) para localizar e acompanhar o retorno de cada estudante.',
          url: 'https://buscaativaescolar.org.br',
        },
      ],
      bridge: ATTENDANCE_BRIDGE,
      legalRef: 'PNE 2026–2036 — meta 4.a e estratégia 4.10',
    }),
    frente({
      id: 'rede-preparada-para-o-clima',
      mechanismId: 'interrupcoes-em-eventos-climaticos',
      title: 'Preparar a rede para eventos climáticos',
      steps: [
        'Mapear unidades, rotas e serviços mais expostos a eventos extremos.',
        'Definir com a Defesa Civil procedimentos para proteger pessoas, manter atividades e recuperar dias letivos.',
        'Informar danos no sistema federal e preparar os pedidos de apoio para reparos.',
      ],
      implementationMilestone: 'Plano de continuidade educacional aprovado e testado, com níveis de alerta, responsáveis e alternativas de atendimento.',
      monitoringSignal: 'Na próxima leitura, o atendimento escolar deve avançar; recuo após novos eventos exige rever tempo de resposta, cobertura temporária e retomada das aulas.',
      programs: [
        {
          name: 'S2iD / Defesa Civil',
          description: 'Registro de desastres que dá acesso a transferências da União para reconstrução.',
        },
        PAR,
      ],
      legalRef: 'PNE 2026–2036 — estratégias 8.1 e 8.13',
    }),
  ]),

  '4.b': Object.freeze([
    frente({
      id: 'alfabetizar-na-idade-certa',
      mechanismId: 'atraso-acumulado',
      startHere: true,
      title: 'Alfabetizar cada criança na idade certa',
      steps: [
        'Integrar a rede às formações, aos materiais e às avaliações do compromisso federal de alfabetização.',
        'Identificar rapidamente cada criança que não consolidou leitura e escrita.',
        'Oferecer apoio de curta duração e verificar o progresso antes do fim do ciclo.',
      ],
      implementationMilestone: 'Mapa de domínio por estudante atualizado, com habilidades pendentes, atendimento recebido e evolução registrada.',
      monitoringSignal: 'Na próxima leitura, o percentual de estudantes em atraso nos anos iniciais deve cair; se subir, convém rever alcance, rapidez e efetividade das intervenções.',
      programs: [CNCA],
      bridge: TRAJECTORY_BRIDGE,
      legalRef: 'PNE 2026–2036 — meta 3.a e estratégia 3.10',
    }),
    frente({
      id: 'trajetorias-e-recomposicao',
      mechanismId: 'reprovacao-amplia-defasagem',
      title: 'Acompanhar trajetórias e recompor aprendizagens',
      steps: [
        'Sinalizar cedo estudantes com frequência irregular, baixo desempenho ou reprovação recente.',
        'Definir apoios específicos para as habilidades pendentes, sem adotar repetência como resposta padrão.',
        'Reavaliar a trajetória em intervalos curtos e ajustar a intervenção.',
      ],
      implementationMilestone: 'Plano individual de progressão ativo para o público priorizado, com objetivos de aprendizagem, prazos e decisões registradas.',
      monitoringSignal: 'Na próxima leitura, a reprovação nos anos iniciais deve cair; se subir, convém rever prevenção de risco, resposta pedagógica e critérios de avanço escolar.',
      programs: [PAR],
      bridge: TRAJECTORY_BRIDGE,
      legalRef: 'PNE 2026–2036 — estratégias 3.15 e 5.11',
    }),
  ]),

  '19.c': Object.freeze([
    frente({
      id: 'acessibilidade-das-escolas',
      mechanismId: 'pendencias-sem-inventario-unico',
      startHere: true,
      title: 'Adequar prédios e salas à acessibilidade',
      steps: [
        'Vistoriar cada unidade com lista padronizada de barreiras arquitetônicas, comunicacionais e de uso.',
        'Ordenar as intervenções pelo risco e pelo número de estudantes afetados.',
        'Combinar recursos do PAR e repasses às escolas conforme o porte de cada serviço.',
      ],
      implementationMilestone: 'Inventário municipal validado, com barreiras classificadas, orçamento preliminar e cronograma de adequação por unidade.',
      monitoringSignal: 'Na próxima leitura, o percentual de salas acessíveis deve subir; estagnação exige rever execução, cobertura e uso efetivo das melhorias.',
      programs: [
        PAR,
        {
          name: 'PDDE e ações de acessibilidade',
          description: 'Recursos repassados diretamente às escolas, com ações voltadas à acessibilidade.',
          url: 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/programas/pdde',
        },
      ],
      bridge: INFRASTRUCTURE_BRIDGE,
      legalRef: 'PNE 2026–2036 — meta 19.c; estratégias 19.4 e 10.2',
    }),
    frente({
      id: 'investimento-por-padroes-minimos',
      mechanismId: 'adequacoes-sem-programacao-financeira',
      title: 'Planejar o investimento por padrões mínimos',
      steps: [
        'Comparar a situação de cada escola com os padrões nacionais de infraestrutura e funcionamento.',
        'Estimar custo, urgência e impacto das melhorias necessárias.',
        'Definir metas anuais e divulgar à comunidade quanto foi aplicado e o que foi entregue.',
      ],
      implementationMilestone: 'Programa plurianual de investimentos aprovado, com carteira hierarquizada, fontes de financiamento e entregas por exercício.',
      monitoringSignal: 'Na próxima leitura, o percentual de salas acessíveis deve subir; estagnação exige rever suficiência dos recursos, ritmo de entrega e aderência às prioridades.',
      programs: [PAR],
      bridge: INFRASTRUCTURE_BRIDGE,
      legalRef: 'PNE 2026–2036 — estratégias 19.4, 19.11 e 19.19',
    }),
  ]),
})

/** Chave estável de uma frente, sem uso como identidade municipal. */
export function matrizFrenteKey(goalId: string, frenteId: string): string {
  return `${goalId}|${frenteId}`
}

export function resolveMatrizFrentes(goalId: string): readonly MatrizFrente[] {
  return MATRIZ_FRENTES[goalId] ?? []
}
