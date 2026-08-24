/**
 * Leitura editorial por meta para apoiar decisão.
 *
 * A estrutura adapta a escada de evidência do Vocações: fatos publicados
 * contextualizam mecanismos plausíveis, e cada mecanismo termina em uma
 * verificação local concreta. Nenhum texto afirma razão local comprovada.
 */

import type { MatrizEducationContextReference } from './matrizEducationContext.js'

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

/** Leituras por meta prioritária do piloto (chave = goalId do artefato). */
export const MATRIZ_GOAL_INSIGHTS: Readonly<Record<string, MatrizGoalInsight>> = Object.freeze({
  '1.a': insight({
    focus: 'Para decidir onde agir, é preciso separar procura ainda não registrada, falta de vagas e barreiras territoriais.',
    mechanisms: [
      {
        id: 'procura-maior-que-oferta',
        title: 'Procura por vaga maior que a oferta disponível',
        explanation: 'O déficit de atendimento pode reunir famílias já cadastradas e famílias que ainda nem aparecem na fila municipal.',
        verification: 'Reconciliar cadastro de procura, vagas ocupadas e capacidade disponível por território.',
      },
      {
        id: 'distribuicao-territorial-das-vagas',
        title: 'Vagas e deslocamento não chegam igualmente aos territórios',
        explanation: 'Uma vaga distante da residência ou da rota diária da família pode não se converter em atendimento efetivo.',
        verification: 'Mapear endereço da procura, unidades, tempo de deslocamento e recusas de vaga por território.',
      },
    ],
  }),
  '5.a': insight({
    focus: 'A resposta precisa conectar alfabetização e apoio pedagógico, em vez de tratar apenas o resultado final da avaliação.',
    mechanisms: [
      {
        id: 'lacunas-anteriores-de-aprendizagem',
        title: 'Lacunas formadas antes dos anos avaliados',
        explanation: 'Dificuldades não resolvidas na alfabetização podem limitar a aprendizagem nos anos seguintes.',
        verification: 'Comparar resultados por escola e turma e identificar quais habilidades ainda não foram consolidadas.',
        relatedGoal: {
          goalId: '3.a',
          use: 'Mostra se a recomposição precisa começar pelas habilidades básicas, antes dos conteúdos avaliados nos anos iniciais.',
        },
      },
      {
        id: 'apoio-pedagogico-descontinuo',
        title: 'Apoio pedagógico que não alcança todos os estudantes',
        explanation: 'Diagnóstico, recomposição e acompanhamento precisam funcionar como uma rotina contínua para produzir avanço.',
        verification: 'Cruzar estudantes com defasagem, apoio recebido, frequência às atividades e evolução por ciclo de acompanhamento.',
      },
    ],
  }),
  '11.c': insight({
    focus: 'A decisão depende de compatibilizar a EJA com a vida de quem trabalha e aproximá-la da formação profissional.',
    mechanisms: [
      {
        id: 'oferta-eja-pouco-compativel',
        title: 'Oferta de EJA pouco compatível com a rotina adulta',
        explanation: 'Horário, local, duração e deslocamento podem limitar o retorno de quem concilia estudo, trabalho e cuidado familiar.',
        verification: 'Comparar procura, matrícula e abandono por turno, território e motivo declarado pelos estudantes.',
        measure: {
          measureId: 'inep.censo_escolar.sinopse.mat_eja_medio',
          use: 'Dimensiona a oferta atual, mas não mede a procura reprimida nem se horários e locais atendem quem precisa voltar.',
          peerUse: 'A posição diante da mediana ajuda a distinguir uma oferta municipal atípica de um padrão comum ao grupo e orienta a checagem de procura, horários e locais.',
        },
      },
      {
        id: 'eja-sem-formacao-profissional',
        title: 'EJA sem conexão suficiente com formação profissional',
        explanation: 'A conclusão escolar pode ser mais atrativa quando se conecta a uma qualificação com utilidade percebida no território.',
        verification: 'Mapear cursos, vagas, horários e instituições que podem compor uma oferta integrada na região.',
        relatedGoal: {
          goalId: '12.c',
          use: 'O resultado mostra se a integração já aparece nas matrículas; não define qual curso oferecer nem comprova demanda profissional.',
        },
      },
    ],
  }),
  '17.a': insight({
    focus: 'O diagnóstico precisa distinguir formação fora da área, disciplinas com escassez e dificuldades de provimento ou permanência.',
    mechanisms: [
      {
        id: 'docencias-fora-da-area',
        title: 'Docências ocupadas por profissionais formados em outra área',
        explanation: 'A necessidade de formação não é uniforme e precisa ser localizada por disciplina e etapa de ensino.',
        verification: 'Cruzar componente curricular, formação inicial e vínculo de cada docente para dimensionar as turmas necessárias.',
        measure: {
          measureId: 'inep.afd.grupo3.fun_af',
          use: 'Dá a ordem de grandeza nos anos finais; o detalhamento por disciplina define quem precisa de formação complementar.',
          peerUse: 'A posição diante da mediana indica se a formação fora da área merece investigação mais concentrada e orienta o recorte por disciplina e etapa.',
        },
      },
      {
        id: 'provimento-e-permanencia-docente',
        title: 'Dificuldade de atrair e manter profissionais habilitados',
        explanation: 'Escassez em áreas específicas pode persistir quando provimento, jornada e carreira não sustentam vínculos estáveis.',
        verification: 'Analisar vagas recorrentes, contratos temporários, rotatividade e tempo para provimento por disciplina.',
      },
    ],
  }),
  '4.a': insight({
    focus: 'Busca ativa e continuidade da rede em emergências formam duas frentes complementares para recuperar o acesso.',
    mechanisms: [
      {
        id: 'saida-sem-resposta-rapida',
        title: 'Saída da escola sem resposta rápida da rede',
        explanation: 'Quanto maior o intervalo entre perda de vínculo, localização e rematrícula, mais difícil tende a ser o retorno.',
        verification: 'Cruzar matrícula, frequência e cadastros sociais para medir tempo de resposta e retorno sustentado.',
      },
      {
        id: 'interrupcoes-em-eventos-climaticos',
        title: 'Interrupções associadas a eventos climáticos',
        explanation: 'Danos, deslocamentos e rotas interrompidas podem romper a frequência mesmo quando a matrícula permanece ativa.',
        verification: 'Registrar por escola dias sem aula, estudantes deslocados, rotas afetadas, reposição e retorno após cada evento.',
        measure: {
          measureId: 'midr.atlas.public_education_loss',
          use: 'Confirma prejuízo educacional registrado em evento recente; não informa dias de aula perdidos nem efeito sobre a permanência.',
          peerUse: 'A posição diante da mediana mostra se o registro de perdas destoa do grupo e orienta a revisão de eventos, danos e interrupções por escola.',
        },
      },
    ],
  }),
  '4.b': insight({
    focus: 'Atraso escolar e reprovação devem ser lidos juntos para impedir que a defasagem se acumule até o 5º ano.',
    mechanisms: [
      {
        id: 'atraso-acumulado',
        title: 'Atraso acumulado antes da conclusão dos anos iniciais',
        explanation: 'A distorção entre idade e etapa sinaliza trajetórias que já precisam de acompanhamento individual.',
        verification: 'Identificar por escola os estudantes em atraso, o momento da defasagem e o apoio recebido desde então.',
        measure: {
          measureId: 'inep.tdi.fun_ai',
          use: 'Dimensiona o grupo em atraso nos anos iniciais que precisa entrar primeiro no acompanhamento de trajetória.',
          peerUse: 'A posição diante da mediana indica se o atraso escolar exige atenção adicional e orienta o acompanhamento por escola, turma e trajetória.',
        },
      },
      {
        id: 'reprovacao-amplia-defasagem',
        title: 'Reprovação que amplia a defasagem',
        explanation: 'Quando a resposta à dificuldade é repetir o ano sem recomposição suficiente, o atraso pode se tornar cumulativo.',
        verification: 'Comparar reprovação, motivo, apoio pedagógico e resultado posterior por escola e turma.',
        measure: {
          measureId: 'inep.rendimento.reprovacao.fun_ai',
          use: 'Mostra a parcela recente de reprovação nos anos iniciais; não revela, sozinha, o motivo nem o apoio oferecido.',
          peerUse: 'A posição diante da mediana mostra se a reprovação destoa do grupo e orienta a checagem de apoio pedagógico e evolução posterior.',
        },
      },
    ],
  }),
  '19.c': insight({
    focus: 'A prioridade é localizar as lacunas por rede e escola e transformá-las em uma sequência de adequações com responsável, custo e fonte de recurso.',
    mechanisms: [
      {
        id: 'pendencias-sem-inventario-unico',
        title: 'Lacunas diferentes entre as redes e escolas',
        explanation: 'O percentual geral não mostra onde estão as barreiras nem separa o que cabe diretamente ao município do que exige articulação com o Estado.',
        verification: 'Vistoriar cada escola com lista padronizada de barreiras, usuários afetados, criticidade e solução necessária.',
        educationContext: {
          key: 'accessibility_by_network',
          use: 'O recorte separa ação municipal de articulação com o Estado; declarações administrativas orientam a vistoria, mas não substituem avaliação técnica.',
        },
      },
      {
        id: 'adequacoes-sem-programacao-financeira',
        title: 'Adequações sem programação financeira contínua',
        explanation: 'Obras pequenas e grandes competem por recursos e podem permanecer pendentes sem priorização e fonte definida.',
        verification: 'Vincular cada adequação a custo estimado, fonte de recurso, etapa de contratação e rotina de manutenção.',
      },
    ],
  }),
})

export function resolveMatrizGoalInsight(goalId: string): MatrizGoalInsight | null {
  return MATRIZ_GOAL_INSIGHTS[goalId] ?? null
}
