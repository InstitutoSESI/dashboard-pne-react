import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { build } from 'vite'
import { createViteConfig } from '../../vite.config.js'

const repoRoot = fileURLToPath(new URL('../..', import.meta.url))

function normalized(value) {
  return value.replaceAll('\\', '/')
}

async function appOnlyGraph(stateCode, experience) {
  const moduleIds = new Set()
  const profileConfig = createViteConfig(
    { command: 'build', mode: 'app-only' },
    { PLATFORM_STATE: stateCode, PLATFORM_EXPERIENCE: experience },
  )
  const result = await build({
    ...profileConfig,
    configFile: false,
    root: repoRoot,
    logLevel: 'silent',
    plugins: [
      ...profileConfig.plugins,
      {
        name: 'capture-experience-module-graph',
        generateBundle() {
          for (const moduleId of this.getModuleIds()) moduleIds.add(normalized(moduleId))
        },
      },
    ],
    build: {
      ...profileConfig.build,
      emptyOutDir: false,
      write: false,
    },
  })
  const outputs = (Array.isArray(result) ? result : [result]).flatMap((item) => item.output)
  return {
    moduleIds: [...moduleIds],
    outputFiles: outputs.map((item) => normalized(item.fileName)),
  }
}

function hasModule(graph, suffix) {
  return graph.moduleIds.some((moduleId) => moduleId.endsWith(suffix))
}

function assertNoPublicData(graph) {
  assert.equal(graph.moduleIds.some((moduleId) => moduleId.includes('/public/data/')), false)
  assert.equal(graph.outputFiles.some((fileName) => fileName.startsWith('data/')), false)
}

test('grafos app-only isolam RS atual, RS PME e AL atual no Vite real', async () => {
  const [rsCurrent, rsPme, alCurrent] = await Promise.all([
    appOnlyGraph('RS', 'atual'),
    appOnlyGraph('RS', 'pme'),
    appOnlyGraph('AL', 'atual'),
  ])

  for (const graph of [rsCurrent, alCurrent]) {
    assert.equal(hasModule(graph, '/src/main.jsx'), true)
    assert.equal(hasModule(graph, '/src/App.tsx'), true)
    assert.equal(hasModule(graph, '/src/main-pme.tsx'), false)
    assert.equal(hasModule(graph, '/src/experiences/pme/PmeApp.tsx'), false)
    assert.equal(hasModule(graph, '/src/experiences/pme/PmeShell.tsx'), false)
    assert.equal(hasModule(graph, '/src/experiences/pme/styles/pme.css'), false)
    assertNoPublicData(graph)
  }

  assert.equal(hasModule(rsPme, '/src/main-pme.tsx'), true)
  assert.equal(hasModule(rsPme, '/src/experiences/pme/PmeApp.tsx'), true)
  assert.equal(hasModule(rsPme, '/src/experiences/pme/PmeShell.tsx'), true)
  assert.equal(hasModule(rsPme, '/src/experiences/pme/styles/pme.css'), true)
  assert.equal(hasModule(rsPme, '/src/main.jsx'), false)
  assert.equal(hasModule(rsPme, '/src/App.tsx'), false)
  assert.equal(hasModule(rsPme, '/src/App.css'), false)
  assertNoPublicData(rsPme)
})
