export type VocacoesPneEvidenceFormat =
  | 'integer'
  | 'decimal1'
  | 'percent1'
  | 'percentage_points1'

export type VocacoesPneEvidenceAvailability =
  | 'observed'
  | 'observed_zero'
  | 'calculated'
  | 'estimated_range'

export interface VocacoesPneAdvancedEvidence {
  readonly label: string
  readonly value: number
  readonly valueTo?: number
  readonly valueKind: 'point' | 'change' | 'interval'
  readonly format: VocacoesPneEvidenceFormat
  readonly unit: string
  readonly period: string
  readonly contextLabel: string
  readonly availability: VocacoesPneEvidenceAvailability
  readonly startValue?: number
  readonly endValue?: number
}

export type VocacoesPneAnalysisCheckStatus =
  | 'consistent'
  | 'watch'
  | 'not_confirmed'
  | 'not_comparable'

export interface VocacoesPneAnalysisCheck {
  readonly status: VocacoesPneAnalysisCheckStatus
  readonly label: string
  readonly title: string
  readonly scopeLabel: string
  readonly scopeDisclosure: string
  readonly summary: string
  readonly planningMeaning: string
  readonly details: readonly string[]
  readonly sources: readonly string[]
}

export interface VocacoesPneAdvancedReading {
  readonly id: string
  readonly order: number
  readonly theme: string
  readonly title: string
  readonly question: string
  readonly conclusion: string
  readonly territorialReading: string
  readonly evidenceClass: {
    readonly kind: 'accounting' | 'contextual' | 'distributional' | 'monitoring' | 'boundary'
    readonly label: string
    readonly explanation: string
  }
  readonly evidence: readonly VocacoesPneAdvancedEvidence[]
  readonly comparisonNote: string
  readonly analysisCheck: VocacoesPneAnalysisCheck
  readonly visualKind: 'decomposition' | 'benchmark' | 'range' | 'stage-change' | 'parallel-change'
  readonly mechanism: {
    readonly summary: string
    readonly expectedPattern: string
    readonly alternatives: readonly string[]
    readonly boundary: string
  }
  readonly planning: {
    readonly question: string
    readonly implication: string
    readonly indicators: readonly string[]
  }
  readonly limit: string
  readonly sources: readonly string[]
}

export interface VocacoesPneAdvancedAgenda {
  readonly id: string
  readonly order: number
  readonly title: string
  readonly status: string
  readonly whyNow: string
  readonly action: string
  readonly educationStage: string
  readonly exposedPopulation: string
  readonly responsibility: {
    readonly level: string
    readonly lead: string
    readonly contributors: readonly string[]
  }
  readonly indicators: readonly string[]
  readonly trigger: string
  readonly cadence: string
  readonly strengthenIf: string
  readonly weakenIf: string
  readonly relatedReadingId: string
}

export interface VocacoesPneAdvancedTransversal {
  readonly id: string
  readonly title: string
  readonly interpretation: string
  readonly evidence: readonly VocacoesPneAdvancedEvidence[]
  readonly planningQuestion: string
  readonly limit: string
  readonly sources: readonly string[]
  readonly analysisCheck?: VocacoesPneAnalysisCheck
}

export interface VocacoesPneRelationshipAtlasSummary {
  readonly testedRelationships: 98
  readonly robustRows: 6
  readonly robustMechanisms: 1
  readonly notRobustRows: 28
  readonly insufficientRows: 61
  readonly descriptiveRows: 2
  readonly blockedRows: 1
  readonly statement: string
  readonly familyThresholdStatement: string
}

export interface VocacoesPneAdvancedScopeVariant {
  readonly entityType: 'region' | 'municipality'
  readonly entityName: string
  readonly municipalityIbgeCode: string | null
  readonly headline: string
  readonly standfirst: string
  readonly containmentDisclosure: string
  readonly decisionSignals: readonly {
    readonly title: string
    readonly text: string
  }[]
  readonly readings: readonly VocacoesPneAdvancedReading[]
  readonly agendas: readonly VocacoesPneAdvancedAgenda[]
  readonly transversal: readonly VocacoesPneAdvancedTransversal[]
}

export interface VocacoesPneAdvancedBundle {
  readonly schemaVersion: 'vocacoes-pne-advanced-insights-v1'
  readonly contentVersion: string
  readonly publicationStatus: 'official'
  readonly generatedAt: string
  readonly region: {
    readonly id: string
    readonly slug: 'vale-do-sinos'
    readonly name: string
    readonly stateCode: 'RS'
    readonly municipalityCount: 10
    readonly municipalities: readonly {
      readonly ibgeCode: string
      readonly name: string
      readonly slug: string
    }[]
    readonly advancedMunicipalityIbgeCodes: readonly ['4313375']
  }
  readonly methodology: {
    readonly educationNetworkScope: 'total_all_dependencies'
    readonly municipalIdentity: string
    readonly readingDirections: readonly {
      readonly label: string
      readonly description: string
    }[]
    readonly evidenceStatement: string
    readonly availabilityStatement: string
    readonly causalityStatement: string
    readonly relationshipAtlas: VocacoesPneRelationshipAtlasSummary
    readonly sources: readonly string[]
  }
  readonly scopeVariants: {
    readonly region: VocacoesPneAdvancedScopeVariant
    readonly novaSantaRita: VocacoesPneAdvancedScopeVariant
  }
}

export interface VocacoesPneAdvancedRegistry {
  readonly schemaVersion: 'vocacoes-pne-advanced-insights-registry-v1'
  readonly publicationStatus: 'official'
  readonly regionSlug: 'vale-do-sinos'
  readonly bundlePath: './vocacoesPneAdvancedInsightsValeDoSinos.json'
  readonly bundleSha256: string
  readonly bundleByteSize: number
  readonly contentVersion: string
  readonly selectionSha256: string
  readonly allowlistSha256: string
  readonly sourceManifestSha256: string
  readonly sourceArtifactSetDigestSha256: string
  readonly expandedAnalysisEvidenceSha256: string
  readonly relationshipAtlasArtifactSetDigestSha256: string
  readonly canonicalMunicipalityCount: 10
  readonly advancedMunicipalityIbgeCodes: readonly ['4313375']
  readonly readingCount: 5
  readonly agendaCount: 4
  readonly fallbackContract: 'vocacoes-pne-official-promotion-v1'
  readonly generatedAt: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function invariant(condition: unknown, label: string): asserts condition {
  if (!condition) throw new TypeError(`Leitura avançada Vocações × PNE inválida: ${label}.`)
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function assertEvidence(raw: unknown): asserts raw is VocacoesPneAdvancedEvidence {
  invariant(isRecord(raw), 'evidência')
  invariant(isNonEmptyString(raw.label), 'rótulo da evidência')
  invariant(typeof raw.value === 'number' && Number.isFinite(raw.value), 'valor da evidência')
  invariant(raw.valueTo === undefined || (typeof raw.valueTo === 'number' && Number.isFinite(raw.valueTo)), 'limite da evidência')
  invariant(['point', 'change', 'interval'].includes(String(raw.valueKind)), 'tipo de valor')
  invariant(['integer', 'decimal1', 'percent1', 'percentage_points1'].includes(String(raw.format)), 'formato de valor')
  invariant(isNonEmptyString(raw.unit), 'unidade da evidência')
  invariant(isNonEmptyString(raw.period), 'período da evidência')
  invariant(isNonEmptyString(raw.contextLabel), 'contexto da evidência')
  invariant(['observed', 'observed_zero', 'calculated', 'estimated_range'].includes(String(raw.availability)), 'disponibilidade da evidência')
  invariant(raw.startValue === undefined || (typeof raw.startValue === 'number' && Number.isFinite(raw.startValue)), 'valor inicial')
  invariant(raw.endValue === undefined || (typeof raw.endValue === 'number' && Number.isFinite(raw.endValue)), 'valor final')
  if (raw.availability === 'observed_zero') invariant(raw.value === 0, 'zero observado deve valer zero')
}

function assertStringArray(raw: unknown, label: string): asserts raw is string[] {
  invariant(Array.isArray(raw) && raw.length > 0 && raw.every(isNonEmptyString), label)
}

function assertAnalysisCheck(raw: unknown, label: string): asserts raw is VocacoesPneAnalysisCheck {
  invariant(isRecord(raw), `${label}.verificação adicional`)
  invariant(
    ['consistent', 'watch', 'not_confirmed', 'not_comparable'].includes(String(raw.status)),
    `${label}.estado da verificação adicional`,
  )
  for (const key of ['label', 'title', 'scopeLabel', 'scopeDisclosure', 'summary', 'planningMeaning']) {
    invariant(isNonEmptyString(raw[key]), `${label}.verificação adicional.${key}`)
  }
  assertStringArray(raw.details, `${label}.detalhes da verificação adicional`)
  invariant(raw.details.length >= 2, `${label}.ao menos dois detalhes da verificação adicional`)
  assertStringArray(raw.sources, `${label}.fontes da verificação adicional`)
}

function assertScopeVariant(raw: unknown, entityType: 'region' | 'municipality'): asserts raw is VocacoesPneAdvancedScopeVariant {
  invariant(isRecord(raw), `variante ${entityType}`)
  invariant(raw.entityType === entityType, `tipo da variante ${entityType}`)
  invariant(isNonEmptyString(raw.entityName), 'nome do recorte')
  invariant(entityType === 'region' ? raw.municipalityIbgeCode === null : raw.municipalityIbgeCode === '4313375', 'identidade do recorte')
  for (const key of ['headline', 'standfirst', 'containmentDisclosure']) {
    invariant(isNonEmptyString(raw[key]), key)
  }
  invariant(Array.isArray(raw.decisionSignals) && raw.decisionSignals.length === 3, 'três sinais de decisão')
  invariant(raw.decisionSignals.every((item) => isRecord(item) && isNonEmptyString(item.title) && isNonEmptyString(item.text)), 'sinais de decisão completos')
  invariant(Array.isArray(raw.readings) && raw.readings.length === 5, 'cinco leituras públicas')
  const readingIds = new Set<string>()
  for (const reading of raw.readings) {
    invariant(isRecord(reading), 'leitura pública')
    invariant(isNonEmptyString(reading.id) && !readingIds.has(reading.id), 'id único de leitura')
    readingIds.add(reading.id)
    invariant(typeof reading.order === 'number' && Number.isInteger(reading.order), 'ordem de leitura')
    for (const key of ['theme', 'title', 'question', 'conclusion', 'territorialReading', 'comparisonNote', 'limit']) {
      invariant(isNonEmptyString(reading[key]), `leitura.${key}`)
    }
    invariant(isNonEmptyString(reading.comparisonNote), 'leitura.comparisonNote')
    invariant(/(?:Rio Grande do Sul|estadual)/iu.test(reading.comparisonNote), 'comparador estadual incluído ou indisponibilidade justificada')
    invariant(isRecord(reading.evidenceClass), 'classe de evidência')
    invariant(['accounting', 'contextual', 'distributional', 'monitoring', 'boundary'].includes(String(reading.evidenceClass.kind)), 'tipo da classe de evidência')
    invariant(isNonEmptyString(reading.evidenceClass.label) && isNonEmptyString(reading.evidenceClass.explanation), 'classe de evidência completa')
    invariant(Array.isArray(reading.evidence) && reading.evidence.length >= 2 && reading.evidence.length <= 3, 'duas ou três evidências')
    reading.evidence.forEach(assertEvidence)
    invariant(isRecord(reading.analysisCheck), 'verificação adicional')
    invariant(
      ['consistent', 'watch', 'not_confirmed', 'not_comparable'].includes(String(reading.analysisCheck.status)),
      'estado da verificação adicional',
    )
    for (const key of ['label', 'title', 'scopeLabel', 'scopeDisclosure', 'summary', 'planningMeaning']) {
      invariant(isNonEmptyString(reading.analysisCheck[key]), `verificação adicional.${key}`)
    }
    assertStringArray(reading.analysisCheck.details, 'detalhes da verificação adicional')
    invariant(reading.analysisCheck.details.length >= 2, 'ao menos dois detalhes da verificação adicional')
    assertStringArray(reading.analysisCheck.sources, 'fontes da verificação adicional')
    invariant(['decomposition', 'benchmark', 'range', 'stage-change', 'parallel-change'].includes(String(reading.visualKind)), 'visual compatível')
    invariant(isRecord(reading.mechanism), 'mecanismo')
    invariant(isNonEmptyString(reading.mechanism.summary), 'síntese do mecanismo')
    invariant(isNonEmptyString(reading.mechanism.expectedPattern), 'padrão esperado')
    assertStringArray(reading.mechanism.alternatives, 'explicações alternativas')
    invariant(isNonEmptyString(reading.mechanism.boundary), 'fronteira do mecanismo')
    invariant(isRecord(reading.planning), 'implicação de planejamento')
    invariant(isNonEmptyString(reading.planning.question) && isNonEmptyString(reading.planning.implication), 'questão de planejamento')
    assertStringArray(reading.planning.indicators, 'indicadores de acompanhamento')
    assertStringArray(reading.sources, 'fontes da leitura')
  }
  invariant(Array.isArray(raw.agendas) && raw.agendas.length === 4, 'quatro agendas públicas')
  const agendaIds = new Set<string>()
  for (const agenda of raw.agendas) {
    invariant(isRecord(agenda), 'agenda pública')
    invariant(isNonEmptyString(agenda.id) && !agendaIds.has(agenda.id), 'id único de agenda')
    agendaIds.add(agenda.id)
    invariant(typeof agenda.order === 'number' && Number.isInteger(agenda.order), 'ordem da agenda')
    for (const key of ['title', 'status', 'whyNow', 'action', 'educationStage', 'exposedPopulation', 'trigger', 'cadence', 'strengthenIf', 'weakenIf', 'relatedReadingId']) {
      invariant(isNonEmptyString(agenda[key]), `agenda.${key}`)
    }
    invariant(isNonEmptyString(agenda.relatedReadingId), 'agenda.relatedReadingId')
    invariant(readingIds.has(agenda.relatedReadingId), 'agenda ligada a leitura pública')
    invariant(isRecord(agenda.responsibility), 'responsabilidade da agenda')
    invariant(isNonEmptyString(agenda.responsibility.level) && isNonEmptyString(agenda.responsibility.lead), 'responsável da agenda')
    assertStringArray(agenda.responsibility.contributors, 'contribuintes da agenda')
    assertStringArray(agenda.indicators, 'indicadores da agenda')
  }
  invariant(Array.isArray(raw.transversal) && raw.transversal.length === 3, 'três contextos transversais')
  for (const item of raw.transversal) {
    invariant(isRecord(item), 'contexto transversal')
    for (const key of ['id', 'title', 'interpretation', 'planningQuestion', 'limit']) {
      invariant(isNonEmptyString(item[key]), `transversal.${key}`)
    }
    invariant(Array.isArray(item.evidence) && item.evidence.length === 2, 'duas evidências transversais')
    item.evidence.forEach(assertEvidence)
    assertStringArray(item.sources, 'fontes transversais')
    if (item.analysisCheck !== undefined) assertAnalysisCheck(item.analysisCheck, `transversal.${item.id}`)
  }
}

export function assertVocacoesPneAdvancedBundle(raw: unknown): asserts raw is VocacoesPneAdvancedBundle {
  invariant(isRecord(raw), 'bundle')
  invariant(raw.schemaVersion === 'vocacoes-pne-advanced-insights-v1', 'schemaVersion')
  invariant(raw.publicationStatus === 'official', 'status oficial')
  invariant(typeof raw.contentVersion === 'string' && /^[a-f0-9]{64}$/u.test(raw.contentVersion), 'contentVersion')
  invariant(isNonEmptyString(raw.generatedAt), 'data de geração')
  invariant(isRecord(raw.region), 'região')
  invariant(raw.region.id === 'REGION_VALE_DO_SINOS', 'id regional')
  invariant(raw.region.slug === 'vale-do-sinos' && raw.region.stateCode === 'RS', 'identidade regional')
  invariant(raw.region.municipalityCount === 10, 'contagem municipal')
  invariant(Array.isArray(raw.region.municipalities) && raw.region.municipalities.length === 10, 'dez municípios')
  const codes = raw.region.municipalities.map((item) => {
    invariant(isRecord(item), 'registro municipal')
    invariant(typeof item.ibgeCode === 'string' && /^43\d{5}$/u.test(item.ibgeCode), 'IBGE textual')
    invariant(isNonEmptyString(item.name) && isNonEmptyString(item.slug), 'apresentação municipal')
    return item.ibgeCode
  })
  invariant(new Set(codes).size === 10 && codes.includes('4313375'), 'universo municipal reconciliado')
  invariant(Array.isArray(raw.region.advancedMunicipalityIbgeCodes) && raw.region.advancedMunicipalityIbgeCodes.length === 1 && raw.region.advancedMunicipalityIbgeCodes[0] === '4313375', 'município avançado')
  invariant(isRecord(raw.methodology), 'metodologia')
  invariant(raw.methodology.educationNetworkScope === 'total_all_dependencies', 'universo educacional')
  invariant(isNonEmptyString(raw.methodology.municipalIdentity), 'identidade metodológica')
  invariant(Array.isArray(raw.methodology.readingDirections) && raw.methodology.readingDirections.length === 2, 'duas direções de leitura')
  for (const key of ['evidenceStatement', 'availabilityStatement', 'causalityStatement']) {
    invariant(isNonEmptyString(raw.methodology[key]), `metodologia.${key}`)
  }
  invariant(isRecord(raw.methodology.relationshipAtlas), 'resumo do atlas relacional')
  const atlas = raw.methodology.relationshipAtlas
  invariant(atlas.testedRelationships === 98, '98 relações avaliadas')
  invariant(atlas.robustRows === 6 && atlas.robustMechanisms === 1, 'seis linhas em um mecanismo')
  invariant(atlas.notRobustRows === 28 && atlas.insufficientRows === 61, 'resultados negativos e insuficientes')
  invariant(atlas.descriptiveRows === 2 && atlas.blockedRows === 1, 'resultados descritivos e bloqueados')
  invariant(isNonEmptyString(atlas.statement) && isNonEmptyString(atlas.familyThresholdStatement), 'texto do atlas relacional')
  assertStringArray(raw.methodology.sources, 'fontes metodológicas')
  invariant(isRecord(raw.scopeVariants), 'variantes de recorte')
  assertScopeVariant(raw.scopeVariants.region, 'region')
  assertScopeVariant(raw.scopeVariants.novaSantaRita, 'municipality')
}

export function assertVocacoesPneAdvancedRegistry(raw: unknown): asserts raw is VocacoesPneAdvancedRegistry {
  invariant(isRecord(raw), 'registro')
  invariant(raw.schemaVersion === 'vocacoes-pne-advanced-insights-registry-v1', 'schemaVersion do registro')
  invariant(raw.publicationStatus === 'official' && raw.regionSlug === 'vale-do-sinos', 'identidade do registro')
  invariant(raw.bundlePath === './vocacoesPneAdvancedInsightsValeDoSinos.json', 'path do bundle')
  for (const key of ['bundleSha256', 'contentVersion', 'selectionSha256', 'allowlistSha256', 'sourceManifestSha256', 'sourceArtifactSetDigestSha256', 'expandedAnalysisEvidenceSha256', 'relationshipAtlasArtifactSetDigestSha256']) {
    invariant(typeof raw[key] === 'string' && /^[a-f0-9]{64}$/u.test(raw[key]), `registro.${key}`)
  }
  invariant(typeof raw.bundleByteSize === 'number' && Number.isInteger(raw.bundleByteSize) && raw.bundleByteSize > 0, 'tamanho do bundle')
  invariant(raw.canonicalMunicipalityCount === 10, 'cobertura do registro')
  invariant(Array.isArray(raw.advancedMunicipalityIbgeCodes) && raw.advancedMunicipalityIbgeCodes.length === 1 && raw.advancedMunicipalityIbgeCodes[0] === '4313375', 'cobertura municipal avançada')
  invariant(raw.readingCount === 5 && raw.agendaCount === 4, 'contagens do registro')
  invariant(raw.fallbackContract === 'vocacoes-pne-official-promotion-v1', 'fallback registrado')
  invariant(isNonEmptyString(raw.generatedAt), 'data do registro')
}

export function resolveVocacoesPneAdvancedScope(
  bundle: VocacoesPneAdvancedBundle,
  municipalityId: string | null,
): VocacoesPneAdvancedScopeVariant {
  if (municipalityId === null) return bundle.scopeVariants.region
  if (municipalityId === '4313375') return bundle.scopeVariants.novaSantaRita
  throw new TypeError('Leitura avançada: município ainda não possui dossiê público próprio.')
}

export function isVocacoesPneAdvancedScopeSupported(municipalityId: string | null): boolean {
  return municipalityId === null || municipalityId === '4313375'
}
