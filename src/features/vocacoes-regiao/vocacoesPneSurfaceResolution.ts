export type VocacoesPneLoadStatus = 'idle' | 'loading' | 'ready' | 'error'
export type VocacoesPneSurface = 'loading' | 'advanced' | 'official_previous' | 'legacy'

export function resolveVocacoesPneSurface({
  eligible,
  advancedRequested,
  advancedStatus,
  advancedScopeSupported,
  officialStatus,
  officialScopeSupported,
}: {
  readonly eligible: boolean
  readonly advancedRequested: boolean
  readonly advancedStatus: VocacoesPneLoadStatus
  readonly advancedScopeSupported: boolean
  readonly officialStatus: VocacoesPneLoadStatus
  readonly officialScopeSupported: boolean
}): VocacoesPneSurface {
  if (!eligible) return 'legacy'
  if (advancedRequested) {
    if (advancedStatus === 'idle' || advancedStatus === 'loading') return 'loading'
    if (advancedStatus === 'ready' && advancedScopeSupported) return 'advanced'
  }
  if (officialStatus === 'idle' || officialStatus === 'loading') return 'loading'
  if (officialStatus === 'ready' && officialScopeSupported) return 'official_previous'
  return 'legacy'
}
