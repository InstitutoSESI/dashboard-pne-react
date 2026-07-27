import { useAsyncData } from '../../../utils/useAsyncData'
import {
  loadHigherEducationManifest,
  loadHigherEducationMunicipality,
} from '../../../data/higherEducationData'
import { buildHigherEducationViewModel } from '../higherEducationViewModel'

export function useHigherEducation(municipalityId: string | null, enabled: boolean) {
  return useAsyncData(async () => {
    if (!enabled || !municipalityId) return null
    const [manifest, document] = await Promise.all([
      loadHigherEducationManifest(),
      loadHigherEducationMunicipality(municipalityId),
    ])
    return {
      document,
      manifest,
      viewModel: buildHigherEducationViewModel(manifest, document),
    }
  }, [enabled, municipalityId])
}
