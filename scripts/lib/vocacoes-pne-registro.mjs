import { readFileSync } from 'node:fs'
import path from 'node:path'

const DEFAULT_CATALOGO_MECANISMOS_PATH = new URL(
  '../checks/fixtures/vocacoes-pne/catalogo-mecanismos.json',
  import.meta.url,
)
const DEFAULT_REGISTRO_SERIES_PATH = new URL(
  '../checks/fixtures/vocacoes-pne/registro-series.json',
  import.meta.url,
)
const DEFAULT_ETAPA4_SERIES_PATH = new URL(
  '../checks/fixtures/vocacoes-pne/etapa4-series-pesquisa.json',
  import.meta.url,
)
const DEFAULT_REGRAS_UNIVERSO_PATH = new URL(
  '../checks/fixtures/vocacoes-pne/regras-universo.json',
  import.meta.url,
)
const DEFAULT_CATALOGO_REFERENCIAS_PATH = new URL(
  '../checks/fixtures/vocacoes-pne/catalogo-referencias.json',
  import.meta.url,
)

const MECHANISM_AVAILABILITY = new Set([
  'disponivel',
  'disponivel_pesquisa',
  'parcial',
  'pendente',
])
const SERIES_STATUS = new Set([
  'disponivel_plataforma',
  'disponivel_pesquisa',
  'pendente_r3',
  'pendente_r4',
])

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0
}

function resolveSource(filePath) {
  return filePath instanceof URL ? filePath : path.resolve(filePath)
}

function sourceLabel(source) {
  return source instanceof URL ? source.href : source
}

function readFixture(filePath, fixtureName) {
  const source = resolveSource(filePath)
  try {
    return {
      value: JSON.parse(readFileSync(source, 'utf8')),
      label: sourceLabel(source),
    }
  } catch (error) {
    throw new Error(
      fixtureName + ' inválido em ' + sourceLabel(source) + ': JSON não pôde ser lido',
      { cause: error },
    )
  }
}

function throwShape(fixtureName, filePath, violations) {
  if (violations.length === 0) return
  throw new Error(
    fixtureName
    + ' inválido em '
    + filePath
    + ':\n- '
    + violations.join('\n- '),
  )
}

function requireRoot(value, violations) {
  if (!isRecord(value)) {
    violations.push('a raiz deve ser um objeto')
    return false
  }
  if (!isNonEmptyString(value.version)) {
    violations.push('version deve ser uma string não vazia')
  }
  return true
}

function validateUniqueIdArray(items, field, violations, validateItem) {
  if (!Array.isArray(items)) {
    violations.push(field + ' deve ser um array')
    return
  }
  const ids = new Set()
  items.forEach((item, index) => {
    const itemPath = field + '[' + index + ']'
    if (!isRecord(item)) {
      violations.push(itemPath + ' deve ser um objeto')
      return
    }
    if (!isNonEmptyString(item.id)) {
      violations.push(itemPath + '.id deve ser uma string não vazia')
    } else if (ids.has(item.id)) {
      violations.push(field + ' contém id duplicado: ' + item.id)
    } else {
      ids.add(item.id)
    }
    validateItem(item, itemPath)
  })
}

function validateStringArray(value, field, violations, { allowEmpty = true } = {}) {
  if (!Array.isArray(value)) {
    violations.push(field + ' deve ser um array')
    return
  }
  if (!allowEmpty && value.length === 0) {
    violations.push(field + ' deve ser um array não vazio')
  }
  value.forEach((item, index) => {
    if (!isNonEmptyString(item)) {
      violations.push(field + '[' + index + '] deve ser uma string não vazia')
    }
  })
}

function validateAgeRange(value, field, violations) {
  if (value === null) return
  if (
    !Array.isArray(value)
    || value.length !== 2
    || !Number.isInteger(value[0])
    || (value[1] !== null && !Number.isInteger(value[1]))
    || (value[1] !== null && value[1] < value[0])
  ) {
    violations.push(
      field + ' deve ser null ou [idadeMin inteira, idadeMax inteira|null]',
    )
  }
}

function validatePairArray(value, field, violations) {
  if (!Array.isArray(value)) {
    violations.push(field + ' deve ser um array')
    return
  }
  value.forEach((pair, index) => {
    const pairPath = field + '[' + index + ']'
    if (!isRecord(pair)) {
      violations.push(pairPath + ' deve ser um objeto')
      return
    }
    for (const side of ['educacional', 'territorial']) {
      if (!isNonEmptyString(pair[side])) {
        violations.push(pairPath + '.' + side + ' deve ser uma string não vazia')
      }
    }
    if (pair.nota !== undefined && !isNonEmptyString(pair.nota)) {
      violations.push(pairPath + '.nota deve ser uma string não vazia quando presente')
    }
  })
}

function assertCatalogoMecanismosShape(value, filePath) {
  const violations = []
  if (!requireRoot(value, violations)) {
    throwShape('Catálogo de mecanismos', filePath, violations)
  }
  if (!isNonEmptyString(value.descricao)) {
    violations.push('descricao deve ser uma string não vazia')
  }

  validateUniqueIdArray(
    value.mecanismos,
    'mecanismos',
    violations,
    (mechanism, field) => {
      for (const stringField of [
        'familia',
        'titulo',
        'perguntaEducacional',
        'transformacaoTerritorial',
        'justificativa',
        'variavelEducacionalPrincipal',
        'decomposicaoPrevia',
        'leituraPublicaMaxima',
        'utilidadePlanejamento',
      ]) {
        if (!isNonEmptyString(mechanism[stringField])) {
          violations.push(field + '.' + stringField + ' deve ser uma string não vazia')
        }
      }
      for (const arrayField of [
        'variaveisTerritoriaisAceitas',
        'escalaGeografica',
        'afirmacoesProibidas',
        'temasPne',
        'fontesAtuais',
        'fontesDesejaveis',
        'direcoes',
      ]) {
        validateStringArray(
          mechanism[arrayField],
          field + '.' + arrayField,
          violations,
          {
            allowEmpty: ['fontesAtuais', 'fontesDesejaveis'].includes(arrayField),
          },
        )
      }
      if (mechanism.seriesEducacionaisDeApoio !== undefined) {
        validateStringArray(
          mechanism.seriesEducacionaisDeApoio,
          field + '.seriesEducacionaisDeApoio',
          violations,
        )
      }
      if (!Number.isInteger(mechanism.janelaMinimaPontos) || mechanism.janelaMinimaPontos < 1) {
        violations.push(field + '.janelaMinimaPontos deve ser inteiro positivo')
      }
      if (!isRecord(mechanism.populacaoReferencia)) {
        violations.push(field + '.populacaoReferencia deve ser um objeto')
      } else {
        validateAgeRange(
          mechanism.populacaoReferencia.faixaEtaria,
          field + '.populacaoReferencia.faixaEtaria',
          violations,
        )
        if (!isNonEmptyString(mechanism.populacaoReferencia.descricao)) {
          violations.push(
            field + '.populacaoReferencia.descricao deve ser uma string não vazia',
          )
        }
      }
      if (!isRecord(mechanism.defasagem)) {
        violations.push(field + '.defasagem deve ser um objeto')
      } else {
        if (!isNonEmptyString(mechanism.defasagem.tipo)) {
          violations.push(field + '.defasagem.tipo deve ser uma string não vazia')
        }
        for (const yearField of ['anosMin', 'anosMax']) {
          if (!Number.isInteger(mechanism.defasagem[yearField])) {
            violations.push(field + '.defasagem.' + yearField + ' deve ser inteiro')
          }
        }
        if (!isNonEmptyString(mechanism.defasagem.descricao)) {
          violations.push(field + '.defasagem.descricao deve ser uma string não vazia')
        }
      }
      if (!MECHANISM_AVAILABILITY.has(mechanism.disponibilidade)) {
        violations.push(field + '.disponibilidade tem valor inválido')
      }
      if (
        mechanism.disponibilidade === 'pendente'
        && !isNonEmptyString(mechanism.observacaoDisponibilidade)
      ) {
        violations.push(
          field + '.observacaoDisponibilidade é obrigatória para mecanismo pendente',
        )
      }
      validatePairArray(mechanism.paresPermitidos, field + '.paresPermitidos', violations)
      if (mechanism.paresProvisorios !== undefined) {
        validatePairArray(
          mechanism.paresProvisorios,
          field + '.paresProvisorios',
          violations,
        )
      }
    },
  )
  if (Array.isArray(value.mecanismos) && value.mecanismos.length === 0) {
    violations.push('mecanismos deve ser um array não vazio')
  }
  throwShape('Catálogo de mecanismos', filePath, violations)
}

function assertRegistroShape(value, filePath) {
  const violations = []
  if (!requireRoot(value, violations)) {
    throwShape('Registro de séries', filePath, violations)
  }
  if (!isRecord(value.generatedFrom)) {
    violations.push('generatedFrom deve ser um objeto')
  } else if (!isNonEmptyString(value.generatedFrom.componentes)) {
    violations.push('generatedFrom.componentes deve ser uma string não vazia')
  }
  if (!Array.isArray(value.series)) {
    violations.push('series deve ser um array')
    throwShape('Registro de séries', filePath, violations)
  }

  const ids = new Set()
  let previousId = null
  value.series.forEach((item, index) => {
    const field = 'series[' + index + ']'
    if (!isRecord(item)) {
      violations.push(field + ' deve ser um objeto')
      return
    }
    if (!isNonEmptyString(item.seriesId)) {
      violations.push(field + '.seriesId deve ser uma string não vazia')
    } else {
      if (ids.has(item.seriesId)) {
        violations.push('series contém seriesId duplicado: ' + item.seriesId)
      }
      ids.add(item.seriesId)
      if (previousId !== null && item.seriesId < previousId) {
        violations.push('series deve estar ordenado por seriesId')
      }
      previousId = item.seriesId
    }
    if (!isNonEmptyString(item.label)) {
      violations.push(field + '.label deve ser uma string não vazia')
    }
    for (const nullableString of ['unit', 'source', 'evidenceClass']) {
      if (item[nullableString] !== null && !isNonEmptyString(item[nullableString])) {
        violations.push(field + '.' + nullableString + ' deve ser string não vazia ou null')
      }
    }
    for (const stringField of ['universo', 'lente']) {
      if (!isNonEmptyString(item[stringField])) {
        violations.push(field + '.' + stringField + ' deve ser uma string não vazia')
      }
    }
    validateAgeRange(item.faixaEtaria, field + '.faixaEtaria', violations)
    for (const objectField of ['populacaoReferencia', 'ratioOf']) {
      if (item[objectField] !== null && !isRecord(item[objectField])) {
        violations.push(field + '.' + objectField + ' deve ser objeto ou null')
      }
    }
    for (const periodField of ['periodStart', 'periodEnd']) {
      if (item[periodField] !== null && !Number.isInteger(item[periodField])) {
        violations.push(field + '.' + periodField + ' deve ser inteiro ou null')
      }
    }
    if (item.periodGranularity !== null && !isNonEmptyString(item.periodGranularity)) {
      violations.push(field + '.periodGranularity deve ser string não vazia ou null')
    }
    if (
      !Array.isArray(item.preliminaryPeriods)
      || !item.preliminaryPeriods.every(Number.isInteger)
    ) {
      violations.push(field + '.preliminaryPeriods deve ser array de inteiros')
    }
    if (item.componentes !== undefined) {
      validateStringArray(
        item.componentes,
        field + '.componentes',
        violations,
        { allowEmpty: false },
      )
      if (
        Array.isArray(item.componentes)
        && new Set(item.componentes).size !== item.componentes.length
      ) {
        violations.push(field + '.componentes contém valores duplicados')
      }
    }
    if (item.nota !== undefined && !isNonEmptyString(item.nota)) {
      violations.push(field + '.nota deve ser uma string não vazia quando presente')
    }
    if (item.rede !== 'todas') {
      violations.push(field + '.rede deve ser "todas"')
    }
    if (!SERIES_STATUS.has(item.status)) {
      violations.push(field + '.status tem valor inválido: ' + String(item.status))
    }
  })
  throwShape('Registro de séries', filePath, violations)
}

function assertEtapa4SeriesShape(value, filePath) {
  const violations = []
  if (!requireRoot(value, violations)) {
    throwShape('Snapshot de séries da Etapa 4', filePath, violations)
  }
  if (!isNonEmptyString(value.descricao)) {
    violations.push('descricao deve ser uma string não vazia')
  }
  if (value.status !== 'disponivel_pesquisa') {
    violations.push('status deve ser "disponivel_pesquisa"')
  }
  if (!isRecord(value.provenance) || !Array.isArray(value.provenance.sources)) {
    violations.push('provenance.sources deve ser um array')
  } else {
    if (!isNonEmptyString(value.provenance.sourceRoot)) {
      violations.push('provenance.sourceRoot deve ser uma string não vazia')
    }
    if (value.provenance.sources.length !== 6) {
      violations.push('provenance.sources deve conter os seis blocos da Etapa 4')
    }
    const blocks = new Set()
    value.provenance.sources.forEach((source, index) => {
      const field = 'provenance.sources[' + index + ']'
      if (!isRecord(source)) {
        violations.push(field + ' deve ser um objeto')
        return
      }
      for (const stringField of ['block', 'regionalDirectory', 'generatedAt']) {
        if (!isNonEmptyString(source[stringField])) {
          violations.push(field + '.' + stringField + ' deve ser string não vazia')
        }
      }
      if (isNonEmptyString(source.block)) {
        if (blocks.has(source.block)) {
          violations.push('provenance.sources contém bloco duplicado: ' + source.block)
        }
        blocks.add(source.block)
      }
      if (source.regionalFilesChecked !== 10) {
        violations.push(field + '.regionalFilesChecked deve ser 10')
      }
    })
  }

  if (!Array.isArray(value.series)) {
    violations.push('series deve ser um array')
    throwShape('Snapshot de séries da Etapa 4', filePath, violations)
  }
  if (value.series.length !== 87) {
    violations.push('series deve conter as 87 séries da Etapa 4')
  }
  const seriesKeys = new Set()
  value.series.forEach((item, index) => {
    const field = 'series[' + index + ']'
    if (!isRecord(item)) {
      violations.push(field + ' deve ser um objeto')
      return
    }
    if (!isNonEmptyString(item.seriesKey)) {
      violations.push(field + '.seriesKey deve ser uma string não vazia')
    } else if (seriesKeys.has(item.seriesKey)) {
      violations.push('series contém seriesKey duplicada: ' + item.seriesKey)
    } else {
      seriesKeys.add(item.seriesKey)
    }
    for (const stringField of [
      'label',
      'unit',
      'source',
      'evidenceClass',
      'periodGranularity',
    ]) {
      if (!isNonEmptyString(item[stringField])) {
        violations.push(field + '.' + stringField + ' deve ser string não vazia')
      }
    }
    for (const periodField of ['periodStart', 'periodEnd']) {
      if (!Number.isInteger(item[periodField])) {
        violations.push(field + '.' + periodField + ' deve ser inteiro')
      }
    }
    if (
      Number.isInteger(item.periodStart)
      && Number.isInteger(item.periodEnd)
      && item.periodStart > item.periodEnd
    ) {
      violations.push(field + '.periodStart não pode ser posterior a periodEnd')
    }
    if (
      !Array.isArray(item.preliminaryPeriods)
      || !item.preliminaryPeriods.every(Number.isInteger)
    ) {
      violations.push(field + '.preliminaryPeriods deve ser array de inteiros')
    }
    if (Object.hasOwn(item, 'points')) {
      violations.push(field + ' não pode conter pontos')
    }
    if (item.municipiosComDado !== undefined && !isRecord(item.municipiosComDado)) {
      violations.push(field + '.municipiosComDado deve ser objeto quando presente')
    }
  })
  throwShape('Snapshot de séries da Etapa 4', filePath, violations)
  return seriesKeys
}

function assertRegistroComponents(registro, etapa4SeriesKeys, filePath) {
  const violations = []
  registro.series.forEach((item, index) => {
    ;(item.componentes ?? []).forEach((seriesKey, componentIndex) => {
      if (!etapa4SeriesKeys.has(seriesKey)) {
        violations.push(
          'series['
          + index
          + '].componentes['
          + componentIndex
          + '] não resolve no snapshot da Etapa 4: '
          + seriesKey,
        )
      }
    })
  })
  throwShape('Componentes do registro de séries', filePath, violations)
}

function assertRegrasUniversoShape(value, filePath) {
  const violations = []
  if (!requireRoot(value, violations)) {
    throwShape('Regras de universo', filePath, violations)
  }
  if (!isNonEmptyString(value.descricao)) {
    violations.push('descricao deve ser uma string não vazia')
  }
  if (!isRecord(value.universos) || Object.keys(value.universos).length === 0) {
    violations.push('universos deve ser um objeto não vazio')
  } else {
    for (const [universeId, universe] of Object.entries(value.universos)) {
      if (!isRecord(universe)) {
        violations.push('universos.' + universeId + ' deve ser um objeto')
        continue
      }
      for (const field of ['lente', 'descricao']) {
        if (!isNonEmptyString(universe[field])) {
          violations.push(
            'universos.' + universeId + '.' + field + ' deve ser string não vazia',
          )
        }
      }
    }
  }

  const compiled = []
  if (!Array.isArray(value.classificacao) || value.classificacao.length === 0) {
    violations.push('classificacao deve ser um array não vazio')
  } else {
    const orders = new Set()
    value.classificacao.forEach((rule, index) => {
      const field = 'classificacao[' + index + ']'
      if (!isRecord(rule)) {
        violations.push(field + ' deve ser um objeto')
        return
      }
      if (!Number.isInteger(rule.ordem)) {
        violations.push(field + '.ordem deve ser inteiro')
      } else if (orders.has(rule.ordem)) {
        violations.push('ordem de classificação duplicada: ' + rule.ordem)
      } else {
        orders.add(rule.ordem)
      }
      if (!isNonEmptyString(rule.pattern)) {
        violations.push(field + '.pattern deve ser uma string não vazia')
      } else {
        try {
          compiled.push({ ...rule, regex: new RegExp(rule.pattern, 'u') })
        } catch {
          violations.push(field + '.pattern não compila: ' + rule.pattern)
        }
      }
      if (!isNonEmptyString(rule.universo) || !isRecord(value.universos?.[rule.universo])) {
        violations.push(field + '.universo não resolve em universos')
      }
      validateAgeRange(rule.faixaEtaria, field + '.faixaEtaria', violations)
    })
  }

  if (!isRecord(value.populacaoReferenciaMatriculas)) {
    violations.push('populacaoReferenciaMatriculas deve ser um objeto')
  } else {
    for (const [seriesId, reference] of Object.entries(
      value.populacaoReferenciaMatriculas,
    )) {
      const field = 'populacaoReferenciaMatriculas.' + seriesId
      if (!isRecord(reference)) {
        violations.push(field + ' deve ser um objeto')
        continue
      }
      if (!isNonEmptyString(reference.etapa)) {
        violations.push(field + '.etapa deve ser uma string não vazia')
      }
      validateAgeRange(reference.faixaEtaria, field + '.faixaEtaria', violations)
      if (!isNonEmptyString(reference.descricao)) {
        violations.push(field + '.descricao deve ser uma string não vazia')
      }
    }
  }

  if (!Array.isArray(value.seriesPendentes)) {
    violations.push('seriesPendentes deve ser um array')
  } else {
    const pendingIds = new Set()
    value.seriesPendentes.forEach((item, index) => {
      const field = 'seriesPendentes[' + index + ']'
      if (!isRecord(item)) {
        violations.push(field + ' deve ser um objeto')
        return
      }
      if (!isNonEmptyString(item.seriesId)) {
        violations.push(field + '.seriesId deve ser uma string não vazia')
      } else if (pendingIds.has(item.seriesId)) {
        violations.push('seriesPendentes contém seriesId duplicado: ' + item.seriesId)
      } else {
        pendingIds.add(item.seriesId)
      }
      if (!['pendente_r3', 'pendente_r4'].includes(item.status)) {
        violations.push(field + '.status tem valor inválido')
      }
      if (!isNonEmptyString(item.universo) || !isRecord(value.universos?.[item.universo])) {
        violations.push(field + '.universo não resolve em universos')
      }
      validateAgeRange(item.faixaEtaria, field + '.faixaEtaria', violations)
      for (const stringField of ['label', 'fonteDesejavel']) {
        if (!isNonEmptyString(item[stringField])) {
          violations.push(field + '.' + stringField + ' deve ser string não vazia')
        }
      }
    })
  }
  if (
    !isRecord(value.denominadores)
    || !Array.isArray(value.denominadores.adequados)
    || !Array.isArray(value.denominadores.proibidos)
  ) {
    violations.push('denominadores deve conter arrays adequados e proibidos')
  }
  if (!Array.isArray(value.regrasPar) || value.regrasPar.length === 0) {
    violations.push('regrasPar deve ser um array não vazio')
  } else {
    const orders = new Set()
    value.regrasPar.forEach((rule, index) => {
      const field = 'regrasPar[' + index + ']'
      if (!isRecord(rule)) {
        violations.push(field + ' deve ser um objeto')
        return
      }
      if (!Number.isInteger(rule.ordem)) {
        violations.push(field + '.ordem deve ser inteiro')
      } else if (orders.has(rule.ordem)) {
        violations.push('regrasPar contém ordem duplicada: ' + rule.ordem)
      } else {
        orders.add(rule.ordem)
      }
      if (rule.reasonCode !== null && !isNonEmptyString(rule.reasonCode)) {
        violations.push(field + '.reasonCode deve ser string não vazia ou null')
      }
      if (!isNonEmptyString(rule.descricao)) {
        violations.push(field + '.descricao deve ser string não vazia')
      }
    })
  }
  throwShape('Regras de universo', filePath, violations)
  return compiled
}

function assertCatalogoReferenciasShape(value, filePath) {
  const violations = []
  if (!requireRoot(value, violations)) {
    throwShape('Catálogo de referências', filePath, violations)
  }
  if (!isNonEmptyString(value.descricao)) {
    violations.push('descricao deve ser uma string não vazia')
  }
  for (const field of ['temasPne', 'fontes']) {
    validateUniqueIdArray(value[field], field, violations, (item, itemPath) => {
      if (!isNonEmptyString(item.label)) {
        violations.push(itemPath + '.label deve ser uma string não vazia')
      }
    })
  }
  validateUniqueIdArray(
    value.indicadores,
    'indicadores',
    violations,
    (item, itemPath) => {
      if (!isNonEmptyString(item.label)) {
        violations.push(itemPath + '.label deve ser uma string não vazia')
      }
      if (item.seriesId !== null && !isNonEmptyString(item.seriesId)) {
        violations.push(itemPath + '.seriesId deve ser string não vazia ou null')
      }
    },
  )
  throwShape('Catálogo de referências', filePath, violations)
}

export function loadCatalogoMecanismos(
  filePath = DEFAULT_CATALOGO_MECANISMOS_PATH,
) {
  const fixture = readFixture(filePath, 'Catálogo de mecanismos')
  assertCatalogoMecanismosShape(fixture.value, fixture.label)
  return fixture.value
}

export function loadEtapa4SeriesPesquisa(filePath = DEFAULT_ETAPA4_SERIES_PATH) {
  const fixture = readFixture(filePath, 'Snapshot de séries da Etapa 4')
  assertEtapa4SeriesShape(fixture.value, fixture.label)
  return fixture.value
}

export function loadRegistroSeries(
  filePath = DEFAULT_REGISTRO_SERIES_PATH,
  etapa4FilePath = DEFAULT_ETAPA4_SERIES_PATH,
) {
  const fixture = readFixture(filePath, 'Registro de séries')
  assertRegistroShape(fixture.value, fixture.label)
  const etapa4Fixture = readFixture(
    etapa4FilePath,
    'Snapshot de séries da Etapa 4',
  )
  const etapa4SeriesKeys = assertEtapa4SeriesShape(
    etapa4Fixture.value,
    etapa4Fixture.label,
  )
  assertRegistroComponents(fixture.value, etapa4SeriesKeys, fixture.label)
  return fixture.value
}

export function loadRegrasUniverso(filePath = DEFAULT_REGRAS_UNIVERSO_PATH) {
  const fixture = readFixture(filePath, 'Regras de universo')
  const compiled = assertRegrasUniversoShape(fixture.value, fixture.label)
  return {
    ...fixture.value,
    classificacao: compiled.sort((left, right) => left.ordem - right.ordem),
  }
}

export function loadCatalogoReferencias(
  filePath = DEFAULT_CATALOGO_REFERENCIAS_PATH,
) {
  const fixture = readFixture(filePath, 'Catálogo de referências')
  assertCatalogoReferenciasShape(fixture.value, fixture.label)
  return fixture.value
}

export function assertCrossReferences({ mecanismos, registro, referencias }) {
  const violations = []
  if (!isRecord(mecanismos) || !Array.isArray(mecanismos.mecanismos)) {
    violations.push('mecanismos deve ser um catálogo carregado')
  }
  if (!isRecord(registro) || !Array.isArray(registro.series)) {
    violations.push('registro deve ser um registro carregado')
  }
  if (
    !isRecord(referencias)
    || !Array.isArray(referencias.temasPne)
    || !Array.isArray(referencias.indicadores)
    || !Array.isArray(referencias.fontes)
  ) {
    violations.push('referencias deve ser um catálogo carregado')
  }
  if (violations.length > 0) {
    throw new Error('Referências cruzadas Vocações × PNE inválidas:\n- ' + violations.join('\n- '))
  }

  const seriesIds = new Set(registro.series.map((item) => item.seriesId))
  const themeIds = new Set(referencias.temasPne.map((item) => item.id))
  const sourceIds = new Set(referencias.fontes.map((item) => item.id))

  const requireSeries = (seriesId, field) => {
    if (!seriesIds.has(seriesId)) {
      violations.push(field + ' não resolve no registro: ' + seriesId)
    }
  }

  mecanismos.mecanismos.forEach((mechanism, mechanismIndex) => {
    const field = 'mecanismos[' + mechanismIndex + '](' + mechanism.id + ')'
    const educational = new Set([
      mechanism.variavelEducacionalPrincipal,
      ...(mechanism.seriesEducacionaisDeApoio ?? []),
    ])
    const territorial = new Set(mechanism.variaveisTerritoriaisAceitas)

    requireSeries(
      mechanism.variavelEducacionalPrincipal,
      field + '.variavelEducacionalPrincipal',
    )
    ;(mechanism.seriesEducacionaisDeApoio ?? []).forEach((seriesId, index) => {
      requireSeries(seriesId, field + '.seriesEducacionaisDeApoio[' + index + ']')
    })
    mechanism.variaveisTerritoriaisAceitas.forEach((seriesId, index) => {
      requireSeries(seriesId, field + '.variaveisTerritoriaisAceitas[' + index + ']')
    })

    for (const pairField of ['paresPermitidos', 'paresProvisorios']) {
      ;(mechanism[pairField] ?? []).forEach((pair, index) => {
        const pairPath = field + '.' + pairField + '[' + index + ']'
        requireSeries(pair.educacional, pairPath + '.educacional')
        requireSeries(pair.territorial, pairPath + '.territorial')
        if (!educational.has(pair.educacional)) {
          violations.push(
            pairPath
            + '.educacional não pertence à série principal ou de apoio do mecanismo: '
            + pair.educacional,
          )
        }
        if (!territorial.has(pair.territorial)) {
          violations.push(
            pairPath
            + '.territorial não pertence às séries aceitas pelo mecanismo: '
            + pair.territorial,
          )
        }
      })
    }

    mechanism.temasPne.forEach((themeId, index) => {
      if (!themeIds.has(themeId)) {
        violations.push(field + '.temasPne[' + index + '] não resolve: ' + themeId)
      }
    })
    for (const sourceField of ['fontesAtuais', 'fontesDesejaveis']) {
      mechanism[sourceField].forEach((sourceId, index) => {
        if (!sourceIds.has(sourceId)) {
          violations.push(
            field
            + '.'
            + sourceField
            + '['
            + index
            + '] não resolve: '
            + sourceId,
          )
        }
      })
    }
    if (!isNonEmptyString(mechanism.utilidadePlanejamento)) {
      violations.push(field + '.utilidadePlanejamento está vazio')
    }
    if (!isNonEmptyString(mechanism.leituraPublicaMaxima)) {
      violations.push(field + '.leituraPublicaMaxima está vazio')
    }
    if (!MECHANISM_AVAILABILITY.has(mechanism.disponibilidade)) {
      violations.push(field + '.disponibilidade tem valor inválido')
    }
    if (
      mechanism.disponibilidade === 'pendente'
      && !isNonEmptyString(mechanism.observacaoDisponibilidade)
    ) {
      violations.push(field + '.observacaoDisponibilidade está vazia')
    }
  })

  referencias.indicadores.forEach((indicator, index) => {
    if (indicator.seriesId !== null && !seriesIds.has(indicator.seriesId)) {
      violations.push(
        'referencias.indicadores['
        + index
        + ']('
        + indicator.id
        + ').seriesId não resolve no registro: '
        + indicator.seriesId,
      )
    }
  })

  if (violations.length > 0) {
    throw new Error(
      'Referências cruzadas Vocações × PNE inválidas:\n- '
      + violations.join('\n- '),
    )
  }
  return true
}
