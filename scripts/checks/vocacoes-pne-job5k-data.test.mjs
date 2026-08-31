import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import test from 'node:test'

const repoRoot = path.resolve(import.meta.dirname, '..', '..')
const bundlePath = path.join(
  repoRoot,
  'src/features/vocacoes-pne-internal/generated/vocacoesPneJob5kStories.json',
)
const bundle = JSON.parse(await readFile(bundlePath, 'utf8'))
const municipalityCodes = bundle.municipalities.map((item) => item.ibgeCode)

const REQUIRED_STORY_FIELDS = [
  'story_id',
  'direction_id',
  'editorial_role',
  'analytical_sources',
  'analytical_relation_states',
  'title_conclusion',
  'integrated_summary',
  'regional_read',
  'selected_municipality_read',
  'ten_municipality_distribution',
  'primary_evidence',
  'secondary_evidence',
  'planning_implication',
  'monitoring_indicators',
  'institutional_coordination',
  'interpretation_boundary',
  'allowed_claims',
  'forbidden_claims',
  'source_refs',
  'periods',
  'territorial_lenses',
  'network_scope',
  'availability_state',
  'zero_state',
  'manager_review_state',
  'public_narrative_authorized',
]

function story(id) {
  const value = bundle.stories.find((item) => item.story_id === id)
  assert.ok(value, id)
  return value
}

function variant(storyValue, entityId) {
  const value = storyValue.selected_municipality_read.variants.find((item) => item.entity_id === entityId)
  assert.ok(value, `${storyValue.story_id}/${entityId}`)
  return value
}

test('bundle 5K permanece interno, fechado e sem efeito analítico ou público', () => {
  assert.equal(bundle.schema_version, 'vocacoes-pne-insight-first-bundle-v1')
  assert.equal(bundle.meta.job_id, 'v7-job5k')
  assert.equal(bundle.meta.internal_only, true)
  assert.equal(bundle.meta.gate11, 'CLOSED')
  assert.equal(bundle.meta.public_narrative_authorized, false)
  assert.equal(bundle.meta.publication_authorized, false)
  assert.equal(bundle.meta.public_data_writes_authorized, false)
  assert.equal(bundle.meta.manager_validation_started, false)
  assert.equal(bundle.meta.network_used, false)
  assert.equal(bundle.meta.database_used, false)
  assert.equal(bundle.meta.new_acquisition_performed, false)
  assert.equal(bundle.meta.official_formulas_altered, false)
})

test('quatro histórias têm contrato completo e 44 variantes geradas por identidade IBGE', () => {
  assert.equal(bundle.stories.length, 4)
  assert.equal(bundle.directions.length, 2)
  assert.equal(bundle.municipalities.length, 10)
  assert.equal(new Set(municipalityCodes).size, 10)
  assert.ok(municipalityCodes.every((code) => typeof code === 'string' && /^[0-9]{7}$/u.test(code)))

  for (const storyValue of bundle.stories) {
    for (const field of REQUIRED_STORY_FIELDS) assert.ok(field in storyValue, `${storyValue.story_id}.${field}`)
    assert.equal(storyValue.network_scope, 'total_all_dependencies')
    assert.equal(storyValue.manager_review_state, 'pending')
    assert.equal(storyValue.public_narrative_authorized, false)
    assert.equal(storyValue.selected_municipality_read.municipality_overrides, false)
    assert.equal(storyValue.selected_municipality_read.variants.length, 11)
    assert.deepEqual(
      new Set(storyValue.selected_municipality_read.variants.map((item) => item.entity_id)),
      new Set(['REGION_VALE_DO_SINOS', ...municipalityCodes]),
    )
    for (const item of storyValue.selected_municipality_read.variants) {
      assert.ok(item.key_figures.length >= 1 && item.key_figures.length <= 2)
      if (item.municipality_ibge_code !== null) assert.equal(item.entity_id, item.municipality_ibge_code)
    }
  }

  assert.equal(bundle.counts.story_variant_count, 44)
  assert.equal(bundle.normalization.manual_municipality_profiles, false)
  assert.equal(bundle.normalization.municipal_variants_generated_by_rules, true)
  assert.equal(bundle.normalization.regional_evidence_stored_once, true)
  assert.equal(bundle.normalization.ranking_used, false)
})

test('promoções R1–R8 preservam quatro estados analíticos separados da função editorial', () => {
  const relations = Object.fromEntries(bundle.editorial_promotion_contract.map((item) => [item.relation_id, item]))
  assert.equal(relations.R1.analytical_relation_state, 'STRUCTURAL_CONTRAST')
  assert.equal(relations.R1.editorial_story_state, 'PRIMARY_INSIGHT')
  assert.equal(relations.R2.analytical_relation_state, 'NOT_SUPPORTED')
  assert.equal(relations.R2.editorial_story_state, 'NOT_STANDALONE')
  assert.equal(relations.R3.analytical_relation_state, 'NOT_SUPPORTED')
  assert.equal(relations.R3.editorial_story_state, 'PRIMARY_FACTUAL_STORY_WITH_ASSOCIATION_BOUNDARY')
  assert.equal(relations.R4.analytical_relation_state, 'TERRITORIAL_MISMATCH')
  assert.equal(relations.R5.analytical_relation_state, 'TERRITORIAL_MISMATCH')
  assert.equal(relations.R6.editorial_story_state, 'SECONDARY_CONTEXT')
  assert.equal(relations.R7.editorial_story_state, 'CONDITIONAL_EXPANDED')
  assert.equal(relations.R8.editorial_story_state, 'DESCRIPTIVE_CONTEXT_ONLY')
  assert.ok(Object.values(relations).every((item) => item.interpretation_boundary_state === 'REQUIRED_VISIBLE'))
})

test('ensino médio e resultados negativos mantêm as fronteiras editoriais exigidas', () => {
  const highSchool = story('STORY_HIGH_SCHOOL_TRAJECTORY')
  const youth = story('STORY_YOUTH_WORK_APPRENTICESHIP')
  assert.equal(highSchool.title_conclusion, 'A retração regional do ensino médio esconde movimentos municipais em direções diferentes.')
  assert.match(highSchool.interpretation_boundary, /fotografia de mobilidade de 2022 não mostrou um padrão consistente/u)
  assert.match(highSchool.interpretation_boundary, /contexto e não antecipa/u)
  assert.match(youth.interpretation_boundary, /não mostraram uma relação estável com abandono ou reprovação/u)
  assert.match(youth.interpretation_boundary, /Estoques e eventos não equivalem a pessoas únicas/u)
  assert.equal(bundle.stories.some((item) => item.story_id.includes('MOBILITY')), false)
})

test('Nova Santa Rita materializa os contrastes quantitativos sem perfil manual', () => {
  const nsr = '4313375'
  const highSchool = variant(story('STORY_HIGH_SCHOOL_TRAJECTORY'), nsr)
  const eja = variant(story('STORY_EJA_TERRITORY'), nsr)
  const logistics = variant(story('STORY_LOGISTICS_EPT'), nsr)
  const youth = variant(story('STORY_YOUTH_WORK_APPRENTICESHIP'), nsr)
  assert.match(highSchool.title_conclusion, /ampliou matrículas e turmas/u)
  assert.deepEqual(highSchool.key_figures.map((item) => item.value), ['+41', '−4.878'])
  assert.deepEqual(eja.key_figures.map((item) => item.value), ['+2,648 p.p.', '−2,605 p.p.'])
  assert.deepEqual(logistics.key_figures.map((item) => item.value), ['17 → 722', 'zero observado'])
  assert.deepEqual(youth.key_figures.map((item) => item.value), ['104 → 172', '174 / 219 = 79,452%'])

  const logisticsEvidence = story('STORY_LOGISTICS_EPT').primary_evidence.by_entity.find((item) => item.entity_id === nsr)
  assert.equal(logisticsEvidence.occupation.absolute_change, 705)
  assert.equal(logisticsEvidence.occupation_change_share_percent, 38.71499176276771)
  assert.equal(logisticsEvidence.ept.final_value, 0)
  assert.equal(logisticsEvidence.ept.availability_state, 'observed_zero')
  const logisticsContext = story('STORY_LOGISTICS_EPT').secondary_evidence.by_entity.find((item) => item.entity_id === nsr)
  assert.deepEqual([logisticsContext.youth_work_18_24.initial_value, logisticsContext.youth_work_18_24.final_value], [1117, 1638])
  assert.equal(logisticsContext.youth_regional_change_contribution_percent, 45.58180227471566)
})

test('contextos condicionais preservam estabilidade rural e reclassificação descritiva do AEE', () => {
  const rural = bundle.conditional_contexts.find((item) => item.context_id === 'CONTEXT_RURALITY_TRANSPORT')
  const special = bundle.conditional_contexts.find((item) => item.context_id === 'CONTEXT_SPECIAL_AEE')
  const ruralNsr = rural.variants.find((item) => item.entity_id === '4313375')
  const specialNsr = special.variants.find((item) => item.entity_id === '4313375')
  assert.equal(rural.editorial_story_state, 'CONDITIONAL_EXPANDED')
  assert.equal(ruralNsr.rural_enrollments.absolute_change, 55)
  assert.equal(ruralNsr.rural_schools.absolute_change, 0)
  assert.equal(ruralNsr.rural_high_school_enrollments.absolute_change, -90)
  assert.match(ruralNsr.summary, /permaneceu estável/u)
  assert.equal(ruralNsr.pnate_2026.planning_only, true)
  assert.equal(special.editorial_story_state, 'DESCRIPTIVE_CONTEXT_ONLY')
  assert.equal(specialNsr.interpretation_boundary, 'Matrículas da educação especial e escolas que informam AEE cresceram, mas os dados não medem cobertura nem atendimento das mesmas pessoas.')
})

test('texto editorial visível não expõe identificadores ou jargão técnico', () => {
  const visibleTexts = [
    ...bundle.directions.flatMap((item) => [item.title, item.manager_question]),
    ...bundle.stories.flatMap((storyValue) => [
      storyValue.title_conclusion,
      storyValue.integrated_summary,
      storyValue.regional_read,
      storyValue.planning_implication,
      storyValue.interpretation_boundary,
      ...storyValue.selected_municipality_read.variants.flatMap((item) => [item.title_conclusion, item.integrated_summary, item.selected_municipality_read]),
    ]),
    ...bundle.conditional_contexts.flatMap((context) => context.variants.flatMap((item) => [item.title, item.summary, item.interpretation_boundary ?? ''])),
  ].join('\n')
  for (const pattern of [
    /\bR[1-8]\b/u,
    /\bTVD\b/u,
    /\brho\b/iu,
    /\bfixed effects\b/iu,
    /\bregress(?:ão|ion)\b/iu,
    /\bshift[- ]share\b/iu,
    /\bHHI\b/u,
    /\bGate(?: 11)?\b/iu,
    /\bschema\b/iu,
  ]) assert.doesNotMatch(visibleTexts, pattern)
})
