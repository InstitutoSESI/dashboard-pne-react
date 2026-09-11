import financingPrograms from '../../data/diagnostic/financingPrograms.json'
import { resolveMatrizFrentes, resolveMatrizGoalSupport } from '../../features/matriz/matrizFrentes'
import type { PmeEditorialPath, PmeMatrizObjectiveContext } from './pmeTypes'

export interface PmeObjectiveEditorial {
  objectiveId: string
  title: string
  themeId: string
  themeLabel: string
  guidingQuestion: string
}

const editorials: PmeObjectiveEditorial[] = [
  ['1', 'Educação infantil', 'educacao_infantil_acesso', 'Acesso e desigualdade na educação infantil', 'O que as evidências disponíveis mostram sobre o acesso à creche e à pré-escola?'],
  ['2', 'Qualidade da educação infantil', 'educacao_infantil_qualidade', 'Condições de oferta na educação infantil', 'Quais aspectos da oferta de creche e pré-escola podem ser examinados com as evidências publicadas?'],
  ['3', 'Alfabetização', 'alfabetizacao', 'Alfabetização e desigualdades de aprendizagem', 'Que leitura as evidências permitem fazer sobre alfabetização e suas desigualdades?'],
  ['4', 'Trajetórias escolares', 'trajetorias_escolares', 'Acesso, permanência e conclusão', 'O que está publicado sobre acesso à escola e conclusão nas idades de referência?'],
  ['5', 'Aprendizagem', 'aprendizagem_equidade', 'Aprendizagem e equidade', 'Quais resultados de aprendizagem e desigualdades estão disponíveis para discussão?'],
  ['6', 'Educação integral', 'educacao_integral', 'Tempo integral e jornada escolar', 'O que as evidências publicadas permitem examinar sobre matrículas e escolas de tempo integral?'],
  ['7', 'Educação digital', 'educacao_digital', 'Conectividade e educação digital', 'Que informações públicas ajudam a situar conectividade e educação digital?'],
  ['8', 'Clima e educação ambiental', 'clima_educacao_ambiental', 'Resiliência climática e educação ambiental', 'Quais evidências permitem iniciar a conversa sobre clima, infraestrutura e educação ambiental?'],
  ['9', 'Modalidades e territórios', 'modalidades_territorios', 'Educação indígena, do campo e quilombola', 'Que recortes publicados ajudam a discutir o atendimento nas modalidades e territórios previstos?'],
  ['10', 'Educação especial', 'educacao_especial', 'Acesso, permanência e atendimento especializado', 'O que as evidências públicas permitem observar sobre inclusão e atendimento educacional especializado?'],
  ['11', 'Educação de jovens e adultos', 'educacao_jovens_adultos', 'Escolarização e alfabetização de jovens e adultos', 'Quais evidências ajudam a situar a alfabetização e a escolarização da população jovem e adulta?'],
  ['12', 'Educação profissional', 'educacao_profissional', 'Formação técnica e educação profissional', 'O que está disponível para discutir educação profissional e sua articulação com a educação básica?'],
  ['13', 'Qualidade da educação profissional e tecnológica', 'qualidade_ept', 'Qualidade, aprendizagem e inserção na EPT', 'Quais evidências públicas ajudam a discutir referenciais de qualidade, aprendizagem e inserção de egressos da educação profissional e tecnológica?'],
  ['14', 'Graduação', 'graduacao', 'Frequência, conclusão e expansão da graduação', 'O que as evidências disponíveis mostram sobre a graduação no recorte municipal?'],
  ['15', 'Qualidade da educação superior', 'qualidade_educacao_superior', 'Oferta e qualidade da educação superior', 'Que dados publicados ajudam a contextualizar a qualidade e a oferta da educação superior?'],
  ['16', 'Pós-graduação', 'pos_graduacao', 'Formação em pós-graduação', 'Quais evidências públicas estão disponíveis sobre a pós-graduação no município?'],
  ['17', 'Profissionais da educação', 'profissionais_educacao', 'Formação, carreira e vínculos docentes', 'O que pode ser observado publicamente sobre profissionais da educação, sem inferir condições individuais?'],
  ['18', 'Gestão democrática', 'gestao_democratica', 'Participação e governança educacional', 'Que informações públicas ajudam a discutir mecanismos de gestão democrática?'],
  ['19', 'Financiamento e infraestrutura educacional', 'financiamento_infraestrutura', 'Investimento, infraestrutura e recursos públicos', 'Quais evidências permitem examinar investimento, custo por aluno, infraestrutura e recursos públicos para a educação básica, superior e profissional?'],
].map(([objectiveId, title, themeId, themeLabel, guidingQuestion]) => ({ objectiveId, title, themeId, themeLabel, guidingQuestion }))

export const PME_OBJECTIVE_CATALOG = Object.freeze(
  Object.fromEntries(editorials.map((entry) => [entry.objectiveId, Object.freeze(entry)])),
)

function normalize(value: string): string {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
}

function matchFinancingProgram(name: string, officialUrl: string) {
  const normalizedName = normalize(name)
  return financingPrograms.programs.find((program) => (
    program.sourceUrls.includes(officialUrl)
    || normalizedName.includes(normalize(program.title))
    || normalize(program.title).includes(normalizedName)
  )) ?? null
}

function matrizProgramPath(
  context: PmeMatrizObjectiveContext,
  program: { name: string; description: string; url: string },
): PmeEditorialPath {
  const catalog = matchFinancingProgram(program.name, program.url)
  return {
    id: `pme.matriz.${context.goalId}.${normalize(program.name).replace(/[^a-z0-9]+/g, '_')}`,
    goalId: context.goalId,
    title: program.name,
    kind: catalog?.accessMode === 'automatic_transfer' ? 'transfer' : catalog ? 'program' : 'orientation',
    origin: 'matriz_editorial',
    programId: catalog?.programId ?? null,
    sourceId: catalog?.programId ?? 'matriz_frentes',
    officialUrl: catalog?.sourceUrls[0] ?? program.url,
    competence: 'As atribuições de cada ente e as condições de acesso devem ser confirmadas nas regras atuais do instrumento.',
    relationReason: `Apoio à discussão da meta ${context.goalId}. ${program.description}`,
    verificationStatus: 'not_verified',
    validity: null,
    knownConditions: catalog?.restrictions ?? null,
    evidenceRequired: catalog?.evidenceRequired ?? null,
    verifiedAt: null,
    sourceDocument: catalog ? 'src/features/matriz/matrizFrentes.ts; src/data/diagnostic/financingPrograms.json' : 'src/features/matriz/matrizFrentes.ts',
    sourceVersion: catalog ? `${context.sourceVersion}; catálogo ${financingPrograms.catalogVersion}; verificação registrada no catálogo em ${financingPrograms.lastVerifiedAt}` : context.sourceVersion,
    limitations: 'O caminho não confirma vigência atual, adesão, elegibilidade, saldo, repasse, execução ou efeito para o município.',
  }
}

function matrizFirstStepPath(context: PmeMatrizObjectiveContext, step: { factorId: string; text: string; ref: string }): PmeEditorialPath {
  return {
    id: `pme.matriz.first-step.${context.goalId}.${step.factorId}`,
    goalId: context.goalId,
    title: step.text,
    kind: 'instrument',
    origin: 'matriz_first_step',
    programId: null,
    sourceId: 'pne2026_matriz',
    officialUrl: null,
    competence: 'Confira as atribuições e as condições do instrumento federal no canal oficial responsável.',
    relationReason: `Orientação relacionada à meta ${context.goalId}. Consulte os procedimentos e as responsabilidades no canal oficial do instrumento.`,
    verificationStatus: 'not_verified',
    validity: null,
    knownConditions: null,
    evidenceRequired: null,
    verifiedAt: null,
    sourceDocument: 'pne2026-matriz/municipios/{ibge7}.json',
    sourceVersion: context.sourceVersion,
    limitations: 'A indicação da Matriz não comprova elegibilidade, adesão, vigência, saldo, transferência ou resultado municipal.',
  }
}

/**
 * A path only exists where a published Matriz context points to it. Matching a
 * Matriz reference to the financing catalogue enriches its conditions; it does
 * not create a relationship for objectives without that published context.
 */
export function getPmeEditorialPaths(
  objectiveId: string,
  matrizContexts: readonly PmeMatrizObjectiveContext[] = [],
): PmeEditorialPath[] {
  const paths = matrizContexts.flatMap((context) => {
    const programs = [
      ...resolveMatrizFrentes(context.goalId).flatMap((frente) => frente.programs),
      ...(resolveMatrizGoalSupport(context.goalId)?.programs ?? []),
    ]
    return [
      ...context.federalFirstSteps.map((step) => matrizFirstStepPath(context, step)),
      ...programs.map((program) => matrizProgramPath(context, program)),
    ]
  })
  const deduplicated = paths.filter((path, index) => paths.findIndex((candidate) => candidate.id === path.id) === index)
  return deduplicated
}

export function getPmeObjectiveEditorial(objectiveId: string): PmeObjectiveEditorial {
  return PME_OBJECTIVE_CATALOG[objectiveId] ?? {
    objectiveId,
    title: `Objetivo ${objectiveId}`,
    themeId: 'tema_nao_catalogado',
    themeLabel: 'Tema editorial não catalogado',
    guidingQuestion: 'Quais informações públicas estão disponíveis para orientar a leitura deste objetivo?',
  }
}
