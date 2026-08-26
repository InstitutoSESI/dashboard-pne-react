/*
 * Corpus adversarial permanente da camada de conclusões (V2-D8).
 *
 * Cada ataque parte de um documento 2.5.0 válido e altera somente o vetor que
 * pretende medir. `gate` diz qual fronteira precisa recusar primeiro: a guarda
 * lexical severa ou o contrato estrutural que recompõe as provas.
 */

const byKind = (document, label) =>
  document.synthesis.items.find((item) => item.kindLabel === label)

export const SYNTHESIS_ATTACKS = Object.freeze([
  {
    id: 'SYN-A01-causal',
    gate: 'language',
    region: 'central',
    mutate(document) {
      byKind(document, 'De posição na comparação estadual').statement =
        'Conclui-se que a queda da renda causou a redução das matrículas.'
    },
  },
  {
    id: 'SYN-A02-sem-abridor',
    gate: 'contract',
    region: 'central',
    mutate(document) {
      const item = byKind(document, 'Do observado')
      item.statement = item.statement.replace('Conclui-se do observado que, ', '')
    },
  },
  {
    id: 'SYN-A03-numero-sem-ancora',
    gate: 'contract',
    region: 'central',
    mutate(document) {
      const item = byKind(document, 'Do observado')
      item.statement = item.statement.replace(/\.$/u, ' e 999.')
    },
  },
  {
    id: 'SYN-A04-t3-sem-quatro-ancoras',
    gate: 'contract',
    region: 'noroeste',
    mutate(document) {
      const item = byKind(document, 'Sustentado nos quatro cenários')
      const commonBases = new Set(
        document.synthesis.items
          .filter((candidate) => candidate.kindLabel === 'Sustentado nos quatro cenários')
          .map((candidate) => candidate.basisLabel),
      )
      item.basisLabel = document.territoryPortrait.series
        .find((serie) => !commonBases.has(serie.label)).label
    },
  },
  {
    id: 'SYN-A05-t4-fora-da-intersecao',
    gate: 'contract',
    region: 'vale-do-rio-pardo',
    mutate(document) {
      const item = byKind(document, 'Frentes da agenda mobilizadas')
      item.statement = item.statement.replace(
        /\.$/u,
        ', Formação e valorização dos profissionais do ensino.',
      )
    },
  },
  {
    id: 'SYN-A06-sintese-ausente',
    gate: 'contract',
    region: 'central',
    mutate(document) {
      delete document.synthesis
    },
  },
  {
    id: 'SYN-A07-t3-em-regiao-sem-cenarios',
    gate: 'contract',
    region: 'central',
    mutate(document, documents) {
      document.synthesis.items.push(structuredClone(
        byKind(documents.noroeste, 'Sustentado nos quatro cenários'),
      ))
    },
  },
  {
    id: 'SYN-A08-reversor-mas',
    gate: 'language',
    region: 'central',
    mutate(document) {
      const item = byKind(document, 'De posição na comparação estadual')
      item.statement = item.statement.replace(/\.$/u, ', mas o resultado explica a matrícula.')
    },
  },
])

