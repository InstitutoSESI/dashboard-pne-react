import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'

const contractPath = new URL('../contracts/pne2026-goal-indicator-contract.json', import.meta.url)
const policyPath = new URL('../contracts/pne2026-diagnostic-presentation-policy.json', import.meta.url)
const indicatorCatalogPath = new URL('../src/data/diagnostic/indicatorCatalog.json', import.meta.url)
const publicIndicatorCatalogPath = new URL('../public/data/indicadores.json', import.meta.url)
const generatedContractDocumentationPath = new URL(
  '../docs/generated/PNE_2026_CONTRACT.md',
  import.meta.url,
)

export const FORBIDDEN_PRESENTATION_FIELDS = new Set([
  'goalId',
  'indicatorId',
  'mode',
  'tracksGoal',
  'tracks_goal',
  'hasDistance',
  'canDistance',
  'canStatus',
  'canProjection',
  'includeInDiagnostic',
  'includeInReferenceSummary',
  'target',
  'reference',
  'deadline',
  'direction',
  'formulaId',
  'sourceIds',
  'territoriality',
  'classificationPolicy',
  'missingPolicy',
  'valuePolicy',
])

const ALLOWED_RELATION_FIELDS = new Set([
  'relationId',
  'themeId',
  'displayOrder',
  'summaryPriority',
  'displayGroup',
  'layoutHint',
  'narrativeTemplateId',
])
const SUMMARY_PRIORITIES = new Set(['essential', 'standard'])
const PUBLIC_FREQUENCY_LABELS = {
  annual: 'anual',
  biennial: 'bienal',
  decennial_irregular: 'decenal/irregular',
  triennial_cycle: 'ciclo trienal',
}

function firstJsonDocument(contents) {
  let depth = 0
  let started = false
  let inString = false
  let escaped = false
  for (let index = 0; index < contents.length; index += 1) {
    const character = contents[index]
    if (!started) {
      if (/\s/u.test(character)) continue
      if (character !== '{' && character !== '[') return null
      started = true
      depth = 1
      continue
    }
    if (inString) {
      if (escaped) {
        escaped = false
      } else if (character === '\\') {
        escaped = true
      } else if (character === '"') {
        inString = false
      }
      continue
    }
    if (character === '"') {
      inString = true
    } else if (character === '{' || character === '[') {
      depth += 1
    } else if (character === '}' || character === ']') {
      depth -= 1
      if (depth === 0) return contents.slice(0, index + 1)
    }
  }
  return null
}

function readJson(path, { recoverTrailingOutput = false } = {}) {
  const contents = fs.readFileSync(path, 'utf8')
  try {
    return JSON.parse(contents)
  } catch (error) {
    if (!recoverTrailingOutput) throw error
    const recovered = firstJsonDocument(contents)
    if (!recovered) throw error
    return JSON.parse(recovered)
  }
}

function stableJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`
}

function writeGeneratedFile(path, contents) {
  const target = fileURLToPath(path)
  const suffix = `${process.pid}-${Date.now()}`
  const temporary = `${target}.${suffix}.tmp`
  const backup = `${target}.${suffix}.bak`
  fs.writeFileSync(temporary, contents, 'utf8')
  try {
    if (!fs.existsSync(target)) {
      fs.renameSync(temporary, target)
      return
    }
    fs.renameSync(target, backup)
    try {
      fs.renameSync(temporary, target)
    } catch (error) {
      fs.renameSync(backup, target)
      throw error
    }
    fs.rmSync(backup)
  } catch (error) {
    if (fs.existsSync(temporary)) fs.rmSync(temporary)
    if (fs.existsSync(backup) && !fs.existsSync(target)) {
      fs.renameSync(backup, target)
    }
    throw error
  }
}

function normalizeObject(value) {
  if (Array.isArray(value)) return value.map(normalizeObject)
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, normalizeObject(value[key])]),
    )
  }
  return value
}

function normalizedHash(value) {
  return createHash('sha256')
    .update(JSON.stringify(normalizeObject(value)))
    .digest('hex')
}

function projectionMetadata(contract, policy) {
  return {
    generator: 'scripts/generate-diagnostic-catalog.mjs',
    contractVersion: contract.contractVersion,
    contractNormalizedSha256: normalizedHash(contract),
    presentationPolicyVersion: policy.policyVersion,
    presentationPolicyNormalizedSha256: normalizedHash(policy),
  }
}

function requireCondition(condition, message) {
  if (!condition) throw new Error(`Política visual do Diagnóstico PNE 2026 inválida: ${message}`)
}

function forbiddenPaths(value, path = '$') {
  if (Array.isArray(value)) {
    return value.flatMap((child, index) => forbiddenPaths(child, `${path}[${index}]`))
  }
  if (!value || typeof value !== 'object') return []
  return Object.entries(value).flatMap(([key, child]) => {
    const childPath = `${path}.${key}`
    return [
      ...(FORBIDDEN_PRESENTATION_FIELDS.has(key) ? [childPath] : []),
      ...forbiddenPaths(child, childPath),
    ]
  })
}

export function validateDiagnosticPresentationPolicy(policy, contract) {
  requireCondition(
    policy?.schemaVersion === 'pne2026-diagnostic-presentation-policy-v1',
    'schemaVersion não reconhecida',
  )
  requireCondition(policy?.policyVersion === '1.7.0', 'policyVersion inválida')
  const policyForbiddenPaths = forbiddenPaths(policy)
  requireCondition(
    policyForbiddenPaths.length === 0,
    `campos metodológicos proibidos: ${policyForbiddenPaths.join(', ')}`,
  )

  const themeIds = new Set()
  const themeOrders = new Set()
  for (const theme of policy.themes ?? []) {
    requireCondition(
      typeof theme.themeId === 'string' && !themeIds.has(theme.themeId),
      `themeId inválido ou duplicado: ${theme.themeId}`,
    )
    requireCondition(
      Number.isInteger(theme.displayOrder)
        && theme.displayOrder > 0
        && !themeOrders.has(theme.displayOrder),
      `ordem de tema inválida ou duplicada: ${theme.displayOrder}`,
    )
    requireCondition(typeof theme.label === 'string', `${theme.themeId}.label ausente`)
    themeIds.add(theme.themeId)
    themeOrders.add(theme.displayOrder)
  }

  const contractRelations = new Map(
    contract.relations.map((relation) => [relation.relationId, relation]),
  )
  const expected = new Set(
    contract.relations
      .filter((relation) => relation.includeInDiagnostic && relation.mode !== 'hidden')
      .map((relation) => relation.relationId),
  )
  const seen = new Set()
  const ordersByTheme = new Set()
  for (const entry of policy.relations ?? []) {
    const extraFields = Object.keys(entry).filter((key) => !ALLOWED_RELATION_FIELDS.has(key))
    requireCondition(
      extraFields.length === 0,
      `relação visual contém campos não editoriais: ${extraFields.join(', ')}`,
    )
    const forbiddenFields = Object.keys(entry).filter((key) => FORBIDDEN_PRESENTATION_FIELDS.has(key))
    requireCondition(
      forbiddenFields.length === 0,
      `relação visual contém campos metodológicos: ${forbiddenFields.join(', ')}`,
    )
    const relation = contractRelations.get(entry.relationId)
    requireCondition(relation, `relationId inexistente: ${entry.relationId}`)
    requireCondition(!seen.has(entry.relationId), `relationId duplicado: ${entry.relationId}`)
    requireCondition(relation.includeInDiagnostic, `${entry.relationId} não é elegível`)
    requireCondition(relation.mode !== 'hidden', `${entry.relationId} é hidden`)
    requireCondition(themeIds.has(entry.themeId), `themeId inexistente: ${entry.themeId}`)
    requireCondition(
      Number.isInteger(entry.displayOrder) && entry.displayOrder > 0,
      `${entry.relationId}.displayOrder inválido`,
    )
    const themeOrder = `${entry.themeId}:${entry.displayOrder}`
    requireCondition(!ordersByTheme.has(themeOrder), `ordem duplicada no tema: ${themeOrder}`)
    requireCondition(
      SUMMARY_PRIORITIES.has(entry.summaryPriority),
      `${entry.relationId}.summaryPriority inválida`,
    )
    seen.add(entry.relationId)
    ordersByTheme.add(themeOrder)
  }
  assert.deepEqual([...seen].sort(), [...expected].sort())
  return policy
}

function legalMilestones(contract, relation, { filterDimension = true } = {}) {
  const goal = contract.goals[relation.goalId]
  const referenceId = relation.referenceId
    ?? `reference.${relation.goalId}.${relation.indicatorId}`
  const references = goal.legalReferences
    .filter((reference) => reference.referenceId === referenceId)
  return references.flatMap((reference) => reference.milestones)
    .filter((milestone) => (
      !filterDimension
      || relation.referenceDimension == null
      || milestone.dimension === relation.referenceDimension
    ))
    .sort((left, right) => left.year - right.year)
}

function projectionRelationForIndicator(contract, indicatorId) {
  const relations = contract.relations.filter(
    (relation) => relation.indicatorId === indicatorId,
  )
  return relations.length === 1 ? relations[0] : null
}

const ACCELERATED_CATALOG_SEEDS = {
  educacao_indigena_cobertura_estimada_4_17: {
    category: 'territorios',
    territorialCut: {
      numerator: 'município da escola',
      denominator: 'população indígena residente municipal em 2022',
    },
  },
  aee_oferta_escolas_elegiveis: {
    category: 'educacao_especial',
    territorialCut: {
      numerator: 'escolas localizadas no município',
      denominator: 'escolas localizadas no município',
    },
  },
  superior_concluintes_oferta_local: {
    category: 'educacao_superior',
    territorialCut: {
      numerator: 'localização da oferta do curso',
      denominator: 'não se aplica',
    },
  },
  superior_docentes_mestres_doutores_sede: {
    category: 'educacao_superior',
    territorialCut: {
      numerator: 'sede administrativa da IES',
      denominator: 'sede administrativa da IES',
    },
  },
}

function acceleratedIndicatorSeed(template, contract, indicatorId) {
  const indicator = contract.indicators[indicatorId]
  const relation = projectionRelationForIndicator(contract, indicatorId)
  const formula = contract.formulas[indicator?.formulaId]
  const methodology = formula?.catalogProjection
  const seed = ACCELERATED_CATALOG_SEEDS[indicatorId]
  requireCondition(indicator, `indicador acelerado ausente: ${indicatorId}`)
  requireCondition(relation, `relação acelerada ausente: ${indicatorId}`)
  requireCondition(methodology, `projeção de catálogo ausente: ${indicatorId}`)
  requireCondition(seed, `semente de catálogo ausente: ${indicatorId}`)
  requireCondition(
    ['complementary', 'tracking'].includes(relation.mode),
    `indicador acelerado sem modo público: ${indicatorId}`,
  )
  const legalValidation = template.indicators.find(
    (item) => item.legalValidation,
  )?.legalValidation
  requireCondition(legalValidation, 'validação legal do catálogo ausente')

  return {
    administrativeDependence: ['all'],
    category: seed.category,
    correspondence: 'partial',
    legalCorrespondence: 'partial',
    legalTextValidated: true,
    legalValidation: structuredClone(legalValidation),
    operationalizationStatus: 'informational',
    currentImplementation: {
      legalTextCheckedAt: legalValidation.validatedAt,
      officialInepPerEntityDefinitionStatus: 'pending_within_180_day_legal_window',
      tracksGoal: false,
    },
    denominator: methodology.denominator,
    direction: null,
    finality: 'context',
    formula: methodology.formula,
    indicatorId,
    legalGoalRefs: [relation.goalId],
    limits: methodology.limits,
    name: indicator.publicTitle,
    numerator: methodology.numerator,
    periodicity: PUBLIC_FREQUENCY_LABELS[indicator.expectedFrequency]
      ?? indicator.expectedFrequency,
    sourceIds: indicator.sourceIds,
    targets: [],
    territorialCut: seed.territorialCut,
    unit: indicator.unit,
    validRange: methodology.validRange,
    valueDomainPolicy: methodology.valueDomainPolicy,
    displayPolicy: methodology.displayPolicy,
  }
}

function projectIndicatorCatalog(template, contract, policy) {
  const projected = structuredClone(template)
  projected.projectionMetadata = projectionMetadata(contract, policy)
  projected.generatedFrom = (
    'contracts/pne2026-goal-indicator-contract.json + '
    + 'contracts/pne2026-diagnostic-presentation-policy.json'
  )
  const indicatorSeeds = [...template.indicators]
  const registeredIds = new Set(indicatorSeeds.map((item) => item.indicatorId))
  if (!registeredIds.has('fundamental_concluido_15_mais')) {
    const censusCompletionSeed = indicatorSeeds.find(
      (item) => item.indicatorId === 'fundamental_concluido_15_29',
    )
    requireCondition(
      censusCompletionSeed,
      'template do indicador fundamental_concluido_15_29 ausente',
    )
    indicatorSeeds.push({
      ...structuredClone(censusCompletionSeed),
      indicatorId: 'fundamental_concluido_15_mais',
    })
  }
  for (const indicatorId of Object.keys(ACCELERATED_CATALOG_SEEDS)) {
    if (!registeredIds.has(indicatorId)) {
      indicatorSeeds.push(
        acceleratedIndicatorSeed(template, contract, indicatorId),
      )
    }
  }
  projected.indicators = indicatorSeeds.map((catalogSeed) => {
    const indicator = contract.indicators[catalogSeed.indicatorId]
    if (!indicator) {
      // Indicadores informativos fora do contrato PNE continuam fazendo parte
      // do catálogo público atual.
      return catalogSeed
    }
    const relation = projectionRelationForIndicator(contract, indicator.indicatorId)
    const goal = relation ? contract.goals[relation.goalId] : null
    const milestones = relation
      ? legalMilestones(contract, relation, { filterDimension: false })
      : []
    const formula = contract.formulas[indicator.formulaId]
    const methodology = formula?.catalogProjection
    return {
      ...catalogSeed,
      currentImplementation: {
        ...catalogSeed.currentImplementation,
        tracksGoal: Boolean(
          ['progress', 'tracking'].includes(relation?.mode)
          && relation.canStatus,
        ),
      },
      direction: milestones.length ? goal?.direction ?? null : null,
      ...(methodology
        ? {
            denominator: methodology.denominator,
            displayPolicy: methodology.displayPolicy,
            formula: methodology.formula,
            limits: methodology.limits,
            name: indicator.publicTitle,
            numerator: methodology.numerator,
            validRange: methodology.validRange,
            valueDomainPolicy: methodology.valueDomainPolicy,
          }
        : {}),
      indicatorId: indicator.indicatorId,
      legalGoalRefs: relation ? [relation.goalId] : [],
      periodicity: PUBLIC_FREQUENCY_LABELS[indicator.expectedFrequency]
        ?? indicator.expectedFrequency,
      sourceIds: indicator.sourceIds,
      targets: milestones.map((milestone) => ({
        dimension: milestone.dimension ?? 'overall',
        direction: milestone.direction,
        legalGoalRef: relation.goalId,
        validationStatus: 'official_law',
        value: milestone.value,
        year: milestone.year,
      })),
      unit: indicator.unit,
    }
  })
  projected.indicatorCount = projected.indicators.length
  return projected
}

function relationReferenceDescriptor(contract, relation) {
  if (!relation) return null
  if (relation.referenceId) {
    const goal = contract.goals[relation.goalId]
    const reference = goal?.legalReferences?.find(
      (candidate) => candidate.referenceId === relation.referenceId,
    )
    const milestones = legalMilestones(contract, relation)
    if (reference && milestones.length) {
      return {
        kind: 'legal',
        referenceId: reference.referenceId,
        validationStatus: reference.validationStatus,
        direction: goal.direction,
        milestones,
      }
    }
  }

  const monitoring = contract.monitoringReferences?.[relation.comparisonReferenceId]
  if (!monitoring) return null
  return {
    kind: 'monitoring',
    referenceId: monitoring.referenceId,
    validationStatus: monitoring.validationStatus,
    direction: monitoring.direction,
    value: monitoring.value,
    unit: monitoring.unit,
    milestones: [],
  }
}

function publicReferenceLabel(reference) {
  if (!reference) return null
  if (reference.kind === 'monitoring') return 'Referência de acompanhamento'
  const firstYear = reference.milestones[0]?.year
  return Number.isFinite(firstYear) ? `Meta PNE ${firstYear}` : 'Meta do PNE'
}

export function projectPublicIndicatorCatalog(template, contract) {
  const projected = structuredClone(template)
  const cycle = projected.cycles?.[contract.cycle.cycleId]
  requireCondition(cycle?.categories, 'ciclo PNE 2026 ausente do catálogo público')

  cycle.categories = cycle.categories.map((category) => ({
    ...category,
    items: category.items.map((itemSeed) => {
      const indicator = contract.indicators[itemSeed.key]
      if (!indicator) return itemSeed

      const relation = projectionRelationForIndicator(contract, indicator.indicatorId)
      const formula = contract.formulas[indicator.formulaId]
      const reference = relationReferenceDescriptor(contract, relation)
      const methodology = formula?.catalogProjection
      const projectedItem = {
        ...itemSeed,
        label: relation?.publicLabelOverride ?? indicator.publicTitle,
        desc: relation?.publicDescriptionOverride
          ?? indicator.publicDescription
          ?? formula?.description
          ?? itemSeed.desc,
        formulaId: indicator.formulaId,
        formula: methodology?.formula ?? formula?.description ?? formula?.implementationKey,
        sourceIds: indicator.sourceIds,
        contractVersion: contract.contractVersion,
        valuePolicyId: indicator.valuePolicyId,
        conceptuallyMayExceed100: indicator.conceptuallyMayExceed100 === true,
      }
      const referenceLabel = publicReferenceLabel(reference)
      if (referenceLabel) {
        projectedItem.meta_label = referenceLabel
        projectedItem.reference = reference
      } else {
        delete projectedItem.meta_label
        delete projectedItem.reference
      }
      return projectedItem
    }),
  }))
  projected.contractProjection = {
    generator: 'scripts/generate-diagnostic-catalog.mjs',
    contractVersion: contract.contractVersion,
    contractNormalizedSha256: normalizedHash(contract),
  }
  return projected
}

function markdownCell(value) {
  if (value == null || value === '') return '—'
  return String(value).replaceAll('|', '\\|').replaceAll(/\r?\n/g, ' ')
}

function renderReferenceValue(reference) {
  if (!reference) return '—'
  if (reference.kind === 'monitoring') {
    return `${reference.value} ${reference.unit}`
  }
  return reference.milestones
    .map((milestone) => `${milestone.value} ${milestone.unit} (${milestone.year})`)
    .join('; ')
}

export function renderPneContractDocumentation(contract) {
  const modes = Object.groupBy(contract.relations, (relation) => relation.mode)
  const relationRows = contract.relations
    .toSorted((left, right) => (
      contract.goals[left.goalId].legalOrder - contract.goals[right.goalId].legalOrder
      || left.indicatorId.localeCompare(right.indicatorId, 'pt-BR')
    ))
    .map((relation) => {
      const indicator = contract.indicators[relation.indicatorId]
      const formula = contract.formulas[indicator.formulaId]
      const reference = relationReferenceDescriptor(contract, relation)
      const deadline = reference?.kind === 'legal'
        ? reference.milestones.map((milestone) => milestone.year).join(', ')
        : reference?.kind === 'monitoring'
          ? 'sem prazo legal'
          : 'não se aplica'
      return `| ${markdownCell(relation.goalId)} | ${markdownCell(indicator.indicatorId)} | ${markdownCell(relation.mode)} | ${markdownCell(reference?.kind)} | ${markdownCell(renderReferenceValue(reference))} | ${markdownCell(deadline)} | ${markdownCell(formula?.catalogProjection?.formula ?? formula?.description ?? formula?.implementationKey)} |`
    })

  const sourceRows = Object.values(contract.sources)
    .toSorted((left, right) => left.sourceId.localeCompare(right.sourceId, 'pt-BR'))
    .map((source) => {
      const officialUrl = source.officialUrl
        ? `[link oficial](${source.officialUrl})`
        : '—'
      return `| ${markdownCell(source.sourceId)} | ${markdownCell(source.organization)} | ${markdownCell(source.period)} | ${officialUrl} |`
    })

  const populationSources = [
    contract.sources.municipal_age_population_panel,
    contract.sources.ibge_population_projection_2024,
  ].filter(Boolean)
  const lineageRows = populationSources.map((source) => {
    const lineage = source.lineage ?? {}
    const artifact = lineage.latestSourceArtifact ?? lineage.sourceArtifact ?? '—'
    const hash = lineage.latestSourceSha256 ?? lineage.sourceSha256 ?? '—'
    const configuration = lineage.pathConfiguration ?? '—'
    return `| ${markdownCell(source.sourceId)} | ${markdownCell(lineage.upstreamDataset ?? source.publicTitle)} | ${markdownCell(artifact)} | \`${markdownCell(hash)}\` | \`${markdownCell(configuration)}\` |`
  })

  return [
    '# Contrato PNE 2026–2036',
    '',
    '> Arquivo gerado por `scripts/generate-diagnostic-catalog.mjs`. Não edite manualmente.',
    '',
    `- Fonte canônica: \`contracts/pne2026-goal-indicator-contract.json\``,
    `- Versão do contrato: \`${contract.contractVersion}\``,
    `- Hash normalizado SHA-256: \`${normalizedHash(contract)}\``,
    `- Metas legais: ${Object.keys(contract.goals).length}`,
    `- Indicadores e fórmulas: ${Object.keys(contract.indicators).length}`,
    `- Relações: ${contract.relations.length} (${modes.progress?.length ?? 0} progresso, ${modes.tracking?.length ?? 0} acompanhamento, ${modes.complementary?.length ?? 0} complementares e ${modes.hidden?.length ?? 0} ocultas)`,
    '',
    '## Metas, prazos e fórmulas',
    '',
    '| Meta | Indicador | Modo | Tipo de referência | Valor de referência | Prazo | Fórmula |',
    '| --- | --- | --- | --- | --- | --- | --- |',
    ...relationRows,
    '',
    '## Linhagem populacional',
    '',
    '| Fonte | Conjunto de origem | Artefato versionado | SHA-256 | Configuração reproduzível |',
    '| --- | --- | --- | --- | --- | --- |',
    ...lineageRows,
    '',
    '## Fontes declaradas',
    '',
    '| Identificador | Organização | Período | URL |',
    '| --- | --- | --- | --- |',
    ...sourceRows,
    '',
  ].join('\n')
}

export function projectDiagnosticArtifacts({
  contract,
  policy,
  indicatorCatalog,
}) {
  validateDiagnosticPresentationPolicy(policy, contract)
  return {
    indicatorCatalog: projectIndicatorCatalog(indicatorCatalog, contract, policy),
  }
}

function run() {
  const check = process.argv.includes('--check')
  const contract = readJson(contractPath)
  const policy = readJson(policyPath)
  const indicatorCatalog = readJson(indicatorCatalogPath)
  const publicIndicatorCatalog = readJson(publicIndicatorCatalogPath, {
    recoverTrailingOutput: !check,
  })
  const projected = projectDiagnosticArtifacts({
    contract,
    policy,
    indicatorCatalog,
  })
  const outputs = [
    [indicatorCatalogPath, stableJson(projected.indicatorCatalog)],
    [
      publicIndicatorCatalogPath,
      stableJson(projectPublicIndicatorCatalog(publicIndicatorCatalog, contract)),
    ],
    [
      generatedContractDocumentationPath,
      `${renderPneContractDocumentation(contract)}\n`,
    ],
  ]
  const stale = outputs.filter(([path, contents]) => (
    !fs.existsSync(path) || fs.readFileSync(path, 'utf8') !== contents
  ))
  if (check) {
    if (stale.length) {
      const paths = stale.map(([path]) => fileURLToPath(path)).join('\n')
      throw new Error(`Artefatos gerados do contrato PNE desatualizados:\n${paths}`)
    }
    return
  }
  for (const [path, contents] of stale) {
    fs.mkdirSync(new URL('.', path), { recursive: true })
    writeGeneratedFile(path, contents)
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) run()
