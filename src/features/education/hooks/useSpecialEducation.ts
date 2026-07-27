import { loadSpecialEducationManifest, loadSpecialEducationMunicipality } from '../../../data/specialEducation'
import { useAsyncData } from '../../../utils/useAsyncData'
import { buildSpecialEducationViewModel } from '../specialEducationViewModel'

export function useSpecialEducation(municipalityId: string | null, enabled: boolean) {
  return useAsyncData(async () => {
    if (!enabled || !municipalityId) return null
    const [manifest, document] = await Promise.all([
      loadSpecialEducationManifest(),
      loadSpecialEducationMunicipality(municipalityId),
    ])
    return {
      document,
      manifest,
      viewModel: buildSpecialEducationViewModel(document),
    }
  }, [enabled, municipalityId])
}

