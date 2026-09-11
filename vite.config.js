import process from 'node:process'
import { existsSync, realpathSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { loadExperienceBuildProfile } from './scripts/lib/experience-build-profile.mjs'
import { statePublicAssetsPlugin } from './scripts/lib/state-public-assets.mjs'

// https://vite.dev/config/
export function createViteConfig({ command, mode }, environment = process.env) {
  const appOnly = command === 'build' && mode === 'app-only'
  const repoRoot = fileURLToPath(new URL('.', import.meta.url))
  const dependencyRoot = fileURLToPath(new URL('node_modules', import.meta.url))
  const profile = loadExperienceBuildProfile({
    repoRoot,
    stateCode: environment.PLATFORM_STATE,
    experience: environment.PLATFORM_EXPERIENCE,
    requirePublication: !appOnly,
  })

  return {
    // Independent dev profiles must not replace one another's dependency cache.
    cacheDir: fileURLToPath(new URL(`.tmp/vite/${profile.stateConfig.stateCode.toLowerCase()}-${profile.experience}`, import.meta.url)),
    // Worktrees may reuse installed dependencies through a junction or symlink.
    server: { fs: { allow: [repoRoot, ...(existsSync(dependencyRoot) ? [realpathSync(dependencyRoot)] : [])] } },
    plugins: [
      react(),
      ...(!appOnly ? [statePublicAssetsPlugin(profile)] : []),
    ],
    publicDir: command === 'serve' ? 'public' : false,
    resolve: {
      alias: {
        '@platform-entry': profile.entryPath,
      },
    },
    define: {
      __ACTIVE_STATE_CONFIG__: JSON.stringify(profile.stateConfig),
      __ACTIVE_EXPERIENCE_CONFIG__: JSON.stringify(profile.experienceConfig),
      __ACTIVE_PUBLICATION_CONFIG__: JSON.stringify({
        schemaVersion: profile.publication.schemaVersion,
        stateCode: profile.publication.stateCode,
        analyticsStatus: profile.publication.analyticsStatus,
        analyticsMessage: profile.publication.analyticsMessage,
        enabledProducts: profile.publication.enabledProducts,
      }),
      // null quando a UF ativa não tem mapa regional: sem mapa, sem análise regional.
      __ACTIVE_REGIONS_CONFIG__: JSON.stringify(profile.regionsConfig),
    },
    build: {
      copyPublicDir: false,
    },
  }
}

export default defineConfig(createViteConfig)
