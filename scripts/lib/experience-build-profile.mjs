import path from 'node:path'
import {
  DEFAULT_PLATFORM_STATE,
  loadStateBuildProfile,
  normalizePlatformState,
} from './state-build-profile.mjs'

export const DEFAULT_PLATFORM_EXPERIENCE = 'atual'
export const PLATFORM_EXPERIENCES = Object.freeze(['atual', 'pme'])
export const EXPERIENCE_CONFIG_SCHEMA_VERSION = 'experience-config-v1'

const ENTRY_MODULE_BY_EXPERIENCE = Object.freeze({
  atual: 'src/main.jsx',
  pme: 'src/main-pme.tsx',
})

export function normalizePlatformExperience(value = DEFAULT_PLATFORM_EXPERIENCE) {
  if (typeof value !== 'string') {
    throw new Error('PLATFORM_EXPERIENCE deve ser texto com um valor reconhecido.')
  }
  const normalized = value.trim().toLowerCase()
  if (!PLATFORM_EXPERIENCES.includes(normalized)) {
    throw new Error(
      `PLATFORM_EXPERIENCE inválida ${JSON.stringify(value)}; use ${PLATFORM_EXPERIENCES.join(' ou ')}.`,
    )
  }
  return normalized
}

function assertStateExperienceCompatibility(stateCode, experience) {
  if (experience === 'pme' && stateCode !== 'RS') {
    throw new Error('A experiência PME está disponível somente para a UF RS.')
  }
}

export function loadExperienceBuildProfile({
  repoRoot = process.cwd(),
  stateCode = process.env.PLATFORM_STATE ?? DEFAULT_PLATFORM_STATE,
  experience = process.env.PLATFORM_EXPERIENCE,
  requirePublication = true,
} = {}) {
  const normalizedStateCode = normalizePlatformState(stateCode)
  const normalizedExperience = normalizePlatformExperience(experience)
  assertStateExperienceCompatibility(normalizedStateCode, normalizedExperience)
  const stateProfile = loadStateBuildProfile({
    repoRoot,
    stateCode: normalizedStateCode,
    requirePublication,
  })

  const entryModule = ENTRY_MODULE_BY_EXPERIENCE[normalizedExperience]
  return Object.freeze({
    ...stateProfile,
    experience: normalizedExperience,
    experienceConfig: Object.freeze({
      schemaVersion: EXPERIENCE_CONFIG_SCHEMA_VERSION,
      stateCode: stateProfile.stateConfig.stateCode,
      experience: normalizedExperience,
    }),
    entryModule,
    entryPath: path.join(path.resolve(repoRoot), entryModule),
  })
}
