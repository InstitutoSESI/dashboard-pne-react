/**
 * Leitura editorial por meta para apoiar decisão.
 *
 * A estrutura adapta a escada de evidência do Vocações: fatos publicados
 * contextualizam mecanismos plausíveis, e cada mecanismo termina em uma
 * verificação local concreta. Nenhum texto afirma razão local comprovada.
 */

import type { MatrizEducationContextReference } from './matrizEducationContext.js'
import type { MatrizPriorityGoal } from './matrizTypes.js'

export interface MatrizMeasureContext {
  readonly measureId: string
  /** Consequência prática e limite desse número para a decisão. */
  readonly use: string
  /** Uso editorial da posição publicada frente à mediana dos pares. */
  readonly peerUse?: string
}

export interface MatrizRelatedGoalContext {
  readonly goalId: string
  /** Relação prática entre o resultado relacionado e o mecanismo. */
  readonly use: string
}

export interface MatrizGoalMechanism {
  readonly id: string
  readonly title: string
  readonly explanation: string
  readonly verification: string
  readonly measure?: MatrizMeasureContext
  readonly relatedGoal?: MatrizRelatedGoalContext
  readonly educationContext?: MatrizEducationContextReference
}

export interface MatrizGoalInsight {
  /** Complemento curto à leitura comparativa da meta. */
  readonly focus: string
  /** Exatamente dois mecanismos para manter a página enxuta. */
  readonly mechanisms: readonly MatrizGoalMechanism[]
}

function insight(entry: MatrizGoalInsight): MatrizGoalInsight {
  return Object.freeze({
    ...entry,
    mechanisms: Object.freeze(entry.mechanisms.map((mechanism) => Object.freeze({
      ...mechanism,
      measure: mechanism.measure ? Object.freeze({ ...mechanism.measure }) : undefined,
      relatedGoal: mechanism.relatedGoal ? Object.freeze({ ...mechanism.relatedGoal }) : undefined,
      educationContext: mechanism.educationContext
        ? Object.freeze({ ...mechanism.educationContext })
        : undefined,
    }))),
  })
}

/** Leituras para todas as metas prioritárias publicadas no RS (chave = goalId). */
export const MATRIZ_GOAL_INSIGHTS: Readonly<Record<string, MatrizGoalInsight>> = Object.freeze({
  '1.a': insight({
    focus: 'Para decidir onde agir, é preciso separar procura ainda não registrada, falta de vagas e barreiras territoriais.',
    mechanisms: [
      {
        id: 'procura-maior-que-oferta',
        title: 'Procura por vaga maior que a oferta disponível',
        explanation: 'O déficit de atendimento pode reunir famílias já cadastradas e famílias que ainda nem aparecem na fila municipal.',
        verification: 'Qual território reúne fila envelhecida, demanda não registrada e vagas ociosas; essa combinação define a primeira busca.',
      },
      {
        id: 'distribuicao-territorial-das-vagas',
        title: 'Vagas e deslocamento não chegam igualmente aos territórios',
        explanation: 'Uma vaga distante da residência ou da rota diária da família pode não se converter em atendimento efetivo.',
        verification: 'Qual vazio territorial não pode ser resolvido com remanejamento ou transporte; somente esse déficit justifica expansão física.',
      },
    ],
  }),
  '5.a': insight({
    focus: 'A resposta deve partir do componente medido, localizar habilidades pendentes e sustentar um ciclo de intervenção e reavaliação.',
    mechanisms: [
      {
        id: 'lacunas-anteriores-de-aprendizagem',
        title: 'Habilidades estruturantes ainda não consolidadas',
        explanation: 'Lacunas anteriores podem limitar o desempenho no componente avaliado e precisam ser localizadas antes de definir a resposta.',
        verification: 'Qual habilidade do componente avaliado concentra estudantes abaixo do esperado e em quais turmas ela deve ser retomada primeiro.',
        relatedGoal: {
          goalId: '3.a',
          use: 'Mostra se a recomposição também precisa retomar habilidades básicas, sem transformar alfabetização e aprendizagem dos anos iniciais na mesma frente.',
        },
      },
      {
        id: 'apoio-pedagogico-descontinuo',
        title: 'Apoio pedagógico que não alcança todos os estudantes',
        explanation: 'Diagnóstico, recomposição e acompanhamento precisam funcionar como uma rotina contínua para produzir avanço.',
        verification: 'Quais escolas ainda não mantêm diagnóstico, intervenção e reavaliação como um ciclo regular para todos os estudantes priorizados.',
      },
    ],
  }),
  '11.c': insight({
    focus: 'A conclusão do ensino médio na vida adulta exige oferta compatível, articulação entre redes e rotas claras de certificação e continuidade.',
    mechanisms: [
      {
        id: 'oferta-eja-pouco-compativel',
        title: 'Oferta de EJA pouco compatível com a rotina adulta',
        explanation: 'Horário, local, duração e deslocamento podem limitar o retorno de quem concilia estudo, trabalho e cuidado familiar.',
        verification: 'Qual combinação de turno, local e duração explica as perdas entre interesse, matrícula e conclusão; ela define o ajuste da oferta.',
        measure: {
          measureId: 'inep.censo_escolar.sinopse.mat_eja_medio',
          use: 'Dimensiona a oferta atual, mas não mede a procura reprimida nem se horários e locais atendem quem precisa voltar.',
          peerUse: 'A posição diante da mediana ajuda a distinguir uma oferta municipal atípica de um padrão comum ao grupo e orienta a checagem de procura, horários e locais.',
        },
      },
      {
        id: 'conclusao-sem-certificacao-articulada',
        title: 'Conclusão sem rota de certificação articulada',
        explanation: 'Adultos com trajetórias interrompidas podem precisar combinar retomada da EJA, aproveitamento de proficiências e certificação pelos órgãos competentes.',
        verification: 'Quantos adultos já reúnem saberes ou proficiências passíveis de reconhecimento e qual órgão certificador pode atender cada caso.',
      },
    ],
  }),
  '17.a': insight({
    focus: 'O diagnóstico deve usar a etapa indicada na meta e distinguir falta de habilitação, necessidade formativa e lotação fora da área.',
    mechanisms: [
      {
        id: 'docencias-fora-da-area',
        title: 'Docências ocupadas por profissionais formados em outra área',
        explanation: 'A necessidade de formação não é uniforme e precisa ser localizada por disciplina e etapa de ensino.',
        verification: 'Em qual etapa e componente se concentra a formação inadequada; esse recorte define quem precisa de complementação primeiro.',
      },
      {
        id: 'lotacao-fora-da-area',
        title: 'Lotação que não aproveita a formação disponível',
        explanation: 'A rede pode manter docências fora da área quando atribuição de turmas, carga horária e planejamento de pessoal não usam as habilitações existentes.',
        verification: 'Quantas turmas estão atribuídas fora da habilitação apesar de haver profissional adequado na rede e quais regras de lotação produzem isso.',
      },
    ],
  }),
  '4.a': insight({
    focus: 'A busca ativa localiza quem saiu; a segunda frente remove a barreira comprovada ao retorno, inclusive a climática quando houver evidência local.',
    mechanisms: [
      {
        id: 'saida-sem-resposta-rapida',
        title: 'Saída da escola sem resposta rápida da rede',
        explanation: 'Quanto maior o intervalo entre perda de vínculo, localização e rematrícula, mais difícil tende a ser o retorno.',
        verification: 'Quais estudantes estão fora ou com frequência rompida, há quantos dias e sem qual encaminhamento concluído.',
      },
      {
        id: 'barreira-documentada-ao-retorno',
        title: 'Barreira ao retorno ainda sem resposta adequada',
        explanation: 'Transporte, documentação, cuidado, mudança de território ou interrupção climática exigem respostas diferentes depois que o estudante é localizado.',
        verification: 'Qual barreira comprovada concentra casos não resolvidos; perdas climáticas entram nessa decisão somente onde houver ocorrência ou risco local.',
        measure: {
          measureId: 'midr.atlas.public_education_loss',
          use: 'Confirma prejuízo educacional registrado em evento recente; não informa dias de aula perdidos nem efeito sobre a permanência.',
          peerUse: 'A posição diante da mediana mostra se o registro de perdas destoa do grupo e orienta a revisão de eventos, danos e interrupções por escola.',
        },
      },
    ],
  }),
  '4.b': insight({
    focus: 'A decisão precisa separar quem já acumulou atraso de quem ainda pode evitar uma nova reprovação com apoio pedagógico oportuno.',
    mechanisms: [
      {
        id: 'atraso-acumulado',
        title: 'Atraso acumulado antes da conclusão dos anos iniciais',
        explanation: 'A distorção entre idade e etapa sinaliza trajetórias que já precisam de acompanhamento individual.',
        verification: 'Em qual ano ou transição surge o atraso e quais estudantes ainda podem regularizar a trajetória com apoio imediato.',
        measure: {
          measureId: 'inep.tdi.fun_ai',
          use: 'Dimensiona o grupo em atraso nos anos iniciais que precisa entrar primeiro no acompanhamento de trajetória.',
          peerUse: 'A posição diante da mediana indica se o atraso escolar exige atenção adicional e orienta o acompanhamento por escola, turma e trajetória.',
        },
      },
      {
        id: 'reprovacao-amplia-defasagem',
        title: 'Reprovação sem apoio oportuno',
        explanation: 'Quando a resposta à dificuldade é repetir o ano sem recomposição suficiente, o atraso pode se tornar cumulativo.',
        verification: 'Em quais escolas a reprovação ocorre sem intervenção documentada e como esses estudantes evoluem no período seguinte.',
        measure: {
          measureId: 'inep.rendimento.reprovacao.fun_ai',
          use: 'Mostra a parcela recente de reprovação nos anos iniciais; não revela, sozinha, o motivo nem o apoio oferecido.',
          peerUse: 'A posição diante da mediana mostra se a reprovação destoa do grupo e orienta a checagem de apoio pedagógico e evolução posterior.',
        },
      },
    ],
  }),
  '19.c': insight({
    focus: 'O indicador de salas acessíveis é um sinal parcial; a decisão requer vistoria mais ampla e uma sequência de adequações por rede e escola.',
    mechanisms: [
      {
        id: 'pendencias-sem-inventario-unico',
        title: 'Lacunas diferentes entre as redes e escolas',
        explanation: 'O percentual geral não mostra onde estão as barreiras nem separa o que cabe diretamente ao município do que exige articulação com o Estado.',
        verification: 'Quais unidades têm barreira crítica, quem é afetado e qual condição impede circulação, comunicação ou uso autônomo.',
        educationContext: {
          key: 'accessibility_by_network',
          use: 'O recorte separa ação municipal de articulação com o Estado; declarações administrativas orientam a vistoria, mas não substituem avaliação técnica.',
        },
      },
      {
        id: 'adequacoes-sem-programacao-financeira',
        title: 'Adequações sem programação financeira contínua',
        explanation: 'Obras pequenas e grandes competem por recursos e podem permanecer pendentes sem priorização e fonte definida.',
        verification: 'Quais adequações cabem em manutenção, repasse direto ou obra e quais ainda não possuem orçamento ou fonte compatível.',
      },
    ],
  }),
  '1.c': insight({
    focus: 'A universalização da pré-escola exige localizar toda criança de 4 e 5 anos e garantir uma vaga que possa ser frequentada de fato.',
    mechanisms: [
      {
        id: 'criancas-fora-do-cadastro',
        title: 'Crianças em idade obrigatória ainda não localizadas',
        explanation: 'Matrícula e lista de espera não mostram as crianças que nunca chegaram aos canais da educação.',
        verification: 'Quais crianças de 4 e 5 anos seguem sem registro escolar após reconciliar educação, saúde, assistência e contato familiar.',
      },
      {
        id: 'vaga-distante-ou-transicao-fragil',
        title: 'Vaga distante ou passagem frágil para a pré-escola',
        explanation: 'Distância, turno e falhas na passagem da creche para a pré-escola podem impedir a frequência mesmo quando há capacidade na rede.',
        verification: 'Qual território concentra recusas por distância ou turno e crianças sem transição confirmada da creche para a pré-escola.',
      },
    ],
  }),
  '3.a': insight({
    focus: 'Avaliar cedo só produz avanço quando a rede transforma habilidades não consolidadas em resposta pedagógica rápida e acompanhada.',
    mechanisms: [
      {
        id: 'avaliacao-sem-resposta-comum',
        title: 'Avaliação sem resposta comum da rede',
        explanation: 'Resultados podem ficar apenas no registro quando não definem qual habilidade ensinar novamente, para quem e em que prazo.',
        verification: 'Quais habilidades de leitura, escrita ou matemática ainda não se consolidaram até o 2º ano e em quais grupos elas se concentram.',
      },
      {
        id: 'formacao-sem-acompanhamento-pratico',
        title: 'Formação sem acompanhamento da prática',
        explanation: 'Encontros isolados têm pouco alcance quando o professor não recebe devolutiva sobre planejamento, material e resposta dos estudantes.',
        verification: 'Quais práticas priorizadas na formação ainda não aparecem no planejamento ou na sala e que apoio explica essa distância.',
      },
    ],
  }),
  '4.c': insight({
    focus: 'A conclusão do 9º ano depende de agir antes que frequência irregular, reprovação e baixo domínio se convertam em atraso acumulado.',
    mechanisms: [
      {
        id: 'risco-acumulado-nos-anos-finais',
        title: 'Risco acumulado sem resposta precoce',
        explanation: 'Faltas, reprovações e habilidades pendentes podem se reforçar ao longo dos anos finais até interromper a trajetória.',
        verification: 'Quais estudantes acumulam dois ou mais alertas sem resposta concluída e em que ponto da trajetória o risco começou.',
      },
      {
        id: 'transicao-e-pertencimento-fragil',
        title: 'Transição e vínculo frágeis nos anos finais',
        explanation: 'Mudança de escola, maior número de professores e pouca participação podem reduzir o vínculo com a vida escolar.',
        verification: 'Em qual escola ou território a passagem do 5º para o 6º ano concentra perda de frequência, transferência ou baixo pertencimento.',
      },
    ],
  }),
  '4.d': insight({
    focus: 'Como o ensino médio costuma estar na rede estadual, o município agrega valor protegendo a transição e removendo barreiras de permanência.',
    mechanisms: [
      {
        id: 'transicao-para-rede-estadual-fragil',
        title: 'Passagem para o ensino médio sem confirmação',
        explanation: 'Concluir o 9º ano não garante ingresso quando inscrição, documentação ou troca de rede não são acompanhadas até a matrícula.',
        verification: 'Quais concluintes do 9º ano ainda não têm matrícula confirmada no ensino médio e qual pendência bloqueia cada ingresso.',
      },
      {
        id: 'permanencia-no-medio-interrompida',
        title: 'Barreiras de permanência no ensino médio',
        explanation: 'Frequência, deslocamento, trabalho e responsabilidades de cuidado podem interromper uma matrícula já efetivada.',
        verification: 'Qual barreira responde pelas faltas e saídas recentes e qual apoio municipal ou estadual pode removê-la no prazo necessário.',
      },
    ],
  }),
  '5.b': insight({
    focus: 'Nos anos finais, a recomposição deve partir do componente medido, priorizar habilidades estruturantes e considerar a adolescência.',
    mechanisms: [
      {
        id: 'lacunas-prioritarias-nos-anos-finais',
        title: 'Lacunas essenciais diluídas no currículo',
        explanation: 'Tentar recuperar todo o conteúdo ao mesmo tempo pode impedir foco nas habilidades que sustentam as aprendizagens seguintes.',
        verification: 'Quais habilidades do componente avaliado bloqueiam aprendizagens seguintes e em quais turmas sua concentração é maior.',
      },
      {
        id: 'apoio-pedagogico-aos-adolescentes',
        title: 'Apoio pouco ajustado aos adolescentes',
        explanation: 'Reforço desconectado de interesse, participação e rotina escolar pode ter baixa adesão mesmo quando a necessidade está bem medida.',
        verification: 'Qual formato de apoio combina melhor adesão e progresso entre os grupos priorizados, segundo frequência e reavaliação.',
      },
    ],
  }),
  '5.d': insight({
    focus: 'A aprendizagem no ensino médio requer uma agenda com a rede estadual para dar continuidade às habilidades do componente medido.',
    mechanisms: [
      {
        id: 'recomposicao-desarticulada-entre-redes',
        title: 'Recomposição sem agenda entre as redes',
        explanation: 'Lacunas vindas do fundamental podem chegar ao ensino médio sem continuidade quando município e Estado trabalham com diagnósticos separados.',
        verification: 'Quais lacunas do componente avaliado persistem entre a saída do 9º ano e a entrada no médio e ainda não têm resposta pactuada.',
      },
      {
        id: 'apoio-sem-intensidade-ajustada',
        title: 'Apoio pedagógico sem intensidade ajustada',
        explanation: 'Uma intervenção uniforme pode não responder a lacunas diferentes e prolongar dificuldades mesmo quando o estudante permanece frequentando.',
        verification: 'Qual grupo não progride após o apoio regular e quais ajustes de tempo, agrupamento ou estratégia precisam ser testados.',
      },
    ],
  }),
  '6.a': insight({
    focus: 'A expansão do tempo integral precisa começar por quem mais se beneficia e combinar jornada ampliada com um projeto pedagógico coerente.',
    mechanisms: [
      {
        id: 'expansao-sem-prioridade-equitativa',
        title: 'Expansão sem prioridade territorial e social',
        explanation: 'Novas matrículas podem ampliar desigualdades quando capacidade física, procura e vulnerabilidade não orientam a sequência de implantação.',
        verification: 'Quais territórios combinam demanda, vulnerabilidade e capacidade de implantação sem reduzir o acesso em outras etapas.',
      },
      {
        id: 'jornada-ampliada-sem-projeto-integrado',
        title: 'Mais horas sem integração pedagógica',
        explanation: 'Alongar o turno não garante desenvolvimento quando currículo, equipe, alimentação, espaços e acompanhamento funcionam separadamente.',
        verification: 'Quais escolas já reúnem currículo integrado, equipe, alimentação e espaços para sustentar a jornada completa com frequência.',
      },
    ],
  }),
  '8.b': insight({
    focus: 'Conforto térmico exige diagnóstico técnico da escola e uma solução completa, não apenas a compra isolada de equipamentos.',
    mechanisms: [
      {
        id: 'diagnostico-termico-incompleto',
        title: 'Calor e ventilação sem diagnóstico por ambiente',
        explanation: 'Orientação solar, cobertura, sombreamento, ventilação e ocupação fazem salas da mesma escola exigir respostas diferentes.',
        verification: 'Quais ambientes apresentam condição crítica nos horários de maior uso e quais fatores físicos explicam a prioridade.',
      },
      {
        id: 'equipamentos-sem-infraestrutura-e-manutencao',
        title: 'Equipamentos sem rede elétrica e manutenção adequadas',
        explanation: 'Climatização pode falhar ou elevar risco e custo quando potência, instalação, operação e limpeza não entram no mesmo plano.',
        verification: 'Quais ambientes priorizados possuem capacidade elétrica e manutenção compatíveis com a solução antes de qualquer compra.',
      },
    ],
  }),
  '11.a': insight({
    focus: 'A alfabetização de jovens e adultos começa pela identificação territorial do público e precisa levar a uma trajetória educacional contínua.',
    mechanisms: [
      {
        id: 'publico-nao-identificado-alfabetizacao',
        title: 'Público potencial ainda não identificado',
        explanation: 'Estimativas populacionais não informam quem deseja estudar, onde vive nem qual formato permite sua participação.',
        verification: 'Quais territórios concentram pessoas localizadas ainda sem encaminhamento e qual barreira impede a matrícula em alfabetização.',
      },
      {
        id: 'alfabetizacao-sem-continuidade-eja',
        title: 'Alfabetização sem continuidade na EJA',
        explanation: 'Uma ação inicial pode perder efeito quando não há passagem organizada para a escolarização básica e acompanhamento da permanência.',
        verification: 'Qual parcela conclui a alfabetização sem ingresso confirmado na EJA e em quais territórios falta uma oferta de continuidade.',
      },
    ],
  }),
  '11.b': insight({
    focus: 'Concluir o ensino fundamental na vida adulta requer oferta compatível e um percurso que reconheça saberes sem abrir mão das aprendizagens essenciais.',
    mechanisms: [
      {
        id: 'oferta-fundamental-incompativel-adultos',
        title: 'Oferta pouco compatível com a vida adulta',
        explanation: 'Turno, duração, deslocamento e organização curricular podem afastar quem trabalha ou cuida de outras pessoas.',
        verification: 'Qual combinação de turno, local e duração retém mais interessados sem comprometer as aprendizagens e a certificação.',
      },
      {
        id: 'saberes-sem-reconhecimento-certificacao',
        title: 'Saberes prévios fora do percurso escolar',
        explanation: 'Sem diagnóstico e aproveitamento regulamentado, o estudante pode repetir o que já sabe ou abandonar antes de concluir o fundamental.',
        verification: 'Quais saberes podem ser reconhecidos e quais aprendizagens ainda precisam compor o percurso individual até a conclusão.',
      },
    ],
  }),
  '11.d': insight({
    focus: 'Elevar matrículas na EJA depende de converter procura em ingresso e sustentar turmas acessíveis ao longo do território e do calendário.',
    mechanisms: [
      {
        id: 'chamada-publica-nao-converte-matricula',
        title: 'Chamada pública com baixa conversão em matrícula',
        explanation: 'Divulgação ampla não basta quando o município não acompanha cada manifestação de interesse até a turma adequada.',
        verification: 'Em qual etapa entre localização, interesse, encaminhamento, matrícula e frequência ocorre a maior perda e por qual motivo.',
      },
      {
        id: 'turmas-instaveis-e-barreiras-permanencia',
        title: 'Turmas instáveis e barreiras de permanência',
        explanation: 'Mudança de local, fechamento recorrente e falta de apoio ao deslocamento reduzem confiança e continuidade da oferta.',
        verification: 'Quais turmas acumulam mudança, fechamento ou baixa ocupação e qual ajuste preserva acesso e continuidade no território.',
      },
    ],
  }),
  '12.a': insight({
    focus: 'A oferta técnica precisa combinar interesse dos estudantes, capacidade das instituições e oportunidades territoriais sem presumir demanda.',
    mechanisms: [
      {
        id: 'oferta-tecnica-sem-leitura-territorial',
        title: 'Oferta técnica sem leitura conjunta do território',
        explanation: 'Catálogo de cursos e perfil econômico orientam opções, mas não substituem a escuta dos estudantes nem a capacidade real de oferta.',
        verification: 'Quais cursos combinam interesse validado, requisitos alcançáveis, deslocamento possível e capacidade real da instituição ofertante.',
      },
      {
        id: 'articulacao-regional-insuficiente',
        title: 'Capacidade regional ainda não articulada',
        explanation: 'Municípios pequenos podem depender de rede estadual, institutos federais e outras instituições para viabilizar turma e certificação.',
        verification: 'Qual instituição pode assumir oferta e certificação e quais responsabilidades ainda impedem formalizar e abrir a turma.',
      },
    ],
  }),
  '12.c': insight({
    focus: 'A EJA articulada à formação profissional precisa funcionar como um percurso único, com currículo, matrícula, acesso e certificação coerentes.',
    mechanisms: [
      {
        id: 'curriculo-e-certificacao-desconectados',
        title: 'Currículo e certificação ainda desconectados',
        explanation: 'Apenas oferecer dois cursos no mesmo local não cria integração quando calendários, aprendizagens e responsabilidades não convergem.',
        verification: 'Qual arranjo garante currículo, matrícula, avaliação e certificação em um único percurso, com atribuição clara entre instituições.',
      },
      {
        id: 'curso-sem-acesso-ou-utilidade-validada',
        title: 'Curso sem acesso ou utilidade validados',
        explanation: 'Uma opção tecnicamente disponível pode não atrair o público se horário, deslocamento, requisitos ou aplicação percebida forem inadequados.',
        verification: 'Quais barreiras de horário, deslocamento, requisito ou utilidade percebida impediriam o público validado de concluir o percurso.',
      },
    ],
  }),
  '14.d': insight({
    focus: 'A prefeitura não controla as vagas superiores, mas pode ampliar acesso ao aproximar oferta pública e apoiar a transição dos estudantes.',
    mechanisms: [
      {
        id: 'acesso-superior-distante-ou-restrito',
        title: 'Oferta superior distante ou pouco acessível',
        explanation: 'Distância de campus, conectividade e ausência de polo presencial podem limitar o ingresso mesmo quando existem cursos regionais ou a distância.',
        verification: 'Qual combinação de curso, polo, conectividade e deslocamento atende procura validada e cabe em chamada ou parceria vigente.',
      },
      {
        id: 'transicao-ensino-medio-superior-fragil',
        title: 'Transição para o ensino superior pouco apoiada',
        explanation: 'Informação tardia, inscrição incompleta e falta de acesso digital podem interromper o caminho entre conclusão do médio e candidatura.',
        verification: 'Em qual etapa entre orientação, inscrição, seleção e matrícula os concluintes deixam o percurso e qual apoio é cabível.',
      },
    ],
  }),
})

export function resolveMatrizGoalInsight(goalId: string): MatrizGoalInsight | null {
  return MATRIZ_GOAL_INSIGHTS[goalId] ?? null
}

/** Explicita o recorte do indicador quando a mesma meta usa medidas municipais diferentes. */
export function resolveMatrizIndicatorScope(
  goal: Pick<MatrizPriorityGoal, 'goalId' | 'indicatorId'>,
): string | null {
  if (goal.goalId === '5.a' || goal.goalId === '5.b' || goal.goalId === '5.d') {
    if (goal.indicatorId.includes('matematica')) {
      return 'O indicador desta leitura mede Matemática; priorize as habilidades matemáticas pendentes sem reduzir o currículo ao teste.'
    }
    if (goal.indicatorId.includes('portugues')) {
      return 'O indicador desta leitura mede Língua Portuguesa; priorize leitura, escrita e análise linguística sem reduzir o currículo ao teste.'
    }
    return 'O indicador desta leitura cobre um componente específico; use esse recorte para orientar o diagnóstico sem reduzir o currículo ao teste.'
  }

  if (goal.goalId === '17.a') {
    const stage = goal.indicatorId === 'adequacao_ai'
      ? 'os anos iniciais do ensino fundamental'
      : goal.indicatorId === 'adequacao_af'
        ? 'os anos finais do ensino fundamental'
        : goal.indicatorId === 'adequacao_em'
          ? 'o ensino médio'
          : 'a etapa indicada na meta'
    return `Nesta leitura, a adequação da formação se refere a ${stage}; formação e lotação devem ser verificadas nesse mesmo recorte.`
  }

  if (goal.goalId === '19.c' && goal.indicatorId === 'salas_acessiveis') {
    return 'Salas acessíveis são um sinal parcial: o diagnóstico municipal também deve verificar circulação, comunicação, sanitários e uso autônomo dos ambientes.'
  }

  if (goal.goalId === '6.a') {
    return goal.indicatorId === 'escolas_integral'
      ? 'O indicador conta escolas com oferta; acompanhe também estudantes atendidos, ocupação das vagas e equidade territorial.'
      : 'O indicador conta estudantes atendidos; acompanhe também escolas com oferta, ocupação das vagas e equidade territorial.'
  }

  return null
}
