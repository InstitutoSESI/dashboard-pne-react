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
  readonly url: string
}

export interface MatrizFrenteBridge {
  readonly label: string
  readonly page: AppPageKey
  readonly params?: Readonly<Record<string, string>>
}

export interface MatrizGoalSupport {
  /** Referências que servem aos dois caminhos e aparecem uma única vez na meta. */
  readonly programs: readonly MatrizFrenteProgram[]
  /** Aprofundamento comum aos dois caminhos, exibido uma única vez. */
  readonly bridge?: MatrizFrenteBridge
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

const PACTO_RECOMPOSICAO = Object.freeze({
  name: 'Pacto Nacional pela Recomposição das Aprendizagens',
  description: 'Adesão voluntária com diagnóstico, reorganização curricular, formação e acompanhamento das aprendizagens.',
  url: 'https://www.gov.br/mec/pt-br/acesso-a-informacao/perguntas-frequentes/pacto-nacional-pela-recomposicao-das-aprendizagens/adesao/a-adesao-ao-pacto-e',
})

const GUIA_REORGANIZACAO_CURRICULAR = Object.freeze({
  name: 'Guia de Reorganização Curricular para a Recomposição',
  description: 'Orientação do MEC para priorizar aprendizagens, planejar intervenções e acompanhar o progresso.',
  url: 'https://www.gov.br/mec/pt-br/recomposicao-aprendizagens/GuiaReorganizaoCurricularparaRecomposi.pdf',
})

const ESCOLA_ADOLESCENCIAS = Object.freeze({
  name: 'Programa Escola das Adolescências',
  description: 'Apoio federal aos anos finais com foco em transição, participação estudantil, currículo e recomposição.',
  url: 'https://www.gov.br/mec/pt-br/escola-das-adolescencias/Guia2_MEC_AnosFinais_v03.pdf',
})

const PACTO_EJA = Object.freeze({
  name: 'Pacto Nacional pela Superação do Analfabetismo e Qualificação da EJA',
  description: 'Política federal que organiza chamada pública, CadEJA, formação, apoio técnico e ampliação da oferta.',
  url: 'https://www.gov.br/mec/pt-br/pacto-eja/como-funciona',
})

const PROGRAMA_BRASIL_ALFABETIZADO = Object.freeze({
  name: 'Programa Brasil Alfabetizado',
  description: 'Apoio técnico e financeiro, em colaboração com municípios, para organizar turmas de alfabetização de jovens, adultos e idosos.',
  url: 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/programas/programas_suplementares/eja/pba',
})

const DIRETRIZES_EJA = Object.freeze({
  name: 'Diretrizes da EJA — Parecer CNE/CEB nº 3/2025',
  description: 'Parecer homologado que fundamenta as diretrizes para oferta, currículo, avaliação e reconhecimento de saberes na EJA.',
  url: 'https://www.gov.br/mec/pt-br/cne/2025/janeiro-2025/pceb003_25.pdf',
})

const ENCCEJA = Object.freeze({
  name: 'Encceja',
  description: 'Exame do Inep para certificação do ensino fundamental ou médio e emissão de declarações parciais de proficiência.',
  url: 'https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/encceja/encceja',
})

const PNLD_EJA = Object.freeze({
  name: 'PNLD EJA 2026–2029',
  description: 'Obras didáticas e orientações oficiais para os anos iniciais e finais do ensino fundamental na EJA.',
  url: 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/programas/programas-do-livro/pnld/escolha-pnld-eja-2026-a-2029',
})

const PDDE_EQUIDADE_EJA = Object.freeze({
  name: 'PDDE Equidade — EJA',
  description: 'Referências do MEC para uso do apoio suplementar em condições de acesso, acolhimento e permanência nas escolas elegíveis.',
  url: 'https://www.gov.br/mec/pt-br/pdde/pdde-equidade/documentos',
})

const PE_DE_MEIA = Object.freeze({
  name: 'Pé-de-Meia',
  description: 'Incentivo federal à permanência e conclusão de estudantes elegíveis do ensino médio, inclusive na EJA.',
  url: 'https://www.gov.br/mec/pt-br/pe-de-meia',
})

const ESCOLA_TEMPO_INTEGRAL = Object.freeze({
  name: 'Programa Escola em Tempo Integral',
  description: 'Adesão municipal com plano de implementação e recursos para criar matrículas em jornada integral com equidade.',
  url: 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/programas/programas_suplementares/educacao-basica/educacao-basica',
})

const UAB = Object.freeze({
  name: 'Sistema Universidade Aberta do Brasil',
  description: 'Graduações públicas a distância apoiadas por polos presenciais mantidos em regime de colaboração.',
  url: 'https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/articulacao-e-inovacao-em-educacao-aberta/sistema-universidade-aberta-do-brasil/mantenedores-de-polos-uab',
})

const PNATE = Object.freeze({
  name: 'Programa Nacional de Apoio ao Transporte do Escolar',
  description: 'Assistência financeira federal ao transporte de estudantes da educação básica pública residentes em área rural.',
  url: 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/programas/pnate/pnate-home/',
})

const CNCT = Object.freeze({
  name: 'Catálogo Nacional de Cursos Técnicos',
  description: 'Referência oficial de denominações, perfis profissionais, carga horária e requisitos da educação técnica.',
  url: 'https://cnct.mec.gov.br/',
})

const PRONATEC = Object.freeze({
  name: 'Pronatec',
  description: 'Política federal de ampliação da educação profissional e tecnológica por meio de instituições ofertantes habilitadas.',
  url: 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/programas/programas_suplementares/educacao_profissional_e_tecnologica/ps-pronatec',
})

const FNDE_MANUAIS_OBRAS = Object.freeze({
  name: 'Manuais e documentos técnicos do FNDE',
  description: 'Referências para diagnóstico, projeto, execução e manutenção da infraestrutura escolar.',
  url: 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/acoes/obras-projetos-padronizados/manuais-e-documentos-tecnicos-1',
})

const CONAQEI = Object.freeze({
  name: 'Compromisso Nacional pela Qualidade e Equidade na Educação Infantil',
  description: 'Orientações do MEC para acesso, equidade, qualidade, gestão e avaliação na educação infantil.',
  url: 'https://www.gov.br/mec/pt-br/pnei/conaquei.pdf',
})

const RETRATO_EDUCACAO_INFANTIL = Object.freeze({
  name: 'Retrato da Educação Infantil',
  description: 'Levantamento e relatório do MEC para identificar demanda, oferta, listas de espera e condições de atendimento.',
  url: 'https://www.gov.br/mec/pt-br/pnei/RelatriodeConsolidaoRetratoEIMEC.pdf',
})

const AVALIACAO_ALFABETIZACAO = Object.freeze({
  name: 'Avaliação da Alfabetização (Inep)',
  description: 'Referência oficial para interpretar padrões de alfabetização e acompanhar resultados ao final do 2º ano.',
  url: 'https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/avaliacao-da-alfabetizacao',
})

const ORIENTACOES_FORMACAO_CNCA = Object.freeze({
  name: 'Orientações para formação continuada do CNCA',
  description: 'Documento do MEC para organizar formação em rede, acompanhamento e atuação dos articuladores.',
  url: 'https://www.gov.br/mec/pt-br/crianca-alfabetizada/pdf/orientacoes_formacao_continuada.pdf',
})

const EDUCACAO_E_RESILIENCIA_CLIMATICA = Object.freeze({
  name: 'Educação, meio ambiente e mudanças climáticas',
  description: 'Orientação do MEC para prevenção de riscos, resiliência e continuidade das comunidades escolares.',
  url: 'https://www.gov.br/mec/pt-br/media/secadi/educacao-ambiental.pdf',
})

const PAR_EQUIPAMENTOS = Object.freeze({
  name: 'Equipamentos e infraestrutura no PAR',
  description: 'Canal do FNDE para demandas de infraestrutura, materiais, equipamentos e insumos escolares.',
  url: 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/programas/par/infraestrutura-fisica-escolar/transporte-materiais-escolares-equipamentos-insumos-e-outros',
})

const GUIA_PROJETOS_CURSOS_TECNICOS = Object.freeze({
  name: 'Guia para projetos pedagógicos de cursos técnicos',
  description: 'Orientação do MEC para estruturar perfil, currículo, prática, avaliação e condições de oferta.',
  url: 'https://www.gov.br/mec/pt-br/media/seb-1/pdf/WEBDesenvolvimentodeProjetosPedagogicosdeCursosTecnicos2.pdf',
})

const ACESSO_UNICO = Object.freeze({
  name: 'Portal Único de Acesso ao Ensino Superior',
  description: 'Canal oficial do MEC para oportunidades e processos federais de ingresso e financiamento estudantil.',
  url: 'https://acessounico.mec.gov.br/',
})

const ESCOLA_ACESSIVEL = Object.freeze({
  name: 'Programa Escola Acessível',
  description: 'Recursos do PDDE Estrutura para adequações de acessibilidade em escolas públicas elegíveis.',
  url: 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/programas/pdde/conta-pdde-estrutura-1/programa-escola-acessivel',
})

const PROGRAMA_INFRAESTRUTURA_ESCOLAR = Object.freeze({
  name: 'Programa Nacional de Infraestrutura Escolar',
  description: 'Marco legal de colaboração para expansão, adequação e modernização da infraestrutura pública, sujeito à regulamentação e aos instrumentos vigentes.',
  url: 'https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2026/lei/l15388.htm',
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
      monitoringSignal: 'Pedidos atualizados, tempo mediano de espera, famílias localizadas e proporção de solicitações que chegam à matrícula.',
      programs: [
        {
          name: 'Busca Ativa Escolar',
          description: 'Plataforma gratuita que apoia o município a localizar crianças fora da creche e da pré-escola.',
          url: 'https://buscaativaescolar.org.br',
        },
        {
          name: 'Lei da lista de espera na educação infantil',
          description: 'A Lei 14.851/2024 exige levantamento e divulgação da demanda, critérios transparentes e planejamento da expansão.',
          url: 'https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2024/lei/l14851.htm',
        },
        CONAQEI,
      ],
      bridge: ATTENDANCE_BRIDGE,
      legalRef: 'PNE 2026–2036 — base principal: meta 1.a; complemento: estratégia 1.3',
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
      monitoringSignal: 'Vagas adicionadas e ocupadas por território, intervenções concluídas no prazo e redução dos vazios de atendimento.',
      programs: [
        PAR,
        {
          name: 'Proinfância / Novo PAC',
          description: 'Construção, ampliação e mobiliário de creches e pré-escolas.',
          url: 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/programas/proinfancia',
        },
        RETRATO_EDUCACAO_INFANTIL,
      ],
      bridge: DEMAND_BRIDGE,
      legalRef: 'PNE 2026–2036 — base principal: meta 1.a; complemento: estratégia 1.12',
    }),
  ]),

  '5.a': Object.freeze([
    frente({
      id: 'avaliar-e-recompor',
      mechanismId: 'lacunas-anteriores-de-aprendizagem',
      startHere: true,
      title: 'Diagnosticar e recompor o componente avaliado',
      steps: [
        'Aplicar instrumentos comuns do componente avaliado no início e ao longo do período letivo.',
        'Definir intervenções por habilidade ainda não consolidada, turma e estudante.',
        'Reavaliar os alunos atendidos e ajustar a intensidade do apoio conforme a resposta observada.',
      ],
      implementationMilestone: 'Registro pedagógico consolidado, com lacunas priorizadas, responsáveis, prazos e evolução após as intervenções.',
      monitoringSignal: 'Estudantes diagnosticados no componente avaliado, atendidos por habilidade e reavaliados com progresso após a intervenção.',
      programs: [CNCA],
      legalRef: 'PNE 2026–2036 — base principal: meta 5.a; complemento: estratégias 5.11 e 5.12',
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
      monitoringSignal: 'Escolas visitadas no calendário, devolutivas concluídas e encaminhamentos pedagógicos executados no prazo.',
      programs: [
        {
          name: 'PNLD',
          description: 'Livros e materiais didáticos distribuídos pelo governo federal, escolhidos pela rede.',
          url: 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/programas/programas-do-livro',
        },
      ],
      legalRef: 'PNE 2026–2036 — base principal: meta 5.a; complemento: estratégias 5.15, 5.17 e 5.22',
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
      monitoringSignal: 'Interessados encaminhados, matriculados, frequentes e concluintes por turno, com motivo conhecido em cada perda do percurso.',
      programs: [
        PE_DE_MEIA,
      ],
      legalRef: 'PNE 2026–2036 — base principal: meta 11.c; complemento: estratégias 11.2, 11.3, 11.5 e 11.12',
    }),
    frente({
      id: 'eja-integrada-profissional',
      mechanismId: 'conclusao-sem-certificacao-articulada',
      title: 'Articular reconhecimento e certificação',
      steps: [
        'Orientar cada adulto sobre retomada da EJA, Encceja e aproveitamento de declarações parciais, conforme seu histórico.',
        'Pactuar com rede estadual e instituições certificadoras um fluxo de encaminhamento e documentação.',
        'Acompanhar inscrição, avaliação, emissão do documento e continuidade dos estudos quando necessária.',
      ],
      implementationMilestone: 'Fluxo de certificação pactuado, com critérios, responsáveis, documentação, calendário e encaminhamento de cada interessado.',
      monitoringSignal: 'Adultos orientados para certificação, inscrições concluídas, declarações de proficiência e certificados emitidos.',
      programs: [ENCCEJA],
      legalRef: 'PNE 2026–2036 — base principal: meta 11.c; complemento: estratégias 11.12, 11.20 e 11.22',
    }),
  ]),

  '17.a': Object.freeze([
    frente({
      id: 'formacao-na-area-de-atuacao',
      mechanismId: 'docencias-fora-da-area',
      startHere: true,
      title: 'Formar docentes para a etapa e a área indicadas',
      steps: [
        'Comparar a habilitação de cada professor com as disciplinas e etapas em que atua.',
        'Encaminhar os profissionais elegíveis para segunda licenciatura ou complementação pedagógica.',
        'Solicitar às universidades públicas turmas compatíveis com as necessidades da rede.',
      ],
      implementationMilestone: 'Plano nominal de qualificação aprovado, com percurso formativo, instituição e prazo definidos para cada docente elegível.',
      monitoringSignal: 'Docências prioritárias mapeadas, profissionais matriculados, percursos concluídos e novas habilitações aplicadas na etapa indicada.',
      programs: [
        {
          name: 'Parfor',
          description: 'Turmas de licenciatura e segunda licenciatura para professores em exercício.',
          url: 'https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/educacao-basica/parfor/parfor',
        },
        UAB,
      ],
      legalRef: 'PNE 2026–2036 — base principal: meta 17.a; complemento: estratégias 17.1, 17.4 e 17.11',
    }),
    frente({
      id: 'carreira-e-vinculos-estaveis',
      mechanismId: 'lotacao-fora-da-area',
      title: 'Corrigir a atribuição de turmas fora da habilitação',
      steps: [
        'Revisar a distribuição de componentes, etapas e cargas horárias à luz das habilitações já existentes na rede.',
        'Corrigir lotações possíveis e registrar as lacunas que realmente exigem formação ou novo provimento.',
        'Integrar as lacunas permanentes ao planejamento de pessoal, carreira e orçamento.',
      ],
      implementationMilestone: 'Mapa de lotação revisado, com correções executadas e lacunas remanescentes vinculadas a formação, seleção ou provimento.',
      monitoringSignal: 'Turmas revisadas, lotações corrigidas e redução de docências atribuídas fora da habilitação disponível na rede.',
      programs: [],
      legalRef: 'PNE 2026–2036 — base principal: meta 17.a; complemento: estratégias 17.11 e 17.25',
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
      monitoringSignal: 'Dias entre o primeiro alerta e o contato, estudantes rematriculados e proporção que mantém frequência após o retorno.',
      programs: [
        {
          name: 'Busca Ativa Escolar',
          description: 'Plataforma gratuita (Unicef/Undime) para localizar e acompanhar o retorno de cada estudante.',
          url: 'https://buscaativaescolar.org.br',
        },
      ],
      bridge: ATTENDANCE_BRIDGE,
      legalRef: 'PNE 2026–2036 — base principal: meta 4.a; complemento: estratégias 4.10 e 4.14',
    }),
    frente({
      id: 'rede-preparada-para-o-clima',
      mechanismId: 'barreira-documentada-ao-retorno',
      title: 'Remover a barreira comprovada ao retorno',
      steps: [
        'Classificar cada caso por barreira e mobilizar a resposta específica de transporte, documentação, proteção ou reorganização da oferta.',
        'Quando houver risco climático, pactuar com a Defesa Civil continuidade, rotas alternativas, reposição e registro de danos.',
        'Acompanhar o retorno até a frequência se estabilizar e revisar a resposta quando o impedimento persistir.',
      ],
      implementationMilestone: 'Protocolo por tipo de barreira aprovado, com responsáveis, prazo, encaminhamento e contingência climática onde necessária.',
      monitoringSignal: 'Casos por barreira, tempo até a solução e retorno sustentado; onde houver evento, dias letivos e rotas restabelecidos.',
      programs: [
        {
          name: 'S2iD / Defesa Civil',
          description: 'Registro de desastres que dá acesso a transferências da União para reconstrução.',
          url: 'https://s2id.mi.gov.br/',
        },
        EDUCACAO_E_RESILIENCIA_CLIMATICA,
        PAR,
      ],
      legalRef: 'PNE 2026–2036 — base principal: meta 4.a; complemento: estratégias 4.1, 4.7 e 8.13',
    }),
  ]),

  '4.b': Object.freeze([
    frente({
      id: 'alfabetizar-na-idade-certa',
      mechanismId: 'atraso-acumulado',
      startHere: true,
      title: 'Acompanhar individualmente a trajetória nos anos iniciais',
      steps: [
        'Localizar em qual ano, transição ou interrupção começou a defasagem de cada estudante priorizado.',
        'Definir apoio pedagógico, frequência e prazo para regularizar a trajetória sem reduzir as expectativas de aprendizagem.',
        'Reavaliar aprendizagem e progressão em ciclos curtos até a trajetória se estabilizar.',
      ],
      implementationMilestone: 'Plano de trajetória ativo por estudante, com origem da defasagem, apoio, prazo, reavaliação e decisão seguinte registrados.',
      monitoringSignal: 'Estudantes com trajetória individual registrada, intervenções iniciadas no prazo e redução dos novos casos de distorção idade-série.',
      programs: [],
      legalRef: 'PNE 2026–2036 — base principal: meta 4.b; complemento: estratégias 4.6 e 5.13',
    }),
    frente({
      id: 'trajetorias-e-recomposicao',
      mechanismId: 'reprovacao-amplia-defasagem',
      title: 'Prevenir novas reprovações com apoio oportuno',
      steps: [
        'Revisar antes do fechamento do período os casos com aprendizagem pendente e risco de reprovação.',
        'Oferecer intervenção por habilidade e verificar a resposta antes da decisão de progressão.',
        'Analisar por escola se a reprovação reduziu dificuldades no período seguinte ou apenas ampliou a defasagem.',
      ],
      implementationMilestone: 'Protocolo de prevenção à reprovação implantado, com intervenção, reavaliação e decisão pedagógica documentadas.',
      monitoringSignal: 'Estudantes em risco atendidos antes da decisão, respostas pedagógicas registradas e novos casos de defasagem acompanhados.',
      programs: [],
      legalRef: 'PNE 2026–2036 — base principal: meta 4.b; complemento: estratégias 5.11 e 5.12',
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
      implementationMilestone: 'Inventário municipal validado, com barreiras de circulação, comunicação e uso classificadas e cronograma por unidade.',
      monitoringSignal: 'Unidades vistoriadas, barreiras críticas eliminadas e salas acessíveis em uso, separadas por rede e escola.',
      programs: [
        ESCOLA_ACESSIVEL,
      ],
      legalRef: 'PNE 2026–2036 — base principal: meta 19.c; complemento: estratégias 10.2, 19.4 e 19.9',
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
      monitoringSignal: 'Adequações com orçamento e fonte definidos, entregas anuais concluídas e pendências críticas remanescentes.',
      programs: [FNDE_MANUAIS_OBRAS, PROGRAMA_INFRAESTRUTURA_ESCOLAR],
      legalRef: 'PNE 2026–2036 — base principal: meta 19.c; complemento: estratégias 19.10, 19.11 e 19.19 e arts. 21 a 25',
    }),
  ]),

  '1.c': Object.freeze([
    frente({
      id: 'localizar-e-matricular-pre-escola',
      mechanismId: 'criancas-fora-do-cadastro',
      startHere: true,
      title: 'Localizar e matricular cada criança de 4 e 5 anos',
      steps: [
        'Usar o Retrato da Educação Infantil para reconciliar demanda, lista de espera, oferta e capacidade por território.',
        'Cruzar registros da educação, saúde e assistência social para localizar nominalmente quem ainda não tem matrícula.',
        'Acompanhar cada contato até a matrícula e a frequência inicial.',
      ],
      implementationMilestone: 'Relação nominal reconciliada, com situação de cada criança, unidade de destino, responsável pelo contato e desfecho.',
      monitoringSignal: 'Crianças localizadas, contatadas, matriculadas e frequentes, com motivo conhecido para cada caso ainda sem atendimento.',
      programs: [RETRATO_EDUCACAO_INFANTIL],
      bridge: ATTENDANCE_BRIDGE,
      legalRef: 'PNE 2026–2036 — base principal: meta 1.c; complemento: estratégias 1.3, 1.6 e 1.13',
    }),
    frente({
      id: 'organizar-oferta-pre-escola-territorio',
      mechanismId: 'vaga-distante-ou-transicao-fragil',
      title: 'Organizar a oferta de pré-escola por território',
      steps: [
        'Mapear capacidade, procura, deslocamento e recusas por unidade e turno.',
        'Confirmar a passagem das crianças da creche para a pré-escola antes do encerramento do ano letivo.',
        'Priorizar no PAR os ajustes de turma, transporte, ampliação ou nova unidade que removam os maiores vazios.',
      ],
      implementationMilestone: 'Plano territorial de atendimento aprovado, com cada lacuna vinculada a uma solução, capacidade, prazo e fonte de recurso.',
      monitoringSignal: 'Vagas disponíveis e ocupadas por território, transições confirmadas e recusas associadas a distância ou turno.',
      programs: [PAR],
      bridge: DEMAND_BRIDGE,
      legalRef: 'PNE 2026–2036 — base principal: meta 1.c; complemento: estratégias 1.11 e 1.12',
    }),
  ]),

  '3.a': Object.freeze([
    frente({
      id: 'ciclo-avaliacao-alfabetizacao',
      mechanismId: 'avaliacao-sem-resposta-comum',
      startHere: true,
      title: 'Transformar avaliação em resposta de alfabetização',
      steps: [
        'Aplicar instrumentos comuns no início do ciclo e em intervalos curtos, sem substituir a avaliação cotidiana do professor.',
        'Priorizar leitura, escrita e matemática por habilidade ainda não consolidada e por estudante.',
        'Reavaliar após cada intervenção e registrar a decisão pedagógica seguinte.',
      ],
      implementationMilestone: 'Ciclo municipal de avaliação e resposta ativo, com calendário, habilidades priorizadas, estudantes atendidos e devolutivas.',
      monitoringSignal: 'Crianças avaliadas, atendidas por habilidade e reavaliadas após a intervenção, com resposta pedagógica registrada.',
      programs: [AVALIACAO_ALFABETIZACAO],
      legalRef: 'PNE 2026–2036 — base principal: meta 3.a; complemento: estratégias 3.10 e 3.15',
    }),
    frente({
      id: 'formacao-acompanhada-alfabetizacao',
      mechanismId: 'formacao-sem-acompanhamento-pratico',
      title: 'Ligar formação continuada ao trabalho em sala',
      steps: [
        'Organizar a formação a partir das habilidades que os diagnósticos mostram como pendentes na rede.',
        'Garantir devolutivas regulares sobre planejamento, material, práticas observadas e resposta das crianças.',
        'Registrar quais ajustes foram aplicados e o que mudou nas turmas acompanhadas.',
      ],
      implementationMilestone: 'Plano de formação em rede executado, com articuladores, calendário, acompanhamento às escolas e produtos de cada ciclo.',
      monitoringSignal: 'Docentes acompanhados, devolutivas realizadas e ajustes de prática observados nas turmas do ciclo de alfabetização.',
      programs: [ORIENTACOES_FORMACAO_CNCA],
      legalRef: 'PNE 2026–2036 — base principal: meta 3.a; complemento: estratégias 3.7 e 3.13',
    }),
  ]),

  '4.c': Object.freeze([
    frente({
      id: 'alerta-precoce-anos-finais',
      mechanismId: 'risco-acumulado-nos-anos-finais',
      startHere: true,
      title: 'Agir cedo sobre risco de atraso nos anos finais',
      steps: [
        'Reunir frequência, reprovação, idade-série e habilidades pendentes em uma rotina de alerta por estudante.',
        'Definir uma resposta com prazo e responsável antes que o alerta se repita no período seguinte.',
        'Verificar se presença, aprendizagem e progressão reagiram ao apoio.',
      ],
      implementationMilestone: 'Rotina de alerta e resposta implantada em todas as escolas de anos finais, com casos, prazos e desfechos registrados.',
      monitoringSignal: 'Alertas tratados no prazo e estudantes que recuperam frequência, aprendizagem e progressão após o apoio.',
      programs: [PACTO_RECOMPOSICAO, GUIA_REORGANIZACAO_CURRICULAR],
      legalRef: 'PNE 2026–2036 — base principal: meta 4.c; complemento: estratégias 4.6 e 5.13',
    }),
    frente({
      id: 'fortalecer-transicao-anos-finais',
      mechanismId: 'transicao-e-pertencimento-fragil',
      title: 'Fortalecer a transição e o vínculo nos anos finais',
      steps: [
        'Preparar a passagem do 5º para o 6º ano com troca de informações pedagógicas e acolhimento dos estudantes.',
        'Criar espaços regulares de participação e escuta sobre currículo, convivência e apoio necessário.',
        'Acompanhar frequência e transferências nos primeiros meses de cada transição.',
      ],
      implementationMilestone: 'Protocolo de transição executado, com acolhimento, registros pedagógicos recebidos e acompanhamento dos estudantes.',
      monitoringSignal: 'Estudantes com transição acompanhada, frequência nos primeiros meses e transferências sem ruptura de vínculo.',
      programs: [ESCOLA_ADOLESCENCIAS],
      legalRef: 'PNE 2026–2036 — base principal: meta 4.c; complemento: estratégias 4.6 e 4.11',
    }),
  ]),

  '4.d': Object.freeze([
    frente({
      id: 'protocolo-transicao-ensino-medio',
      mechanismId: 'transicao-para-rede-estadual-fragil',
      startHere: true,
      title: 'Confirmar a passagem de cada concluinte ao ensino médio',
      steps: [
        'Compartilhar com a rede estadual, de forma segura, a relação de concluintes do 9º ano e a escola de destino prevista.',
        'Orientar estudantes e famílias sobre inscrição, documentos, calendário e benefícios federais aplicáveis.',
        'Conciliar a relação inicial com as matrículas efetivadas e tratar cada ausência.',
      ],
      implementationMilestone: 'Protocolo entre redes concluído, com relação nominal conciliada e encaminhamento registrado para cada estudante sem matrícula.',
      monitoringSignal: 'Concluintes do 9º ano conciliados com matrícula no ensino médio e ausências encaminhadas antes do início das aulas.',
      programs: [],
      bridge: ATTENDANCE_BRIDGE,
      legalRef: 'PNE 2026–2036 — base principal: meta 4.d; complemento: estratégia 4.6',
    }),
    frente({
      id: 'proteger-permanencia-ensino-medio',
      mechanismId: 'permanencia-no-medio-interrompida',
      title: 'Remover barreiras à permanência no ensino médio',
      steps: [
        'Acordar com a rede estadual um alerta rápido para faltas recorrentes e saída da escola.',
        'Articular contato familiar, transporte e acesso aos incentivos federais para cada estudante elegível.',
        'Acompanhar retorno, frequência e conclusão após o apoio.',
      ],
      implementationMilestone: 'Fluxo intersetorial de permanência ativo, com alertas recebidos, apoio mobilizado e retorno acompanhado.',
      monitoringSignal: 'Alertas recebidos da rede estadual, apoios mobilizados e estudantes que retornam e permanecem frequentando.',
      programs: [PNATE],
      bridge: TRAJECTORY_BRIDGE,
      legalRef: 'PNE 2026–2036 — base principal: meta 4.d; complemento: estratégias 4.8, 4.10 e 5.20',
    }),
  ]),

  '5.b': Object.freeze([
    frente({
      id: 'recompor-habilidades-anos-finais',
      mechanismId: 'lacunas-prioritarias-nos-anos-finais',
      startHere: true,
      title: 'Priorizar habilidades estruturantes nos anos finais',
      steps: [
        'Usar avaliações da rede e do Saeb para identificar habilidades que sustentam as aprendizagens seguintes.',
        'Reorganizar o planejamento para ensinar novamente essas habilidades sem reduzir o currículo a exercícios de teste.',
        'Acompanhar progresso por turma e estudante em ciclos definidos.',
      ],
      implementationMilestone: 'Mapa curricular priorizado em uso, com intervenções, estudantes atendidos e reavaliações registradas por ciclo.',
      monitoringSignal: 'Estudantes agrupados por habilidade do componente avaliado, atendidos e reavaliados com progresso em ciclos curtos.',
      programs: [GUIA_REORGANIZACAO_CURRICULAR],
      legalRef: 'PNE 2026–2036 — base principal: meta 5.b; complemento: estratégias 5.11 e 5.12',
    }),
    frente({
      id: 'apoio-pedagogico-para-adolescentes',
      mechanismId: 'apoio-pedagogico-aos-adolescentes',
      title: 'Desenhar apoio pedagógico com os adolescentes',
      steps: [
        'Escutar estudantes sobre horários, formatos e temas que favorecem participação no apoio.',
        'Integrar recomposição a projetos, tutoria e componentes do currículo, com presença acompanhada.',
        'Comparar adesão e progresso entre os formatos adotados.',
      ],
      implementationMilestone: 'Modelo de apoio dos anos finais executado, com escuta registrada, frequência, tutoria e progresso por grupo.',
      monitoringSignal: 'Participação nos formatos de apoio, frequência sustentada e progresso por turma e grupo de estudantes.',
      programs: [ESCOLA_ADOLESCENCIAS],
      legalRef: 'PNE 2026–2036 — base principal: meta 5.b; complemento: estratégias 4.11, 5.11 e 5.13',
    }),
  ]),

  '5.d': Object.freeze([
    frente({
      id: 'plano-interredes-aprendizagem-medio',
      mechanismId: 'recomposicao-desarticulada-entre-redes',
      startHere: true,
      title: 'Construir uma agenda de aprendizagem entre as redes',
      steps: [
        'Compartilhar a leitura das habilidades de saída do 9º ano e do diagnóstico de entrada no médio.',
        'Definir quais respostas cabem à rede municipal antes da transição e quais serão continuadas pela rede estadual.',
        'Acompanhar uma coorte de estudantes para verificar continuidade e progresso.',
      ],
      implementationMilestone: 'Plano inter-redes pactuado, com habilidades priorizadas, responsabilidades, calendário e coorte acompanhada.',
      monitoringSignal: 'Habilidades de saída e entrada comparadas, respostas pactuadas entre redes e estudantes acompanhados durante a transição.',
      programs: [GUIA_REORGANIZACAO_CURRICULAR],
      legalRef: 'PNE 2026–2036 — base principal: meta 5.d; complemento: estratégias 4.6 e 5.11',
    }),
    frente({
      id: 'integrar-aprendizagem-permanencia-medio',
      mechanismId: 'apoio-sem-intensidade-ajustada',
      title: 'Ajustar a intensidade do apoio pedagógico',
      steps: [
        'Agrupar estudantes conforme as habilidades pendentes e a resposta já observada ao apoio regular.',
        'Variar tempo, agrupamento, material e estratégia para os grupos que não progrediram no primeiro ciclo.',
        'Reavaliar o componente medido e registrar a decisão pedagógica seguinte com a rede estadual.',
      ],
      implementationMilestone: 'Ciclos de apoio diferenciados em execução, com agrupamentos, estratégias, reavaliação e decisão seguinte registrados.',
      monitoringSignal: 'Estudantes com apoio no componente avaliado intensificado, reavaliados e com progresso após cada ciclo.',
      programs: [],
      legalRef: 'PNE 2026–2036 — base principal: meta 5.d; complemento: estratégias 5.11, 5.12 e 5.13',
    }),
  ]),

  '6.a': Object.freeze([
    frente({
      id: 'planejar-expansao-tempo-integral',
      mechanismId: 'expansao-sem-prioridade-equitativa',
      startHere: true,
      title: 'Expandir o tempo integral com equidade',
      steps: [
        'Mapear procura, vulnerabilidade, capacidade física e territórios sem atendimento.',
        'Formalizar adesão e plano de implementação com matrículas, escolas, cronograma e aplicação dos recursos.',
        'Acompanhar ocupação das vagas e perfil do público alcançado.',
      ],
      implementationMilestone: 'Plano de expansão aprovado, com escolas, novas matrículas, critérios de equidade, recursos e cronograma de implantação.',
      monitoringSignal: 'Novas vagas ocupadas por território e perfil, estudantes atendidos em jornada integral e escolas implantadas conforme cronograma.',
      programs: [PAR],
      bridge: ATTENDANCE_BRIDGE,
      legalRef: 'PNE 2026–2036 — base principal: meta 6.a; complemento: estratégias 6.1, 6.5 e 6.15',
    }),
    frente({
      id: 'integrar-curriculo-tempo-integral',
      mechanismId: 'jornada-ampliada-sem-projeto-integrado',
      title: 'Integrar currículo e condições da jornada ampliada',
      steps: [
        'Revisar o projeto pedagógico para integrar base comum, experiências formativas e participação dos estudantes.',
        'Dimensionar equipe, alimentação, espaços, materiais e horários antes de ampliar matrículas.',
        'Monitorar frequência no turno completo, aprendizagem e percepção da comunidade escolar.',
      ],
      implementationMilestone: 'Projeto de tempo integral validado em cada escola, com currículo, equipe, espaços, alimentação e acompanhamento definidos.',
      monitoringSignal: 'Frequência no turno completo, atividades integradas executadas e condições de equipe, alimentação e espaços mantidas.',
      programs: [
        {
          name: 'Plano de monitoramento da Escola em Tempo Integral',
          description: 'Referência do MEC para acompanhar acesso, equidade, qualidade e implementação do programa.',
          url: 'https://www.gov.br/mec/pt-br/escola-em-tempo-integral/monitoramento-e-avaliacao/planodemonitoramentoeavaliacaoETI.pdf',
        },
      ],
      bridge: TRAJECTORY_BRIDGE,
      legalRef: 'PNE 2026–2036 — base principal: meta 6.a; complemento: estratégias 6.2 e 6.3',
    }),
  ]),

  '8.b': Object.freeze([
    frente({
      id: 'auditar-conforto-termico-escolas',
      mechanismId: 'diagnostico-termico-incompleto',
      startHere: true,
      title: 'Diagnosticar o conforto térmico por ambiente',
      steps: [
        'Medir condições nos horários críticos e registrar orientação solar, cobertura, sombra, ventilação e ocupação de cada sala.',
        'Priorizar soluções passivas como sombreamento, ventilação cruzada e melhoria de cobertura antes de dimensionar equipamentos.',
        'Classificar urgência, solução, custo e período adequado para a intervenção.',
      ],
      implementationMilestone: 'Laudo simplificado consolidado, com condição de cada ambiente, solução recomendada, custo preliminar e prioridade.',
      monitoringSignal: 'Ambientes medidos, soluções passivas priorizadas e salas que atingem condição adequada nos horários críticos.',
      programs: [FNDE_MANUAIS_OBRAS, EDUCACAO_E_RESILIENCIA_CLIMATICA],
      legalRef: 'PNE 2026–2036 — base principal: meta 8.b; complemento: estratégias 8.1 e 8.5',
    }),
    frente({
      id: 'equipar-e-manter-conforto-termico',
      mechanismId: 'equipamentos-sem-infraestrutura-e-manutencao',
      title: 'Equipar com segurança e garantir manutenção',
      steps: [
        'Verificar carga elétrica, proteção, instalação e consumo antes de definir ventiladores ou climatização.',
        'Cadastrar no PAR a demanda tecnicamente especificada e executar por ordem de prioridade.',
        'Instituir limpeza, manutenção preventiva e controle de ambientes ainda indisponíveis.',
      ],
      implementationMilestone: 'Plano de equipamentos executável, com adequação elétrica, especificação, aquisição, instalação e manutenção programadas.',
      monitoringSignal: 'Equipamentos instalados com adequação elétrica, taxa de funcionamento e manutenções concluídas no prazo.',
      programs: [
        PAR_EQUIPAMENTOS,
        {
          name: 'Especificações de ventiladores do FNDE',
          description: 'Referência técnica do portal de compras para aquisição e uso de ventiladores em escolas.',
          url: 'https://www.fnde.gov.br/portaldecompras/index.php/produtos/ventiladores/apresentacao-ventiladores',
        },
      ],
      legalRef: 'PNE 2026–2036 — base principal: meta 8.b; complemento: estratégias 8.5, 8.8 e 19.11',
    }),
  ]),

  '11.a': Object.freeze([
    frente({
      id: 'mapear-e-chamar-alfabetizacao-adultos',
      mechanismId: 'publico-nao-identificado-alfabetizacao',
      startHere: true,
      title: 'Identificar e mobilizar quem precisa se alfabetizar',
      steps: [
        'Realizar chamada pública e registrar no CadEJA território, idade, disponibilidade e interesse de cada pessoa localizada.',
        'Mobilizar educação, saúde e assistência social para alcançar quem não procura espontaneamente a escola.',
        'Acompanhar cada interessado até a turma, com motivo registrado quando a matrícula não ocorre.',
      ],
      implementationMilestone: 'Cadastro territorial ativo, com público localizado, interesse confirmado, encaminhamento e situação de matrícula.',
      monitoringSignal: 'Pessoas localizadas, encaminhadas e matriculadas em turmas de alfabetização, com perdas conhecidas em cada etapa.',
      programs: [PROGRAMA_BRASIL_ALFABETIZADO],
      legalRef: 'PNE 2026–2036 — base principal: meta 11.a; complemento: estratégias 11.3, 11.9 e 11.10',
    }),
    frente({
      id: 'garantir-continuidade-alfabetizacao-eja',
      mechanismId: 'alfabetizacao-sem-continuidade-eja',
      title: 'Ligar alfabetização à continuidade na EJA',
      steps: [
        'Organizar turmas próximas do público e compatíveis com rotinas de trabalho e cuidado.',
        'Formar educadores para alfabetização de jovens e adultos e planejar a passagem à escolarização básica.',
        'Acompanhar frequência, conclusão e ingresso no período seguinte.',
      ],
      implementationMilestone: 'Percurso de continuidade implantado, com turmas, educadores, transição para a EJA e acompanhamento dos concluintes.',
      monitoringSignal: 'Concluintes da alfabetização que ingressam na EJA e mantêm frequência no período seguinte.',
      programs: [PNLD_EJA],
      legalRef: 'PNE 2026–2036 — base principal: meta 11.a; complemento: estratégias 11.1, 11.13 e 11.15',
    }),
  ]),

  '11.b': Object.freeze([
    frente({
      id: 'organizar-fundamental-eja-flexivel',
      mechanismId: 'oferta-fundamental-incompativel-adultos',
      startHere: true,
      title: 'Organizar o ensino fundamental da EJA para a vida adulta',
      steps: [
        'Usar chamada pública e CadEJA para dimensionar público, território, turno e barreiras de acesso.',
        'Rever calendário, local e organização curricular, preservando as aprendizagens e a certificação exigidas.',
        'Confirmar turmas e comunicar cada interessado até a matrícula.',
      ],
      implementationMilestone: 'Oferta do fundamental na EJA aprovada, com turmas, horários, locais, percurso curricular e interessados encaminhados.',
      monitoringSignal: 'Interessados com oferta compatível, matrículas efetivadas e frequência sustentada por território e turno.',
      programs: [],
      legalRef: 'PNE 2026–2036 — base principal: meta 11.b; complemento: estratégias 11.2, 11.5 e 11.13',
    }),
    frente({
      id: 'acompanhar-permanencia-eja-fundamental',
      mechanismId: 'saberes-sem-reconhecimento-certificacao',
      title: 'Transformar saberes prévios em percurso de conclusão',
      steps: [
        'Realizar diagnóstico inicial e reunir histórico, declarações e experiências formativas relevantes.',
        'Aplicar os critérios do sistema para classificação, reclassificação e aproveitamento, com registro do que foi reconhecido.',
        'Definir as aprendizagens restantes, a sequência de estudo e a previsão de conclusão de cada estudante.',
      ],
      implementationMilestone: 'Percurso individual implantado, com saberes reconhecidos, aprendizagens restantes, critérios e decisão final documentados.',
      monitoringSignal: 'Estudantes avaliados, saberes aproveitados, tempo até a conclusão e continuidade na etapa seguinte.',
      programs: [],
      legalRef: 'PNE 2026–2036 — base principal: meta 11.b; complemento: estratégias 11.13, 11.20 e 11.22',
    }),
  ]),

  '11.d': Object.freeze([
    frente({
      id: 'converter-chamada-em-matricula-eja',
      mechanismId: 'chamada-publica-nao-converte-matricula',
      startHere: true,
      title: 'Converter a chamada pública em matrícula na EJA',
      steps: [
        'Integrar chamada pública, CadEJA e canais locais em um único fluxo de entrada.',
        'Encaminhar cada interessado a uma turma compatível e acompanhar documentação e comparecimento inicial.',
        'Medir as perdas entre localização, interesse, encaminhamento, matrícula e frequência.',
      ],
      implementationMilestone: 'Fluxo de conversão em funcionamento, com volume e motivo de perda conhecidos em cada etapa até a frequência inicial.',
      monitoringSignal: 'Conversão entre localização, interesse, encaminhamento, matrícula e frequência inicial, com motivo registrado para cada perda.',
      programs: [],
      legalRef: 'PNE 2026–2036 — base principal: meta 11.d; complemento: estratégias 11.3, 11.9 e 11.10',
    }),
    frente({
      id: 'estabilizar-oferta-territorial-eja',
      mechanismId: 'turmas-instaveis-e-barreiras-permanencia',
      title: 'Estabilizar a oferta da EJA nos territórios',
      steps: [
        'Planejar a oferta para mais de um período com base no cadastro territorial e na continuidade dos estudantes.',
        'Evitar mudanças de local ou turno sem alternativa e comunicação individual aos matriculados.',
        'Acompanhar ocupação, frequência, fechamento e continuidade de cada turma.',
      ],
      implementationMilestone: 'Mapa plurianual de turmas aprovado, com local, turno, público previsto, regra de continuidade e acompanhamento da ocupação.',
      monitoringSignal: 'Turmas mantidas no local e turno previstos, ocupação, frequência e continuidade confirmadas no período seguinte.',
      programs: [PDDE_EQUIDADE_EJA],
      legalRef: 'PNE 2026–2036 — base principal: meta 11.d; complemento: estratégias 11.2, 11.7 e 11.8',
    }),
  ]),

  '12.a': Object.freeze([
    frente({
      id: 'mapear-oferta-tecnica-e-interesse',
      mechanismId: 'oferta-tecnica-sem-leitura-territorial',
      startHere: true,
      title: 'Mapear oferta técnica e interesse dos estudantes',
      steps: [
        'Usar Sistec e Catálogo Nacional para mapear cursos, vagas, requisitos e instituições alcançáveis na região.',
        'Consultar estudantes sobre interesse, deslocamento, turno e condições de participação.',
        'Confrontar opções com capacidade das instituições e informações econômicas, sem presumir procura.',
      ],
      implementationMilestone: 'Mapa regional validado, com cursos possíveis, instituição, capacidade, interesse estudantil, acesso e lacunas de oferta.',
      monitoringSignal: 'Opções consultadas, interesse validado, vagas formalizadas, matrículas efetivadas e ocupação por curso.',
      programs: [
        CNCT,
        {
          name: 'Dados abertos da educação profissional e tecnológica',
          description: 'Bases oficiais do MEC para consultar cursos, unidades e registros do Sistec.',
          url: 'https://dadosabertos.mec.gov.br/ept',
        },
      ],
      legalRef: 'PNE 2026–2036 — base principal: meta 12.a; complemento: estratégias 12.1 e 12.11',
    }),
    frente({
      id: 'formalizar-arranjo-oferta-tecnica',
      mechanismId: 'articulacao-regional-insuficiente',
      title: 'Formalizar um arranjo regional de oferta técnica',
      steps: [
        'Definir com rede estadual, institutos federais e instituições habilitadas quem pode ofertar cada curso.',
        'Acordar vagas, local, calendário, projeto pedagógico, certificação, transporte e responsabilidades.',
        'Registrar a etapa de autorização e os requisitos para abertura da turma.',
      ],
      implementationMilestone: 'Arranjo formalizado, com instituição ofertante, curso, vagas, local, calendário, acesso e responsabilidades definidos.',
      monitoringSignal: 'Arranjos com responsabilidades assinadas, turmas autorizadas e vagas abertas e ocupadas no calendário acordado.',
      programs: [PRONATEC, GUIA_PROJETOS_CURSOS_TECNICOS],
      legalRef: 'PNE 2026–2036 — base principal: meta 12.a; complemento: estratégias 12.4 e 12.6',
    }),
  ]),

  '12.c': Object.freeze([
    frente({
      id: 'desenhar-percurso-eja-ept-integrado',
      mechanismId: 'curriculo-e-certificacao-desconectados',
      startHere: true,
      title: 'Desenhar um percurso único de EJA e formação profissional',
      steps: [
        'Definir um projeto pedagógico integrado, com aprendizagens, cargas horárias e calendário coerentes.',
        'Formalizar matrícula, avaliação, certificação, equipe e atribuição de cada instituição envolvida.',
        'Testar o fluxo completo antes de abrir inscrições.',
      ],
      implementationMilestone: 'Projeto integrado aprovado, com currículo, calendário, matrícula, equipe, avaliação, certificação e responsabilidades.',
      monitoringSignal: 'Projetos integrados aprovados, turmas abertas e estudantes com matrícula e certificação em fluxo único.',
      programs: [GUIA_PROJETOS_CURSOS_TECNICOS],
      legalRef: 'PNE 2026–2036 — base principal: meta 12.c; complemento: estratégias 11.6, 12.4 e 12.5',
    }),
    frente({
      id: 'validar-acesso-utilidade-eja-ept',
      mechanismId: 'curso-sem-acesso-ou-utilidade-validada',
      title: 'Validar acesso e utilidade antes de abrir a turma',
      steps: [
        'Apresentar opções reais aos estudantes potenciais e registrar interesse, requisitos e barreiras.',
        'Ajustar turno, local, deslocamento e apoio digital sem prometer resultados profissionais não comprovados.',
        'Acompanhar matrícula, frequência e continuidade no percurso integrado.',
      ],
      implementationMilestone: 'Proposta validada com o público, com barreiras tratadas, turma confirmada e acompanhamento de adesão e continuidade.',
      monitoringSignal: 'Interesse validado, barreiras tratadas, matrículas efetivadas e continuidade no percurso integrado.',
      programs: [CNCT],
      legalRef: 'PNE 2026–2036 — base principal: meta 12.c; complemento: estratégias 11.5, 11.7, 12.6 e 12.7',
    }),
  ]),

  '14.d': Object.freeze([
    frente({
      id: 'fortalecer-polo-uab-oferta-regional',
      mechanismId: 'acesso-superior-distante-ou-restrito',
      startHere: true,
      title: 'Fortalecer o polo UAB e a oferta regional',
      steps: [
        'Mapear polos, cursos ativos, procura, conectividade e deslocamento da população local.',
        'Verificar se o polo mantido pelo município atende às condições físicas, tecnológicas e de pessoal da Capes.',
        'Atuar por editais vigentes e com instituições públicas para articular cursos compatíveis com a procura validada.',
      ],
      implementationMilestone: 'Plano do polo formalizado, com diagnóstico de estrutura, cursos de interesse, instituições contatadas e chamadas aplicáveis.',
      monitoringSignal: 'Condições do polo atendidas, cursos articulados em editais vigentes, vagas ofertadas e ocupação pela população local.',
      programs: [],
      bridge: DEMAND_BRIDGE,
      legalRef: 'PNE 2026–2036 — base principal: meta 14.d; complemento: estratégias 14.1 e 14.4',
    }),
    frente({
      id: 'apoiar-transicao-ensino-superior',
      mechanismId: 'transicao-ensino-medio-superior-fragil',
      title: 'Apoiar a transição para o ensino superior',
      steps: [
        'Organizar orientação antecipada sobre Enem e processos federais de seleção, bolsa e financiamento.',
        'Oferecer acesso digital assistido para inscrição, documentos e acompanhamento de prazos.',
        'Acompanhar concluintes orientados, inscrições, aprovações e matrículas efetivadas.',
      ],
      implementationMilestone: 'Calendário de transição executado, com estudantes orientados, inscrições assistidas e matrículas acompanhadas.',
      monitoringSignal: 'Concluintes orientados, inscrições completas, participação nos processos e matrículas efetivadas.',
      programs: [ACESSO_UNICO],
      bridge: TRAJECTORY_BRIDGE,
      legalRef: 'PNE 2026–2036 — base principal: meta 14.d; complemento: estratégias 14.5 e 14.8',
    }),
  ]),
})

function goalSupport(entry: MatrizGoalSupport): MatrizGoalSupport {
  return Object.freeze({
    ...entry,
    programs: Object.freeze(entry.programs.map((program) => Object.freeze({ ...program }))),
    bridge: entry.bridge
      ? Object.freeze({
          ...entry.bridge,
          params: entry.bridge.params ? Object.freeze({ ...entry.bridge.params }) : undefined,
        })
      : undefined,
  })
}

/** Apoios e aprofundamentos que servem igualmente aos dois caminhos da meta. */
export const MATRIZ_GOAL_SUPPORT: Readonly<Record<string, MatrizGoalSupport>> = Object.freeze({
  '1.c': goalSupport({ programs: [CONAQEI] }),
  '3.a': goalSupport({ programs: [CNCA], bridge: TRAJECTORY_BRIDGE }),
  '4.b': goalSupport({ programs: [PACTO_RECOMPOSICAO], bridge: TRAJECTORY_BRIDGE }),
  '4.c': goalSupport({ programs: [], bridge: TRAJECTORY_BRIDGE }),
  '4.d': goalSupport({ programs: [PE_DE_MEIA] }),
  '5.a': goalSupport({ programs: [PACTO_RECOMPOSICAO], bridge: TRAJECTORY_BRIDGE }),
  '5.b': goalSupport({ programs: [PACTO_RECOMPOSICAO], bridge: TRAJECTORY_BRIDGE }),
  '5.d': goalSupport({ programs: [PACTO_RECOMPOSICAO], bridge: TRAJECTORY_BRIDGE }),
  '6.a': goalSupport({ programs: [ESCOLA_TEMPO_INTEGRAL] }),
  '8.b': goalSupport({ programs: [], bridge: INFRASTRUCTURE_BRIDGE }),
  '11.a': goalSupport({ programs: [PACTO_EJA], bridge: MODALITIES_BRIDGE }),
  '11.b': goalSupport({ programs: [PACTO_EJA, DIRETRIZES_EJA], bridge: MODALITIES_BRIDGE }),
  '11.c': goalSupport({ programs: [PACTO_EJA], bridge: MODALITIES_BRIDGE }),
  '11.d': goalSupport({ programs: [PACTO_EJA], bridge: MODALITIES_BRIDGE }),
  '12.c': goalSupport({ programs: [PACTO_EJA, PRONATEC], bridge: MODALITIES_BRIDGE }),
  '14.d': goalSupport({ programs: [UAB] }),
  '17.a': goalSupport({ programs: [], bridge: PROFESSIONALS_BRIDGE }),
  '19.c': goalSupport({ programs: [PAR], bridge: INFRASTRUCTURE_BRIDGE }),
})

/** Chave estável de uma frente, sem uso como identidade municipal. */
export function matrizFrenteKey(goalId: string, frenteId: string): string {
  return `${goalId}|${frenteId}`
}

export function resolveMatrizFrentes(goalId: string): readonly MatrizFrente[] {
  return MATRIZ_FRENTES[goalId] ?? []
}

export function resolveMatrizGoalSupport(goalId: string): MatrizGoalSupport | null {
  return MATRIZ_GOAL_SUPPORT[goalId] ?? null
}
