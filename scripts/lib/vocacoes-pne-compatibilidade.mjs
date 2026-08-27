import {
  loadCatalogoMecanismos,
  loadCatalogoReferencias,
  loadRegistroSeries,
  loadRegrasUniverso,
} from './vocacoes-pne-registro.mjs'

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0
}

function isAgeRange(value) {
  return (
    Array.isArray(value)
    && value.length === 2
    && Number.isInteger(value[0])
    && (value[1] === null || Number.isInteger(value[1]))
  )
}

function containsAgeRange(container, contained) {
  if (!isAgeRange(container) || !isAgeRange(contained)) return false
  if (container[0] > contained[0]) return false
  if (container[1] === null) return true
  if (contained[1] === null) return false
  return container[1] >= contained[1]
}

function normalizeText(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/gu, '')
    .toLowerCase()
}

function findPair(pairs, educationalSeriesId, territorialSeriesId) {
  return (pairs ?? []).find((pair) => (
    pair.educacional === educationalSeriesId
    && pair.territorial === territorialSeriesId
  )) ?? null
}

function resolvePairDependencies(dependencies = {}) {
  return {
    mecanismos: dependencies.mecanismos ?? loadCatalogoMecanismos(),
    registro: dependencies.registro ?? loadRegistroSeries(),
    regras: dependencies.regras ?? loadRegrasUniverso(),
  }
}

function resolveCardDependencies(dependencies = {}) {
  return {
    mecanismos: dependencies.mecanismos ?? loadCatalogoMecanismos(),
    referencias: dependencies.referencias ?? loadCatalogoReferencias(),
  }
}

function populationReferenceRange(educationalSeries, educationalSeriesId, regras) {
  const registeredRange = educationalSeries?.populacaoReferencia?.faixaEtaria
  if (isAgeRange(registeredRange)) return registeredRange

  const rulesRange = regras.populacaoReferenciaMatriculas?.[educationalSeriesId]
    ?.faixaEtaria
  return isAgeRange(rulesRange) ? rulesRange : null
}

function isPendingSeries(series) {
  return typeof series.status === 'string' && series.status.startsWith('pendente_')
}

function annualOverlapPoints(left, right) {
  if (
    left.periodGranularity !== 'annual'
    || right.periodGranularity !== 'annual'
    || !Number.isInteger(left.periodStart)
    || !Number.isInteger(left.periodEnd)
    || !Number.isInteger(right.periodStart)
    || !Number.isInteger(right.periodEnd)
  ) {
    return 0
  }

  const start = Math.max(left.periodStart, right.periodStart)
  const end = Math.min(left.periodEnd, right.periodEnd)
  return Math.max(0, end - start + 1)
}

export function validatePair(
  {
    educationalSeriesId,
    territorialSeriesId,
    mechanismId,
    atendimentoAparente = false,
  },
  dependencies,
) {
  const { mecanismos, registro, regras } = resolvePairDependencies(dependencies)
  const mechanism = mecanismos.mecanismos.find(({ id }) => id === mechanismId)
  const avisos = []
  const blocked = (reasonCode) => ({ allowed: false, reasonCode, avisos })

  // Regra 1.
  if (!mechanism) return blocked('mecanismo-desconhecido')

  const permittedPair = findPair(
    mechanism.paresPermitidos,
    educationalSeriesId,
    territorialSeriesId,
  )
  const provisionalPair = findPair(
    mechanism.paresProvisorios,
    educationalSeriesId,
    territorialSeriesId,
  )
  const listedPair = permittedPair ?? provisionalPair

  if (provisionalPair) avisos.push('aproximacao-declarada')
  if (isNonEmptyString(listedPair?.nota)) avisos.push(listedPair.nota)

  const seriesById = new Map(registro.series.map((series) => [series.seriesId, series]))
  const educationalSeries = seriesById.get(educationalSeriesId)
  const territorialSeries = seriesById.get(territorialSeriesId)

  // Regra 2.
  const referenceRange = populationReferenceRange(
    educationalSeries,
    educationalSeriesId,
    regras,
  )
  if (
    territorialSeries?.universo === 'populacao_residente'
    && isAgeRange(territorialSeries.faixaEtaria)
    && isAgeRange(referenceRange)
    && !containsAgeRange(referenceRange, territorialSeries.faixaEtaria)
    && !(
      provisionalPair
      && containsAgeRange(territorialSeries.faixaEtaria, referenceRange)
    )
  ) {
    return blocked('faixa-etaria-incompativel')
  }

  // Regra 3.
  if (educationalSeries && territorialSeries?.universo === 'cadastro_social') {
    return blocked('cadastro-nao-denominador')
  }

  // Regra 4.
  const mechanismRange = mechanism.populacaoReferencia?.faixaEtaria
  const isYouthPhenomenon = (
    isAgeRange(mechanismRange)
    && containsAgeRange([15, 24], mechanismRange)
  )
  if (
    territorialSeries?.universo === 'trabalho_formal_local'
    && territorialSeries.faixaEtaria === null
    && isYouthPhenomenon
    && !isNonEmptyString(listedPair?.nota)
  ) {
    return blocked('sem-recorte-de-idade')
  }

  // Regra 5.
  if (
    territorialSeries?.universo === 'coorte_censitaria'
    && mechanism.defasagem.tipo !== 'acumulada'
  ) {
    return blocked('fotografia-nao-serie')
  }

  // Regra 6.
  if (!listedPair) return blocked('fora-do-catalogo')

  // Regra 7.
  if (!educationalSeries || !territorialSeries) {
    return blocked('serie-desconhecida')
  }

  // Regra 8.
  if (
    mechanism.defasagem.tipo !== 'acumulada'
    && !isPendingSeries(educationalSeries)
    && !isPendingSeries(territorialSeries)
    && annualOverlapPoints(educationalSeries, territorialSeries)
      < mechanism.janelaMinimaPontos
  ) {
    return blocked('janela-insuficiente')
  }

  // Regra 9. Pares provisórios permanecem aproximações declaradas, não razões
  // de nível já permitidas pelo catálogo.
  const isMixedLevelRatio = (
    permittedPair !== null
    && educationalSeries.universo === 'matriculas_localizadas'
    && educationalSeries.lente === 'escolas_da_regiao'
    && territorialSeries.universo === 'populacao_residente'
    && territorialSeries.lente === 'residentes'
    && normalizeText(mechanism.decomposicaoPrevia).includes('atendimento aparente')
  )
  if (isMixedLevelRatio && atendimentoAparente !== true) {
    return blocked('lente-mista-nao-declarada')
  }

  return { allowed: true, reasonCode: null, avisos }
}

export function validateCardCatalog(card, dependencies) {
  const { mecanismos, referencias } = resolveCardDependencies(dependencies)
  const violations = []
  const mechanismId = card?.internal?.mechanism_id
  const mechanism = mecanismos.mecanismos.find(({ id }) => id === mechanismId)

  if (isNonEmptyString(mechanismId) && !mechanism) {
    violations.push({
      ruleId: 'mecanismo-desconhecido',
      field: 'internal.mechanism_id',
    })
  }
  if (mechanism && !mechanism.direcoes.includes(card?.direction)) {
    violations.push({ ruleId: 'direcao-nao-permitida', field: 'direction' })
  }

  const catalogFields = [
    ['pne_topics', referencias.temasPne],
    ['monitoring_indicators', referencias.indicadores],
    ['sources', referencias.fontes],
  ]
  for (const [field, catalog] of catalogFields) {
    const items = card?.[field]
    if (!Array.isArray(items)) continue

    const labels = new Set(catalog.map(({ label }) => label))
    const seen = new Set()
    let duplicate = false
    items.forEach((item, index) => {
      if (!isNonEmptyString(item) || !labels.has(item)) {
        const itemField = field + '[' + index + ']'
        violations.push({
          ruleId: 'item-fora-do-catalogo:' + itemField,
          field: itemField,
        })
      }
      if (seen.has(item)) duplicate = true
      seen.add(item)
    })
    if (duplicate) {
      violations.push({
        ruleId: 'item-duplicado:' + field,
        field,
      })
    }
  }

  return violations
}
