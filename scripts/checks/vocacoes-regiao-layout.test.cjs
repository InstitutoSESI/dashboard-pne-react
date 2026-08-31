const { runVocacoesPnePageE2e } = require('./vocacoes-pne-page-e2e.test.cjs')

runVocacoesPnePageE2e({ layoutOnly: true }).catch((error) => {
  console.error(error instanceof Error ? error.stack : String(error))
  process.exitCode = 1
})
