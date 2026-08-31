import promotionRaw from './generated/vocacoesPneOfficialPromotion.json'
import type { VocacoesDocument } from './vocacoesRegiaoTypes'
import type { VocacoesPneLoadedBundle } from '../vocacoes-pne-internal/vocacoesPneUiV2Types'

const SHA256_PATTERN = /^[a-f0-9]{64}$/u

export interface VocacoesPneOfficialPromotionContract {
  schemaVersion: 'vocacoes-pne-official-promotion-v1'
  contractVersion: '1.0.0'
  decisionDate: string
  authorizationBasis: 'explicit_user_request_for_official_route_promotion'
  officialRoute: 'vocacoes-regiao'
  stateCode: 'RS'
  regionSlug: 'vale-do-sinos'
  regionEntityId: 'REGION_VALE_DO_SINOS'
  municipalityCount: 10
  publicationScope: 'official_aggregate_observational_pilot'
  legacyContentVersion: string
  fallbackNarrativeContractVersion: '1.5.0'
  sourceBundleHashes: {
    job5iCoreSha256: string
    job5iSeriesSha256: string
    job5kStoriesSha256: string
  }
  evidencePolicy: {
    causalClaimsAllowed: false
    samePersonClaimsAllowed: false
    negativeFindingsVisibleAsBoundaries: true
    mainRelationCount: 4
    agendaCount: 3
    supportingRelationIds: [
      'R6_SOCIOECONOMIC_TRAJECTORY',
      'R7_RURALITY_TRANSPORT',
      'R8_SPECIAL_AEE',
    ]
    publicRelationStates: string[]
  }
  excludedCapabilities: string[]
  publicDataWritesRequired: false
}

function invariant(condition: unknown, message: string): asserts condition {
  if (!condition) throw new TypeError(`Promoção oficial Vocações × PNE inválida: ${message}`)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function exactKeys(value: Record<string, unknown>, expected: readonly string[], label: string) {
  const actual = Object.keys(value).sort()
  const canonical = [...expected].sort()
  invariant(
    actual.length === canonical.length
      && actual.every((key, index) => key === canonical[index]),
    `${label} contém propriedades inesperadas`,
  )
}

export function parseVocacoesPneOfficialPromotion(
  raw: unknown,
): VocacoesPneOfficialPromotionContract {
  invariant(isRecord(raw), 'raiz deve ser objeto')
  exactKeys(raw, [
    'schemaVersion', 'contractVersion', 'decisionDate', 'authorizationBasis',
    'officialRoute', 'stateCode', 'regionSlug', 'regionEntityId', 'municipalityCount',
    'publicationScope', 'legacyContentVersion', 'fallbackNarrativeContractVersion',
    'sourceBundleHashes', 'evidencePolicy', 'excludedCapabilities',
    'publicDataWritesRequired',
  ], 'raiz')
  invariant(raw.schemaVersion === 'vocacoes-pne-official-promotion-v1', 'schemaVersion')
  invariant(raw.contractVersion === '1.0.0', 'contractVersion')
  invariant(raw.decisionDate === '2026-08-30', 'data da decisão')
  invariant(raw.authorizationBasis === 'explicit_user_request_for_official_route_promotion', 'base de autorização')
  invariant(raw.officialRoute === 'vocacoes-regiao', 'rota oficial')
  invariant(raw.stateCode === 'RS', 'estado')
  invariant(raw.regionSlug === 'vale-do-sinos', 'região')
  invariant(raw.regionEntityId === 'REGION_VALE_DO_SINOS', 'identidade regional')
  invariant(raw.municipalityCount === 10, 'dez municípios')
  invariant(raw.publicationScope === 'official_aggregate_observational_pilot', 'escopo da promoção')
  invariant(typeof raw.legacyContentVersion === 'string' && SHA256_PATTERN.test(raw.legacyContentVersion), 'versão legada')
  invariant(raw.fallbackNarrativeContractVersion === '1.5.0', 'contrato de fallback')
  invariant(raw.publicDataWritesRequired === false, 'promoção não pode exigir escrita em public/data')

  invariant(isRecord(raw.sourceBundleHashes), 'hashes dos bundles')
  exactKeys(raw.sourceBundleHashes, [
    'job5iCoreSha256', 'job5iSeriesSha256', 'job5kStoriesSha256',
  ], 'sourceBundleHashes')
  for (const hash of Object.values(raw.sourceBundleHashes)) {
    invariant(typeof hash === 'string' && SHA256_PATTERN.test(hash), 'SHA-256 de bundle')
  }

  invariant(isRecord(raw.evidencePolicy), 'política de evidência')
  exactKeys(raw.evidencePolicy, [
    'causalClaimsAllowed', 'samePersonClaimsAllowed', 'negativeFindingsVisibleAsBoundaries',
    'mainRelationCount', 'agendaCount', 'supportingRelationIds', 'publicRelationStates',
  ], 'evidencePolicy')
  invariant(raw.evidencePolicy.causalClaimsAllowed === false, 'claims causais devem permanecer proibidos')
  invariant(raw.evidencePolicy.samePersonClaimsAllowed === false, 'claims de mesma pessoa devem permanecer proibidos')
  invariant(raw.evidencePolicy.negativeFindingsVisibleAsBoundaries === true, 'resultados negativos devem virar fronteira visível')
  invariant(raw.evidencePolicy.mainRelationCount === 4, 'quatro relações principais')
  invariant(raw.evidencePolicy.agendaCount === 3, 'três agendas')
  invariant(
    Array.isArray(raw.evidencePolicy.supportingRelationIds)
      && raw.evidencePolicy.supportingRelationIds.join('|')
        === 'R6_SOCIOECONOMIC_TRAJECTORY|R7_RURALITY_TRANSPORT|R8_SPECIAL_AEE',
    'relações complementares',
  )
  invariant(Array.isArray(raw.evidencePolicy.publicRelationStates), 'estados públicos de relação')
  invariant(Array.isArray(raw.excludedCapabilities) && raw.excludedCapabilities.length === 4, 'capacidades excluídas')
  return raw as unknown as VocacoesPneOfficialPromotionContract
}

export const VOCACOES_PNE_OFFICIAL_PROMOTION = parseVocacoesPneOfficialPromotion(promotionRaw)

export function matchesVocacoesPneOfficialPromotion(
  legacyDocument: VocacoesDocument,
  activeStateCode: string,
): boolean {
  const contract = VOCACOES_PNE_OFFICIAL_PROMOTION
  return activeStateCode === contract.stateCode
    && legacyDocument.region.uf === contract.stateCode
    && legacyDocument.region.slug === contract.regionSlug
    && legacyDocument.region.municipalityCount === contract.municipalityCount
    && legacyDocument.contentVersion === contract.legacyContentVersion
}

export function assertVocacoesPneOfficialBundle(bundle: VocacoesPneLoadedBundle): void {
  const contract = VOCACOES_PNE_OFFICIAL_PROMOTION
  invariant(bundle.core.region.slug === contract.regionSlug, 'slug do Job 5I')
  invariant(bundle.core.region.entityId === contract.regionEntityId, 'entidade regional do Job 5I')
  invariant(bundle.core.region.stateCode === contract.stateCode, 'estado do Job 5I')
  invariant(bundle.core.municipalities.length === contract.municipalityCount, 'cobertura municipal do Job 5I')
  invariant(bundle.insights.region.slug === contract.regionSlug, 'slug do Job 5K')
  invariant(bundle.insights.region.entity_id === contract.regionEntityId, 'entidade regional do Job 5K')
  invariant(bundle.insights.counts.primary_story_count === contract.evidencePolicy.mainRelationCount, 'relações principais do Job 5K')
  invariant(bundle.insights.counts.relation_count === 8, 'oito relações julgadas no Job 5J')
  invariant(bundle.insights.conditional_contexts.length === 2, 'dois contextos condicionais')
  invariant(bundle.insights.stories.every((story) => story.interpretation_boundary.trim().length > 0), 'fronteiras de interpretação')
}
