import { createHash } from 'node:crypto'
import { createReadStream } from 'node:fs'
import {
  access,
  copyFile,
  mkdir,
  mkdtemp,
  readFile,
  rename,
  rm,
  writeFile,
} from 'node:fs/promises'
import { gunzipSync } from 'node:zlib'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const moduleDir = path.dirname(fileURLToPath(import.meta.url))
export const DEFAULT_REPO_ROOT = path.resolve(moduleDir, '..', '..')

const SELECTION_RELATIVE_PATH = 'data_pipeline/contracts/vocacoes-pne-aa5-public-selection-v1.json'
const ALLOWLIST_RELATIVE_PATH = 'data_pipeline/contracts/vocacoes-pne-aa5-allowlist.json'
const BUNDLE_RELATIVE_PATH = 'src/features/vocacoes-regiao/generated/vocacoesPneAdvancedInsightsValeDoSinos.json'
const REGISTRY_RELATIVE_PATH = 'src/features/vocacoes-regiao/generated/vocacoesPneAdvancedInsightsRegistry.json'

const SCOPE_KEYS = Object.freeze(['VALE_10', 'MUNICIPALITY_4313375'])
const ANALYSIS_CHECK_STATUSES = new Set(['consistent', 'watch', 'not_confirmed', 'not_comparable'])

function invariant(condition, message) {
  if (!condition) throw new Error(`AA5 publication invariant failed: ${message}`)
}

function sha256Bytes(bytes) {
  return createHash('sha256').update(bytes).digest('hex')
}

async function sha256File(filePath) {
  const hash = createHash('sha256')
  await new Promise((resolve, reject) => {
    const stream = createReadStream(filePath)
    stream.on('data', (chunk) => hash.update(chunk))
    stream.on('error', reject)
    stream.on('end', resolve)
  })
  return hash.digest('hex')
}

async function readJson(filePath) {
  return JSON.parse(await readFile(filePath, 'utf8'))
}

function serializeJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`
}

function parseCsv(text) {
  const records = []
  let record = []
  let field = ''
  let quoted = false
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index]
    if (quoted) {
      if (char === '"') {
        if (text[index + 1] === '"') {
          field += '"'
          index += 1
        } else {
          quoted = false
        }
      } else {
        field += char
      }
      continue
    }
    if (char === '"') {
      quoted = true
    } else if (char === ',') {
      record.push(field)
      field = ''
    } else if (char === '\n') {
      record.push(field.endsWith('\r') ? field.slice(0, -1) : field)
      records.push(record)
      record = []
      field = ''
    } else {
      field += char
    }
  }
  invariant(!quoted, 'CSV reconciliado terminou dentro de campo entre aspas')
  if (field.length > 0 || record.length > 0) {
    record.push(field.endsWith('\r') ? field.slice(0, -1) : field)
    records.push(record)
  }
  invariant(records.length > 1, 'CSV reconciliado vazio')
  const headers = records[0]
  return records.slice(1).filter((row) => row.some((value) => value !== '')).map((row) => {
    invariant(row.length === headers.length, `CSV com ${row.length} colunas; esperado ${headers.length}`)
    return Object.fromEntries(headers.map((header, index) => [header, row[index]]))
  })
}

function parseNullableNumber(raw, label) {
  if (raw === undefined || raw === '' || raw === 'null') return null
  const value = Number(raw)
  invariant(Number.isFinite(value), `${label} não é número finito`)
  return value
}

function publicAvailability(raw) {
  const mapping = {
    observed: 'observed',
    observed_zero: 'observed_zero',
    AVAILABLE: 'observed',
    DETERMINISTIC_EXACT: 'calculated',
    IDENTIFICATION_BOUND: 'estimated_range',
  }
  const value = mapping[raw]
  invariant(value !== undefined, `estado de disponibilidade público não mapeado: ${raw}`)
  return value
}

function publicUnit(raw) {
  const mapping = {
    active_bonds: 'empregos formais',
    enrollments: 'matrículas',
    enrollments_absolute_change_component: 'matrículas',
    people: 'pessoas',
    percent: '%',
    percentage_points: 'p.p.',
    percent_of_active_bonds: '%',
    percent_of_active_bonds_in_normatively_connected_subgroups: '%',
    schools: 'escolas',
  }
  const value = mapping[raw]
  invariant(value !== undefined, `unidade pública não mapeada: ${raw}`)
  return value
}

function publicPeriod(start, end) {
  const safe = (value) => /^\d{4}(?:-\d{2})?$/u.test(value)
  if (safe(start) && safe(end)) return start === end ? start : `${start}–${end}`
  return 'período declarado na análise'
}

function sanitizePublicText(raw) {
  invariant(typeof raw === 'string' && raw.trim().length > 0, 'texto público vazio')
  return raw
    .replaceAll('Em o Vale', 'No Vale do Sinos')
    .replaceAll('em o Vale', 'no Vale do Sinos')
    .replaceAll('No AA2', 'Na análise estatística')
    .replaceAll('no AA2', 'na análise estatística')
    .replaceAll('AA2', 'a análise estatística')
    .replaceAll('NO_ROBUST_ASSOCIATION', 'ausência de associação robusta')
    .replaceAll('BH familiar conservador', 'ajuste conservador para múltiplos testes')
    .replaceAll('p rural bruto', 'resultado bruto para ruralidade')
    .replaceAll('componentes da decomposição', 'parte ligada à população e diferença a investigar')
    .replaceAll('se recompuseram', 'mudaram')
    .replaceAll('recomposição econômica', 'mudança no perfil dos empregos')
    .replaceAll('conexão normativa', 'comparação entre as classificações de ocupações e cursos')
    .replaceAll('nomenclatura', 'nomes das classificações')
    .replaceAll('cobertura parcial', 'uma conexão possível ainda incompleta')
    .replaceAll('pactuar expansão', 'decidir uma expansão em conjunto')
    .replaceAll('pactuação regional de cursos', 'decisão regional sobre cursos')
    .replaceAll('egressos', 'pessoas que concluíram os cursos')
    .replaceAll('relação robusta', 'ligação consistente nos testes')
    .replaceAll('comparação ajustada inconclusiva', 'comparação sem resultado claro depois de considerar outros fatores')
    .replaceAll('escola/coorte', 'escola e grupo de estudantes')
    .replaceAll('coortes em transição para a etapa', 'estudantes que estão chegando ao ensino médio')
    .replaceAll('banda contextual', 'faixa encontrada em contextos semelhantes')
    .replaceAll('nova estimação válida', 'nova análise com dados suficientes')
    .replaceAll('ajuste de composição', 'nova análise que considere mudanças no perfil dos estudantes')
    .replaceAll('composição discente', 'perfil dos estudantes')
    .replaceAll('Rebase populacional', 'Revisão da estimativa de população')
    .replaceAll('rebase populacional', 'revisão da estimativa de população')
    .replaceAll('hipótese operacional', 'hipótese de planejamento')
    .replaceAll('dados granulares', 'dados mais detalhados')
    .replaceAll('além da nomes das classificações', 'além da comparação entre os nomes das classificações')
    .replaceAll('Coordenar demografia, matrículas e capacidade da rede', 'Planejar matrículas, vagas e capacidade da rede junto com as mudanças na população')
    .replaceAll('Mapear acesso regional, oferta e trajetórias da EPT', 'Mapear cursos técnicos, acesso regional e caminhos dos estudantes')
    .replaceAll('Monitorar trajetória com contexto e composição', 'Acompanhar o abandono junto com informações sobre estudantes e escolas')
    .replaceAll('Divergência por duas atualizações entre população e matrícula ou mudança material de capacidade.', 'População e matrículas seguirem caminhos diferentes em duas atualizações seguidas, ou houver mudança importante na capacidade das escolas.')
    .replaceAll('Persistência da mudança no perfil dos empregos e evidência de barreira de acesso ou lacuna validada de oferta.', 'A mudança no perfil dos empregos continuar e os dados mostrarem dificuldade de acesso ou falta de oferta.')
    .replaceAll('Semestral operacional; anual para revisão do PME.', 'A cada semestre para a gestão; uma vez por ano para revisar o PME.')
    .replaceAll('Mudança persistente por etapa ou procura registrada não atendida por turno/território.', 'A mudança por etapa continuar ou houver pessoas interessadas sem turma adequada por turno ou local.')
    .replaceAll('com composição e mobilidade documentadas', 'registrando o perfil dos estudantes e as mudanças de escola ou deslocamento')
    .replaceAll('Mudança persistente de abandono ou saída da faixa encontrada em contextos semelhantes em nova análise com dados suficientes.', 'O abandono mudar de forma contínua ou sair da faixa encontrada para contextos semelhantes em uma nova análise com dados suficientes.')
    .replaceAll('Padrão reaparecer por escola e grupo de estudantes e sobreviver a nova análise que considere mudanças no perfil dos estudantes.', 'O mesmo resultado aparecer novamente por escola e continuar depois de uma análise que considere mudanças no perfil dos estudantes.')
    .replaceAll('Mudança decorrer de registro, composição ou mobilidade não controlada.', 'A mudança for explicada por correção de registro, mudança no perfil dos estudantes ou troca de escola e deslocamento.')
    .replaceAll('Fluxos residência–escola e capacidade confirmarem a hipótese de planejamento.', 'Os dados sobre onde os estudantes moram e estudam, junto da capacidade das escolas, confirmarem a hipótese.')
    .replaceAll('correção de registro explicar a divergência.', 'correção de registro explicar a diferença.')
    .replaceAll('Vagas, conclusão, deslocamento e pessoas que concluíram os cursos confirmarem conexão além da comparação entre os nomes das classificações.', 'Dados de vagas, conclusão, deslocamento e destino de quem concluiu confirmarem uma conexão além dos nomes das classificações.')
    .replaceAll('conexão CBO–curso', 'comparação entre ocupações e cursos')
    .trim()
}

function buildFactLookup(rows) {
  const facts = new Map()
  for (const row of rows) {
    invariant(/^([A-Z0-9_-]+)$/u.test(row.fact_id), `fact_id inválido: ${row.fact_id}`)
    invariant(!facts.has(row.fact_id), `fact_id duplicado: ${row.fact_id}`)
    facts.set(row.fact_id, row)
  }
  return facts
}

function buildEvidence(spec, factLookup) {
  const fact = factLookup.get(spec.factId)
  invariant(fact !== undefined, `fato selecionado ausente: ${spec.factId}`)
  invariant(fact.manager_facing_eligible === 'True', `fato não elegível para gestor: ${spec.factId}`)
  const availability = publicAvailability(fact.availability_state_end)
  let value
  let valueTo
  if (spec.valueField === 'interval') {
    value = parseNullableNumber(fact.interval_lower, `${spec.factId}.interval_lower`)
    valueTo = parseNullableNumber(fact.interval_upper, `${spec.factId}.interval_upper`)
    invariant(value !== null && valueTo !== null && value <= valueTo, `intervalo inválido: ${spec.factId}`)
  } else {
    invariant([
      'absolute_change',
      'effect_estimate',
      'value_end',
      'value_start',
    ].includes(spec.valueField), `valueField inválido: ${spec.valueField}`)
    value = parseNullableNumber(fact[spec.valueField], `${spec.factId}.${spec.valueField}`)
    invariant(value !== null, `valor selecionado nulo: ${spec.factId}.${spec.valueField}`)
  }
  const startValue = spec.includeEndpoints
    ? parseNullableNumber(fact.value_start, `${spec.factId}.value_start`)
    : null
  const endValue = spec.includeEndpoints
    ? parseNullableNumber(fact.value_end, `${spec.factId}.value_end`)
    : null
  if (spec.includeEndpoints) {
    invariant(startValue !== null && endValue !== null, `extremos ausentes: ${spec.factId}`)
  }
  const evidence = {
    label: spec.label,
    value,
    valueKind: spec.valueField === 'interval' ? 'interval' : spec.isChange ? 'change' : 'point',
    format: spec.format,
    unit: publicUnit(fact.unit),
    period: publicPeriod(fact.period_start, fact.period_end),
    contextLabel: spec.contextLabel,
    availability,
  }
  if (valueTo !== undefined) evidence.valueTo = valueTo
  if (startValue !== null && endValue !== null) {
    evidence.startValue = startValue
    evidence.endValue = endValue
  }
  return evidence
}

function findDossier(document, dossierId) {
  const dossier = document.dossiers.find((item) => item.dossierId === dossierId)
  invariant(dossier !== undefined, `dossiê ausente: ${dossierId}`)
  return dossier
}

function findAgenda(agendasDocument, agendaId) {
  const agenda = agendasDocument.agendas.find((item) => item.agendaId === agendaId)
  invariant(agenda !== undefined, `agenda ausente: ${agendaId}`)
  return agenda
}

function publicSources(sourceIds, sourceCatalog) {
  return sourceIds.map((sourceId) => {
    const label = sourceCatalog[sourceId]
    invariant(typeof label === 'string' && label.length > 0, `fonte pública ausente: ${sourceId}`)
    return label
  })
}

function assertEditorialSelection(selection) {
  const policy = selection.editorialSelection
  invariant(policy !== null && typeof policy === 'object', 'política de seleção editorial')
  invariant(typeof policy.decisionRule === 'string' && policy.decisionRule.length > 0, 'regra de seleção editorial')
  const criterionIds = policy.criteria.map((item) => item.id)
  invariant(
    JSON.stringify(criterionIds) === JSON.stringify(['evidence', 'materiality', 'stability', 'communication', 'planningValue']),
    'cinco critérios editoriais ordenados',
  )
  invariant(policy.criteria.every((item) => typeof item.question === 'string' && item.question.length > 0), 'perguntas dos critérios editoriais')
  invariant(policy.retainedReadings.length === selection.readings.length, 'ledger de leituras retidas')
  const retainedReadingIds = policy.retainedReadings.map((item) => item.id).sort()
  invariant(
    JSON.stringify(retainedReadingIds) === JSON.stringify(selection.readings.map((item) => item.id).sort()),
    'ledger de leituras deve reconciliar a seleção',
  )
  const allowedCriterionStates = new Set(['PASS', 'PASS_WITH_BOUNDARY'])
  for (const item of policy.retainedReadings) {
    invariant(typeof item.rationale === 'string' && item.rationale.length > 0, `justificativa editorial: ${item.id}`)
    invariant(
      JSON.stringify(Object.keys(item.criterionResults).sort()) === JSON.stringify([...criterionIds].sort()),
      `critérios completos: ${item.id}`,
    )
    invariant(Object.values(item.criterionResults).every((state) => allowedCriterionStates.has(state)), `resultado editorial inválido: ${item.id}`)
    invariant(
      ['INCLUDED_COMPATIBLE_MEASURE', 'NOT_INCLUDED_NO_COMPATIBLE_AA4_MEASURE'].includes(item.stateComparatorDisposition),
      `disposição do comparador estadual: ${item.id}`,
    )
  }
  invariant(policy.retainedAgendas.length === selection.planningAgendas.length, 'ledger de agendas retidas')
  invariant(
    JSON.stringify(policy.retainedAgendas.map((item) => item.sourceAgendaId).sort())
      === JSON.stringify(selection.planningAgendas.map((item) => item.sourceAgendaId).sort()),
    'ledger de agendas deve reconciliar a seleção',
  )
  invariant(policy.retainedAgendas.every((item) => typeof item.rationale === 'string' && item.rationale.length > 0), 'justificativas das agendas')
  invariant(selection.rejectedCandidates.some((item) => item.sourceAgendaId === 'AG3_YOUTH_WORK_EDUCATION_MONITORING'), 'agenda negativa no ledger de rejeição')
  invariant(selection.rejectedCandidates.some((item) => item.candidateId === 'P8_FINANCING_OFFER_AND_CAPACITY'), 'financiamento bloqueado no ledger')
}

function assertExpandedEvidenceFreeze(freeze) {
  invariant(freeze?.schemaVersion === 'vocacoes-pne-aa5-expanded-evidence-v1', 'contrato congelado das análises ampliadas')
  invariant(freeze.analysisDate === '2026-08-30', 'data da análise ampliada')
  const sourceKeys = ['demographyNetwork', 'economyWork', 'socialAccess']
  invariant(
    JSON.stringify(Object.keys(freeze.sourceArtifactSets ?? {}).sort()) === JSON.stringify([...sourceKeys].sort()),
    'três conjuntos de evidência ampliada',
  )
  for (const sourceKey of sourceKeys) {
    const source = freeze.sourceArtifactSets[sourceKey]
    for (const hashKey of ['resultsSha256', 'manifestSha256', 'preregistrationSha256', 'qaSha256']) {
      invariant(/^[a-f0-9]{64}$/u.test(source?.[hashKey]), `hash ${sourceKey}.${hashKey}`)
    }
  }

  const demography = freeze.sourceArtifactSets.demographyNetwork
  invariant(demography.qa.schemaVersion === 'vocacoes-pne-expanded-relations-validation-v1', 'schema de QA demográfico')
  invariant(demography.qa.overallState === 'PASS' && demography.qa.failedCount === 0, 'QA demográfico')
  invariant(demography.candidates.DN01.classification === 'PROMOTABLE_TECHNICAL_CANDIDATE', 'DN01 elegível')
  invariant(demography.candidates.DN02.classification === 'PROMOTABLE_TECHNICAL_CANDIDATE', 'DN02 elegível')
  invariant(
    demography.candidates.DN04.editorialDisposition === 'NOT_PUBLICIZED_FRAGILE_TO_PANDEMIC_EXCLUSION_AND_THEORY_GAP',
    'DN04 deve permanecer fora da publicação',
  )

  const economy = freeze.sourceArtifactSets.economyWork
  invariant(economy.qa.schemaVersion === 'economy-work-expanded-relations-qa-v1' && economy.qa.status === 'PASS', 'QA econômico')
  invariant(economy.candidates.EW3_EPT_INDUSTRIAL_STRUCTURE.selection === 'apenas_monitoramento', 'EW3 apenas para monitoramento')
  for (const candidateId of ['EW1_DROPOUT_YOUTH_WORK', 'EW1_APPROVAL_YOUTH_WORK_SECONDARY', 'EW2_EJA_EMPLOYMENT_INCOME']) {
    invariant(economy.candidates[candidateId].selection === 'rejeitada/indisponível', `${candidateId} não confirmado`)
  }

  const social = freeze.sourceArtifactSets.socialAccess
  invariant(social.qa.schemaVersion === 'vocacoes-pne-social-access-data-quality-v1', 'schema de QA social')
  invariant(social.qa.overallAssessment === 'SHARE_WITH_CAVEATS_AND_RESPECT_BLOCKS', 'QA social com limites respeitados')
  invariant(social.qa.denominatorZeroProducesNull === true, 'denominador zero preservado')
  invariant(social.qa.percentagesCapped === false, 'percentuais não truncados')
  invariant(social.qa.zeroDistinctFromUnavailable === true, 'zero distinto de indisponível')
  invariant(social.candidates.T1_INSE_LEARNING_AF_2023_2025.promotionState === 'BLOCKED_NETWORK_SCOPE_MISMATCH', 'aprendizagem bloqueada por escopo de rede')
  for (const candidateId of [
    'T2_INSE_DROPOUT_MEDIO_2023_2025',
    'T3_RURAL_SHARE_DISTORTION_AF_PANEL',
    'T4_FULLTIME_SHARE_DROPOUT_MEDIO_PANEL',
  ]) {
    invariant(social.candidates[candidateId].promotionState === 'NEGATIVE_NO_ROBUST_ASSOCIATION', `${candidateId} não confirmado`)
  }
  invariant(freeze.editorialGuardrails.causalClaimsAllowed === false, 'análises ampliadas não autorizam causalidade')
  invariant(freeze.editorialGuardrails.statewideOrRegionalEvidenceMustDiscloseScope === true, 'escopo ampliado deve ser declarado')
  invariant(JSON.stringify(freeze.editorialGuardrails.groupedCandidates) === JSON.stringify(['DN01', 'DN02']), 'DN01 e DN02 devem aparecer agrupados')
  invariant(freeze.editorialGuardrails.notPublicizedCandidates.includes('DN04'), 'DN04 no ledger de não publicação')
}

function assertExpandedAnalysisSelection(selection, freeze) {
  const expanded = selection.expandedAnalysis
  invariant(expanded?.schemaVersion === 'vocacoes-pne-expanded-reading-checks-v1', 'seleção das verificações adicionais')
  invariant(typeof expanded.evidenceFreezePath === 'string' && expanded.evidenceFreezePath.length > 0, 'path da evidência congelada')
  invariant(/^[a-f0-9]{64}$/u.test(expanded.evidenceFreezeSha256), 'hash da evidência congelada')
  invariant(expanded.fableCheckpoint?.verdict === 'ON_TRACK', 'checkpoint Fable da seleção ampliada')
  invariant(typeof expanded.fableCheckpoint.confidence === 'number' && expanded.fableCheckpoint.confidence >= 0.8, 'confiança do checkpoint Fable')

  const sourceKeys = ['demographyNetwork', 'economyWork', 'socialAccess']
  invariant(
    JSON.stringify(Object.keys(expanded.sourceArtifacts ?? {}).sort()) === JSON.stringify([...sourceKeys].sort()),
    'fontes da seleção ampliada',
  )
  for (const sourceKey of sourceKeys) {
    const declared = expanded.sourceArtifacts[sourceKey]
    const frozen = freeze.sourceArtifactSets[sourceKey]
    for (const hashKey of ['resultsSha256', 'manifestSha256', 'preregistrationSha256', 'qaSha256']) {
      invariant(declared[hashKey] === frozen[hashKey], `reconciliação ${sourceKey}.${hashKey}`)
    }
    for (const pathKey of ['resultsPath', 'manifestPath', 'preregistrationPath', 'qaPath']) {
      invariant(typeof declared[pathKey] === 'string' && declared[pathKey].length > 0, `proveniência ${sourceKey}.${pathKey}`)
    }
    if (declared.artifactSetDigestSha256 !== undefined) {
      invariant(declared.artifactSetDigestSha256 === frozen.artifactSetDigestSha256, `digest ${sourceKey}`)
    }
  }

  const expectedChecks = {
    'demografia-matriculas-rede': {
      sourceKey: 'demographyNetwork',
      evidenceRefs: ['DN01', 'DN02'],
      status: 'consistent',
    },
    'trajetoria-contexto': {
      sourceKey: 'socialAccess',
      evidenceRefs: [
        'T1_INSE_LEARNING_AF_2023_2025',
        'T2_INSE_DROPOUT_MEDIO_2023_2025',
        'T3_RURAL_SHARE_DISTORTION_AF_PANEL',
        'T4_FULLTIME_SHARE_DROPOUT_MEDIO_PANEL',
      ],
      status: 'not_confirmed',
    },
    'transformacao-economica-ept': {
      sourceKey: 'economyWork',
      evidenceRefs: ['EW3_EPT_INDUSTRIAL_STRUCTURE'],
      status: 'watch',
    },
    'escolaridade-adulta-eja': {
      sourceKey: 'economyWork',
      evidenceRefs: ['EW2_EJA_EMPLOYMENT_INCOME'],
      status: 'not_confirmed',
    },
    'trabalho-juvenil-permanencia': {
      sourceKey: 'economyWork',
      evidenceRefs: ['EW1_DROPOUT_YOUTH_WORK', 'EW1_APPROVAL_YOUTH_WORK_SECONDARY'],
      status: 'not_confirmed',
    },
  }
  invariant(
    JSON.stringify(Object.keys(expanded.readingChecks ?? {}).sort()) === JSON.stringify(Object.keys(expectedChecks).sort()),
    'uma verificação adicional para cada leitura',
  )
  for (const [readingId, expected] of Object.entries(expectedChecks)) {
    const check = expanded.readingChecks[readingId]
    invariant(check.sourceKey === expected.sourceKey, `fonte da verificação ${readingId}`)
    invariant(JSON.stringify(check.evidenceRefs) === JSON.stringify(expected.evidenceRefs), `evidências da verificação ${readingId}`)
    invariant(check.status === expected.status && ANALYSIS_CHECK_STATUSES.has(check.status), `estado da verificação ${readingId}`)
    invariant(!check.evidenceRefs.includes('DN04'), `DN04 não pode aparecer em ${readingId}`)
    invariant(
      JSON.stringify(Object.keys(check.scopeDisclosures ?? {}).sort()) === JSON.stringify([...SCOPE_KEYS].sort()),
      `declarações de escopo ${readingId}`,
    )
    for (const key of ['label', 'title', 'scopeLabel', 'summary', 'planningMeaning']) {
      invariant(typeof check[key] === 'string' && check[key].trim().length > 0, `${readingId}.${key}`)
    }
    invariant(Array.isArray(check.details) && check.details.length >= 2, `detalhes da verificação ${readingId}`)
    invariant(Array.isArray(check.sources) && check.sources.length > 0, `fontes da verificação ${readingId}`)
    invariant(check.details.every((item) => typeof item === 'string' && item.trim().length > 0), `detalhes preenchidos ${readingId}`)
    invariant(check.sources.every((item) => typeof item === 'string' && item.trim().length > 0), `fontes preenchidas ${readingId}`)
    invariant(check.evidenceRefs.every((reference) => freeze.sourceArtifactSets[check.sourceKey].candidates[reference] !== undefined), `referências congeladas ${readingId}`)
  }
}

function assertRelationshipCheck(check, label) {
  invariant(check !== null && typeof check === 'object', `verificação do atlas: ${label}`)
  invariant(ANALYSIS_CHECK_STATUSES.has(check.status), `estado do atlas: ${label}`)
  invariant(
    JSON.stringify(Object.keys(check.scopeDisclosures ?? {}).sort()) === JSON.stringify([...SCOPE_KEYS].sort()),
    `declarações territoriais do atlas: ${label}`,
  )
  for (const key of ['label', 'title', 'scopeLabel', 'summary', 'planningMeaning']) {
    invariant(typeof check[key] === 'string' && check[key].trim().length > 0, `atlas ${label}.${key}`)
  }
  invariant(Array.isArray(check.details) && check.details.length >= 2, `detalhes do atlas: ${label}`)
  invariant(Array.isArray(check.sources) && check.sources.length > 0, `fontes do atlas: ${label}`)
}

function assertRelationshipAtlasSelection(selection, evidence) {
  const atlas = selection.relationshipAtlas
  invariant(atlas?.schemaVersion === 'vocacoes-pne-relationship-atlas-public-selection-v1', 'seleção do atlas relacional')
  invariant(atlas.state === 'COMPLETE_RECONCILED_FOR_PUBLICATION', 'estado reconciliado do atlas')
  invariant(evidence.executionContract.schemaVersion === 'vocacoes-pne-relationship-atlas-execution-v1', 'contrato de execução relacional')
  invariant(evidence.executionContract.multiplicityProtocol.statewideMaximumQ === 0.05, 'limiar estadual congelado')
  invariant(evidence.executionContract.multiplicityProtocol.valeMaximumQ === 0.1, 'limiar do Vale congelado')
  invariant(atlas.multiplicityThresholds.statewideMaximumQ === 0.05, 'limiar estadual publicado')
  invariant(atlas.multiplicityThresholds.valeMaximumQ === 0.1, 'limiar do Vale publicado')
  invariant(atlas.multiplicityThresholds.globalQIsExploratoryOnly === true, 'q global apenas exploratório')

  invariant(evidence.manifest.schemaVersion === 'vocacoes-pne-relationship-atlas-reconciliation-manifest-v1', 'manifesto relacional')
  invariant(evidence.manifest.state === 'COMPLETE', 'resultado relacional completo')
  invariant(evidence.manifest.artifactSetDigestSha256 === atlas.artifactSetDigestSha256, 'digest relacional reconciliado')
  invariant(evidence.manifest.executionContractSha256 === atlas.executionContractSha256, 'contrato usado no resultado relacional')
  invariant(evidence.qa.state === 'PASS' && evidence.qa.resultCount === 98, 'QA relacional')
  invariant(evidence.qa.uniqueHypothesisCount === 98 && evidence.qa.allCausalClaimsBlocked === true, 'unicidade e causalidade do atlas')
  invariant(evidence.allResults.length === 98, '98 relações no atlas')
  invariant(new Set(evidence.allResults.map((item) => item.hypothesisId)).size === 98, 'hipóteses relacionais únicas')
  invariant(evidence.allResults.every((item) => item.causalClaimAllowed === false), 'nenhuma relação causal no atlas')
  invariant(evidence.allResults.every((item) => Number.isFinite(item.qValueFamily) && Number.isFinite(item.qValueGlobal)), 'q-valores relacionais completos')

  const expectedStatusCounts = {
    ROBUST_ASSOCIATION: 6,
    NO_ROBUST_ASSOCIATION: 28,
    INSUFFICIENT_DATA: 61,
    DESCRIPTIVE_ONLY: 2,
    BLOCKED_NOT_COMPARABLE: 1,
  }
  const statusCounts = Object.fromEntries(Object.keys(expectedStatusCounts).map((status) => [
    status,
    evidence.allResults.filter((item) => item.status === status).length,
  ]))
  invariant(JSON.stringify(statusCounts) === JSON.stringify(expectedStatusCounts), 'distribuição dos 98 resultados')
  invariant(evidence.promotions.length === 6, 'seis linhas aprovadas no atlas')
  invariant(evidence.promotions.every(({ result }) => (
    result.familyId === 'R12_RURALITY_ACCESS'
    && result.promotionEligible === true
    && result.causalClaimAllowed === false
    && result.qValueFamily <= 0.1
  )), 'aprovações restritas ao mecanismo rural e ao limiar congelado')
  invariant(new Set(evidence.promotions.map(({ result }) => result.mechanismId)).size === 1, 'seis linhas agrupadas em um mecanismo')

  invariant(evidence.fableAudit.verdict === 'AT_RISK', 'veredito final do Fable preservado')
  invariant(atlas.fableVerdict === 'AT_RISK_RECONCILED', 'risco do Fable deve estar reconciliado')
  for (const fragment of ['## Accepted findings', '## Clarified finding', '## Product decision']) {
    invariant(evidence.fableReconciliation.includes(fragment), `reconciliação Fable: ${fragment}`)
  }

  const selectedReadingIds = selection.readings.map((item) => item.id).sort()
  invariant(
    JSON.stringify(Object.keys(atlas.readingChecks ?? {}).sort()) === JSON.stringify(selectedReadingIds),
    'uma verificação relacional para cada leitura pública',
  )
  for (const [readingId, check] of Object.entries(atlas.readingChecks)) assertRelationshipCheck(check, readingId)
  invariant(
    JSON.stringify(Object.keys(atlas.transversalChecks ?? {})) === JSON.stringify(['ruralidade-organizacao-rede']),
    'um contexto estrutural rural agrupado',
  )
  assertRelationshipCheck(atlas.transversalChecks['ruralidade-organizacao-rede'], 'ruralidade-organizacao-rede')
  invariant(atlas.resultSummary.testedRelationships === 98, 'resumo público de 98 relações')
  invariant(atlas.resultSummary.robustRows === 6 && atlas.resultSummary.robustMechanisms === 1, 'seis linhas em um mecanismo no resumo')
  invariant(atlas.resultSummary.causalClaimsAllowed === false, 'resumo sem causalidade')
}

function buildAnalysisCheck(check, scopeKey) {
  return {
    status: check.status,
    label: sanitizePublicText(check.label),
    title: sanitizePublicText(check.title),
    scopeLabel: sanitizePublicText(check.scopeLabel),
    scopeDisclosure: sanitizePublicText(check.scopeDisclosures[scopeKey]),
    summary: sanitizePublicText(check.summary),
    planningMeaning: sanitizePublicText(check.planningMeaning),
    details: check.details.map(sanitizePublicText),
    sources: check.sources.map(sanitizePublicText),
  }
}

function buildReading(selection, analysisCheck, dossierDocument, agendasDocument, factLookup, sourceCatalog, scopeKey) {
  const dossier = findDossier(dossierDocument, selection.dossierId)
  findAgenda(agendasDocument, selection.planningAgendaId)
  const theory = dossier.theoryAndBoundaries[selection.theoryIndex]
  invariant(theory !== undefined, `mecanismo ${selection.theoryIndex} ausente em ${selection.dossierId}`)
  const evidenceSpecs = selection.evidence[scopeKey]
  invariant(Array.isArray(evidenceSpecs), `evidências ausentes em ${selection.id}/${scopeKey}`)
  const evidence = evidenceSpecs.map((spec) => buildEvidence(spec, factLookup))
  invariant(evidence.length >= 2 && evidence.length <= 3, `${selection.id} deve ter duas ou três evidências`)
  const copy = selection.publicCopy
  invariant(copy !== null && typeof copy === 'object', `texto acessível ausente: ${selection.id}`)
  invariant(typeof copy.conclusions?.[scopeKey] === 'string', `conclusão acessível ausente: ${selection.id}/${scopeKey}`)
  invariant(Array.isArray(copy.mechanism?.alternatives) && copy.mechanism.alternatives.length > 0, `alternativas acessíveis ausentes: ${selection.id}`)
  invariant(Array.isArray(copy.planning?.indicators) && copy.planning.indicators.length > 0, `indicadores acessíveis ausentes: ${selection.id}`)
  return {
    id: selection.id,
    order: selection.order,
    theme: selection.theme,
    title: sanitizePublicText(copy.title),
    question: sanitizePublicText(copy.question),
    conclusion: sanitizePublicText(copy.conclusions[scopeKey]),
    territorialReading: sanitizePublicText(copy.territorialReading),
    evidenceClass: { ...selection.evidenceClass },
    evidence,
    comparisonNote: selection.comparisonNotes[scopeKey],
    analysisCheck: buildAnalysisCheck(analysisCheck, scopeKey),
    visualKind: selection.visualKind,
    mechanism: {
      summary: sanitizePublicText(copy.mechanism.summary),
      expectedPattern: sanitizePublicText(copy.mechanism.expectedPattern),
      alternatives: copy.mechanism.alternatives.map(sanitizePublicText),
      boundary: sanitizePublicText(copy.mechanism.boundary),
    },
    planning: {
      question: sanitizePublicText(copy.planning.question),
      implication: sanitizePublicText(copy.planning.implication),
      indicators: copy.planning.indicators.map(sanitizePublicText),
    },
    limit: sanitizePublicText(copy.limit),
    sources: publicSources(selection.sourceIds, sourceCatalog),
  }
}

function buildAgenda(selection, agendasDocument, scopeKey, readings) {
  const source = findAgenda(agendasDocument, selection.sourceAgendaId)
  const scopeVariant = source.scopeVariants.find((item) => item.scopeId === scopeKey)
  invariant(scopeVariant !== undefined, `variante de agenda ausente: ${selection.sourceAgendaId}/${scopeKey}`)
  const relatedReading = readings.find((readingSelection) => readingSelection.planningAgendaId === selection.sourceAgendaId)
  invariant(relatedReading !== undefined, `agenda sem leitura: ${selection.sourceAgendaId}`)
  return {
    id: selection.id,
    order: selection.order,
    title: sanitizePublicText(source.title),
    status: 'Agenda de planejamento; não é prioridade automática.',
    whyNow: sanitizePublicText(source.observedCondition),
    action: sanitizePublicText(source.concreteAction),
    educationStage: sanitizePublicText(source.educationStage),
    exposedPopulation: sanitizePublicText(source.exposedPopulation),
    responsibility: {
      level: source.responsibilityLevel,
      lead: sanitizePublicText(source.leadResponsibility),
      contributors: source.contributors.map(sanitizePublicText),
    },
    indicators: source.indicators.map(sanitizePublicText),
    trigger: sanitizePublicText(scopeVariant.triggerDefinition),
    cadence: sanitizePublicText(source.cadence),
    strengthenIf: sanitizePublicText(source.strengthenIf),
    weakenIf: sanitizePublicText(source.weakenIf),
    relatedReadingId: relatedReading.id,
  }
}

function buildTransversal(item, factLookup, sourceCatalog, scopeKey, analysisCheck = null) {
  const evidence = item.evidence[scopeKey].map((spec) => buildEvidence(spec, factLookup))
  const result = {
    id: item.id,
    title: item.title,
    interpretation: item.interpretation,
    evidence,
    planningQuestion: item.question,
    limit: item.limit,
    sources: publicSources(item.sourceIds, sourceCatalog),
  }
  if (analysisCheck !== null) result.analysisCheck = buildAnalysisCheck(analysisCheck, scopeKey)
  return result
}

function deepVisit(value, callback) {
  if (Array.isArray(value)) {
    value.forEach((item) => deepVisit(item, callback))
    return
  }
  if (value !== null && typeof value === 'object') {
    for (const [key, child] of Object.entries(value)) {
      callback(key, child)
      deepVisit(child, callback)
    }
  }
}

export function assertPublicBundle(bundle, allowlist) {
  invariant(bundle.schemaVersion === 'vocacoes-pne-advanced-insights-v1', 'schemaVersion público')
  invariant(bundle.publicationStatus === 'official', 'status público')
  invariant(/^[a-f0-9]{64}$/u.test(bundle.contentVersion), 'contentVersion público')
  invariant(JSON.stringify(Object.keys(bundle).sort()) === JSON.stringify([...allowlist.requiredTopLevelKeys].sort()), 'chaves de topo fora da allowlist')
  invariant(bundle.region.stateCode === 'RS', 'UF pública')
  invariant(bundle.region.slug === 'vale-do-sinos', 'slug público')
  invariant(bundle.region.municipalityCount === 10, 'contagem municipal pública')
  invariant(bundle.region.municipalities.length === 10, 'registro municipal público')
  invariant(new Set(bundle.region.municipalities.map((item) => item.ibgeCode)).size === 10, 'IBGE municipal duplicado')
  invariant(bundle.region.municipalities.every((item) => /^43\d{5}$/u.test(item.ibgeCode)), 'IBGE público deve ser texto de sete dígitos')
  invariant(bundle.region.advancedMunicipalityIbgeCodes.length === 1 && bundle.region.advancedMunicipalityIbgeCodes[0] === '4313375', 'escopo municipal avançado')
  const atlasSummary = bundle.methodology.relationshipAtlas
  invariant(atlasSummary?.testedRelationships === 98, '98 relações no resumo público')
  invariant(atlasSummary.robustRows === 6 && atlasSummary.robustMechanisms === 1, 'seis linhas em um mecanismo público')
  invariant(atlasSummary.notRobustRows === 28 && atlasSummary.insufficientRows === 61, 'resultados negativos e insuficientes explícitos')
  invariant(typeof atlasSummary.statement === 'string' && atlasSummary.statement.length > 0, 'síntese pública do atlas')
  invariant(typeof atlasSummary.familyThresholdStatement === 'string' && atlasSummary.familyThresholdStatement.length > 0, 'regra de multiplicidade pública')
  invariant(Object.keys(bundle.scopeVariants).sort().join(',') === 'novaSantaRita,region', 'variantes públicas')
  for (const variant of Object.values(bundle.scopeVariants)) {
    invariant(variant.readings.length >= allowlist.selectionLimits.readingCountMinimum, 'mínimo de leituras')
    invariant(variant.readings.length <= allowlist.selectionLimits.readingCountMaximum, 'máximo de leituras')
    invariant(variant.agendas.length >= allowlist.selectionLimits.agendaCountMinimum, 'mínimo de agendas')
    invariant(variant.agendas.length <= allowlist.selectionLimits.agendaCountMaximum, 'máximo de agendas')
    for (const reading of variant.readings) {
      invariant(typeof reading.conclusion === 'string' && reading.conclusion.length > 0, `conclusão pública: ${reading.id}`)
      invariant(reading.evidence.length >= 2 && reading.evidence.length <= 3, `duas ou três evidências: ${reading.id}`)
      invariant(typeof reading.comparisonNote === 'string' && reading.comparisonNote.length > 0, `comparação pública: ${reading.id}`)
      invariant(/(?:Rio Grande do Sul|estadual)/iu.test(reading.comparisonNote), `disposição estadual pública: ${reading.id}`)
      invariant(typeof reading.mechanism.summary === 'string' && reading.mechanism.summary.length > 0, `mecanismo público: ${reading.id}`)
      invariant(reading.mechanism.alternatives.length > 0, `alternativas públicas: ${reading.id}`)
      invariant(typeof reading.mechanism.boundary === 'string' && reading.mechanism.boundary.length > 0, `fronteira técnica: ${reading.id}`)
      invariant(typeof reading.planning.implication === 'string' && reading.planning.implication.length > 0, `implicação pública: ${reading.id}`)
      invariant(reading.planning.indicators.length > 0, `indicadores públicos: ${reading.id}`)
      invariant(typeof reading.limit === 'string' && reading.limit.length > 0, `limite público: ${reading.id}`)
      invariant(reading.sources.length > 0, `fontes públicas: ${reading.id}`)
      const analysisCheck = reading.analysisCheck
      invariant(analysisCheck !== null && typeof analysisCheck === 'object', `verificação adicional: ${reading.id}`)
      invariant(ANALYSIS_CHECK_STATUSES.has(analysisCheck.status), `estado da verificação adicional: ${reading.id}`)
      for (const key of ['label', 'title', 'scopeLabel', 'scopeDisclosure', 'summary', 'planningMeaning']) {
        invariant(typeof analysisCheck[key] === 'string' && analysisCheck[key].length > 0, `verificação adicional ${reading.id}.${key}`)
      }
      invariant(Array.isArray(analysisCheck.details) && analysisCheck.details.length >= 2, `detalhes da verificação adicional: ${reading.id}`)
      invariant(Array.isArray(analysisCheck.sources) && analysisCheck.sources.length > 0, `fontes da verificação adicional: ${reading.id}`)
    }
    const analysisStates = Object.fromEntries(variant.readings.map((reading) => [reading.id, reading.analysisCheck.status]))
    invariant(analysisStates['demografia-matriculas-rede'] === 'not_confirmed', 'robustez demográfica incompleta')
    invariant(analysisStates['transformacao-economica-ept'] === 'watch', 'relação econômica apenas para acompanhamento')
    invariant(
      ['trajetoria-contexto', 'trabalho-juvenil-permanencia']
        .every((readingId) => analysisStates[readingId] === 'not_confirmed'),
      'resultados não confirmados devem permanecer visíveis',
    )
    invariant(analysisStates['escolaridade-adulta-eja'] === 'watch', 'sinal EJA deve preservar a falha no placebo')
    const ruralContext = variant.transversal.find((item) => item.id === 'ruralidade-organizacao-rede')
    invariant(ruralContext?.analysisCheck?.status === 'consistent', 'contexto rural deve carregar a verificação agrupada')
    invariant(variant.readings.some((reading) => reading.evidenceClass.kind === 'boundary'), 'resultado negativo deve permanecer visível')
  }
  invariant(
    Object.values(bundle.scopeVariants).some((variant) => variant.readings.some((reading) => reading.evidence.some((item) => item.value === 0 && item.availability === 'observed_zero'))),
    'zero observado deve permanecer explícito',
  )
  const forbiddenKeys = new Set(allowlist.forbiddenKeyNames)
  deepVisit(bundle, (key, child) => {
    invariant(!forbiddenKeys.has(key), `chave interna no bundle público: ${key}`)
    if (typeof child === 'string') {
      for (const token of allowlist.forbiddenStringTokens) {
        invariant(!child.includes(token), `token interno no bundle público: ${token}`)
      }
      for (const token of allowlist.forbiddenPublicLanguageTokens) {
        invariant(!child.toLocaleLowerCase('pt-BR').includes(token.toLocaleLowerCase('pt-BR')), `termo técnico não explicado no bundle público: ${token}`)
      }
    }
  })
}

function assertRegistry(
  registry,
  bundleBytes,
  bundle,
  selectionHash,
  allowlistHash,
  sourceManifestHash,
  expandedAnalysisEvidenceHash,
  relationshipAtlasArtifactSetDigestSha256,
) {
  invariant(registry.schemaVersion === 'vocacoes-pne-advanced-insights-registry-v1', 'schemaVersion do registro')
  invariant(registry.bundleSha256 === sha256Bytes(bundleBytes), 'hash do bundle no registro')
  invariant(registry.bundleByteSize === Buffer.byteLength(bundleBytes), 'tamanho do bundle no registro')
  invariant(registry.contentVersion === bundle.contentVersion, 'contentVersion no registro')
  invariant(registry.selectionSha256 === selectionHash, 'hash da seleção no registro')
  invariant(registry.allowlistSha256 === allowlistHash, 'hash da allowlist no registro')
  invariant(registry.sourceManifestSha256 === sourceManifestHash, 'hash do manifesto no registro')
  invariant(registry.expandedAnalysisEvidenceSha256 === expandedAnalysisEvidenceHash, 'hash das análises ampliadas no registro')
  invariant(registry.relationshipAtlasArtifactSetDigestSha256 === relationshipAtlasArtifactSetDigestSha256, 'digest do atlas relacional no registro')
  invariant(registry.readingCount === 5 && registry.agendaCount === 4, 'contagens do registro')
}

async function loadAndVerifyInputs(repoRoot) {
  const selectionPath = path.join(repoRoot, SELECTION_RELATIVE_PATH)
  const allowlistPath = path.join(repoRoot, ALLOWLIST_RELATIVE_PATH)
  const selectionBytes = await readFile(selectionPath)
  const allowlistBytes = await readFile(allowlistPath)
  const selection = JSON.parse(selectionBytes.toString('utf8'))
  const allowlist = JSON.parse(allowlistBytes.toString('utf8'))
  invariant(selection.schemaVersion === 'vocacoes-pne-aa5-public-selection-v1', 'contrato de seleção')
  invariant(allowlist.schemaVersion === 'vocacoes-pne-aa5-allowlist-v1', 'contrato de allowlist')
  invariant(JSON.stringify(allowlist.allowedOutputPaths) === JSON.stringify([BUNDLE_RELATIVE_PATH, REGISTRY_RELATIVE_PATH]), 'paths de saída da allowlist')
  invariant(Array.isArray(allowlist.stageOwnedPaths) && allowlist.stageOwnedPaths.length > 0, 'inventário de paths AA5')
  invariant(allowlist.stageOwnedPaths.every((item) => typeof item === 'string' && !item.replaceAll('\\', '/').startsWith('public/data/')), 'AA5 não possui path em public/data')
  invariant(allowlist.allowedOutputPaths.every((item) => allowlist.stageOwnedPaths.includes(item)), 'saídas devem pertencer ao inventário AA5')
  assertEditorialSelection(selection)

  const expandedEvidencePath = path.join(repoRoot, selection.expandedAnalysis.evidenceFreezePath)
  const expandedEvidenceBytes = await readFile(expandedEvidencePath)
  const expandedAnalysisEvidenceHash = sha256Bytes(expandedEvidenceBytes)
  invariant(expandedAnalysisEvidenceHash === selection.expandedAnalysis.evidenceFreezeSha256, 'hash congelado das análises ampliadas')
  const expandedEvidence = JSON.parse(expandedEvidenceBytes.toString('utf8'))
  assertExpandedEvidenceFreeze(expandedEvidence)
  assertExpandedAnalysisSelection(selection, expandedEvidence)

  const relationship = selection.relationshipAtlas
  const readVerified = async (relativePath, expectedHash, label) => {
    const bytes = await readFile(path.join(repoRoot, relativePath))
    invariant(sha256Bytes(bytes) === expectedHash, `hash relacional divergente: ${label}`)
    return bytes
  }
  const relationshipEvidence = {
    executionContract: JSON.parse((await readVerified(
      relationship.executionContractPath,
      relationship.executionContractSha256,
      'executionContract',
    )).toString('utf8')),
    manifest: JSON.parse((await readVerified(
      relationship.manifestPath,
      relationship.manifestSha256,
      'manifest',
    )).toString('utf8')),
    allResults: JSON.parse((await readVerified(
      relationship.allResultsPath,
      relationship.allResultsSha256,
      'allResults',
    )).toString('utf8')),
    promotions: JSON.parse((await readVerified(
      relationship.promotionLedgerPath,
      relationship.promotionLedgerSha256,
      'promotionLedger',
    )).toString('utf8')),
    qa: JSON.parse((await readVerified(
      relationship.qaPath,
      relationship.qaSha256,
      'qa',
    )).toString('utf8')),
    fableAudit: JSON.parse((await readVerified(
      relationship.fableAuditPath,
      relationship.fableAuditSha256,
      'fableAudit',
    )).toString('utf8')),
    fableReconciliation: (await readVerified(
      relationship.fableReconciliationPath,
      relationship.fableReconciliationSha256,
      'fableReconciliation',
    )).toString('utf8'),
  }
  assertRelationshipAtlasSelection(selection, relationshipEvidence)

  const manifestPath = path.join(repoRoot, selection.source.manifestPath)
  const manifestHash = await sha256File(manifestPath)
  invariant(manifestHash === selection.source.manifestSha256, 'hash congelado do manifesto AA4')
  const manifest = await readJson(manifestPath)
  invariant(manifest.finalState === selection.source.requiredFinalState, 'estado final AA4')
  invariant(manifest.artifactSetDigestSha256 === selection.source.artifactSetDigestSha256, 'digest do conjunto AA4')
  invariant(manifest.qa.state === 'PASS' && manifest.qa.failedCount === 0, 'QA AA4')
  invariant(manifest.opusReconciliation.reAudit.aa5EntryAllowed === true, 'entrada AA5 autorizada pela reauditoria')
  for (const [relativeName, expectedHash] of Object.entries(selection.source.artifacts)) {
    const artifactPath = path.join(path.dirname(manifestPath), relativeName)
    invariant(await sha256File(artifactPath) === expectedHash, `hash AA4 divergente: ${relativeName}`)
  }

  const factsPath = path.join(path.dirname(manifestPath), 'FATOS_RECONCILIADOS_AA4.csv.gz')
  const factRows = parseCsv(gunzipSync(await readFile(factsPath)).toString('utf8'))
  const dossiersVale = await readJson(path.join(path.dirname(manifestPath), 'DOSSIES_VALE_AA4.json'))
  const dossiersNsr = await readJson(path.join(path.dirname(manifestPath), 'DOSSIES_NOVA_SANTA_RITA_AA4.json'))
  const agendas = await readJson(path.join(path.dirname(manifestPath), 'AGENDAS_PLANEJAMENTO_AA4.json'))
  const municipalityRegistry = await readJson(path.join(repoRoot, selection.scope.municipalityRegistryPath))
  return {
    selection,
    allowlist,
    manifest,
    manifestHash,
    selectionHash: sha256Bytes(selectionBytes),
    allowlistHash: sha256Bytes(allowlistBytes),
    expandedAnalysisEvidenceHash,
    relationshipAtlasArtifactSetDigestSha256: relationship.artifactSetDigestSha256,
    factRows,
    dossiersVale,
    dossiersNsr,
    agendas,
    municipalityRegistry,
  }
}

export async function materializeVocacoesPneAdvancedPublication(repoRoot = DEFAULT_REPO_ROOT) {
  const inputs = await loadAndVerifyInputs(repoRoot)
  const {
    selection,
    allowlist,
    manifest,
    manifestHash,
    selectionHash,
    allowlistHash,
    expandedAnalysisEvidenceHash,
    relationshipAtlasArtifactSetDigestSha256,
    factRows,
    dossiersVale,
    dossiersNsr,
    agendas,
    municipalityRegistry,
  } = inputs
  invariant(selection.readings.length === 5, 'seleção deve conter cinco leituras')
  invariant(selection.planningAgendas.length === 4, 'seleção deve conter quatro agendas')
  invariant(selection.rejectedCandidates.some((item) => item.sourceAgendaId === 'AG3_YOUTH_WORK_EDUCATION_MONITORING'), 'agenda negativa deve ser rejeitada como cartão autônomo')
  invariant(municipalityRegistry.schemaVersion === 'municipality-registry-v1' && municipalityRegistry.stateCode === 'RS', 'registro municipal canônico')
  const registryByCode = new Map(municipalityRegistry.municipalities.map((item) => [item.ibgeCode, item]))
  const municipalities = selection.scope.regionMunicipalityIbgeCodes.map((ibgeCode) => {
    invariant(/^43\d{5}$/u.test(ibgeCode), `IBGE textual inválido: ${ibgeCode}`)
    const municipality = registryByCode.get(ibgeCode)
    invariant(municipality !== undefined, `município ausente do registro: ${ibgeCode}`)
    return { ibgeCode, name: municipality.name, slug: municipality.slug }
  })
  invariant(new Set(municipalities.map((item) => item.ibgeCode)).size === 10, 'dez municípios canônicos distintos')
  const selectedMunicipality = registryByCode.get(selection.scope.selectedMunicipalityIbgeCode)
  invariant(selectedMunicipality !== undefined, 'Nova Santa Rita ausente do registro')
  invariant(selectedMunicipality.name === 'Nova Santa Rita', 'identidade de Nova Santa Rita')

  const factLookup = buildFactLookup(factRows)
  const scopeInputs = {
    VALE_10: { document: dossiersVale, editorial: selection.scopeEditorial.VALE_10 },
    MUNICIPALITY_4313375: { document: dossiersNsr, editorial: selection.scopeEditorial.MUNICIPALITY_4313375 },
  }
  const scopeVariants = {}
  for (const scopeKey of SCOPE_KEYS) {
    const scopeInput = scopeInputs[scopeKey]
    const readings = selection.readings
      .map((item) => buildReading(
        item,
        selection.relationshipAtlas.readingChecks[item.id],
        scopeInput.document,
        agendas,
        factLookup,
        selection.sourceCatalog,
        scopeKey,
      ))
      .sort((left, right) => left.order - right.order)
    const publicAgendas = selection.planningAgendas
      .map((item) => buildAgenda(item, agendas, scopeKey, selection.readings))
      .sort((left, right) => left.order - right.order)
    const transversal = selection.transversalItems.map((item) => buildTransversal(
      item,
      factLookup,
      selection.sourceCatalog,
      scopeKey,
      selection.relationshipAtlas.transversalChecks[item.id] ?? null,
    ))
    const publicKey = scopeKey === 'VALE_10' ? 'region' : 'novaSantaRita'
    scopeVariants[publicKey] = {
      entityType: scopeInput.editorial.entityType,
      entityName: scopeKey === 'VALE_10' ? selection.scope.regionName : selectedMunicipality.name,
      municipalityIbgeCode: scopeKey === 'VALE_10' ? null : selection.scope.selectedMunicipalityIbgeCode,
      headline: scopeInput.editorial.headline,
      standfirst: scopeInput.editorial.standfirst,
      containmentDisclosure: scopeInput.editorial.containmentDisclosure,
      decisionSignals: scopeInput.editorial.decisionSignals,
      readings,
      agendas: publicAgendas,
      transversal,
    }
  }

  const contentVersion = sha256Bytes(Buffer.from(JSON.stringify({
    sourceArtifactSetDigestSha256: manifest.artifactSetDigestSha256,
    expandedAnalysisEvidenceSha256: expandedAnalysisEvidenceHash,
    relationshipAtlasArtifactSetDigestSha256,
    selectionHash,
    allowlistHash,
  })))
  const bundle = {
    schemaVersion: 'vocacoes-pne-advanced-insights-v1',
    contentVersion,
    publicationStatus: 'official',
    generatedAt: selection.relationshipAtlas.state === 'COMPLETE_RECONCILED_FOR_PUBLICATION'
      ? '2026-08-31T00:00:00-03:00'
      : manifest.generatedAt,
    region: {
      id: selection.scope.regionId,
      slug: selection.scope.regionSlug,
      name: selection.scope.regionName,
      stateCode: selection.scope.stateCode,
      municipalityCount: municipalities.length,
      municipalities,
      advancedMunicipalityIbgeCodes: selection.scope.advancedMunicipalityIbgeCodes,
    },
    methodology: {
      educationNetworkScope: selection.scope.educationNetworkScope,
      municipalIdentity: 'Cada município é identificado pelo código IBGE de sete dígitos; os dados não são juntados apenas pelo nome.',
      readingDirections: [
        {
          label: 'Educação → território',
          description: 'Parte de um resultado educacional e procura nos dados do território pistas que ajudem a compreendê-lo.',
        },
        {
          label: 'Território → educação',
          description: 'Parte das mudanças no território e mostra perguntas, ações e condições de revisão para o planejamento.',
        },
      ],
      evidenceStatement: 'A plataforma separa o tipo de leitura original e acrescenta uma verificação estatística: padrão consistente, sinal para acompanhar, ligação não confirmada ou comparação que ainda não pode ser feita.',
      availabilityStatement: 'Zero registrado, dado ausente, dado indisponível, dado suprimido e medida que não se aplica são situações diferentes.',
      causalityStatement: 'Duas coisas podem mudar no mesmo período sem que uma tenha causado a outra. A teoria ajuda a formular perguntas, mas os dados locais precisam sustentar cada conclusão.',
      relationshipAtlas: {
        testedRelationships: selection.relationshipAtlas.resultSummary.testedRelationships,
        robustRows: selection.relationshipAtlas.resultSummary.robustRows,
        robustMechanisms: selection.relationshipAtlas.resultSummary.robustMechanisms,
        notRobustRows: selection.relationshipAtlas.resultSummary.notRobustRows,
        insufficientRows: selection.relationshipAtlas.resultSummary.insufficientRows,
        descriptiveRows: selection.relationshipAtlas.resultSummary.descriptiveRows,
        blockedRows: selection.relationshipAtlas.resultSummary.blockedRows,
        statement: selection.relationshipAtlas.resultSummary.publicStatement,
        familyThresholdStatement: 'Os resultados do Vale usam limite de 0,10 dentro de cada família; o ajuste global dos 98 testes é mostrado apenas na camada técnica.',
      },
      sources: Object.values(selection.sourceCatalog),
    },
    scopeVariants,
  }
  assertPublicBundle(bundle, allowlist)
  const bundleBytes = serializeJson(bundle)
  const registry = {
    schemaVersion: 'vocacoes-pne-advanced-insights-registry-v1',
    publicationStatus: 'official',
    regionSlug: selection.scope.regionSlug,
    bundlePath: './vocacoesPneAdvancedInsightsValeDoSinos.json',
    bundleSha256: sha256Bytes(bundleBytes),
    bundleByteSize: Buffer.byteLength(bundleBytes),
    contentVersion,
    selectionSha256: selectionHash,
    allowlistSha256: allowlistHash,
    sourceManifestSha256: manifestHash,
    sourceArtifactSetDigestSha256: manifest.artifactSetDigestSha256,
    expandedAnalysisEvidenceSha256: expandedAnalysisEvidenceHash,
    relationshipAtlasArtifactSetDigestSha256,
    canonicalMunicipalityCount: municipalities.length,
    advancedMunicipalityIbgeCodes: selection.scope.advancedMunicipalityIbgeCodes,
    readingCount: bundle.scopeVariants.region.readings.length,
    agendaCount: bundle.scopeVariants.region.agendas.length,
    fallbackContract: 'vocacoes-pne-official-promotion-v1',
    generatedAt: bundle.generatedAt,
  }
  const registryBytes = serializeJson(registry)
  assertRegistry(
    registry,
    bundleBytes,
    bundle,
    selectionHash,
    allowlistHash,
    manifestHash,
    expandedAnalysisEvidenceHash,
    relationshipAtlasArtifactSetDigestSha256,
  )
  return {
    bundle,
    registry,
    bundleBytes,
    registryBytes,
    paths: {
      bundle: path.join(repoRoot, BUNDLE_RELATIVE_PATH),
      registry: path.join(repoRoot, REGISTRY_RELATIVE_PATH),
    },
  }
}

async function exists(filePath) {
  try {
    await access(filePath)
    return true
  } catch {
    return false
  }
}

export async function checkVocacoesPneAdvancedPublication(repoRoot = DEFAULT_REPO_ROOT) {
  const materialized = await materializeVocacoesPneAdvancedPublication(repoRoot)
  for (const [kind, expected] of [
    ['bundle', materialized.bundleBytes],
    ['registry', materialized.registryBytes],
  ]) {
    const target = materialized.paths[kind]
    invariant(await exists(target), `arquivo gerado ausente: ${path.relative(repoRoot, target)}`)
    const actual = await readFile(target, 'utf8')
    invariant(actual === expected, `arquivo gerado divergente: ${path.relative(repoRoot, target)}`)
  }
  return materialized
}

export async function promoteVocacoesPneAdvancedPublication(repoRoot = DEFAULT_REPO_ROOT, options = {}) {
  const materialized = await materializeVocacoesPneAdvancedPublication(repoRoot)
  const outputDir = path.dirname(materialized.paths.bundle)
  await mkdir(outputDir, { recursive: true })
  const tempRootParent = path.join(repoRoot, '.tmp', 'vocacoes-pne', 'advanced-analytics-v1')
  await mkdir(tempRootParent, { recursive: true })
  const stageDir = await mkdtemp(path.join(tempRootParent, 'aa5-publication-'))
  const staged = {
    bundle: path.join(stageDir, path.basename(materialized.paths.bundle)),
    registry: path.join(stageDir, path.basename(materialized.paths.registry)),
  }
  const backups = []
  const promoted = []
  try {
    await writeFile(staged.bundle, materialized.bundleBytes, 'utf8')
    await writeFile(staged.registry, materialized.registryBytes, 'utf8')
    const stagedBundle = JSON.parse(await readFile(staged.bundle, 'utf8'))
    const stagedRegistry = JSON.parse(await readFile(staged.registry, 'utf8'))
    assertPublicBundle(stagedBundle, (await loadAndVerifyInputs(repoRoot)).allowlist)
    assertRegistry(
      stagedRegistry,
      await readFile(staged.bundle, 'utf8'),
      stagedBundle,
      stagedRegistry.selectionSha256,
      stagedRegistry.allowlistSha256,
      stagedRegistry.sourceManifestSha256,
      stagedRegistry.expandedAnalysisEvidenceSha256,
      stagedRegistry.relationshipAtlasArtifactSetDigestSha256,
    )

    const promotionOrder = ['bundle', 'registry']
    invariant(promotionOrder.at(-1) === 'registry', 'registro deve ser promovido por último')
    for (const kind of promotionOrder) {
      const target = materialized.paths[kind]
      const desired = kind === 'bundle' ? materialized.bundleBytes : materialized.registryBytes
      if (await exists(target)) {
        const current = await readFile(target, 'utf8')
        if (current === desired) continue
        const backup = `${target}.aa5-backup-${process.pid}`
        await copyFile(target, backup)
        backups.push({ target, backup })
      }
      const next = `${target}.aa5-next-${process.pid}`
      await copyFile(staged[kind], next)
      if (await exists(target)) await rm(target)
      await rename(next, target)
      promoted.push(target)
      if (typeof options.afterPromote === 'function') {
        await options.afterPromote({ kind, target })
      }
    }
  } catch (error) {
    for (const target of promoted.reverse()) {
      await rm(target, { force: true })
    }
    for (const { target, backup } of backups.reverse()) {
      if (await exists(backup)) await rename(backup, target)
    }
    throw error
  } finally {
    for (const { backup } of backups) await rm(backup, { force: true })
    await rm(stageDir, { recursive: true, force: true })
  }
  await checkVocacoesPneAdvancedPublication(repoRoot)
  return materialized
}

export const VOCACOES_PNE_AA5_PATHS = Object.freeze({
  selection: SELECTION_RELATIVE_PATH,
  allowlist: ALLOWLIST_RELATIVE_PATH,
  bundle: BUNDLE_RELATIVE_PATH,
  registry: REGISTRY_RELATIVE_PATH,
})
