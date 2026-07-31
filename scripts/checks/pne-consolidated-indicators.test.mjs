import test from 'node:test'
import assert from 'node:assert/strict'

import {
  PNE_2026_GOAL_INDICATOR_CONTRACT as contract,
} from '../../src/data/pne2026GoalIndicatorContract.js'
import presentationPolicy from '../../contracts/pne2026-diagnostic-presentation-policy.json' with { type: 'json' }
import {
  getPne2026DataStatusLabel,
} from '../../src/features/diagnostic/pne2026PublicDiagnosticV3.js'
import {
  MUNICIPAL_REPORT_PUBLIC_LABELS,
} from '../../src/features/education/municipalTechnicalReportCatalog.ts'

const relation = (relationId) => contract.relations.find(
  (entry) => entry.relationId === relationId,
)

test('consolidated relations expose the intended legal and monitoring modes', () => {
  assert.equal(contract.contractVersion, '1.9.0')
  assert.equal(contract.relations.length, 59)
  assert.equal(relation('relation.3.a.alfabetizacao').mode, 'progress')
  assert.equal(relation('relation.3.a.alfabetizacao').canProjection, false)
  assert.equal(relation('relation.11.d.eja_atendimento_18_mais').mode, 'progress')
  assert.equal(relation('relation.14.a.graduacao_frequencia_18_24').mode, 'tracking')
  assert.equal(relation('relation.14.b.superior_completo_25_34').mode, 'tracking')
  assert.equal(relation('relation.14.d.taxa_bruta_graduacao').mode, 'progress')
  assert.equal(relation('relation.15.b.docentes_tempo_integral_ies').mode, 'progress')
  assert.equal(
    relation('relation.15.b.docentes_tempo_integral_universidades').includeInLegalSummary,
    false,
  )
  assert.equal(relation('relation.17.d.temporarios').mode, 'complementary')
  assert.equal(relation('relation.7.a.internet').mode, 'complementary')
  assert.equal(relation('relation.7.a.internet').includeInDiagnostic, false)
})

test('public wording and negative status labels do not leak technical codes', () => {
  assert.equal(
    contract.indicators.alfabetizacao.publicTitle,
    'Estudantes alfabetizados ao final do 2º ano do Ensino Fundamental — rede municipal',
  )
  assert.equal(
    getPne2026DataStatusLabel('unavailable', 'below_minimum_participation'),
    'Participação abaixo do mínimo para divulgação',
  )
  assert.equal(
    getPne2026DataStatusLabel('unavailable', 'no_published_result'),
    'Resultado não publicado pela fonte',
  )
})

test('diagnostic, technical report and PME adapters cover all new relations', () => {
  const policyIds = new Set(presentationPolicy.relations.map((entry) => entry.relationId))
  const indicatorIds = [
    'alfabetizacao',
    'eja_atendimento_18_mais',
    'graduacao_frequencia_18_24',
    'superior_completo_25_34',
    'taxa_bruta_graduacao',
    'docentes_tempo_integral_ies',
    'docentes_tempo_integral_universidades',
    'docentes_tempo_integral_centros_universitarios',
    'docentes_tempo_integral_faculdades',
  ]
  for (const indicatorId of indicatorIds) {
    const relationEntry = contract.relations.find(
      (entry) => entry.indicatorId === indicatorId,
    )
    assert.ok(relationEntry)
    assert.ok(policyIds.has(relationEntry.relationId))
    assert.ok(MUNICIPAL_REPORT_PUBLIC_LABELS[indicatorId])
  }
})
