import { createHash } from 'node:crypto'
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
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const DEFAULT_REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..')

const AUTHORING_RELATIVE_PATH = 'data_pipeline/contracts/vocacoes-pne-foresight-v1.json'
const ADVANCED_BUNDLE_RELATIVE_PATH = 'src/features/vocacoes-regiao/generated/vocacoesPneAdvancedInsightsValeDoSinos.json'
const ADVANCED_REGISTRY_RELATIVE_PATH = 'src/features/vocacoes-regiao/generated/vocacoesPneAdvancedInsightsRegistry.json'
const REGION_CONFIG_RELATIVE_PATH = 'config/regions/rs.json'
const MUNICIPALITY_REGISTRY_RELATIVE_PATH = 'config/municipalities/rs.json'
const BUNDLE_RELATIVE_PATH = 'src/features/cenarios-educacao/generated/cenariosEducacaoValeDoSinos.json'
const REGISTRY_RELATIVE_PATH = 'src/features/cenarios-educacao/generated/cenariosEducacaoRegistry.json'

const FOCAL_MUNICIPALITY_IBGE_CODE = '4313375'
const GENERATED_AT = '2026-08-31T12:00:00-03:00'
const DETAILS_METRICS = Object.freeze([
  'internet_aprendizagem',
  'acesso_internet_computador',
])
const REQUIRED_EVIDENCE_CLASSES = Object.freeze([
  'OBSERVED',
  'ACCOUNTING_DERIVATION',
  'VALIDATED_ENVELOPE',
  'SCENARIO_ASSUMPTION',
  'NORMATIVE_CHOICE',
])
const REQUIRED_AVAILABILITY_STATES = Object.freeze([
  'observed',
  'observed_zero',
  'calculated',
  'estimated_range',
  'null',
  'unavailable',
  'suppressed',
  'not_applicable',
])
const REQUIRED_DRIVER_MATURITY = Object.freeze({
  X_CLIMATE: 'OBSERVED_PUBLIC_SENTINEL',
  X_TECHNOLOGY: 'OBSERVED_SERIES',
  X_FISCAL: 'OBSERVED_RECONCILED_CONTEXT',
  X_REGULATION: 'EXPLICIT_GAP',
})
const PNE_STRESS_STATUSES = new Set([
  'SUPPORTED',
  'PRESSURED',
  'AMBIGUOUS',
  'INSUFFICIENT_EVIDENCE',
])
const FORBIDDEN_ACTIVE_PATTERN = /novo hamburgo|4313409|contraste|oficina|validação humana|humanvalidation|municipalcontrast/iu

function invariant(condition, message) {
  if (!condition) throw new TypeError('Cenários da Educação: ' + message + '.')
}

function isRecord(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function assertNonEmptyString(value, label) {
  invariant(typeof value === 'string' && value.trim().length > 0, label)
}

function assertUniqueStrings(values, label) {
  invariant(Array.isArray(values) && values.every((value) => typeof value === 'string'), label)
  invariant(new Set(values).size === values.length, label + ' sem duplicatas')
}

function assertExactOrder(actual, expected, label) {
  invariant(
    Array.isArray(actual)
      && actual.length === expected.length
      && actual.every((value, index) => value === expected[index]),
    label,
  )
}

function assertIbgeCode(value, label) {
  invariant(typeof value === 'string' && /^\d{7}$/u.test(value), label + ' deve ser código IBGE textual de sete dígitos')
}

function serializeJson(value) {
  return JSON.stringify(value, null, 2) + '\n'
}

function sha256Text(value) {
  return createHash('sha256').update(value, 'utf8').digest('hex')
}

function sourceDescriptor(relativePath, bytes) {
  return {
    path: relativePath.replaceAll('\\', '/'),
    sha256: sha256Text(bytes),
    byteSize: Buffer.byteLength(bytes, 'utf8'),
  }
}

function parseJson(bytes, label) {
  try {
    return JSON.parse(bytes)
  } catch (error) {
    throw new TypeError('Cenários da Educação: JSON inválido em ' + label + ': ' + error.message)
  }
}

function getRegion(regionsConfig, slug) {
  const regions = Array.isArray(regionsConfig) ? regionsConfig : regionsConfig.regions
  invariant(Array.isArray(regions), 'configuração regional sem lista de regiões')
  const region = regions.find((candidate) => candidate.slug === slug)
  invariant(isRecord(region), 'região ' + slug + ' ausente na configuração canônica')
  return region
}

function getMunicipalities(municipalityRegistry) {
  const municipalities = Array.isArray(municipalityRegistry)
    ? municipalityRegistry
    : municipalityRegistry.municipalities
  invariant(Array.isArray(municipalities), 'registro municipal sem lista de municípios')
  return municipalities
}

function hammingDistance(left, right, factorIds) {
  return factorIds.reduce(
    (distance, factorId) => distance + Number(left.configurationStates[factorId] !== right.configurationStates[factorId]),
    0,
  )
}

function collectStrings(value, output = []) {
  if (typeof value === 'string') output.push(value)
  else if (Array.isArray(value)) value.forEach((item) => collectStrings(item, output))
  else if (isRecord(value)) Object.values(value).forEach((item) => collectStrings(item, output))
  return output
}

function collectKeys(value, output = []) {
  if (Array.isArray(value)) value.forEach((item) => collectKeys(item, output))
  else if (isRecord(value)) {
    Object.entries(value).forEach(([key, item]) => {
      output.push(key)
      collectKeys(item, output)
    })
  }
  return output
}

function normalizeLongText(value) {
  return value.normalize('NFKC').replace(/\s+/gu, ' ').trim().toLocaleLowerCase('pt-BR')
}

function assertNoUnsupportedFutureNumbers(scenario) {
  const narrative = {
    summary: scenario.summary,
    causalChain: scenario.causalChain,
    opportunities: scenario.opportunities,
    risks: scenario.risks,
    tradeOffs: scenario.tradeOffs,
    distributionalEffects: scenario.distributionalEffects.map((effect) => ({
      publicLabel: effect.publicLabel,
      exposure: effect.exposure,
      potentialUpside: effect.potentialUpside,
      potentialDownside: effect.potentialDownside,
      equityQuestion: effect.equityQuestion,
    })),
    regionalDependencies: scenario.regionalDependencies.map((dependency) => ({
      label: dependency.label,
      mechanism: dependency.mechanism,
    })),
    limitations: scenario.limitations,
    domains: scenario.domains,
    assumptions: scenario.assumptions,
    falsifiers: scenario.falsifiers,
  }
  for (const text of collectStrings(narrative)) {
    const withoutAllowedHorizons = text.replaceAll('2030', '').replaceAll('2031', '').replaceAll('2036', '')
    invariant(!/[0-9%]/u.test(withoutAllowedHorizons), 'numeral futuro não autorizado no cenário ' + scenario.scenarioId)
  }
}

function resolveDiagnosticReference(advancedBundle, scopeKey, selector) {
  const scope = scopeKey === 'region'
    ? advancedBundle.scopeVariants.region
    : advancedBundle.scopeVariants.novaSantaRita
  invariant(isRecord(scope), 'lente diagnóstica ' + scopeKey + ' ausente no bundle de Vocações')
  const records = scope[selector.collection]
  invariant(Array.isArray(records), 'coleção diagnóstica ' + selector.collection + ' ausente')
  const record = records.find((candidate) => candidate.id === selector.recordId)
  invariant(isRecord(record), 'registro diagnóstico ausente: ' + selector.recordId)
  invariant(Array.isArray(record.evidence), 'evidências ausentes em ' + selector.recordId)
  const evidence = record.evidence[selector.evidenceIndex]
  invariant(isRecord(evidence), 'índice de evidência inválido em ' + selector.recordId)
  invariant(REQUIRED_AVAILABILITY_STATES.includes(evidence.availability), 'availability inválida em ' + selector.evidenceId)
  if (['null', 'unavailable', 'suppressed', 'not_applicable'].includes(evidence.availability)) {
    invariant(evidence.value === null || evidence.value === undefined, 'ausência preservada em ' + selector.evidenceId)
  } else {
    invariant(typeof evidence.value === 'number' && Number.isFinite(evidence.value), 'valor finito em ' + selector.evidenceId)
  }
  return {
    evidenceId: selector.evidenceId,
    sourceRef: 'advanced:' + scopeKey + ':' + selector.collection + ':' + selector.recordId + ':' + selector.evidenceIndex,
  }
}

function validateAuthoringContract(contract, canonicalRegion, municipalityByCode, advancedBundle) {
  invariant(isRecord(contract), 'contrato de autoria inválido')
  invariant(contract.schemaVersion === 'vocacoes-pne-foresight-authoring-v2', 'schema do contrato de autoria')
  invariant(contract.contractVersion === '2.0.0', 'versão do contrato de autoria')
  invariant(contract.contractStatus === 'PUBLIC_DATA_AUDITED_EXPLORATORY_MODEL', 'status do contrato de autoria')
  invariant(!Object.prototype.hasOwnProperty.call(contract, 'municipalContrastValidation'), 'bloco municipal comparativo deve estar ausente')
  invariant(contract.publicationPolicy?.status === 'exploratory_model_public_data_audited', 'status público do modelo')
  invariant(contract.publicationPolicy?.equalScenarioWeight === true, 'peso equivalente dos cenários')
  invariant(contract.publicationPolicy?.futureProbabilitiesAllowed === false, 'probabilidades futuras devem ser proibidas')
  invariant(contract.publicationPolicy?.automaticRecommendationAllowed === false, 'recomendação automática deve ser proibida')
  invariant(contract.publicationPolicy?.institutionalValidationClaimAllowed === false, 'alegação de validação institucional deve ser proibida')
  assertNonEmptyString(contract.publicationPolicy?.validationGate, 'gate de dados públicos')
  assertExactOrder(contract.evidencePolicy?.classes ?? [], REQUIRED_EVIDENCE_CLASSES, 'classes de evidência canônicas')
  assertExactOrder(contract.evidencePolicy?.availabilityStates ?? [], REQUIRED_AVAILABILITY_STATES, 'estados de disponibilidade canônicos')
  assertNonEmptyString(contract.evidencePolicy?.crossCuttingMaturityRule, 'regra de maturidade transversal')

  invariant(contract.region?.stateCode === 'RS' && contract.region?.slug === canonicalRegion.slug, 'identidade regional do contrato')
  assertExactOrder(contract.region.municipalityIbgeCodes, canonicalRegion.municipalityIbgeCodes, 'universo municipal regional')
  contract.region.municipalityIbgeCodes.forEach((code) => assertIbgeCode(code, 'município regional'))
  assertIbgeCode(contract.requiredMunicipality?.ibgeCode, 'município focal')
  invariant(contract.requiredMunicipality.ibgeCode === FOCAL_MUNICIPALITY_IBGE_CODE, 'lente municipal deve ser Nova Santa Rita')
  const focalMunicipality = municipalityByCode.get(contract.requiredMunicipality.ibgeCode)
  invariant(focalMunicipality?.name === contract.requiredMunicipality.name, 'nome focal deve coincidir com o registro canônico')

  invariant(Array.isArray(contract.domainRegistry) && contract.domainRegistry.length === 6, 'seis domínios obrigatórios')
  const domainIds = contract.domainRegistry.map((domain) => domain.domainId)
  assertUniqueStrings(domainIds, 'IDs dos domínios')
  contract.domainRegistry.forEach((domain) => assertNonEmptyString(domain.label, 'rótulo do domínio ' + domain.domainId))

  invariant(Array.isArray(contract.factorRegistry) && contract.factorRegistry.length === 5, 'cinco fatores morfológicos')
  const factorIds = contract.factorRegistry.map((factor) => factor.factorId)
  assertUniqueStrings(factorIds, 'IDs dos fatores')
  const validStateIds = new Map()
  for (const factor of contract.factorRegistry) {
    assertNonEmptyString(factor.label, 'rótulo do fator ' + factor.factorId)
    assertNonEmptyString(factor.uncertainty, 'incerteza do fator ' + factor.factorId)
    invariant(Array.isArray(factor.states) && factor.states.length >= 3, 'estados do fator ' + factor.factorId)
    const stateIds = factor.states.map((state) => state.stateId)
    assertUniqueStrings(stateIds, 'estados do fator ' + factor.factorId)
    validStateIds.set(factor.factorId, new Set(stateIds))
  }

  invariant(Array.isArray(contract.crossCuttingDrivers) && contract.crossCuttingDrivers.length === 4, 'quatro drivers transversais')
  assertExactOrder(
    contract.crossCuttingDrivers.map((driver) => driver.driverId),
    Object.keys(REQUIRED_DRIVER_MATURITY),
    'ordem dos drivers transversais',
  )
  for (const driver of contract.crossCuttingDrivers) {
    invariant(driver.maturity === REQUIRED_DRIVER_MATURITY[driver.driverId], 'maturidade de ' + driver.driverId)
    invariant(REQUIRED_EVIDENCE_CLASSES.includes(driver.evidenceClass), 'classe de evidência de ' + driver.driverId)
    invariant(REQUIRED_AVAILABILITY_STATES.includes(driver.availability), 'availability de ' + driver.driverId)
    ;['evidencePlan', 'claimCeiling', 'unresolvedGap', 'scenarioUse'].forEach((field) => {
      assertNonEmptyString(driver[field], field + ' de ' + driver.driverId)
    })
  }

  const driverIds = contract.crossCuttingDrivers.map((driver) => driver.driverId)
  const impactEndpoints = new Set([...factorIds, ...driverIds])
  invariant(Array.isArray(contract.crossImpactMatrix) && contract.crossImpactMatrix.length >= 8, 'matriz de impactos cruzados')
  assertUniqueStrings(contract.crossImpactMatrix.map((impact) => impact.impactId), 'IDs de impactos cruzados')
  const factorsWithImpact = new Set()
  for (const impact of contract.crossImpactMatrix) {
    invariant(impactEndpoints.has(impact.from) && factorIds.includes(impact.to), 'extremos do impacto ' + impact.impactId)
    invariant(impact.evidenceClass === 'SCENARIO_ASSUMPTION', 'classe do impacto ' + impact.impactId)
    assertNonEmptyString(impact.mechanism, 'mecanismo do impacto ' + impact.impactId)
    if (factorIds.includes(impact.from)) factorsWithImpact.add(impact.from)
    factorsWithImpact.add(impact.to)
  }
  invariant(factorIds.every((factorId) => factorsWithImpact.has(factorId)), 'todos os fatores participam dos impactos cruzados')

  const selectorGroups = contract.diagnosticReferenceSelectors
  invariant(isRecord(selectorGroups), 'seletores de referência diagnóstica')
  assertExactOrder(Object.keys(selectorGroups), ['region', 'municipality'], 'lentes dos seletores diagnósticos')
  const resolvedReferences = []
  for (const scopeKey of ['region', 'municipality']) {
    invariant(Array.isArray(selectorGroups[scopeKey]) && selectorGroups[scopeKey].length > 0, 'seletores diagnósticos de ' + scopeKey)
    for (const selector of selectorGroups[scopeKey]) {
      assertNonEmptyString(selector.evidenceId, 'ID de referência diagnóstica')
      invariant(['readings', 'transversal'].includes(selector.collection), 'coleção do seletor ' + selector.evidenceId)
      invariant(Number.isInteger(selector.evidenceIndex) && selector.evidenceIndex >= 0, 'índice do seletor ' + selector.evidenceId)
      assertNonEmptyString(selector.lens, 'lente do seletor ' + selector.evidenceId)
      assertNonEmptyString(selector.claimCeiling, 'teto de afirmação ' + selector.evidenceId)
      resolvedReferences.push(resolveDiagnosticReference(advancedBundle, scopeKey, selector))
    }
  }
  const evidenceIds = resolvedReferences.map((reference) => reference.evidenceId)
  assertUniqueStrings(evidenceIds, 'referências diagnósticas')
  const evidenceIdSet = new Set(evidenceIds)

  invariant(Array.isArray(contract.actions) && contract.actions.length > 0, 'ações de decisão')
  const actionIds = contract.actions.map((action) => action.actionId)
  assertUniqueStrings(actionIds, 'IDs de ações')
  const actionIdSet = new Set(actionIds)
  for (const action of contract.actions) {
    invariant(['NO_REGRET', 'CONTINGENT', 'REVERSIBLE_EXPERIMENT'].includes(action.type), 'tipo da ação ' + action.actionId)
    invariant(['MUNICIPAL', 'SHARED', 'EXTERNAL'].includes(action.authority), 'autoridade da ação ' + action.actionId)
    ;['title', 'description', 'trigger', 'lockInRisk'].forEach((field) => assertNonEmptyString(action[field], field + ' da ação ' + action.actionId))
  }

  invariant(Array.isArray(contract.sentinelIndicators) && contract.sentinelIndicators.length > 0, 'indicadores sentinela')
  const sentinelIds = contract.sentinelIndicators.map((indicator) => indicator.indicatorId)
  assertUniqueStrings(sentinelIds, 'IDs sentinela')
  const sentinelIdSet = new Set(sentinelIds)
  for (const indicator of contract.sentinelIndicators) {
    invariant(REQUIRED_AVAILABILITY_STATES.includes(indicator.availability), 'availability do sentinela ' + indicator.indicatorId)
    assertNonEmptyString(indicator.decisionUse, 'uso do sentinela ' + indicator.indicatorId)
  }

  invariant(Array.isArray(contract.scenarios) && contract.scenarios.length === 4, 'exatamente quatro cenários')
  const scenarioIds = contract.scenarios.map((scenario) => scenario.scenarioId)
  assertUniqueStrings(scenarioIds, 'IDs dos cenários')
  assertUniqueStrings(contract.scenarios.map((scenario) => scenario.title), 'títulos dos cenários')
  assertExactOrder(contract.scenarios.map((scenario) => scenario.order), [1, 2, 3, 4], 'ordem dos cenários')
  const symmetry = contract.blindSubstitutabilityReview?.requiredSymmetry
  invariant(contract.blindSubstitutabilityReview?.status === 'PASSED_BY_CONTRACT_RULE', 'gate de substituibilidade')
  invariant(Number.isInteger(contract.blindSubstitutabilityReview?.requiredMinimumPairwiseHammingDistance), 'distância mínima do contrato')
  for (const scenario of contract.scenarios) {
    invariant(scenario.status === 'EXPLORATORY_NON_PROBABILISTIC', 'status exploratório em ' + scenario.scenarioId)
    assertExactOrder(Object.keys(scenario.configurationStates), factorIds, 'fatores do cenário ' + scenario.scenarioId)
    factorIds.forEach((factorId) => invariant(validStateIds.get(factorId).has(scenario.configurationStates[factorId]), 'estado de ' + factorId + ' em ' + scenario.scenarioId))
    invariant(scenario.opportunities.length === symmetry.opportunitiesPerScenario, 'oportunidades simétricas em ' + scenario.scenarioId)
    invariant(scenario.risks.length === symmetry.risksPerScenario, 'riscos simétricos em ' + scenario.scenarioId)
    invariant(scenario.tradeOffs.length === symmetry.tradeOffsPerScenario, 'trade-offs simétricos em ' + scenario.scenarioId)
    invariant(scenario.domains.length === symmetry.domainsPerScenario, 'domínios simétricos em ' + scenario.scenarioId)
    invariant(scenario.distributionalEffects.length === symmetry.distributionalEffectsPerScenario, 'efeitos distributivos simétricos em ' + scenario.scenarioId)
    invariant(scenario.regionalDependencies.length === symmetry.regionalDependenciesPerScenario, 'dependências regionais simétricas em ' + scenario.scenarioId)
    invariant(scenario.limitations.length === symmetry.limitationsPerScenario, 'limitações simétricas em ' + scenario.scenarioId)
    assertExactOrder(scenario.domains.map((domain) => domain.domainId), domainIds, 'domínios do cenário ' + scenario.scenarioId)
    scenario.evidenceRefs.forEach((evidenceId) => invariant(evidenceIdSet.has(evidenceId), 'referência diagnóstica ' + evidenceId + ' em ' + scenario.scenarioId))
    scenario.sentinelIndicatorIds.forEach((indicatorId) => invariant(sentinelIdSet.has(indicatorId), 'sentinela ' + indicatorId + ' em ' + scenario.scenarioId))
    assertNoUnsupportedFutureNumbers(scenario)
  }

  const pairwiseDistances = []
  for (let leftIndex = 0; leftIndex < contract.scenarios.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < contract.scenarios.length; rightIndex += 1) {
      const left = contract.scenarios[leftIndex]
      const right = contract.scenarios[rightIndex]
      pairwiseDistances.push({
        leftScenarioId: left.scenarioId,
        rightScenarioId: right.scenarioId,
        distance: hammingDistance(left, right, factorIds),
      })
    }
  }
  const minimumDistance = Math.min(...pairwiseDistances.map((pair) => pair.distance))
  invariant(minimumDistance >= contract.blindSubstitutabilityReview.requiredMinimumPairwiseHammingDistance, 'distância morfológica mínima')
  const blindSignatures = contract.scenarios.map((scenario) => ({
    scenarioId: scenario.scenarioId,
    sha256: sha256Text(serializeJson({
      configurationStates: scenario.configurationStates,
      causalChain: scenario.causalChain,
      municipalExposures: scenario.domains.map((domain) => domain.novaSantaRitaExposure),
      distributionalEffects: scenario.distributionalEffects,
      regionalDependencies: scenario.regionalDependencies,
      limitations: scenario.limitations,
      falsifiers: scenario.falsifiers,
    })),
  }))
  invariant(new Set(blindSignatures.map((signature) => signature.sha256)).size === 4, 'assinaturas cegas distintas')

  invariant(Array.isArray(contract.municipalities) && contract.municipalities.length === 1, 'uma lente municipal')
  const municipalLens = contract.municipalities[0]
  invariant(municipalLens.municipalityIbgeCode === FOCAL_MUNICIPALITY_IBGE_CODE, 'lente municipal exclusiva de Nova Santa Rita')
  invariant(municipalLens.municipalityName === focalMunicipality.name, 'nome municipal canônico')
  invariant(!Object.prototype.hasOwnProperty.call(municipalLens, 'baselineContribution'), 'narrativa diagnóstica municipal não deve ser copiada')
  invariant(municipalLens.diagnosticBridgeRoute === '#vocacoes-regiao', 'rota da ponte diagnóstica municipal')
  assertUniqueStrings(municipalLens.diagnosticEvidenceRefs, 'referências da lente municipal')
  municipalLens.diagnosticEvidenceRefs.forEach((evidenceId) => invariant(evidenceIdSet.has(evidenceId), 'referência da lente municipal ' + evidenceId))
  assertExactOrder(municipalLens.scenarioExposures.map((exposure) => exposure.scenarioId), scenarioIds, 'exposições municipais por cenário')
  for (const exposure of municipalLens.scenarioExposures) {
    assertExactOrder(Object.keys(exposure.exposures), ['demographic', 'educational', 'economic', 'social', 'territorial'], 'dimensões municipais em ' + exposure.scenarioId)
    exposure.evidenceRefs.forEach((evidenceId) => invariant(evidenceIdSet.has(evidenceId), 'evidência municipal ' + evidenceId))
    exposure.leverIds.forEach((actionId) => invariant(actionIdSet.has(actionId), 'alavanca municipal ' + actionId))
  }
  municipalLens.localSignalIds.forEach((indicatorId) => invariant(sentinelIdSet.has(indicatorId), 'sinal local ' + indicatorId))

  const stress = contract.pneStressTest
  assertUniqueStrings(stress.goalIds, 'metas PNE')
  const clusterIds = stress.clusters.map((cluster) => cluster.clusterId)
  assertUniqueStrings(clusterIds, 'clusters PNE')
  const goalIdSet = new Set(stress.goalIds)
  stress.clusters.forEach((cluster) => invariant(cluster.goalIds.length > 0 && cluster.goalIds.every((goalId) => goalIdSet.has(goalId)), 'metas do cluster ' + cluster.clusterId))
  assertExactOrder(stress.scenarioAssessments.map((assessment) => assessment.scenarioId), scenarioIds, 'cenários no stress-test PNE')
  for (const assessment of stress.scenarioAssessments) {
    assertExactOrder(assessment.impacts.map((impact) => impact.clusterId), clusterIds, 'clusters PNE em ' + assessment.scenarioId)
    for (const impact of assessment.impacts) {
      invariant(PNE_STRESS_STATUSES.has(impact.status), 'status PNE em ' + assessment.scenarioId + '/' + impact.clusterId)
      invariant(actionIdSet.has(impact.response), 'resposta PNE em ' + assessment.scenarioId + '/' + impact.clusterId)
    }
  }

  invariant(contract.sourceGovernance?.publicDataOnly === true, 'governança exclusiva de dados públicos')
  invariant(contract.sourceGovernance?.localFirst === true, 'política local-first')
  invariant(contract.sourceGovernance?.deduplicationPolicy?.minimumLength === 80, 'limiar de não duplicação')
  invariant(Array.isArray(contract.sourceGovernance?.deduplicationPolicy?.whitelist) && contract.sourceGovernance.deduplicationPolicy.whitelist.length === 0, 'lista de exceções da não duplicação vazia')
  invariant(
    !FORBIDDEN_ACTIVE_PATTERN.test(JSON.stringify(contract).replaceAll('4313409', '')),
    'termos retirados ainda presentes no contrato ativo',
  )

  return {
    factorIds,
    domainIds,
    scenarioIds,
    pairwiseDistances,
    blindSignatures,
    minimumDistance,
    resolvedReferences,
  }
}

function assertAdvancedInputs(bundle, registry, bundleBytes, authoringContract) {
  invariant(registry.schemaVersion === 'vocacoes-pne-advanced-insights-registry-v1', 'schema do registro avançado')
  invariant(registry.publicationStatus === 'official', 'publicação avançada deve ser oficial')
  invariant(registry.bundleByteSize === Buffer.byteLength(bundleBytes, 'utf8'), 'tamanho do bundle avançado')
  invariant(registry.bundleSha256 === sha256Text(bundleBytes), 'hash do bundle avançado')
  invariant(bundle.schemaVersion === 'vocacoes-pne-advanced-insights-v1', 'schema do bundle avançado')
  invariant(bundle.contentVersion === registry.contentVersion, 'versão do bundle avançado')
  invariant(bundle.region?.slug === authoringContract.region.slug, 'região do bundle avançado')
  assertExactOrder(bundle.region.municipalities.map((item) => item.ibgeCode), authoringContract.region.municipalityIbgeCodes, 'municípios do bundle avançado')
  invariant(bundle.scopeVariants?.region?.entityType === 'region', 'lente regional avançada')
  invariant(bundle.scopeVariants?.novaSantaRita?.municipalityIbgeCode === FOCAL_MUNICIPALITY_IBGE_CODE, 'lente municipal avançada')
}

function findMeasureRecords(value, output = []) {
  if (Array.isArray(value)) {
    value.forEach((item) => findMeasureRecords(item, output))
  } else if (isRecord(value)) {
    if (typeof value.measureId === 'string') output.push(value)
    Object.values(value).forEach((item) => findMeasureRecords(item, output))
  }
  return output
}

function percentage(numerator, denominator) {
  return denominator === 0 ? null : (numerator / denominator) * 100
}

function median(values) {
  const ordered = [...values].sort((left, right) => left - right)
  const middle = Math.floor(ordered.length / 2)
  return ordered.length % 2 === 1
    ? ordered[middle]
    : (ordered[middle - 1] + ordered[middle]) / 2
}

function buildCrossCuttingDrivers(contract, inputs) {
  const codes = contract.region.municipalityIbgeCodes
  const climateProtocols = new Set()
  const focalClimateProtocols = new Set()
  const municipalitiesWithClimateEvent = new Set()
  let municipalitiesWithRegulationProxy = 0

  for (const code of codes) {
    const matrix = inputs.pneMatrices.get(code)
    const measures = findMeasureRecords(matrix)
    const regulationProxy = measures.some((measure) => measure.measureId === 'ibge.munic.public_transport_accessibility_action')
    if (regulationProxy) municipalitiesWithRegulationProxy += 1
    for (const measure of measures.filter((candidate) => candidate.measureId.startsWith('midr.atlas.'))) {
      const protocolMatch = /(?:^|;)protocolS2id=([^;]+)/u.exec(String(measure.dimensions ?? ''))
      const year = Number(measure.period)
      if (protocolMatch === null || !Number.isInteger(year) || year < 2014 || year > 2025) continue
      const key = code + '|' + protocolMatch[1]
      climateProtocols.add(key)
      municipalitiesWithClimateEvent.add(code)
      if (code === FOCAL_MUNICIPALITY_IBGE_CODE) focalClimateProtocols.add(key)
    }
  }

  const technologyMetrics = DETAILS_METRICS.map((metricId) => {
    let regionalNumerator = 0
    let regionalDenominator = 0
    let focalNumerator = null
    let focalDenominator = null
    let label = null
    for (const code of codes) {
      const metric = inputs.detailsByMunicipality.get(code)?.[metricId]
      invariant(isRecord(metric) && Array.isArray(metric.series_components), 'série tecnológica ' + metricId + ' para ' + code)
      const point = metric.series_components.find((candidate) => candidate.ano === 2025)
      invariant(isRecord(point), 'ponto 2025 de ' + metricId + ' para ' + code)
      invariant(Number.isFinite(point.numerador) && Number.isFinite(point.denominador), 'numerador e denominador de ' + metricId + ' para ' + code)
      regionalNumerator += point.numerador
      regionalDenominator += point.denominador
      label = metric.title
      if (code === FOCAL_MUNICIPALITY_IBGE_CODE) {
        focalNumerator = point.numerador
        focalDenominator = point.denominador
      }
    }
    invariant(focalNumerator !== null && focalDenominator !== null, 'ponto focal de ' + metricId)
    return {
      metricId,
      label,
      period: '2025',
      unit: 'percent_of_schools',
      region: {
        numerator: regionalNumerator,
        denominator: regionalDenominator,
        valueRaw: percentage(regionalNumerator, regionalDenominator),
      },
      novaSantaRita: {
        numerator: focalNumerator,
        denominator: focalDenominator,
        valueRaw: percentage(focalNumerator, focalDenominator),
      },
    }
  })

  const fiscalMargins = []
  let focalFiscalMargin = null
  for (const code of codes) {
    const finance = inputs.financeByMunicipality.get(code)
    invariant(finance?.municipality?.ibgeCode === code, 'identidade financeira de ' + code)
    invariant(finance.constitutionalApplication?.status === 'reconciled', 'aplicação constitucional reconciliada de ' + code)
    invariant(finance.reconciliation?.status === 'reconciled', 'reconciliação MDE de ' + code)
    invariant(finance.constitutionalApplication.referenceYear === 2025, 'ano financeiro fechado de ' + code)
    const margin = finance.constitutionalApplication.mdeMarginFromMinimum?.value
    invariant(typeof margin === 'number' && Number.isFinite(margin), 'margem MDE de ' + code)
    fiscalMargins.push(margin)
    if (code === FOCAL_MUNICIPALITY_IBGE_CODE) focalFiscalMargin = margin
  }
  invariant(focalFiscalMargin !== null, 'margem MDE focal')

  const evidenceByDriverId = {
    X_CLIMATE: {
      period: '2014–2025',
      lens: 'PUBLIC_DISASTER_EVENT_REGISTRY',
      calculation: {
        formula: 'count(distinct municipalityIbgeCode + protocolS2id)',
        uniqueRegisteredOrRecognizedEventProtocols: climateProtocols.size,
        municipalitiesWithEvent: municipalitiesWithClimateEvent.size,
        regionalMunicipalityCount: codes.length,
        novaSantaRitaUniqueEventProtocols: focalClimateProtocols.size,
      },
      coverage: {
        status: 'complete',
        municipalityCount: codes.length,
        expectedMunicipalityCount: codes.length,
        sourceFileCount: codes.length,
      },
      sourceRefs: ['regional-public-inputs:pne-matrix:midr-atlas'],
    },
    X_TECHNOLOGY: {
      period: '2025',
      lens: 'SCHOOL_DECLARED_INFRASTRUCTURE',
      calculation: {
        formula: 'sum(municipal numerators) / sum(municipal denominators) * 100',
        denominatorZeroRule: 'null',
        roundingRule: 'presentation_only',
      },
      metrics: technologyMetrics,
      coverage: {
        status: 'complete',
        municipalityCount: codes.length,
        expectedMunicipalityCount: codes.length,
        sourceFileCount: codes.length,
      },
      sourceRefs: ['regional-public-inputs:details:school-technology'],
    },
    X_FISCAL: {
      period: '2025',
      lens: 'MUNICIPAL_RECONCILED_MDE_CONTEXT',
      calculation: {
        formula: 'distribution(municipal mdeAppliedRate - 25 percentage points)',
        aggregationGuard: 'municipal distribution; values are not summed',
        minimumMarginPercentagePoints: Math.min(...fiscalMargins),
        medianMarginPercentagePoints: median(fiscalMargins),
        maximumMarginPercentagePoints: Math.max(...fiscalMargins),
        novaSantaRitaMarginPercentagePoints: focalFiscalMargin,
      },
      coverage: {
        status: 'complete_reconciled',
        municipalityCount: codes.length,
        expectedMunicipalityCount: codes.length,
        reconciledMunicipalityCount: fiscalMargins.length,
        sourceFileCount: codes.length,
      },
      sourceRefs: ['regional-public-inputs:finance:constitutional-application'],
    },
    X_REGULATION: {
      period: '2023–2026',
      lens: 'REGIONAL_EDUCATION_COLLABORATION',
      proxyAudit: {
        excludedMeasureId: 'ibge.munic.public_transport_accessibility_action',
        municipalitiesWithExcludedProxy: municipalitiesWithRegulationProxy,
        eligiblePublicEvidenceCount: 0,
        exclusionReason: 'Ação geral de acessibilidade no transporte não mede pacto educacional regional, responsabilidades, nível de serviço, cofinanciamento, revisão ou saída.',
      },
      coverage: {
        status: 'source_review_complete_target_construct_unavailable',
        municipalityCount: codes.length,
        expectedMunicipalityCount: codes.length,
        sourceFileCount: codes.length,
      },
      sourceRefs: ['regional-public-inputs:pne-matrix:ibge-munic-proxy-audit'],
    },
  }

  return contract.crossCuttingDrivers.map((driver) => ({
    ...driver,
    ...evidenceByDriverId[driver.driverId],
  }))
}

function collectPneGoals(matrix, goalIds) {
  const candidates = [
    ...(matrix.priorityGoals ?? []),
    ...(matrix.goalsWithoutOwnCause ?? []),
    ...(matrix.outOfReach ?? []),
  ]
  const byId = new Map()
  for (const candidate of candidates) {
    if (!goalIds.includes(candidate.goalId)) continue
    invariant(!byId.has(candidate.goalId), 'meta PNE duplicada: ' + candidate.goalId)
    byId.set(candidate.goalId, candidate)
  }
  return goalIds.map((goalId) => {
    const goal = byId.get(goalId)
    invariant(isRecord(goal), 'meta PNE ausente no diagnóstico municipal: ' + goalId)
    const numericValue = goal.valueRaw === null || goal.valueRaw === undefined ? null : Number(goal.valueRaw)
    const availability = goal.valueRaw === null || goal.valueRaw === undefined
      ? 'null'
      : Number.isFinite(numericValue) && Object.is(numericValue, 0)
        ? 'observed_zero'
        : 'observed'
    return {
      goalId,
      title: goal.title,
      valueRaw: goal.valueRaw ?? null,
      referenceRaw: goal.referenceRaw ?? null,
      unit: goal.unit ?? null,
      year: goal.year ?? goal.severity?.peerBenchmark?.year ?? null,
      severity: goal.severity?.level ?? null,
      availability,
      evidenceClass: 'OBSERVED',
      evidenceRef: 'pne-matrix:' + FOCAL_MUNICIPALITY_IBGE_CODE + ':' + goalId,
    }
  })
}

function findDiagnosticDuplicates(scenarioSlice, advancedBundle, minimumLength) {
  const advancedIndex = new Map()
  for (const text of collectStrings(advancedBundle)) {
    const normalized = normalizeLongText(text)
    if (normalized.length >= minimumLength && !advancedIndex.has(normalized)) {
      advancedIndex.set(normalized, text)
    }
  }
  const duplicates = []
  const scenarioStrings = collectStrings(scenarioSlice)
  for (const text of scenarioStrings) {
    const normalized = normalizeLongText(text)
    if (normalized.length < minimumLength || !advancedIndex.has(normalized)) continue
    duplicates.push({
      scenarioText: text,
      diagnosticText: advancedIndex.get(normalized),
    })
  }
  return {
    duplicates,
    scenarioStringCount: scenarioStrings.filter((text) => normalizeLongText(text).length >= minimumLength).length,
    diagnosticStringCount: advancedIndex.size,
  }
}

async function loadInputs(repoRoot) {
  const initialPaths = [
    AUTHORING_RELATIVE_PATH,
    ADVANCED_BUNDLE_RELATIVE_PATH,
    ADVANCED_REGISTRY_RELATIVE_PATH,
    REGION_CONFIG_RELATIVE_PATH,
    MUNICIPALITY_REGISTRY_RELATIVE_PATH,
  ]
  const initialBytes = await Promise.all(initialPaths.map((relativePath) => readFile(path.join(repoRoot, relativePath), 'utf8')))
  const [
    authoringContract,
    advancedBundle,
    advancedRegistry,
    regionsConfig,
    municipalityRegistry,
  ] = initialBytes.map((bytes, index) => parseJson(bytes, initialPaths[index]))
  const sources = Object.fromEntries(initialPaths.map((relativePath, index) => [
    relativePath,
    sourceDescriptor(relativePath, initialBytes[index]),
  ]))

  const canonicalRegion = getRegion(regionsConfig, authoringContract.region?.slug)
  const municipalityByCode = new Map(getMunicipalities(municipalityRegistry).map((municipality) => [municipality.ibgeCode, municipality]))
  assertAdvancedInputs(advancedBundle, advancedRegistry, initialBytes[1], authoringContract)
  const methodValidation = validateAuthoringContract(
    authoringContract,
    canonicalRegion,
    municipalityByCode,
    advancedBundle,
  )

  const publicInputSpecs = authoringContract.region.municipalityIbgeCodes.flatMap((ibgeCode) => [
    {
      ibgeCode,
      kind: 'details',
      relativePath: 'public/data/municipios/' + ibgeCode + '/details.json',
    },
    {
      ibgeCode,
      kind: 'finance',
      relativePath: 'public/data/municipios/' + ibgeCode + '/financeiro.json',
    },
    {
      ibgeCode,
      kind: 'pneMatrix',
      relativePath: 'public/data/pne2026-matriz/municipios/' + ibgeCode + '.json',
    },
  ])
  const publicInputBytes = await Promise.all(publicInputSpecs.map((spec) => readFile(path.join(repoRoot, spec.relativePath), 'utf8')))
  const detailsByMunicipality = new Map()
  const financeByMunicipality = new Map()
  const pneMatrices = new Map()
  const publicInputManifestFiles = []

  publicInputSpecs.forEach((spec, index) => {
    const bytes = publicInputBytes[index]
    const parsed = parseJson(bytes, spec.relativePath)
    const descriptor = sourceDescriptor(spec.relativePath, bytes)
    publicInputManifestFiles.push({
      municipalityIbgeCode: spec.ibgeCode,
      kind: spec.kind,
      ...descriptor,
    })
    if (spec.kind === 'details') {
      detailsByMunicipality.set(spec.ibgeCode, parsed)
      return
    }
    if (spec.kind === 'finance') {
      invariant(parsed.municipality?.ibgeCode === spec.ibgeCode, 'identidade em ' + spec.relativePath)
      financeByMunicipality.set(spec.ibgeCode, parsed)
      return
    }
    invariant(parsed.schemaVersion === 'matriz-4.0.0', 'schema em ' + spec.relativePath)
    invariant(parsed.municipality?.ibge7 === spec.ibgeCode, 'identidade em ' + spec.relativePath)
    pneMatrices.set(spec.ibgeCode, parsed)
  })

  const regionalPublicInputsManifest = {
    schemaVersion: 'cenarios-educacao-regional-public-inputs-v1',
    regionSlug: authoringContract.region.slug,
    files: publicInputManifestFiles,
  }
  const focalPneSpecIndex = publicInputSpecs.findIndex((spec) => spec.kind === 'pneMatrix' && spec.ibgeCode === FOCAL_MUNICIPALITY_IBGE_CODE)
  invariant(focalPneSpecIndex >= 0, 'matriz PNE focal no manifesto de entradas')

  return {
    authoringContract,
    advancedBundle,
    advancedRegistry,
    canonicalRegion,
    municipalityByCode,
    methodValidation,
    sources,
    detailsByMunicipality,
    financeByMunicipality,
    pneMatrices,
    regionalPublicInputsManifest,
    regionalPublicInputsSha256: sha256Text(serializeJson(regionalPublicInputsManifest)),
    focalPneDescriptor: sourceDescriptor(publicInputSpecs[focalPneSpecIndex].relativePath, publicInputBytes[focalPneSpecIndex]),
  }
}

function buildBundle(inputs) {
  const contract = inputs.authoringContract
  const crossCuttingDrivers = buildCrossCuttingDrivers(contract, inputs)
  const pneGoals = collectPneGoals(
    inputs.pneMatrices.get(FOCAL_MUNICIPALITY_IBGE_CODE),
    contract.pneStressTest.goalIds,
  )
  const assessmentByScenario = new Map(
    contract.pneStressTest.scenarioAssessments.map((assessment) => [assessment.scenarioId, assessment]),
  )
  const sentinelById = new Map(contract.sentinelIndicators.map((indicator) => [indicator.indicatorId, indicator]))
  const scenarios = contract.scenarios.map((scenario) => ({
    ...scenario,
    pneImpacts: assessmentByScenario.get(scenario.scenarioId).impacts,
    sentinelIndicators: scenario.sentinelIndicatorIds.map((indicatorId) => sentinelById.get(indicatorId)),
  }))
  const municipalLens = contract.municipalities.map((municipality) => ({
    municipalityIbgeCode: municipality.municipalityIbgeCode,
    municipalityName: municipality.municipalityName,
    diagnosticBridgeRoute: municipality.diagnosticBridgeRoute,
    diagnosticEvidenceRefs: municipality.diagnosticEvidenceRefs,
    scenarioExposures: municipality.scenarioExposures,
    localSignalIds: municipality.localSignalIds,
    limitations: municipality.limitations,
    smallNumberCaveat: contract.evidencePolicy.municipalSmallNumberCaveat,
  }))
  const sourceSnapshot = {
    authoringContract: inputs.sources[AUTHORING_RELATIVE_PATH],
    advancedBundle: inputs.sources[ADVANCED_BUNDLE_RELATIVE_PATH],
    advancedRegistry: inputs.sources[ADVANCED_REGISTRY_RELATIVE_PATH],
    regionConfig: inputs.sources[REGION_CONFIG_RELATIVE_PATH],
    municipalityRegistry: inputs.sources[MUNICIPALITY_REGISTRY_RELATIVE_PATH],
    focalPneMunicipalMatrix: inputs.focalPneDescriptor,
    regionalPublicInputs: {
      schemaVersion: 'cenarios-educacao-regional-public-inputs-v1',
      sha256: inputs.regionalPublicInputsSha256,
      fileCount: inputs.regionalPublicInputsManifest.files.length,
      municipalityCount: contract.region.municipalityIbgeCodes.length,
      coverage: {
        details: contract.region.municipalityIbgeCodes.length,
        finance: contract.region.municipalityIbgeCodes.length,
        pneMatrix: contract.region.municipalityIbgeCodes.length,
      },
      pathPatterns: [
        'public/data/municipios/<IBGE>/details.json',
        'public/data/municipios/<IBGE>/financeiro.json',
        'public/data/pne2026-matriz/municipios/<IBGE>.json',
      ],
    },
    advancedSourceManifestSha256: inputs.advancedRegistry.sourceManifestSha256,
    advancedSourceArtifactSetDigestSha256: inputs.advancedRegistry.sourceArtifactSetDigestSha256,
  }
  const diagnosticEvidenceRefs = inputs.methodValidation.resolvedReferences.map((reference) => reference.evidenceId)
  const diagnosticBridge = {
    canonicalSection: 'Vocações da Região',
    route: '#vocacoes-regiao',
    boundary: 'O diagnóstico factual, suas séries e relações permanecem em Vocações da Região. Esta seção usa somente referências verificadas para construir incertezas, mecanismos, impactos, opções e sentinelas.',
    sourceBundle: sourceSnapshot.advancedBundle,
    sourceRegistry: sourceSnapshot.advancedRegistry,
    evidenceRefs: diagnosticEvidenceRefs,
    evidenceRefCount: diagnosticEvidenceRefs.length,
    resolvedEvidenceRefCount: diagnosticEvidenceRefs.length,
    copiedDiagnosticAssertions: 0,
  }
  const morphologicalField = {
    requiredMinimumPairwiseHammingDistance: contract.blindSubstitutabilityReview.requiredMinimumPairwiseHammingDistance,
    minimumObservedPairwiseHammingDistance: inputs.methodValidation.minimumDistance,
    pairwiseDistances: inputs.methodValidation.pairwiseDistances,
    blindSubstitutabilityReview: {
      status: contract.blindSubstitutabilityReview.status,
      method: contract.blindSubstitutabilityReview.method,
      signatures: inputs.methodValidation.blindSignatures,
    },
  }
  const scenarioSlice = {
    crossCuttingDrivers,
    crossImpactMatrix: contract.crossImpactMatrix,
    scenarios,
    municipalities: municipalLens,
    pneStressTest: {
      normativeSeparation: contract.pneStressTest.normativeSeparation,
      municipalityIbgeCode: FOCAL_MUNICIPALITY_IBGE_CODE,
      goalBaseline: pneGoals,
      clusters: contract.pneStressTest.clusters,
      scenarioAssessments: contract.pneStressTest.scenarioAssessments,
    },
    actions: contract.actions,
    sentinelIndicators: contract.sentinelIndicators,
  }
  const minimumLength = contract.sourceGovernance.deduplicationPolicy.minimumLength
  const duplicateAudit = findDiagnosticDuplicates(scenarioSlice, inputs.advancedBundle, minimumLength)
  invariant(
    duplicateAudit.duplicates.length === 0,
    'afirmações diagnósticas longas duplicadas entre Cenários e Vocações: '
      + duplicateAudit.duplicates.slice(0, 3).map((item) => item.scenarioText).join(' | '),
  )
  diagnosticBridge.deDuplicationAudit = {
    status: 'passed',
    normalization: contract.sourceGovernance.deduplicationPolicy.normalization,
    minimumLength,
    whitelist: [],
    comparedScenarioStringCount: duplicateAudit.scenarioStringCount,
    comparedDiagnosticStringCount: duplicateAudit.diagnosticStringCount,
    duplicateCount: 0,
    scope: [
      'crossCuttingDrivers',
      'crossImpactMatrix',
      'scenarios',
      'municipalities',
      'pneStressTest',
      'actions',
      'sentinelIndicators',
    ],
  }

  const semanticIdentity = {
    schemaVersion: 'vocacoes-pne-foresight-v2',
    sourceSnapshot,
    diagnosticEvidenceRefs,
    driverEvidence: crossCuttingDrivers,
    scenarioConfigurations: scenarios.map((scenario) => ({
      scenarioId: scenario.scenarioId,
      configurationStates: scenario.configurationStates,
    })),
    pairwiseDistances: morphologicalField.pairwiseDistances,
    pneGoalBaseline: pneGoals,
  }
  const contentVersion = sha256Text(serializeJson(semanticIdentity))

  return {
    schemaVersion: 'vocacoes-pne-foresight-v2',
    contentVersion,
    publicationStatus: contract.publicationPolicy.status,
    generatedAt: GENERATED_AT,
    title: contract.title,
    publicLabel: contract.publicationPolicy.publicLabel,
    region: {
      stateCode: contract.region.stateCode,
      slug: contract.region.slug,
      name: contract.region.name,
      municipalityCount: contract.region.municipalityIbgeCodes.length,
    },
    horizons: contract.horizons,
    publicationPolicy: contract.publicationPolicy,
    evidencePolicy: contract.evidencePolicy,
    diagnosticBridge,
    sourceSnapshot,
    domainRegistry: contract.domainRegistry,
    factorRegistry: contract.factorRegistry,
    crossCuttingDrivers,
    crossImpactMatrix: contract.crossImpactMatrix,
    morphologicalField,
    scenarios,
    municipalities: municipalLens,
    pneStressTest: scenarioSlice.pneStressTest,
    actions: contract.actions,
    sentinelIndicators: contract.sentinelIndicators,
    sourceGovernance: contract.sourceGovernance,
    methodology: contract.methodology,
    qualityGate: {
      status: 'passed',
      publicDataOnly: true,
      localInputsOnly: true,
      networkDownloadUsed: false,
      databaseUsed: false,
      regionalMunicipalityCoverage: {
        expected: contract.region.municipalityIbgeCodes.length,
        details: contract.region.municipalityIbgeCodes.length,
        finance: contract.region.municipalityIbgeCodes.length,
        pneMatrix: contract.region.municipalityIbgeCodes.length,
      },
      provenanceReferenceCount: diagnosticEvidenceRefs.length,
      unresolvedProvenanceReferenceCount: 0,
      diagnosticDuplicateCount: 0,
      institutionalValidationClaimAllowed: false,
    },
  }
}

function assertSourceDescriptor(value, label) {
  invariant(isRecord(value), 'descritor de ' + label)
  assertNonEmptyString(value.path, 'path de ' + label)
  invariant(typeof value.sha256 === 'string' && /^[a-f0-9]{64}$/u.test(value.sha256), 'hash de ' + label)
  invariant(Number.isInteger(value.byteSize) && value.byteSize > 0, 'tamanho de ' + label)
}

export function assertCenariosEducacaoBundle(bundle) {
  invariant(isRecord(bundle), 'bundle inválido')
  invariant(bundle.schemaVersion === 'vocacoes-pne-foresight-v2', 'schema do bundle')
  invariant(bundle.publicationStatus === 'exploratory_model_public_data_audited', 'status da publicação')
  invariant(bundle.publicationPolicy?.futureProbabilitiesAllowed === false, 'cenários sem probabilidades')
  invariant(bundle.publicationPolicy?.automaticRecommendationAllowed === false, 'cenários sem recomendação automática')
  invariant(bundle.publicationPolicy?.institutionalValidationClaimAllowed === false, 'sem alegação de validação institucional')
  invariant(!Object.prototype.hasOwnProperty.call(bundle, 'baseline'), 'baseline diagnóstico deve estar ausente')
  invariant(!FORBIDDEN_ACTIVE_PATTERN.test(JSON.stringify(bundle)), 'termos retirados ainda presentes no bundle ativo')
  invariant(bundle.region?.slug === 'vale-do-sinos' && bundle.region.municipalityCount === 10, 'região e cobertura')
  invariant(!Object.prototype.hasOwnProperty.call(bundle.region, 'municipalities'), 'lista municipal regional não deve ser publicada')

  const bridge = bundle.diagnosticBridge
  invariant(bridge?.route === '#vocacoes-regiao', 'rota da ponte diagnóstica')
  invariant(bridge?.copiedDiagnosticAssertions === 0, 'nenhuma afirmação diagnóstica copiada')
  assertUniqueStrings(bridge?.evidenceRefs, 'referências diagnósticas publicadas')
  invariant(bridge.evidenceRefs.length === bridge.evidenceRefCount, 'contagem de referências diagnósticas')
  invariant(bridge.resolvedEvidenceRefCount === bridge.evidenceRefCount, 'todas as referências diagnósticas resolvidas')
  invariant(bridge.deDuplicationAudit?.status === 'passed', 'auditoria de não duplicação')
  invariant(bridge.deDuplicationAudit?.minimumLength === 80, 'limiar da auditoria de não duplicação')
  invariant(bridge.deDuplicationAudit?.duplicateCount === 0, 'zero duplicações diagnósticas')
  invariant(Array.isArray(bridge.deDuplicationAudit?.whitelist) && bridge.deDuplicationAudit.whitelist.length === 0, 'sem exceções de duplicação')

  ;['authoringContract', 'advancedBundle', 'advancedRegistry', 'regionConfig', 'municipalityRegistry', 'focalPneMunicipalMatrix'].forEach((key) => {
    assertSourceDescriptor(bundle.sourceSnapshot?.[key], key)
  })
  const regionalInputs = bundle.sourceSnapshot?.regionalPublicInputs
  invariant(regionalInputs?.schemaVersion === 'cenarios-educacao-regional-public-inputs-v1', 'schema das entradas públicas regionais')
  invariant(typeof regionalInputs?.sha256 === 'string' && /^[a-f0-9]{64}$/u.test(regionalInputs.sha256), 'hash das entradas públicas regionais')
  invariant(regionalInputs?.fileCount === 30 && regionalInputs?.municipalityCount === 10, '30 entradas públicas para 10 municípios')
  invariant(regionalInputs?.coverage?.details === 10 && regionalInputs?.coverage?.finance === 10 && regionalInputs?.coverage?.pneMatrix === 10, 'cobertura 10/10 das entradas públicas')

  invariant(Array.isArray(bundle.domainRegistry) && bundle.domainRegistry.length === 6, 'seis domínios')
  invariant(Array.isArray(bundle.factorRegistry) && bundle.factorRegistry.length === 5, 'cinco fatores')
  const factorIds = bundle.factorRegistry.map((factor) => factor.factorId)
  const validStates = new Map(bundle.factorRegistry.map((factor) => [factor.factorId, new Set(factor.states.map((state) => state.stateId))]))

  invariant(Array.isArray(bundle.crossCuttingDrivers) && bundle.crossCuttingDrivers.length === 4, 'quatro drivers transversais')
  assertExactOrder(bundle.crossCuttingDrivers.map((driver) => driver.driverId), Object.keys(REQUIRED_DRIVER_MATURITY), 'ordem dos drivers')
  for (const driver of bundle.crossCuttingDrivers) {
    invariant(driver.maturity === REQUIRED_DRIVER_MATURITY[driver.driverId], 'maturidade publicada de ' + driver.driverId)
    invariant(driver.coverage?.municipalityCount === 10 && driver.coverage?.expectedMunicipalityCount === 10, 'cobertura transversal de ' + driver.driverId)
    assertNonEmptyString(driver.claimCeiling, 'teto de afirmação de ' + driver.driverId)
    assertNonEmptyString(driver.unresolvedGap, 'lacuna de ' + driver.driverId)
  }
  const climate = bundle.crossCuttingDrivers.find((driver) => driver.driverId === 'X_CLIMATE')
  invariant(climate.availability === 'calculated' && climate.calculation.uniqueRegisteredOrRecognizedEventProtocols > 0, 'sentinela climática calculada')
  const technology = bundle.crossCuttingDrivers.find((driver) => driver.driverId === 'X_TECHNOLOGY')
  invariant(technology.availability === 'calculated' && technology.metrics.length === 2, 'duas métricas tecnológicas')
  for (const metric of technology.metrics) {
    for (const lens of ['region', 'novaSantaRita']) {
      const value = metric[lens]
      const expected = percentage(value.numerator, value.denominator)
      invariant(value.denominator === 0 ? value.valueRaw === null : Math.abs(value.valueRaw - expected) < 1e-12, 'razão tecnológica bruta de ' + metric.metricId + '/' + lens)
    }
  }
  const fiscal = bundle.crossCuttingDrivers.find((driver) => driver.driverId === 'X_FISCAL')
  invariant(fiscal.coverage?.reconciledMunicipalityCount === 10, 'dez contextos fiscais reconciliados')
  invariant(fiscal.calculation.minimumMarginPercentagePoints <= fiscal.calculation.medianMarginPercentagePoints, 'ordem mínima/mediana fiscal')
  invariant(fiscal.calculation.medianMarginPercentagePoints <= fiscal.calculation.maximumMarginPercentagePoints, 'ordem mediana/máxima fiscal')
  const regulation = bundle.crossCuttingDrivers.find((driver) => driver.driverId === 'X_REGULATION')
  invariant(regulation.maturity === 'EXPLICIT_GAP' && regulation.availability === 'unavailable', 'lacuna regulatória explícita')
  invariant(regulation.proxyAudit?.eligiblePublicEvidenceCount === 0, 'proxy regulatório excluído')

  invariant(Array.isArray(bundle.scenarios) && bundle.scenarios.length === 4, 'quatro cenários')
  assertExactOrder(bundle.scenarios.map((scenario) => scenario.order), [1, 2, 3, 4], 'ordem dos cenários publicados')
  const scenarioIds = bundle.scenarios.map((scenario) => scenario.scenarioId)
  assertUniqueStrings(scenarioIds, 'IDs dos cenários publicados')
  for (const scenario of bundle.scenarios) {
    assertExactOrder(Object.keys(scenario.configurationStates), factorIds, 'fatores publicados em ' + scenario.scenarioId)
    factorIds.forEach((factorId) => invariant(validStates.get(factorId).has(scenario.configurationStates[factorId]), 'estado publicado de ' + factorId))
    invariant(scenario.domains.length === 6, 'seis domínios em ' + scenario.scenarioId)
    invariant(scenario.distributionalEffects.length === 4, 'quatro efeitos distributivos em ' + scenario.scenarioId)
    invariant(scenario.pneImpacts.length === 5, 'cinco impactos PNE em ' + scenario.scenarioId)
    scenario.evidenceRefs.forEach((evidenceId) => invariant(bridge.evidenceRefs.includes(evidenceId), 'referência diagnóstica resolvida ' + evidenceId))
  }
  const observedDistances = []
  for (let leftIndex = 0; leftIndex < bundle.scenarios.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < bundle.scenarios.length; rightIndex += 1) {
      observedDistances.push(hammingDistance(bundle.scenarios[leftIndex], bundle.scenarios[rightIndex], factorIds))
    }
  }
  invariant(Math.min(...observedDistances) === bundle.morphologicalField?.minimumObservedPairwiseHammingDistance, 'distância morfológica reproduzida')
  invariant(bundle.morphologicalField.minimumObservedPairwiseHammingDistance >= 4, 'distância morfológica observada mínima de quatro')

  invariant(Array.isArray(bundle.municipalities) && bundle.municipalities.length === 1, 'uma lente municipal publicada')
  const municipality = bundle.municipalities[0]
  invariant(municipality.municipalityIbgeCode === FOCAL_MUNICIPALITY_IBGE_CODE && municipality.municipalityName === 'Nova Santa Rita', 'lente exclusiva de Nova Santa Rita')
  invariant(!Object.prototype.hasOwnProperty.call(municipality, 'baselineContribution'), 'sem narrativa diagnóstica municipal copiada')
  assertExactOrder(municipality.scenarioExposures.map((exposure) => exposure.scenarioId), scenarioIds, 'exposições municipais')
  municipality.diagnosticEvidenceRefs.forEach((evidenceId) => invariant(bridge.evidenceRefs.includes(evidenceId), 'referência municipal resolvida ' + evidenceId))

  invariant(bundle.pneStressTest?.municipalityIbgeCode === FOCAL_MUNICIPALITY_IBGE_CODE, 'stress-test PNE focal')
  invariant(bundle.pneStressTest?.goalBaseline?.length === 7, 'sete metas no stress-test PNE')
  invariant(bundle.pneStressTest?.scenarioAssessments?.length === 4, 'quatro avaliações PNE')
  invariant(Array.isArray(bundle.actions) && bundle.actions.length === 10, 'dez opções de decisão')
  invariant(Array.isArray(bundle.sentinelIndicators) && bundle.sentinelIndicators.length === 12, 'doze sentinelas')
  invariant(bundle.methodology?.scenarioType === 'EXPLORATORY_ALTERNATIVE_FUTURES', 'tipo de cenário')
  invariant(bundle.qualityGate?.status === 'passed', 'gate de qualidade aprovado')
  invariant(bundle.qualityGate?.publicDataOnly === true && bundle.qualityGate?.localInputsOnly === true, 'dados públicos locais')
  invariant(bundle.qualityGate?.networkDownloadUsed === false && bundle.qualityGate?.databaseUsed === false, 'sem rede nem banco')
  invariant(bundle.qualityGate?.diagnosticDuplicateCount === 0, 'gate de não duplicação')

  const suspiciousKeys = collectKeys(bundle).filter((key) => /^(probability|probabilities|ranking|score)$/iu.test(key))
  invariant(suspiciousKeys.length === 0, 'campos probabilísticos ou de ranking ausentes')
}

export function assertCenariosEducacaoRegistry(registry, bundleBytes, bundle) {
  invariant(isRecord(registry), 'registro inválido')
  invariant(registry.schemaVersion === 'vocacoes-pne-foresight-registry-v2', 'schema do registro')
  invariant(registry.publicationStatus === bundle.publicationStatus, 'status entre registro e bundle')
  invariant(registry.publicDataValidationStatus === 'passed', 'status do gate público')
  invariant(registry.regionSlug === bundle.region.slug, 'região entre registro e bundle')
  invariant(registry.bundleSha256 === sha256Text(bundleBytes), 'hash do bundle no registro')
  invariant(registry.bundleByteSize === Buffer.byteLength(bundleBytes, 'utf8'), 'tamanho do bundle no registro')
  invariant(registry.contentVersion === bundle.contentVersion, 'versão de conteúdo no registro')
  invariant(registry.scenarioCount === 4 && registry.domainCount === 6 && registry.factorCount === 5, 'contagens do registro')
  invariant(registry.regionalMunicipalityCount === 10, 'cobertura municipal do registro')
  invariant(registry.focalMunicipalityIbgeCode === FOCAL_MUNICIPALITY_IBGE_CODE, 'município focal do registro')
  invariant(registry.minimumPairwiseHammingDistance === bundle.morphologicalField.minimumObservedPairwiseHammingDistance, 'distância no registro')
  invariant(registry.diagnosticDuplicateCount === 0, 'não duplicação no registro')
  invariant(registry.authoringContractSha256 === bundle.sourceSnapshot.authoringContract.sha256, 'hash do contrato no registro')
  invariant(registry.advancedBundleSha256 === bundle.sourceSnapshot.advancedBundle.sha256, 'hash de Vocações no registro')
  invariant(registry.advancedRegistrySha256 === bundle.sourceSnapshot.advancedRegistry.sha256, 'hash do registro de Vocações')
  invariant(registry.focalPneMunicipalMatrixSha256 === bundle.sourceSnapshot.focalPneMunicipalMatrix.sha256, 'hash da matriz PNE focal')
  invariant(registry.regionalPublicInputsSha256 === bundle.sourceSnapshot.regionalPublicInputs.sha256, 'hash das entradas públicas regionais')
  invariant(!FORBIDDEN_ACTIVE_PATTERN.test(JSON.stringify(registry)), 'termos retirados ainda presentes no registro ativo')
}

export async function materializeCenariosEducacaoPublication(repoRoot = DEFAULT_REPO_ROOT) {
  const inputs = await loadInputs(repoRoot)
  const bundle = buildBundle(inputs)
  assertCenariosEducacaoBundle(bundle)
  const bundleBytes = serializeJson(bundle)
  const registry = {
    schemaVersion: 'vocacoes-pne-foresight-registry-v2',
    publicationStatus: bundle.publicationStatus,
    publicDataValidationStatus: bundle.qualityGate.status,
    regionSlug: bundle.region.slug,
    regionalMunicipalityCount: bundle.region.municipalityCount,
    focalMunicipalityIbgeCode: FOCAL_MUNICIPALITY_IBGE_CODE,
    bundlePath: './cenariosEducacaoValeDoSinos.json',
    bundleSha256: sha256Text(bundleBytes),
    bundleByteSize: Buffer.byteLength(bundleBytes, 'utf8'),
    contentVersion: bundle.contentVersion,
    scenarioCount: bundle.scenarios.length,
    domainCount: bundle.domainRegistry.length,
    factorCount: bundle.factorRegistry.length,
    minimumPairwiseHammingDistance: bundle.morphologicalField.minimumObservedPairwiseHammingDistance,
    diagnosticDuplicateCount: bundle.diagnosticBridge.deDuplicationAudit.duplicateCount,
    authoringContractSha256: bundle.sourceSnapshot.authoringContract.sha256,
    advancedBundleSha256: bundle.sourceSnapshot.advancedBundle.sha256,
    advancedRegistrySha256: bundle.sourceSnapshot.advancedRegistry.sha256,
    focalPneMunicipalMatrixSha256: bundle.sourceSnapshot.focalPneMunicipalMatrix.sha256,
    regionalPublicInputsSha256: bundle.sourceSnapshot.regionalPublicInputs.sha256,
    generatedAt: bundle.generatedAt,
  }
  const registryBytes = serializeJson(registry)
  assertCenariosEducacaoRegistry(registry, bundleBytes, bundle)
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

async function assertDeterministicMaterialization(repoRoot) {
  const first = await materializeCenariosEducacaoPublication(repoRoot)
  const second = await materializeCenariosEducacaoPublication(repoRoot)
  invariant(first.bundleBytes === second.bundleBytes, 'materialização do bundle não determinística')
  invariant(first.registryBytes === second.registryBytes, 'materialização do registro não determinística')
  return first
}

export async function checkCenariosEducacaoPublication(repoRoot = DEFAULT_REPO_ROOT) {
  const materialized = await assertDeterministicMaterialization(repoRoot)
  for (const [kind, expected] of [
    ['bundle', materialized.bundleBytes],
    ['registry', materialized.registryBytes],
  ]) {
    const target = materialized.paths[kind]
    invariant(await exists(target), 'arquivo gerado ausente: ' + path.relative(repoRoot, target))
    const actual = await readFile(target, 'utf8')
    invariant(actual === expected, 'arquivo gerado divergente: ' + path.relative(repoRoot, target))
  }
  return materialized
}

export async function promoteCenariosEducacaoPublication(repoRoot = DEFAULT_REPO_ROOT) {
  const materialized = await assertDeterministicMaterialization(repoRoot)
  const outputDir = path.dirname(materialized.paths.bundle)
  await mkdir(outputDir, { recursive: true })
  const tempRoot = path.join(repoRoot, '.tmp', 'vocacoes-pne', 'education-scenarios-v2')
  await mkdir(tempRoot, { recursive: true })
  const stageDir = await mkdtemp(path.join(tempRoot, 'publication-'))
  const staged = {
    bundle: path.join(stageDir, path.basename(materialized.paths.bundle)),
    registry: path.join(stageDir, path.basename(materialized.paths.registry)),
  }
  const journal = []
  try {
    await writeFile(staged.bundle, materialized.bundleBytes, 'utf8')
    await writeFile(staged.registry, materialized.registryBytes, 'utf8')
    const stagedBundleBytes = await readFile(staged.bundle, 'utf8')
    const stagedRegistryBytes = await readFile(staged.registry, 'utf8')
    const stagedBundle = parseJson(stagedBundleBytes, 'bundle em staging')
    const stagedRegistry = parseJson(stagedRegistryBytes, 'registro em staging')
    assertCenariosEducacaoBundle(stagedBundle)
    assertCenariosEducacaoRegistry(stagedRegistry, stagedBundleBytes, stagedBundle)

    for (const kind of ['bundle', 'registry']) {
      const target = materialized.paths[kind]
      const desired = kind === 'bundle' ? materialized.bundleBytes : materialized.registryBytes
      const targetExists = await exists(target)
      if (targetExists && await readFile(target, 'utf8') === desired) continue
      const backup = targetExists ? target + '.foresight-backup-' + process.pid : null
      if (backup !== null) await copyFile(target, backup)
      journal.push({ target, backup })
      const next = target + '.foresight-next-' + process.pid
      await copyFile(staged[kind], next)
      if (targetExists) await rm(target)
      await rename(next, target)
    }
  } catch (error) {
    for (const { target, backup } of journal.reverse()) {
      await rm(target, { force: true })
      if (backup !== null && await exists(backup)) await rename(backup, target)
    }
    throw error
  } finally {
    for (const { backup } of journal) {
      if (backup !== null) await rm(backup, { force: true })
    }
    await rm(stageDir, { recursive: true, force: true })
  }
  await checkCenariosEducacaoPublication(repoRoot)
  return materialized
}

export const CENARIOS_EDUCACAO_PATHS = Object.freeze({
  authoringContract: AUTHORING_RELATIVE_PATH,
  advancedBundle: ADVANCED_BUNDLE_RELATIVE_PATH,
  advancedRegistry: ADVANCED_REGISTRY_RELATIVE_PATH,
  regionConfig: REGION_CONFIG_RELATIVE_PATH,
  municipalityRegistry: MUNICIPALITY_REGISTRY_RELATIVE_PATH,
  detailsPattern: 'public/data/municipios/<IBGE>/details.json',
  financePattern: 'public/data/municipios/<IBGE>/financeiro.json',
  pneMatrixPattern: 'public/data/pne2026-matriz/municipios/<IBGE>.json',
  bundle: BUNDLE_RELATIVE_PATH,
  registry: REGISTRY_RELATIVE_PATH,
})
