export type CenariosEducacaoEvidenceClass =
  | 'OBSERVED'
  | 'ACCOUNTING_DERIVATION'
  | 'VALIDATED_ENVELOPE'
  | 'SCENARIO_ASSUMPTION'
  | 'NORMATIVE_CHOICE'

export type CenariosEducacaoAvailability =
  | 'observed'
  | 'observed_zero'
  | 'calculated'
  | 'estimated_range'
  | 'null'
  | 'unavailable'
  | 'suppressed'
  | 'not_applicable'

export type CenariosEducacaoDriverMaturity =
  | 'OBSERVED_PUBLIC_SENTINEL'
  | 'OBSERVED_SERIES'
  | 'OBSERVED_RECONCILED_CONTEXT'
  | 'EXPLICIT_GAP'

export type CenariosEducacaoPneStatus =
  | 'SUPPORTED'
  | 'PRESSURED'
  | 'AMBIGUOUS'
  | 'INSUFFICIENT_EVIDENCE'

export type CenariosEducacaoActionType =
  | 'NO_REGRET'
  | 'CONTINGENT'
  | 'REVERSIBLE_EXPERIMENT'

export type CenariosEducacaoAuthority = 'MUNICIPAL' | 'SHARED' | 'EXTERNAL'

export interface CenariosEducacaoSourceDescriptor {
  readonly path: string
  readonly sha256: string
  readonly byteSize: number
}

export interface CenariosEducacaoDriverCoverage {
  readonly status: string
  readonly municipalityCount: number
  readonly expectedMunicipalityCount: number
  readonly sourceFileCount: number
  readonly reconciledMunicipalityCount?: number
}

export interface CenariosEducacaoTechnologyValue {
  readonly numerator: number
  readonly denominator: number
  readonly valueRaw: number | null
}

export interface CenariosEducacaoTechnologyMetric {
  readonly metricId: string
  readonly label: string
  readonly period: string
  readonly unit: 'percent_of_schools'
  readonly region: CenariosEducacaoTechnologyValue
  readonly novaSantaRita: CenariosEducacaoTechnologyValue
}

export interface CenariosEducacaoCrossCuttingDriver {
  readonly driverId: 'X_CLIMATE' | 'X_TECHNOLOGY' | 'X_FISCAL' | 'X_REGULATION'
  readonly label: string
  readonly maturity: CenariosEducacaoDriverMaturity
  readonly evidenceClass: CenariosEducacaoEvidenceClass
  readonly availability: CenariosEducacaoAvailability
  readonly evidencePlan: string
  readonly claimCeiling: string
  readonly unresolvedGap: string
  readonly scenarioUse: string
  readonly period: string
  readonly lens: string
  readonly coverage: CenariosEducacaoDriverCoverage
  readonly sourceRefs: readonly string[]
  readonly calculation?: Readonly<Record<string, string | number | null>>
  readonly metrics?: readonly CenariosEducacaoTechnologyMetric[]
  readonly proxyAudit?: {
    readonly excludedMeasureId: string
    readonly municipalitiesWithExcludedProxy: number
    readonly eligiblePublicEvidenceCount: number
    readonly exclusionReason: string
  }
}

export interface CenariosEducacaoFactorState {
  readonly stateId: string
  readonly label: string
  readonly definition: string
}

export interface CenariosEducacaoFactor {
  readonly factorId: string
  readonly label: string
  readonly uncertainty: string
  readonly states: readonly CenariosEducacaoFactorState[]
}

export interface CenariosEducacaoDomain {
  readonly domainId: string
  readonly label: string
}

export interface CenariosEducacaoDistributionalEffect {
  readonly publicId: string
  readonly publicLabel: string
  readonly evidenceClass: CenariosEducacaoEvidenceClass
  readonly exposure: string
  readonly potentialUpside: string
  readonly potentialDownside: string
  readonly equityQuestion: string
  readonly evidenceRefs: readonly string[]
}

export interface CenariosEducacaoRegionalDependency {
  readonly dependencyId: string
  readonly label: string
  readonly mechanism: string
  readonly authority: CenariosEducacaoAuthority
  readonly evidenceClass: CenariosEducacaoEvidenceClass
  readonly evidenceRefs: readonly string[]
}

export interface CenariosEducacaoScenarioDomain {
  readonly domainId: string
  readonly state: string
  readonly mechanism: string
  readonly regionalImplication: string
  readonly novaSantaRitaExposure: string
}

export interface CenariosEducacaoPneImpact {
  readonly clusterId: string
  readonly status: CenariosEducacaoPneStatus
  readonly mechanism: string
  readonly response: string
}

export interface CenariosEducacaoSentinel {
  readonly indicatorId: string
  readonly label: string
  readonly availability: CenariosEducacaoAvailability
  readonly cadence: string
  readonly decisionUse: string
}

export interface CenariosEducacaoScenario {
  readonly scenarioId: string
  readonly order: number
  readonly title: string
  readonly shortLabel: string
  readonly status: 'EXPLORATORY_NON_PROBABILISTIC'
  readonly configurationStates: Readonly<Record<string, string>>
  readonly summary: string
  readonly causalChain: readonly string[]
  readonly opportunities: readonly string[]
  readonly risks: readonly string[]
  readonly tradeOffs: readonly string[]
  readonly distributionalEffects: readonly CenariosEducacaoDistributionalEffect[]
  readonly regionalDependencies: readonly CenariosEducacaoRegionalDependency[]
  readonly limitations: readonly string[]
  readonly domains: readonly CenariosEducacaoScenarioDomain[]
  readonly assumptions: readonly string[]
  readonly falsifiers: readonly string[]
  readonly sentinelIndicatorIds: readonly string[]
  readonly evidenceRefs: readonly string[]
  readonly pneImpacts: readonly CenariosEducacaoPneImpact[]
  readonly sentinelIndicators: readonly CenariosEducacaoSentinel[]
}

export interface CenariosEducacaoMunicipalExposure {
  readonly scenarioId: string
  readonly headline: string
  readonly exposures: {
    readonly demographic: string
    readonly educational: string
    readonly economic: string
    readonly social: string
    readonly territorial: string
  }
  readonly regionalDependencies: readonly string[]
  readonly leverIds: readonly string[]
  readonly evidenceRefs: readonly string[]
}

export interface CenariosEducacaoMunicipality {
  readonly municipalityIbgeCode: '4313375'
  readonly municipalityName: 'Nova Santa Rita'
  readonly diagnosticBridgeRoute: '#vocacoes-regiao'
  readonly diagnosticEvidenceRefs: readonly string[]
  readonly scenarioExposures: readonly CenariosEducacaoMunicipalExposure[]
  readonly localSignalIds: readonly string[]
  readonly limitations: readonly string[]
  readonly smallNumberCaveat: string
}

export interface CenariosEducacaoAction {
  readonly actionId: string
  readonly type: CenariosEducacaoActionType
  readonly title: string
  readonly description: string
  readonly authority: CenariosEducacaoAuthority
  readonly trigger: string
  readonly lockInRisk: string
}

export interface CenariosEducacaoPneGoal {
  readonly goalId: string
  readonly title: string
  readonly valueRaw: string | null
  readonly referenceRaw: string | null
  readonly unit: string | null
  readonly year: string | number | null
  readonly severity: string | null
  readonly availability: CenariosEducacaoAvailability
  readonly evidenceClass: 'OBSERVED'
  readonly evidenceRef: string
}

export interface CenariosEducacaoPneCluster {
  readonly clusterId: string
  readonly label: string
  readonly goalIds: readonly string[]
}

export interface CenariosEducacaoBundle {
  readonly schemaVersion: 'vocacoes-pne-foresight-v2'
  readonly contentVersion: string
  readonly publicationStatus: 'exploratory_model_public_data_audited'
  readonly generatedAt: string
  readonly title: string
  readonly publicLabel: string
  readonly region: {
    readonly stateCode: 'RS'
    readonly slug: 'vale-do-sinos'
    readonly name: string
    readonly municipalityCount: 10
  }
  readonly horizons: {
    readonly baselineLabel: string
    readonly checkpoint: string
    readonly scenarioHorizon: string
    readonly checkpointRule: string
  }
  readonly publicationPolicy: {
    readonly status: 'exploratory_model_public_data_audited'
    readonly publicLabel: string
    readonly validationGate: string
    readonly equalScenarioWeight: true
    readonly futureProbabilitiesAllowed: false
    readonly futureNumericClaimsAllowedOnlyAsValidatedEnvelope: true
    readonly automaticRecommendationAllowed: false
    readonly institutionalValidationClaimAllowed: false
  }
  readonly evidencePolicy: {
    readonly classes: readonly CenariosEducacaoEvidenceClass[]
    readonly availabilityStates: readonly CenariosEducacaoAvailability[]
    readonly municipalSmallNumberCaveat: string
    readonly residualGuard: string
    readonly observedZeroGuard: string
    readonly administrativeRegisterGuard: string
    readonly crossCuttingMaturityRule: string
  }
  readonly diagnosticBridge: {
    readonly canonicalSection: string
    readonly route: '#vocacoes-regiao'
    readonly boundary: string
    readonly sourceBundle: CenariosEducacaoSourceDescriptor
    readonly sourceRegistry: CenariosEducacaoSourceDescriptor
    readonly evidenceRefs: readonly string[]
    readonly evidenceRefCount: number
    readonly resolvedEvidenceRefCount: number
    readonly copiedDiagnosticAssertions: 0
    readonly deDuplicationAudit: {
      readonly status: 'passed'
      readonly normalization: string
      readonly minimumLength: 80
      readonly whitelist: readonly string[]
      readonly comparedScenarioStringCount: number
      readonly comparedDiagnosticStringCount: number
      readonly duplicateCount: 0
      readonly scope: readonly string[]
    }
  }
  readonly sourceSnapshot: {
    readonly authoringContract: CenariosEducacaoSourceDescriptor
    readonly advancedBundle: CenariosEducacaoSourceDescriptor
    readonly advancedRegistry: CenariosEducacaoSourceDescriptor
    readonly regionConfig: CenariosEducacaoSourceDescriptor
    readonly municipalityRegistry: CenariosEducacaoSourceDescriptor
    readonly focalPneMunicipalMatrix: CenariosEducacaoSourceDescriptor
    readonly regionalPublicInputs: {
      readonly schemaVersion: 'cenarios-educacao-regional-public-inputs-v1'
      readonly sha256: string
      readonly fileCount: 30
      readonly municipalityCount: 10
      readonly coverage: {
        readonly details: 10
        readonly finance: 10
        readonly pneMatrix: 10
      }
      readonly pathPatterns: readonly string[]
    }
    readonly advancedSourceManifestSha256: string
    readonly advancedSourceArtifactSetDigestSha256: string
  }
  readonly domainRegistry: readonly CenariosEducacaoDomain[]
  readonly factorRegistry: readonly CenariosEducacaoFactor[]
  readonly crossCuttingDrivers: readonly CenariosEducacaoCrossCuttingDriver[]
  readonly crossImpactMatrix: readonly Readonly<Record<string, string>>[]
  readonly morphologicalField: {
    readonly requiredMinimumPairwiseHammingDistance: number
    readonly minimumObservedPairwiseHammingDistance: number
    readonly pairwiseDistances: readonly {
      readonly leftScenarioId: string
      readonly rightScenarioId: string
      readonly distance: number
    }[]
    readonly blindSubstitutabilityReview: {
      readonly status: string
      readonly method: string
      readonly signatures: readonly {
        readonly scenarioId: string
        readonly sha256: string
      }[]
    }
  }
  readonly scenarios: readonly CenariosEducacaoScenario[]
  readonly municipalities: readonly CenariosEducacaoMunicipality[]
  readonly pneStressTest: {
    readonly normativeSeparation: string
    readonly municipalityIbgeCode: '4313375'
    readonly goalBaseline: readonly CenariosEducacaoPneGoal[]
    readonly clusters: readonly CenariosEducacaoPneCluster[]
    readonly scenarioAssessments: readonly {
      readonly scenarioId: string
      readonly impacts: readonly CenariosEducacaoPneImpact[]
    }[]
  }
  readonly actions: readonly CenariosEducacaoAction[]
  readonly sentinelIndicators: readonly CenariosEducacaoSentinel[]
  readonly sourceGovernance: {
    readonly publicDataOnly: true
    readonly localFirst: true
    readonly downloadPolicy: string
    readonly publicationBoundary: string
    readonly deduplicationPolicy: {
      readonly normalization: string
      readonly minimumLength: 80
      readonly whitelist: readonly string[]
    }
  }
  readonly methodology: {
    readonly scenarioType: 'EXPLORATORY_ALTERNATIVE_FUTURES'
    readonly selectionMethod: string
    readonly notForecast: string
    readonly aa4Role: string
    readonly independentReviewPolicy: string
  }
  readonly qualityGate: {
    readonly status: 'passed'
    readonly publicDataOnly: true
    readonly localInputsOnly: true
    readonly networkDownloadUsed: false
    readonly databaseUsed: false
    readonly regionalMunicipalityCoverage: {
      readonly expected: 10
      readonly details: 10
      readonly finance: 10
      readonly pneMatrix: 10
    }
    readonly provenanceReferenceCount: number
    readonly unresolvedProvenanceReferenceCount: 0
    readonly diagnosticDuplicateCount: 0
    readonly institutionalValidationClaimAllowed: false
  }
}

export interface CenariosEducacaoRegistry {
  readonly schemaVersion: 'vocacoes-pne-foresight-registry-v2'
  readonly publicationStatus: 'exploratory_model_public_data_audited'
  readonly publicDataValidationStatus: 'passed'
  readonly regionSlug: 'vale-do-sinos'
  readonly regionalMunicipalityCount: 10
  readonly focalMunicipalityIbgeCode: '4313375'
  readonly bundlePath: './cenariosEducacaoValeDoSinos.json'
  readonly bundleSha256: string
  readonly bundleByteSize: number
  readonly contentVersion: string
  readonly scenarioCount: 4
  readonly domainCount: 6
  readonly factorCount: 5
  readonly minimumPairwiseHammingDistance: number
  readonly diagnosticDuplicateCount: 0
  readonly authoringContractSha256: string
  readonly advancedBundleSha256: string
  readonly advancedRegistrySha256: string
  readonly focalPneMunicipalMatrixSha256: string
  readonly regionalPublicInputsSha256: string
  readonly generatedAt: string
}

const DRIVER_IDS = ['X_CLIMATE', 'X_TECHNOLOGY', 'X_FISCAL', 'X_REGULATION'] as const
const DRIVER_MATURITY: Readonly<Record<(typeof DRIVER_IDS)[number], CenariosEducacaoDriverMaturity>> = {
  X_CLIMATE: 'OBSERVED_PUBLIC_SENTINEL',
  X_TECHNOLOGY: 'OBSERVED_SERIES',
  X_FISCAL: 'OBSERVED_RECONCILED_CONTEXT',
  X_REGULATION: 'EXPLICIT_GAP',
}

function invariant(condition: unknown, message: string): asserts condition {
  if (!condition) throw new TypeError('Cenários da Educação: ' + message + '.')
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function isSha256(value: unknown): value is string {
  return typeof value === 'string' && /^[a-f0-9]{64}$/u.test(value)
}

function assertSourceDescriptor(value: unknown, label: string): asserts value is CenariosEducacaoSourceDescriptor {
  invariant(isRecord(value), 'descritor de ' + label)
  invariant(isNonEmptyString(value.path), 'path de ' + label)
  invariant(isSha256(value.sha256), 'hash de ' + label)
  invariant(Number.isInteger(value.byteSize) && Number(value.byteSize) > 0, 'tamanho de ' + label)
}

function hammingDistance(
  left: Record<string, unknown>,
  right: Record<string, unknown>,
  factorIds: readonly string[],
): number {
  return factorIds.reduce((distance, factorId) => distance + Number(left[factorId] !== right[factorId]), 0)
}

export function assertCenariosEducacaoBundle(raw: unknown): asserts raw is CenariosEducacaoBundle {
  invariant(isRecord(raw), 'bundle inválido')
  invariant(raw.schemaVersion === 'vocacoes-pne-foresight-v2', 'schema do bundle')
  invariant(raw.publicationStatus === 'exploratory_model_public_data_audited', 'status da publicação')
  invariant(isSha256(raw.contentVersion), 'versão de conteúdo')
  invariant(isRecord(raw.publicationPolicy), 'política de publicação')
  invariant(raw.publicationPolicy.futureProbabilitiesAllowed === false, 'cenários sem probabilidades')
  invariant(raw.publicationPolicy.automaticRecommendationAllowed === false, 'cenários sem recomendação automática')
  invariant(raw.publicationPolicy.institutionalValidationClaimAllowed === false, 'sem alegação de validação institucional')

  invariant(isRecord(raw.region), 'região')
  invariant(raw.region.stateCode === 'RS' && raw.region.slug === 'vale-do-sinos', 'identidade regional')
  invariant(raw.region.municipalityCount === 10, 'dez municípios na cobertura')
  invariant(!Object.prototype.hasOwnProperty.call(raw.region, 'municipalities'), 'sem lista municipal publicada')

  invariant(isRecord(raw.diagnosticBridge), 'ponte diagnóstica')
  invariant(raw.diagnosticBridge.route === '#vocacoes-regiao', 'rota da ponte diagnóstica')
  invariant(raw.diagnosticBridge.copiedDiagnosticAssertions === 0, 'nenhuma afirmação diagnóstica copiada')
  invariant(Array.isArray(raw.diagnosticBridge.evidenceRefs), 'referências diagnósticas')
  invariant(new Set(raw.diagnosticBridge.evidenceRefs).size === raw.diagnosticBridge.evidenceRefs.length, 'referências diagnósticas sem duplicatas')
  invariant(raw.diagnosticBridge.evidenceRefCount === raw.diagnosticBridge.evidenceRefs.length, 'contagem das referências diagnósticas')
  invariant(raw.diagnosticBridge.resolvedEvidenceRefCount === raw.diagnosticBridge.evidenceRefCount, 'referências diagnósticas resolvidas')
  invariant(isRecord(raw.diagnosticBridge.deDuplicationAudit), 'auditoria de não duplicação')
  invariant(raw.diagnosticBridge.deDuplicationAudit.status === 'passed', 'auditoria de não duplicação aprovada')
  invariant(raw.diagnosticBridge.deDuplicationAudit.minimumLength === 80, 'limiar da auditoria')
  invariant(raw.diagnosticBridge.deDuplicationAudit.duplicateCount === 0, 'zero duplicações diagnósticas')
  invariant(Array.isArray(raw.diagnosticBridge.deDuplicationAudit.whitelist) && raw.diagnosticBridge.deDuplicationAudit.whitelist.length === 0, 'sem exceções de duplicação')

  invariant(isRecord(raw.sourceSnapshot), 'snapshot de fontes')
  for (const key of ['authoringContract', 'advancedBundle', 'advancedRegistry', 'regionConfig', 'municipalityRegistry', 'focalPneMunicipalMatrix']) {
    assertSourceDescriptor(raw.sourceSnapshot[key], key)
  }
  invariant(isRecord(raw.sourceSnapshot.regionalPublicInputs), 'entradas públicas regionais')
  invariant(raw.sourceSnapshot.regionalPublicInputs.fileCount === 30, 'trinta arquivos públicos locais')
  invariant(raw.sourceSnapshot.regionalPublicInputs.municipalityCount === 10, 'cobertura pública de dez municípios')
  invariant(isSha256(raw.sourceSnapshot.regionalPublicInputs.sha256), 'hash das entradas públicas regionais')

  invariant(Array.isArray(raw.domainRegistry) && raw.domainRegistry.length === 6, 'seis domínios')
  invariant(Array.isArray(raw.factorRegistry) && raw.factorRegistry.length === 5, 'cinco fatores')
  const factorIds = raw.factorRegistry.map((factor) => {
    invariant(isRecord(factor) && isNonEmptyString(factor.factorId), 'fator')
    invariant(Array.isArray(factor.states) && factor.states.length >= 3, 'estados do fator ' + factor.factorId)
    return factor.factorId
  })

  invariant(Array.isArray(raw.crossCuttingDrivers) && raw.crossCuttingDrivers.length === 4, 'quatro transversais')
  raw.crossCuttingDrivers.forEach((driver, index) => {
    invariant(isRecord(driver), 'transversal')
    const driverId = DRIVER_IDS[index]
    invariant(driver.driverId === driverId, 'ordem do transversal ' + driverId)
    invariant(driver.maturity === DRIVER_MATURITY[driverId], 'maturidade do transversal ' + driverId)
    invariant(isRecord(driver.coverage), 'cobertura do transversal ' + driverId)
    invariant(driver.coverage.municipalityCount === 10 && driver.coverage.expectedMunicipalityCount === 10, 'cobertura 10/10 de ' + driverId)
    invariant(isNonEmptyString(driver.claimCeiling) && isNonEmptyString(driver.unresolvedGap), 'limites de ' + driverId)
  })

  invariant(Array.isArray(raw.scenarios) && raw.scenarios.length === 4, 'quatro cenários')
  const scenarioIds = raw.scenarios.map((scenario, index) => {
    invariant(isRecord(scenario), 'cenário')
    invariant(scenario.order === index + 1 && isNonEmptyString(scenario.scenarioId), 'ordem do cenário')
    invariant(scenario.status === 'EXPLORATORY_NON_PROBABILISTIC', 'status exploratório de ' + String(scenario.scenarioId))
    invariant(isRecord(scenario.configurationStates), 'configuração de ' + String(scenario.scenarioId))
    invariant(Object.keys(scenario.configurationStates).every((factorId, factorIndex) => factorId === factorIds[factorIndex]), 'fatores de ' + String(scenario.scenarioId))
    invariant(Array.isArray(scenario.domains) && scenario.domains.length === 6, 'domínios de ' + String(scenario.scenarioId))
    invariant(Array.isArray(scenario.distributionalEffects) && scenario.distributionalEffects.length === 4, 'efeitos distributivos de ' + String(scenario.scenarioId))
    invariant(Array.isArray(scenario.pneImpacts) && scenario.pneImpacts.length === 5, 'impactos PNE de ' + String(scenario.scenarioId))
    return scenario.scenarioId
  })
  invariant(new Set(scenarioIds).size === 4, 'IDs de cenário distintos')

  const distances: number[] = []
  for (let left = 0; left < raw.scenarios.length; left += 1) {
    for (let right = left + 1; right < raw.scenarios.length; right += 1) {
      const leftScenario = raw.scenarios[left]
      const rightScenario = raw.scenarios[right]
      invariant(isRecord(leftScenario) && isRecord(rightScenario), 'par de cenários')
      invariant(isRecord(leftScenario.configurationStates) && isRecord(rightScenario.configurationStates), 'configuração do par')
      distances.push(hammingDistance(leftScenario.configurationStates, rightScenario.configurationStates, factorIds))
    }
  }
  invariant(isRecord(raw.morphologicalField), 'campo morfológico')
  invariant(Math.min(...distances) === raw.morphologicalField.minimumObservedPairwiseHammingDistance, 'distância morfológica reproduzida')
  invariant(Number(raw.morphologicalField.minimumObservedPairwiseHammingDistance) >= 4, 'distância morfológica mínima de quatro')

  invariant(Array.isArray(raw.municipalities) && raw.municipalities.length === 1, 'uma lente municipal')
  const municipality = raw.municipalities[0]
  invariant(isRecord(municipality), 'lente municipal')
  invariant(municipality.municipalityIbgeCode === '4313375' && municipality.municipalityName === 'Nova Santa Rita', 'lente exclusiva de Nova Santa Rita')
  invariant(municipality.diagnosticBridgeRoute === '#vocacoes-regiao', 'ponte municipal')
  invariant(!Object.prototype.hasOwnProperty.call(municipality, 'baselineContribution'), 'sem narrativa diagnóstica municipal copiada')
  invariant(Array.isArray(municipality.scenarioExposures) && municipality.scenarioExposures.length === 4, 'quatro exposições municipais')

  invariant(isRecord(raw.pneStressTest), 'stress-test PNE')
  invariant(raw.pneStressTest.municipalityIbgeCode === '4313375', 'stress-test PNE focal')
  invariant(Array.isArray(raw.pneStressTest.goalBaseline) && raw.pneStressTest.goalBaseline.length === 7, 'sete metas PNE')
  invariant(Array.isArray(raw.pneStressTest.scenarioAssessments) && raw.pneStressTest.scenarioAssessments.length === 4, 'quatro avaliações PNE')
  invariant(Array.isArray(raw.actions) && raw.actions.length === 10, 'dez opções de decisão')
  invariant(Array.isArray(raw.sentinelIndicators) && raw.sentinelIndicators.length === 12, 'doze sentinelas')

  invariant(isRecord(raw.qualityGate) && raw.qualityGate.status === 'passed', 'gate de dados públicos')
  invariant(raw.qualityGate.publicDataOnly === true && raw.qualityGate.localInputsOnly === true, 'fontes públicas locais')
  invariant(raw.qualityGate.networkDownloadUsed === false && raw.qualityGate.databaseUsed === false, 'sem rede nem banco')
  invariant(raw.qualityGate.diagnosticDuplicateCount === 0, 'gate de não duplicação')
}

export function assertCenariosEducacaoRegistry(raw: unknown): asserts raw is CenariosEducacaoRegistry {
  invariant(isRecord(raw), 'registro inválido')
  invariant(raw.schemaVersion === 'vocacoes-pne-foresight-registry-v2', 'schema do registro')
  invariant(raw.publicationStatus === 'exploratory_model_public_data_audited', 'status do registro')
  invariant(raw.publicDataValidationStatus === 'passed', 'status do gate público')
  invariant(raw.regionSlug === 'vale-do-sinos' && raw.regionalMunicipalityCount === 10, 'região do registro')
  invariant(raw.focalMunicipalityIbgeCode === '4313375', 'município focal do registro')
  invariant(raw.bundlePath === './cenariosEducacaoValeDoSinos.json', 'path do bundle')
  invariant(isSha256(raw.bundleSha256) && Number.isInteger(raw.bundleByteSize) && Number(raw.bundleByteSize) > 0, 'integridade do bundle')
  invariant(isSha256(raw.contentVersion), 'versão do registro')
  invariant(raw.scenarioCount === 4 && raw.domainCount === 6 && raw.factorCount === 5, 'contagens do registro')
  invariant(Number(raw.minimumPairwiseHammingDistance) >= 4, 'distância do registro')
  invariant(raw.diagnosticDuplicateCount === 0, 'não duplicação do registro')
  for (const key of [
    'authoringContractSha256',
    'advancedBundleSha256',
    'advancedRegistrySha256',
    'focalPneMunicipalMatrixSha256',
    'regionalPublicInputsSha256',
  ]) {
    invariant(isSha256(raw[key]), 'hash ' + key)
  }
}
