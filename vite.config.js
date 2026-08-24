import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { loadStateBuildProfile } from './scripts/lib/state-build-profile.mjs'
import { statePublicAssetsPlugin } from './scripts/lib/state-public-assets.mjs'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const appOnly = command === 'build' && mode === 'app-only'
  const profile = loadStateBuildProfile({
    repoRoot: fileURLToPath(new URL('.', import.meta.url)),
    stateCode: process.env.PLATFORM_STATE,
    requirePublication: !appOnly,
  })

  return {
    plugins: [
      react(),
      ...(!appOnly ? [statePublicAssetsPlugin(profile)] : []),
    ],
    publicDir: command === 'serve' ? 'public' : false,
    define: {
      __ACTIVE_STATE_CONFIG__: JSON.stringify(profile.stateConfig),
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
})
