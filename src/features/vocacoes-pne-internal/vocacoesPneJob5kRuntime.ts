import type {
  Job5KStory,
  VocacoesPneJob5KBundle,
} from './vocacoesPneJob5kTypes'

function invariant(condition: unknown, message: string): asserts condition {
  if (!condition) throw new TypeError(`Bundle Job 5K inválido: ${message}`)
}

function record(value: unknown, label: string): Record<string, unknown> {
  invariant(value !== null && typeof value === 'object' && !Array.isArray(value), `${label} deve ser objeto`)
  return value as Record<string, unknown>
}

function textualIbgeCode(value: unknown): value is string {
  return typeof value === 'string' && /^[0-9]{7}$/u.test(value)
}

export function parseVocacoesPneJob5K(raw: unknown): VocacoesPneJob5KBundle {
  const bundle = record(raw, 'raiz')
  invariant(bundle.schema_version === 'vocacoes-pne-insight-first-bundle-v1', 'schemaVersion')
  const meta = record(bundle.meta, 'meta')
  invariant(meta.job_id === 'v7-job5k', 'jobId')
  invariant(meta.internal_only === true, 'bundle deve ser interno')
  invariant(meta.gate11 === 'CLOSED', 'Gate 11 deve permanecer fechado')
  invariant(meta.public_narrative_authorized === false, 'narrativa pública não autorizada')
  invariant(meta.publication_authorized === false, 'publicação não autorizada')
  invariant(meta.public_data_writes_authorized === false, 'public/data deve permanecer somente leitura')
  invariant(meta.manager_validation_started === false, 'validação da gestora não iniciada')
  invariant(Array.isArray(bundle.municipalities) && bundle.municipalities.length === 10, 'dez municípios')
  const codes = bundle.municipalities.map((value) => {
    const municipality = record(value, 'município')
    invariant(textualIbgeCode(municipality.ibgeCode), 'código IBGE textual de sete dígitos')
    invariant(typeof municipality.name === 'string' && municipality.name.length > 0, 'nome municipal')
    return municipality.ibgeCode
  })
  invariant(new Set(codes).size === 10, 'dez códigos municipais únicos')
  invariant(bundle.fallback_municipality_ibge_code === '4313375', 'fallback Nova Santa Rita')
  invariant(Array.isArray(bundle.directions) && bundle.directions.length === 2, 'duas direções')
  invariant(Array.isArray(bundle.stories) && bundle.stories.length === 4, 'quatro histórias')
  const storyIds = new Set<string>()
  for (const value of bundle.stories) {
    const story = record(value, 'história')
    invariant(typeof story.story_id === 'string' && !storyIds.has(story.story_id), 'storyId único')
    storyIds.add(story.story_id)
    invariant(story.network_scope === 'total_all_dependencies', 'rede total')
    invariant(story.manager_review_state === 'pending', 'revisão da gestora pendente')
    invariant(story.public_narrative_authorized === false, 'história não pública')
    const selected = record(story.selected_municipality_read, 'variantes municipais')
    invariant(selected.municipality_overrides === false, 'sem perfis municipais manuais')
    invariant(Array.isArray(selected.variants) && selected.variants.length === 11, 'Vale + dez variantes')
    const entities = selected.variants.map((variantValue) => {
      const variant = record(variantValue, 'variante')
      invariant(typeof variant.title_conclusion === 'string' && variant.title_conclusion.length > 0, 'título conclusivo')
      invariant(typeof variant.integrated_summary === 'string' && variant.integrated_summary.length > 0, 'síntese integrada')
      invariant(Array.isArray(variant.key_figures) && variant.key_figures.length >= 1 && variant.key_figures.length <= 2, 'uma ou duas cifras essenciais')
      invariant(variant.entity_id === 'REGION_VALE_DO_SINOS' || textualIbgeCode(variant.entity_id), 'identidade de variante')
      if (variant.entity_id !== 'REGION_VALE_DO_SINOS') {
        invariant(variant.municipality_ibge_code === variant.entity_id, 'variante municipal × IBGE')
      }
      return variant.entity_id
    })
    invariant(new Set(entities).size === 11, 'onze entidades únicas por história')
  }
  invariant(storyIds.has('STORY_HIGH_SCHOOL_TRAJECTORY'), 'história do ensino médio')
  invariant(storyIds.has('STORY_EJA_TERRITORY'), 'história da EJA')
  invariant(storyIds.has('STORY_LOGISTICS_EPT'), 'história logística/EPT')
  invariant(storyIds.has('STORY_YOUTH_WORK_APPRENTICESHIP'), 'história trabalho/aprendizagem')
  invariant(Array.isArray(bundle.conditional_contexts) && bundle.conditional_contexts.length === 2, 'dois contextos condicionais')
  const normalization = record(bundle.normalization, 'normalização')
  invariant(normalization.regional_evidence_stored_once === true, 'evidência regional armazenada uma vez')
  invariant(normalization.municipal_variants_generated_by_rules === true, 'variantes municipais por regras')
  invariant(normalization.manual_municipality_profiles === false, 'sem perfil manual por município')
  invariant(normalization.ranking_used === false, 'sem ranking')
  const counts = record(bundle.counts, 'contagens')
  invariant(counts.story_variant_count === 44, '44 variantes principais')
  invariant(counts.conditional_variant_count === 22, '22 variantes condicionais')
  return raw as VocacoesPneJob5KBundle
}

export function storyVariant(story: Job5KStory, entityId: string) {
  const variant = story.selected_municipality_read.variants.find((item) => item.entity_id === entityId)
  if (!variant) throw new TypeError(`Bundle Job 5K inválido: variante ausente em ${story.story_id}/${entityId}`)
  return variant
}
